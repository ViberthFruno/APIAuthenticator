"""
API Integration Context - Use Cases (Application Layer)
Casos de uso para interactuar con la API externa
"""

import time
from datetime import datetime
from typing import Optional

from api_integration.application.dtos import GetPreingresoInput, \
    GetPreingresoOutput, HealthCheckResult
from api_integration.domain.entities import ApiResponse
from api_integration.domain.exceptions import (
    APIException,
    ApplicationException
)
from api_integration.infrastructure.retry_policy import RetryPolicy
from api_integration.ports.interfaces import (
    IApiIfrProRepository
)
from logger import get_logger, log_execution_time

logger = get_logger(__name__)


# ===== Use Cases =====

class GetPreingresoUseCase:
    """
    Caso de uso: Obtener preingreso por número de boleta
    
    Responsabilidades:
    - Buscar preingreso en la API
    - Procesar respuesta
    - Manejar caso de no encontrado
    """

    def __init__(self, api_ifrpro_repository: IApiIfrProRepository):
        self.repository = api_ifrpro_repository
        self.logger = logger.bind(use_case="GetPreingreso")

    @log_execution_time
    async def execute(
            self,
            input_dto: GetPreingresoInput
    ) -> GetPreingresoOutput:
        """
        Ejecuta el caso de uso
        
        Args:
            input_dto: Datos de entrada
            
        Returns:
            GetPreingresoOutput con el resultado
        """
        self.logger.info(
            "Getting preingreso",
            numero_boleta=input_dto.numero_boleta
        )

        try:
            # Buscar en la API
            response = await self.repository.consultar_boleta(
                input_dto.numero_boleta
            )

            if response is None:
                self.logger.info(
                    "Preingreso not found",
                    numero_boleta=input_dto.numero_boleta
                )

                return GetPreingresoOutput(
                    found=False,
                    response=None,
                    data=None
                )

            # Validar respuesta
            response.validate_success()

            self.logger.info(
                "Preingreso found",
                numero_boleta=input_dto.numero_boleta,
                response_time_ms=response.response_time_ms
            )

            return GetPreingresoOutput(
                found=True,
                response=response,
                data=response.body
            )

        except APIException as e:
            self.logger.error(
                "Error getting preingreso",
                numero_boleta=input_dto.numero_boleta,
                error=str(e)
            )
            raise ApplicationException(
                f"Error al obtener preingreso: {str(e)}",
                code="GET_PREINGRESO_ERROR"
            ) from e


class HealthCheckUseCase:
    """
    Caso de uso para verificar la salud de la API.

    Realiza una petición GET al endpoint de health check de la API
    y retorna el estado de salud del servicio.

    Principios SOLID aplicados:
    - Single Responsibility: Solo verifica la salud de la API
    - Dependency Inversion: Depende de abstracciones (repository, retry_policy)
    - Open/Closed: Extensible sin modificar el código existente
    """

    def __init__(
            self,
            api_ifrpro_repository: IApiIfrProRepository,
            retry_policy: Optional[RetryPolicy] = None
    ):
        """
        Inicializa el caso de uso.

        Args:
            api_ifrpro_repository: Repositorio para comunicación con la API
            retry_policy: Política de reintentos (opcional)
        """
        self.repository = api_ifrpro_repository
        self.retry_policy = retry_policy

    async def execute(self, endpoint: str = "/") -> HealthCheckResult:
        """
        Ejecuta la verificación de salud de la API.

        Args:
            endpoint: Endpoint a verificar (default: /health)

        Returns:
            HealthCheckResult con el estado de la API

        Seguridad:
        - Timeout automático para evitar bloqueos
        - No expone información sensible en logs
        - Manejo seguro de excepciones
        """
        start_time = time.time()
        timestamp = datetime.now()

        logger.info(f"Probando conexión API iFR Pro en endpoint: {endpoint}")

        try:
            # Ejecutar la petición con retry policy si está disponible
            if self.retry_policy:
                response = await self._execute_with_retry(endpoint)
            else:
                response = await self._execute_request(endpoint)

            # Calcular tiempo de respuesta
            response_time = (time.time() - start_time) * 1000

            # Verificar el resultado
            if response and response.status_code in [200, 204]:
                logger.info(f"Health check exitoso: {response.status_code}")
                return HealthCheckResult(
                    is_healthy=True,
                    status_code=response.status_code,
                    response_time_ms=response_time,
                    message="API está funcionando correctamente",
                    timestamp=timestamp,
                    endpoint=endpoint
                )
            else:
                status_code = response.status_code if response else None
                logger.warning(f"Health check falló con status: {status_code}")
                return HealthCheckResult(
                    is_healthy=False,
                    status_code=status_code,
                    response_time_ms=response_time,
                    message=f"API respondió con status code: {status_code}",
                    timestamp=timestamp,
                    error=f"Status code inesperado: {status_code}",
                    endpoint=endpoint
                )

        except ConnectionError as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Error de conexión en health check: {str(e)}")
            return HealthCheckResult(
                is_healthy=False,
                status_code=None,
                response_time_ms=response_time,
                message="No se pudo conectar con la API",
                timestamp=timestamp,
                error=f"Error de conexión: {str(e)}",
                error_type=type(e).__name__,
                endpoint=endpoint
            )

        except TimeoutError as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Timeout en health check: {str(e)}")
            return HealthCheckResult(
                is_healthy=False,
                status_code=None,
                response_time_ms=response_time,
                message="La API no respondió a tiempo",
                timestamp=timestamp,
                error=f"Timeout: {str(e)}",
                error_type=type(e).__name__,
                endpoint=endpoint
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Error inesperado en health check: {str(e)}")
            return HealthCheckResult(
                is_healthy=False,
                status_code=None,
                response_time_ms=response_time,
                message="Error inesperado al verificar la API",
                timestamp=timestamp,
                error=str(e),
                error_type=type(e).__name__,
                endpoint=endpoint
            )

    async def _execute_request(self, endpoint: str) -> ApiResponse:
        """
        Ejecuta la petición HTTP al endpoint.

        Args:
            endpoint: Endpoint a consultar

        Returns:
            Response object o None si falla
        """
        try:
            # Usar el método GET del repositorio
            response = await self.repository.health_check()
            return response
        except Exception as e:
            logger.error(f"Error ejecutando petición GET a {endpoint}: {e}")
            raise

    async def _execute_with_retry(self, endpoint: str) -> ApiResponse | None:
        """
        Ejecuta la petición con política de reintentos.

        Args:
            endpoint: Endpoint a consultar

        Returns:
            Response object o None si falla después de todos los reintentos
        """
        attempt = 0
        last_exception = None

        while attempt < self.retry_policy.max_retries:
            try:
                attempt += 1
                logger.debug(f"Health check intento {attempt}/{self.retry_policy.max_retries}")

                response = await self._execute_request(endpoint)

                # Si la respuesta es exitosa, retornar inmediatamente
                if response and response.status_code in [200, 204]:
                    if attempt > 1:
                        logger.info(f"Health check exitoso después de {attempt} intentos")
                    return response

                # Si el status code indica que no se debe reintentar
                if response and not self.retry_policy.should_retry(response.status_code):
                    logger.debug(f"Status {response.status_code} - no se reintenta")
                    return response

            except Exception as e:
                last_exception = e
                logger.warning(f"Intento {attempt} falló: {str(e)}")

            # Esperar antes del siguiente reintento (excepto en el último)
            if attempt < self.retry_policy.max_retries:
                delay = self.retry_policy.get_delay(attempt)
                logger.debug(f"Esperando {delay}s antes del siguiente intento")
                time.sleep(delay)

        # Si llegamos aquí, todos los reintentos fallaron
        logger.error(f"Health check falló después de {attempt} intentos")
        if last_exception:
            raise last_exception

        return None
