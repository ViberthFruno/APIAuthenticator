# ====================
# API INTEGRATION EXCEPTIONS
# ====================

from typing import Optional, Dict, Any


class DomainException(Exception):
    """Excepción base para errores de dominio"""

    def __init__(
            self,
            message: str,
            code: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details
        }


class APIException(DomainException):
    """Excepción base para API Integration Context"""
    pass


class APIConnectionError(APIException):
    """Error de conexión con API"""
    pass


class APIAuthenticationError(APIException):
    """Error de autenticación con API"""
    pass


class APIValidationError(APIException):
    """Error de validación en request/response API"""
    pass


class APITimeoutError(APIException):
    """Timeout en llamada a API"""
    pass


class APIRateLimitError(APIException):
    """Rate limit excedido"""
    pass

# ====================
# APPLICATION EXCEPTIONS
# ====================

class ApplicationException(DomainException):
    """Excepción base para Application Layer"""
    pass
