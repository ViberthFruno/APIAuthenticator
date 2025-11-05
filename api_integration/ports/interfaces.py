"""
API Integration Context - Repository Interfaces (Ports)
Contratos para comunicación con API externa
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from api_integration.domain.entities import (
    ApiRequest,
    ApiResponse,
    PreingresoData,
    ApiCredentials
)


class IApiAuthenticator(ABC):
    """
    Puerto: Autenticador de API
    
    Define el contrato para generar headers de autenticación
    """

    @abstractmethod
    def generate_auth_headers(
            self,
            request: ApiRequest,
            credentials: ApiCredentials
    ) -> Dict[str, str]:
        """
        Genera headers de autenticación para una petición
        
        Args:
            request: Petición a autenticar
            credentials: Credenciales de la API
            
        Returns:
            Diccionario con headers de autenticación
        """
        pass

    @abstractmethod
    def validate_credentials(self, credentials: ApiCredentials) -> bool:
        """
        Valida que las credenciales sean correctas
        
        Args:
            credentials: Credenciales a validar
            
        Returns:
            True si son válidas
        """
        pass


class IApiClient(ABC):
    """
    Puerto: Cliente HTTP para API
    
    Define el contrato para hacer peticiones HTTP
    """

    @abstractmethod
    async def execute_request(self, request: ApiRequest) -> ApiResponse:
        """
        Ejecuta una petición HTTP
        
        Args:
            request: Petición a ejecutar
            
        Returns:
            Respuesta de la API
        """
        pass

    @abstractmethod
    async def health_check(self, credentials: ApiCredentials) -> ApiResponse:
        """
        Verifica conectividad con la API

        Returns:
            Respuesta de la API
        """
        pass

    @abstractmethod
    def close(self):
        """Cierra el cliente y libera recursos"""
        pass


class IApiIfrProRepository(ABC):
    """
    Puerto: Repositorio de preingresos
    
    Define el contrato para operaciones de preingreso en la API
    """

    @abstractmethod
    async def create_preingreso(
            self,
            data: PreingresoData
    ) -> ApiResponse:
        """
        Crea un preingreso en la API
        
        Args:
            data: Datos del preingreso
            
        Returns:
            Respuesta de la API con el preingreso creado
        """
        pass

    @abstractmethod
    async def consultar_boleta(
            self,
            numero_boleta: str
    ) -> Optional[ApiResponse]:
        """
        Obtiene un preingreso por número de boleta
        
        Args:
            numero_boleta: Número de boleta a buscar
            
        Returns:
            Respuesta con datos del preingreso si existe, None si no
        """
        pass

    @abstractmethod
    async def listar_sucursales(
            self
    ) -> Optional[ApiResponse]:
        """
        Obtiene un preingreso por número de boleta

        Args:
            numero_boleta: Número de boleta a buscar

        Returns:
            Respuesta con datos del preingreso si existe, None si no
        """
        pass

    @abstractmethod
    async def health_check(self) -> ApiResponse:
        """
        Verifica conectividad con la API

        Returns:
            Respuesta de la API
        """
        pass


class IRetryPolicy(ABC):
    """
    Puerto: Política de reintentos
    
    Define el contrato para manejar reintentos
    """

    @abstractmethod
    async def execute_with_retry(
            self,
            func,
            *args,
            **kwargs
    ) -> Any:
        """
        Ejecuta una función con política de reintentos
        
        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos nombrados
            
        Returns:
            Resultado de la función
        """
        pass

    @abstractmethod
    def should_retry(self, response: ApiResponse) -> bool:
        """
        Determina si debe reintentar basado en la respuesta
        
        Args:
            response: Respuesta a evaluar
            
        Returns:
            True si debe reintentar
        """
        pass


class IRateLimiter(ABC):
    """
    Puerto: Limitador de tasa
    
    Define el contrato para limitar llamadas a la API
    """

    @abstractmethod
    async def acquire(self):
        """Espera hasta que se pueda hacer una petición"""
        pass

    @abstractmethod
    def release(self):
        """Libera un slot de petición"""
        pass

    @abstractmethod
    def get_remaining_calls(self) -> int:
        """
        Obtiene el número de llamadas restantes
        
        Returns:
            Número de llamadas disponibles
        """
        pass

    @abstractmethod
    def reset(self):
        """Resetea el contador de llamadas"""
        pass


class IApiLogger(ABC):
    """
    Puerto: Logger especializado para API
    
    Define el contrato para logging de peticiones/respuestas
    """

    @abstractmethod
    def log_request(self, request: ApiRequest):
        """Loguea una petición"""
        pass

    @abstractmethod
    def log_response(self, response: ApiResponse):
        """Loguea una respuesta"""
        pass

    @abstractmethod
    def log_error(self, request: ApiRequest, error: Exception):
        """Loguea un error"""
        pass

    @abstractmethod
    def log_retry(self, request: ApiRequest, attempt: int):
        """Loguea un reintento"""
        pass
