from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from api_integration.domain.entities import PreingresoData, ApiResponse


# ===== DTOs (Data Transfer Objects) =====

@dataclass
class CreatePreingresoInput:
    """Input para crear preingreso"""
    preingreso_data: PreingresoData
    retry_on_failure: bool = True
    validate_before_send: bool = True


@dataclass
class CreatePreingresoOutput:
    """Output de crear preingreso"""
    success: bool
    response: Optional[ApiResponse]
    preingreso_id: Optional[str]  # ID retornado por la API
    error_message: Optional[str] = None
    validation_errors: list = None

    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


@dataclass
class GetPreingresoInput:
    """Input para obtener preingreso"""
    numero_boleta: str


@dataclass
class GetPreingresoOutput:
    """Output de obtener preingreso"""
    found: bool
    response: Optional[ApiResponse]
    data: Optional[Dict[str, Any]] = None


@dataclass
class HealthCheckResult:
    """Output de health check"""
    is_healthy: bool
    status_code: Optional[int]
    response_time_ms: float
    message: str
    timestamp: datetime
    error: Optional[str] = None
    error_type: Optional[str] = None
    endpoint: str = "/"

    def get_message(self) -> str:
        """Mensaje para mostrar"""
        if self.is_healthy:
            return f"✅ Conectado ({self.response_time_ms:.0f}ms)"
        else:
            msg = f"❌ Error"
            if self.message:
                msg += f": {self.message}"
            if self.error_type:
                msg += f" ({self.error_type})"
            return msg

    def to_dict(self):
        """Convierte el resultado a diccionario"""
        return {
            'is_healthy': self.is_healthy,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'error_type': self.error_type,
            'endpoint': self.endpoint
        }
