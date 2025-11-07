#http_cliente.py
"""
API Integration Context - Infrastructure Layer
Cliente HTTP robusto con manejo de reintentos y rate limiting
"""
import asyncio
import uuid
from datetime import datetime
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from api_integration.domain.entities import (
    ApiRequest,
    ApiResponse,
    RequestMethod,
    Endpoint,
    ApiCredentials
)
from api_integration.domain.exceptions import (
    APIConnectionError,
    APITimeoutError,
    APIException
)
from api_integration.ports.interfaces import (
    IApiClient,
    IRetryPolicy,
    IRateLimiter,
    IApiAuthenticator
)
from logger import get_logger

logger = get_logger(__name__)


class HttpApiClient(IApiClient):
    """
    Cliente HTTP robusto para la API
    
    Features:
    - HTTP/2 support
    - Connection pooling
    - Timeout handling
    - Async operations
    - Automatic retries
    """

    def __init__(
            self,
            authenticator: IApiAuthenticator,
            base_url: str,
            timeout_seconds: int = 30,
            max_connections: int = 100,
            verify_ssl: bool = True
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = httpx.Timeout(timeout_seconds)
        self.verify_ssl = verify_ssl
        self.authenticator = authenticator

        # Crear cliente async con pooling
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            verify=self.verify_ssl,
            http2=True,  # Habilitar HTTP/2
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=20
            )
        )

        self.logger = logger.bind(component="HttpApiClient")

    async def execute_request(self, request: ApiRequest) -> ApiResponse:
        """
        Ejecuta una petición HTTP
        
        Args:
            request: Petición a ejecutar
            
        Returns:
            ApiResponse con el resultado
        """
        self.logger.debug(
            "Executing request",
            request_id=request.request_id,
            method=request.endpoint.method.value,
            url=request.endpoint.full_url
        )

        start_time = datetime.now()

        try:
            # Marcar como en progreso
            request.mark_in_progress()

            # Ejecutar según método
            if request.endpoint.method == RequestMethod.GET:
                response = await self._execute_get(request)
            elif request.endpoint.method == RequestMethod.POST:
                response = await self._execute_post(request)
            elif request.endpoint.method == RequestMethod.PUT:
                response = await self._execute_put(request)
            elif request.endpoint.method == RequestMethod.DELETE:
                response = await self._execute_delete(request)
            else:
                raise APIException(
                    f"Método no soportado: {request.endpoint.method}",
                    code="UNSUPPORTED_METHOD"
                )

            # Calcular tiempo de respuesta
            end_time = datetime.now()
            response_time_ms = (end_time - start_time).total_seconds() * 1000

            # Crear ApiResponse
            api_response = self._build_api_response(
                request.request_id,
                response,
                response_time_ms
            )

            # Marcar request como exitoso
            if api_response.is_success():
                request.mark_success()
            else:
                request.mark_failed()

            self.logger.info(
                "Request completed",
                request_id=request.request_id,
                status_code=api_response.status_code,
                response_time_ms=response_time_ms
            )

            return api_response

        except httpx.TimeoutException as e:
            request.mark_failed()

            self.logger.error(
                "Request timeout",
                request_id=request.request_id,
                error=str(e)
            )

            raise APITimeoutError(
                f"Timeout en petición: {str(e)}",
                code="REQUEST_TIMEOUT"
            ) from e

        except httpx.ConnectError as e:
            request.mark_failed()

            self.logger.error(
                "Connection error",
                request_id=request.request_id,
                error=str(e)
            )

            raise APIConnectionError(
                f"Error de conexión: {str(e)}",
                code="CONNECTION_ERROR"
            ) from e

        except Exception as e:
            request.mark_failed()

            self.logger.exception(
                "Unexpected error executing request",
                request_id=request.request_id,
                error=str(e)
            )

            raise APIException(
                f"Error inesperado: {str(e)}",
                code="UNEXPECTED_ERROR"
            ) from e

    async def _execute_get(self, request: ApiRequest) -> httpx.Response:
        """Ejecuta petición GET"""
        return await self.client.get(
            request.endpoint.path,
            headers=request.headers,
            params=request.query_params
        )

    async def _execute_post(self, request: ApiRequest) -> httpx.Response:
        """Ejecuta petición POST"""
        if request.is_multipart():
            # Multipart/form-data con archivos
            return await self.client.post(
                request.endpoint.path,
                headers=request.headers,
                data=request.body,
                files=request.files
            )
        else:
            # JSON o form-urlencoded
            return await self.client.post(
                request.endpoint.path,
                headers=request.headers,
                data=request.body
            )

    async def _execute_put(self, request: ApiRequest) -> httpx.Response:
        """Ejecuta petición PUT"""
        return await self.client.put(
            request.endpoint.path,
            headers=request.headers,
            data=request.body
        )

    async def _execute_delete(self, request: ApiRequest) -> httpx.Response:
        """Ejecuta petición DELETE"""
        return await self.client.delete(
            request.endpoint.path,
            headers=request.headers
        )

    def _build_api_response(
            self,
            request_id: str,
            httpx_response: httpx.Response,
            response_time_ms: float
    ) -> ApiResponse:
        """Construye ApiResponse desde httpx.Response"""

        # Intentar parsear como JSON
        body = None
        try:
            if httpx_response.text:
                body = httpx_response.json()
        except Exception:
            # No es JSON, ignorar
            pass

        return ApiResponse(
            request_id=request_id,
            status_code=httpx_response.status_code,
            headers=dict(httpx_response.headers),
            body=body,
            raw_content=httpx_response.content,
            response_time_ms=response_time_ms
        )

    async def health_check(self, credentials: ApiCredentials) -> ApiResponse:
        """Verifica conectividad con la API"""

        # Construir endpoint
        endpoint = Endpoint(
            path=f"/",
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
            request, credentials
        )

        for key, value in auth_headers.items():
            request.add_header(key, value)

        # Ejecutar petición
        try:
            response = await self.execute_request(request)
            self.logger.info(
                "Conexión establecida exitosamente",
                status_code=response.status_code,
                response_time_ms=response.response_time_ms
            )
            return response

        except Exception as e:
            self.logger.error(
                "Error al verificar la conexión",
                error=str(e)
            )
            raise

    async def close(self):
        """Cierra el cliente"""
        await asyncio.create_task(self.client.aclose())

    async def __aenter__(self):
        """Context manager async"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cierre automático"""
        await self.client.aclose()


class TenacityRetryPolicy(IRetryPolicy):
    """
    Política de reintentos usando tenacity
    
    Features:
    - Exponential backoff
    - Configurable attempts
    - Retry on specific errors
    """

    def __init__(
            self,
            max_attempts: int = 3,
            min_wait_seconds: float = 1.0,
            max_wait_seconds: float = 10.0
    ):
        self.max_attempts = max_attempts
        self.min_wait = min_wait_seconds
        self.max_wait = max_wait_seconds
        self.logger = logger.bind(component="RetryPolicy")

    async def execute_with_retry(self, func, *args, **kwargs) -> Any:
        """Ejecuta función con reintentos"""

        @retry(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential(
                multiplier=self.min_wait,
                max=self.max_wait
            ),
            retry=retry_if_exception_type(
                (APIConnectionError, APITimeoutError)
            ),
            reraise=True
        )
        async def _execute():
            return await func(*args, **kwargs)

        return await _execute()

    def should_retry(self, response: ApiResponse) -> bool:
        """Determina si debe reintentar"""
        return response.is_retryable()


class SimpleRateLimiter(IRateLimiter):
    """
    Rate limiter simple basado en tokens
    
    Features:
    - Token bucket algorithm
    - Async-safe
    - Configurable rate
    """

    def __init__(
            self,
            calls_per_period: int = 100,
            period_seconds: int = 3600
    ):
        self.max_calls = calls_per_period
        self.period = period_seconds
        self.tokens = calls_per_period
        self.last_refill = datetime.now()
        self._lock = asyncio.Lock()
        self.logger = logger.bind(component="RateLimiter")

    async def acquire(self):
        """Espera hasta poder hacer una petición"""
        async with self._lock:
            self._refill_tokens()

            while self.tokens <= 0:
                # Esperar hasta el próximo refill
                wait_time = self._time_until_refill()
                self.logger.warning(
                    "Rate limit reached, waiting",
                    wait_seconds=wait_time
                )
                await asyncio.sleep(wait_time)
                self._refill_tokens()

            self.tokens -= 1

            self.logger.debug(
                "Token acquired",
                remaining=self.tokens
            )

    def release(self):
        """Libera un token (no usado en este algoritmo)"""
        pass

    def get_remaining_calls(self) -> int:
        """Obtiene llamadas restantes"""
        return max(0, self.tokens)

    def reset(self):
        """Resetea el contador"""
        self.tokens = self.max_calls
        self.last_refill = datetime.now()

    def _refill_tokens(self):
        """Rellena tokens si ha pasado el período"""
        now = datetime.now()
        elapsed = (now - self.last_refill).total_seconds()

        if elapsed >= self.period:
            self.tokens = self.max_calls
            self.last_refill = now

            self.logger.debug(
                "Tokens refilled",
                tokens=self.tokens
            )

    def _time_until_refill(self) -> float:
        """Calcula tiempo hasta el próximo refill"""
        now = datetime.now()
        elapsed = (now - self.last_refill).total_seconds()
        return max(0.0, self.period - elapsed)


# Factory para crear cliente con dependencias
def create_api_client(
        authenticator: IApiAuthenticator,
        base_url: str,
        timeout: int = 30,
        verify_ssl: bool = True,
        max_attempts: int = 3,
        rate_limit_calls: int = 100
) -> tuple[HttpApiClient, TenacityRetryPolicy, SimpleRateLimiter]:
    """
    Factory para crear cliente HTTP con todas sus dependencias
    
    Args:
        authenticator: Autenticador de API
        base_url: URL base de la API
        timeout: Timeout en segundos
        verify_ssl: Verificar certificados SSL
        max_attempts: Número máximo de reintentos
        rate_limit_calls: Llamadas por hora
        
    Returns:
        Tupla (client, retry_policy, rate_limiter)
    """
    client = HttpApiClient(
        authenticator=authenticator,
        base_url=base_url,
        timeout_seconds=timeout,
        verify_ssl=verify_ssl
    )

    retry_policy = TenacityRetryPolicy(
        max_attempts=max_attempts
    )

    rate_limiter = SimpleRateLimiter(
        calls_per_period=rate_limit_calls,
        period_seconds=3600
    )

    return client, retry_policy, rate_limiter


class HttpClient:
    pass