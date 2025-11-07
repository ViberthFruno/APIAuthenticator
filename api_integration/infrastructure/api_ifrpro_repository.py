# api_ifrpro_repository.py
"""
API Integration Context - Infrastructure: PreingresoRepository
Implementación del repositorio de preingresos usando la API externa
"""
import uuid
from typing import Optional

from api_integration.domain.entities import (
    ApiRequest,
    ApiResponse,
    PreingresoData,
    ApiCredentials,
    Endpoint,
    RequestMethod
)
from api_integration.domain.exceptions import APIException
from api_integration.ports.interfaces import (
    IApiIfrProRepository,
    IApiClient,
    IApiAuthenticator,
    IRateLimiter
)
from logger import get_logger

logger = get_logger(__name__)


# Factory para crear repositorio con dependencias
def create_ifrpro_repository(
        api_client: IApiClient,
        authenticator: IApiAuthenticator,
        credentials: ApiCredentials,
        base_url: str,
        rate_limiter: Optional[IRateLimiter] = None
) -> IfrProRepository:
    """
    Factory para crear IfrProRepository

    Args:
        api_client: Cliente HTTP
        authenticator: Autenticador
        credentials: Credenciales de API
        base_url: URL base
        rate_limiter: Rate limiter opcional

    Returns:
        IfrProRepository configurado
    """
    return IfrProRepository(
        api_client=api_client,
        authenticator=authenticator,
        credentials=credentials,
        base_url=base_url,
        rate_limiter=rate_limiter
    )


class IfrProRepository(IApiIfrProRepository):
    """
    Implementación del repositorio de preingresos

    Responsabilidades:
    - Construir peticiones para la API
    - Agregar autenticación
    - Aplicar rate limiting
    - Ejecutar peticiones
    - Procesar respuestas
    """

    def __init__(
            self,
            api_client: IApiClient,
            authenticator: IApiAuthenticator,
            credentials: ApiCredentials,
            base_url: str,
            rate_limiter: Optional[IRateLimiter] = None
    ):
        self.client = api_client
        self.authenticator = authenticator
        self.credentials = credentials
        self.base_url = base_url
        self.rate_limiter = rate_limiter
        self.logger = logger.bind(
            component="PreingresoRepository",
            api_cuenta=credentials.cuenta
        )

    async def health_check(
            self
    ) -> ApiResponse:
        """
        Prueba la conexión con la API

        Returns:
            ApiResponse
        """

        # Construir endpoint
        endpoint = Endpoint(
            path="/",
            method=RequestMethod.GET,
            base_url=self.base_url
        )

        # Crear request
        request = ApiRequest(
            request_id=str(uuid.uuid4()),
            endpoint=endpoint
        )

        # Agregar autenticación
        auth_headers = self.authenticator.generate_auth_headers(
            request,
            self.credentials
        )

        for key, value in auth_headers.items():
            request.add_header(key, value)

        # Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        try:
            response = await self.client.health_check(self.credentials)
            return response
        except Exception as e:
            self.logger.exception(
                "Error de conexión",
                True,
                error=str(e)
            )
            raise

    async def create_preingreso(
            self,
            data: PreingresoData
    ) -> ApiResponse:
        """
        Crea un preingreso en la API

        Args:
            data: Datos del preingreso

        Returns:
            ApiResponse con el resultado
        """
        self.logger.info(
            "Creando preingreso",
            boleta_tienda=data.boleta_tienda
        )

        # Validar datos antes de enviar
        validation_errors = data.validate_for_api()
        if validation_errors:
            raise APIException(
                f"Datos inválidos: {'; '.join(validation_errors)}",
                code="INVALID_PREINGRESO_DATA",
                details={"errors": validation_errors}
            )

        # Construir endpoint
        endpoint = Endpoint(
            path="/v1/preingreso",
            method=RequestMethod.POST,
            base_url=self.base_url
        )

        # Construir body (sin archivos)
        body = data.to_api_body()

        # Construir files (PDF)
        files = []
        pdf_tuple = data.to_file_tuple()
        if pdf_tuple:
            files.append(pdf_tuple)

        # Crear request
        request = ApiRequest(
            request_id=str(uuid.uuid4()),
            endpoint=endpoint,
            body=body,
            files=files if files else None
        )

        # Agregar headers de autenticación
        auth_headers = self.authenticator.generate_auth_headers(
            request,
            self.credentials
        )

        for key, value in auth_headers.items():
            request.add_header(key, value)

        # Aplicar rate limiting si está configurado
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # Ejecutar petición
        try:
            response = await self.client.execute_request(request)

            self.logger.info(
                "Preingreso creado",
                boleta_tienda=data.boleta_tienda,
                status_code=response.status_code,
                response_time_ms=response.response_time_ms
            )

            return response

        except Exception as e:
            self.logger.error(
                "Error creando preingreso",
                boleta_tienda=data.boleta_tienda,
                error=str(e)
            )
            raise

    async def consultar_boleta(
            self,
            numero_boleta: str
    ) -> Optional[ApiResponse]:
        """
        Obtiene un preingreso por número de boleta

        Args:
            numero_boleta: Número de boleta a buscar

        Returns:
            ApiResponse si existe, None si no
        """
        self.logger.info(
            "Getting preingreso",
            numero_boleta=numero_boleta
        )

        # Construir endpoint
        endpoint = Endpoint(
            path=f"/v1/reparacion/{numero_boleta}/consultar",
            method=RequestMethod.GET,
            base_url=self.base_url
        )

        # Crear request
        request = ApiRequest(
            request_id=str(uuid.uuid4()),
            endpoint=endpoint
        )

        # Agregar autenticación
        auth_headers = self.authenticator.generate_auth_headers(
            request,
            self.credentials
        )

        for key, value in auth_headers.items():
            request.add_header(key, value)

        # Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # Ejecutar
        try:
            response = await self.client.execute_request(request)

            # Si es 404, retornar None
            if response.status_code == 404:
                self.logger.info(
                    "No se encontró la boleta",
                    numero_boleta=numero_boleta
                )
                return None

            self.logger.info(
                "Si se encontró la boleta",
                numero_boleta=numero_boleta,
                status_code=response.status_code
            )

            return response

        except Exception as e:
            self.logger.error(
                "Error getting preingreso",
                numero_boleta=numero_boleta,
                error=str(e)
            )
            raise

    async def listar_sucursales(
            self
    ) -> Optional[ApiResponse]:
        """
        Obtiene un preingreso por número de boleta

        Returns:
            ApiResponse si existe, None si no
        """
        self.logger.info(
            "Listar sucursales"
        )

        # Construir endpoint
        endpoint = Endpoint(
            path="/v1/cliente/sucursal",
            method=RequestMethod.GET,
            base_url=self.base_url
        )

        # Crear request
        request = ApiRequest(
            request_id=str(uuid.uuid4()),
            endpoint=endpoint
        )

        # Agregar autenticación
        auth_headers = self.authenticator.generate_auth_headers(
            request,
            self.credentials
        )

        for key, value in auth_headers.items():
            request.add_header(key, value)

        # Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # Ejecutar
        try:
            response = await self.client.execute_request(request)

            # Si es 404, retornar None
            if response.status_code == 404:
                self.logger.info(
                    "No se encontraron sucursales",
                )
                return None

            self.logger.info(
                "Si se encontraron sucursales",
                status_code=response.status_code
            )

            return response

        except Exception as e:
            self.logger.error(
                "Error al listar las sucursales",
                error=str(e)
            )
            raise

    async def listar_marcas(
            self
    ) -> Optional[ApiResponse]:
        """
        Obtiene el catálogo de marcas

        Returns:
            ApiResponse con las marcas disponibles
        """
        self.logger.info("Listar marcas")

        # Construir endpoint
        endpoint = Endpoint(
            path="/v1/unidad/marca",
            method=RequestMethod.GET,
            base_url=self.base_url
        )

        # Crear request
        request = ApiRequest(
            request_id=str(uuid.uuid4()),
            endpoint=endpoint
        )

        # Agregar autenticación
        auth_headers = self.authenticator.generate_auth_headers(
            request,
            self.credentials
        )

        for key, value in auth_headers.items():
            request.add_header(key, value)

        # Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # Ejecutar
        try:
            response = await self.client.execute_request(request)

            if response.status_code == 404:
                self.logger.info("No se encontraron marcas")
                return None

            self.logger.info(
                "Marcas obtenidas",
                status_code=response.status_code
            )

            return response

        except Exception as e:
            self.logger.error(
                "Error al listar las marcas",
                error=str(e)
            )
            raise

    async def listar_recursos_iniciales(
            self
    ) -> Optional[ApiResponse]:
        """
        Obtiene los recursos iniciales para preingreso

        Returns:
            ApiResponse con recursos iniciales
        """
        self.logger.info("Listar recursos iniciales")

        # Construir endpoint
        endpoint = Endpoint(
            path="/v1/preingreso/recursos_iniciales",
            method=RequestMethod.GET,
            base_url=self.base_url
        )

        # Crear request
        request = ApiRequest(
            request_id=str(uuid.uuid4()),
            endpoint=endpoint
        )

        # Agregar autenticación
        auth_headers = self.authenticator.generate_auth_headers(
            request,
            self.credentials
        )

        for key, value in auth_headers.items():
            request.add_header(key, value)

        # Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # Ejecutar
        try:
            response = await self.client.execute_request(request)

            if response.status_code == 404:
                self.logger.info("No se encontraron recursos iniciales")
                return None

            self.logger.info(
                "Recursos iniciales obtenidos",
                status_code=response.status_code
            )

            return response

        except Exception as e:
            self.logger.error(
                "Error al listar recursos iniciales",
                error=str(e)
            )
            raise

    async def listar_tipos_dispositivo(
            self,
            categoria_id: str
    ) -> Optional[ApiResponse]:
        """
        Obtiene los tipos de dispositivos para una categoría

        Args:
            categoria_id: ID de la categoría

        Returns:
            ApiResponse con tipos de dispositivos
        """
        self.logger.info(
            "Listar tipos de dispositivo",
            categoria_id=categoria_id
        )

        # Construir endpoint
        endpoint = Endpoint(
            path=f"/v1/unidad/categoria/{categoria_id}/tipo_dispositivo",
            method=RequestMethod.GET,
            base_url=self.base_url
        )

        # Crear request
        request = ApiRequest(
            request_id=str(uuid.uuid4()),
            endpoint=endpoint
        )

        # Agregar autenticación
        auth_headers = self.authenticator.generate_auth_headers(
            request,
            self.credentials
        )

        for key, value in auth_headers.items():
            request.add_header(key, value)

        # Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # Ejecutar
        try:
            response = await self.client.execute_request(request)

            if response.status_code == 404:
                self.logger.info(
                    "No se encontraron tipos de dispositivo",
                    categoria_id=categoria_id
                )
                return None

            self.logger.info(
                "Tipos de dispositivo obtenidos",
                categoria_id=categoria_id,
                status_code=response.status_code
            )

            return response

        except Exception as e:
            self.logger.error(
                "Error al listar tipos de dispositivo",
                categoria_id=categoria_id,
                error=str(e)
            )
            raise


class ApiIfrProRepository:
    pass