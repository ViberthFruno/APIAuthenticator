from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from api_integration.domain.entities import PreingresoData, ApiResponse


# =====================================
# DTOs (Data Transfer Objects) - Solo datos, sin lógica
# =====================================

@dataclass
class DatosExtraidosPDF:
    """Datos crudos extraídos del PDF"""
    numero_boleta: str
    referencia: str
    nombre_sucursal: str
    numero_transaccion: str
    cliente_nombre: str
    cliente_telefono: str
    cliente_correo: str
    serie: str
    garantia_nombre: str

    # Opcionales:
    fecha_compra: Optional[str] = None # Si es DOA no tiene fecha compra.
    factura: Optional[str] = None # Si es DOA no tiene factura.
    cliente_cedula: Optional[str] = None
    cliente_direccion: Optional[str] = None
    cliente_telefono2: Optional[str] = None
    fecha_transaccion: Optional[str] = None
    transaccion_gestionada_por: Optional[str] = None
    telefono_sucursal: Optional[str] = None
    producto_codigo: Optional[str] = None
    producto_descripcion: Optional[str] = None
    marca_nombre: Optional[str] = None
    modelo_nombre: Optional[str] = None
    garantia_fecha: Optional[str] = None
    danos: Optional[str] = None
    observaciones: Optional[str] = None
    hecho_por: Optional[str] = None


@dataclass
class ArchivoAdjunto:
    """Representa un archivo a subir"""
    nombre_archivo: str
    ruta_archivo: str  # Referencia, no el contenido
    tipo_mime: str = "application/pdf"

    def leer_contenido(self) -> bytes:
        """Lee el contenido cuando sea necesario"""
        with open(self.ruta_archivo, 'rb') as f:
            return f.read()


@dataclass
class CreatePreingresoInput:
    """Input limpio para el use case de crear preingreso"""
    datos_pdf: DatosExtraidosPDF
    retry_on_failure: bool = False
    validate_before_send: bool = True
    archivo_adjunto: Optional[ArchivoAdjunto] = None


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
