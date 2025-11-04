"""
API Integration Context - Domain Entities
Entidades para manejar requests/responses de API externa
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID

from .exceptions import APIException, APIValidationError


class RequestMethod(Enum):
    """Métodos HTTP soportados"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class RequestStatus(Enum):
    """Estados de una petición API"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Endpoint:
    """Value Object: Endpoint de API"""
    path: str
    method: RequestMethod
    base_url: str

    def __post_init__(self):
        """Validaciones"""
        if not self.path.startswith('/'):
            object.__setattr__(self, 'path', f'/{self.path}')

        if not self.base_url.startswith(('http://', 'https://')):
            raise ValueError("base_url debe comenzar con http:// o https://")

    @property
    def full_url(self) -> str:
        """Retorna la URL completa"""
        return f"{self.base_url.rstrip('/')}{self.path}"

    def __str__(self) -> str:
        return f"{self.method.value} {self.full_url}"


@dataclass
class ApiCredentials:
    """Value Object: Credenciales de API"""
    cuenta: str
    llave: str
    codigo_servicio: str
    pais: str = "CR"

    def __post_init__(self):
        """Validaciones"""
        if not self.cuenta:
            raise ValueError("cuenta no puede estar vacía")
        if not self.llave:
            raise ValueError("llave no puede estar vacía")
        if not self.codigo_servicio:
            raise ValueError("codigo_servicio no puede estar vacío")
        if len(self.pais) != 2:
            raise ValueError("pais debe ser código de 2 letras")

    def mask_sensitive_data(self) -> Dict[str, str]:
        """Retorna credenciales con datos sensibles enmascarados"""
        return {
            "cuenta": self.cuenta,
            "llave": f"{self.llave[:6]}***" if len(self.llave) > 6 else "***",
            "codigo_servicio": self.codigo_servicio,
            "pais": self.pais
        }


@dataclass
class ApiRequest:
    """
    Entity: Petición a API externa
    
    Encapsula toda la información necesaria para hacer una petición
    """
    request_id: str
    endpoint: Endpoint
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    query_params: Optional[Dict[str, str]] = None
    files: Optional[List[tuple]] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    status: RequestStatus = RequestStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        """Validaciones iniciales"""
        if not self.request_id:
            raise ValueError("request_id no puede estar vacío")

        # Validar que POST/PUT/PATCH tengan body o files
        if self.endpoint.method in [RequestMethod.POST, RequestMethod.PUT, RequestMethod.PATCH]:
            if not self.body and not self.files:
                raise APIValidationError(
                    f"Método {self.endpoint.method.value} requiere body o files",
                    code="MISSING_BODY"
                )

    # ===== Query Methods =====

    def can_retry(self) -> bool:
        """Verifica si puede reintentar"""
        return self.retry_count < self.max_retries

    def is_multipart(self) -> bool:
        """Verifica si es multipart/form-data"""
        return self.files is not None and len(self.files) > 0

    def has_body(self) -> bool:
        """Verifica si tiene body"""
        return self.body is not None

    def has_query_params(self) -> bool:
        """Verifica si tiene query params"""
        return self.query_params is not None and len(self.query_params) > 0

    # ===== Command Methods =====

    def mark_in_progress(self):
        """Marca como en progreso"""
        self.status = RequestStatus.IN_PROGRESS

    def mark_success(self):
        """Marca como exitoso"""
        self.status = RequestStatus.SUCCESS

    def mark_failed(self):
        """Marca como fallido"""
        self.status = RequestStatus.FAILED

    def increment_retry(self):
        """Incrementa contador de reintentos"""
        if not self.can_retry():
            raise APIException(
                f"Máximo de reintentos alcanzado ({self.max_retries})",
                code="MAX_RETRIES_EXCEEDED"
            )

        self.retry_count += 1
        self.status = RequestStatus.RETRYING

    def add_header(self, key: str, value: str):
        """Agrega un header"""
        self.headers[key] = value

    def remove_header(self, key: str):
        """Remueve un header"""
        if key in self.headers:
            del self.headers[key]

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para logging"""
        return {
            "request_id": self.request_id,
            "endpoint": str(self.endpoint),
            "method": self.endpoint.method.value,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "has_body": self.has_body(),
            "has_files": self.is_multipart(),
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ApiResponse:
    """
    Entity: Respuesta de API externa
    
    Encapsula la respuesta y provee métodos de validación
    """
    request_id: str
    status_code: int
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None
    raw_content: Optional[bytes] = None

    # Metadata
    response_time_ms: float = 0.0
    received_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validaciones"""
        if self.status_code < 100 or self.status_code >= 600:
            raise ValueError(f"Status code inválido: {self.status_code}")

    # ===== Query Methods =====

    def is_success(self) -> bool:
        """Verifica si es exitoso (2xx)"""
        return 200 <= self.status_code < 300

    def is_client_error(self) -> bool:
        """Verifica si es error de cliente (4xx)"""
        return 400 <= self.status_code < 500

    def is_server_error(self) -> bool:
        """Verifica si es error de servidor (5xx)"""
        return 500 <= self.status_code < 600

    def is_retryable(self) -> bool:
        """Verifica si debe reintentarse"""
        # Reintentar solo en errores de servidor y algunos específicos
        retryable_codes = {408, 429, 500, 502, 503, 504}
        return self.status_code in retryable_codes

    def has_json_body(self) -> bool:
        """Verifica si tiene body JSON"""
        return self.body is not None

    def get_error_message(self) -> Optional[str]:
        """Extrae mensaje de error del response"""
        if not self.has_json_body():
            return None

        # Intentar diferentes formatos comunes
        if isinstance(self.body, dict):
            # Formato 1: {"error": "mensaje"}
            if "error" in self.body:
                return str(self.body["error"])

            # Formato 2: {"message": "mensaje"}
            if "message" in self.body:
                return str(self.body["message"])

            # Formato 3: {"errors": [...]}
            if "errors" in self.body and isinstance(self.body["errors"], list):
                return "; ".join(str(e) for e in self.body["errors"])

        return None

    # ===== Validation Methods =====

    def validate_success(self):
        """Valida que sea exitoso, lanza excepción si no"""
        if not self.is_success():
            error_msg = self.get_error_message() or "Error en API"

            if self.is_client_error():
                raise APIValidationError(
                    f"Error de validación: {error_msg}",
                    code=f"HTTP_{self.status_code}",
                    details={"status_code": self.status_code, "body": self.body}
                )

            if self.is_server_error():
                raise APIException(
                    f"Error del servidor: {error_msg}",
                    code=f"HTTP_{self.status_code}",
                    details={"status_code": self.status_code}
                )

            raise APIException(
                f"Error inesperado: {error_msg}",
                code=f"HTTP_{self.status_code}"
            )

    def extract_data(self, key: str, required: bool = True) -> Any:
        """
        Extrae un campo específico del body
        
        Args:
            key: Clave a extraer
            required: Si es requerido, lanza excepción si no existe
            
        Returns:
            Valor del campo
        """
        if not self.has_json_body():
            if required:
                raise APIValidationError(
                    "Response no tiene body JSON",
                    code="NO_JSON_BODY"
                )
            return None

        if key not in self.body:
            if required:
                raise APIValidationError(
                    f"Campo '{key}' no encontrado en response",
                    code="MISSING_FIELD",
                    details={"key": key, "available_keys": list(self.body.keys())}
                )
            return None

        return self.body[key]

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para logging"""
        return {
            "request_id": self.request_id,
            "status_code": self.status_code,
            "is_success": self.is_success(),
            "response_time_ms": self.response_time_ms,
            "has_body": self.has_json_body(),
            "received_at": self.received_at.isoformat()
        }

    def __repr__(self) -> str:
        return (
            f"ApiResponse(request_id={self.request_id}, "
            f"status={self.status_code}, "
            f"time={self.response_time_ms:.0f}ms)"
        )


# DTO inmutable final
@dataclass(frozen=True)
class PreingresoData:
    """
    Entity: Datos para crear un preingreso
    
    Representa la información necesaria para crear un preingreso en la API
    """
    codigo_sucursal: str
    tipo_preingreso_id: str
    garantia_id: str
    nombres_propietario: str
    apellidos_propietario: str
    correo_propietario: str
    telefono1_propietario: str
    division_1: str  # código provincia
    division_2: str  # código cantón
    division_3: str  # código distrito
    descripcion_division: str  # Dirección exacta de la tienda
    serie: str
    marca_id: UUID
    modelo_comercial_id: UUID
    detalle_recepcion: str  # nombre marca + nombre modelo + Daños + observaciones.
    referencia: str

    boleta_tienda: str

    fecha_compra: Optional[str] = None
    otro_telefono_propietario: Optional[str] = None
    numero_factura: Optional[str] = None

    # Archivos adjuntos
    pdf_filename: str = ""
    pdf_content: Optional[bytes] = None

    def __post_init__(self):
        """Validaciones básicas de los parámetros que se extrajeron del PDF"""
        if not self.codigo_sucursal:
            raise ValueError("codigo_sucursal es requerido")

        if not self.tipo_preingreso_id:
            raise ValueError("tipo_preingreso_id es requerido")

        if not self.garantia_id:
            raise ValueError("garantia_id es requerido")

        if not self.nombres_propietario:
            raise ValueError("nombres_propietario es requerido")

        if not self.apellidos_propietario:
            raise ValueError("apellidos_propietario es requerido")

        if not self.correo_propietario:
            raise ValueError("correo_propietario es requerido")

        if not self.telefono1_propietario:
            raise ValueError("telefono1_propietario es requerido")

        if not self.division_1:
            raise ValueError("division_1 es requerido")

        if not self.division_2:
            raise ValueError("division_2 es requerido")

        if not self.division_3:
            raise ValueError("division_3 es requerido")

        if not self.descripcion_division:
            raise ValueError("descripcion_division es requerido")

        if not self.serie:
            raise ValueError("serie es requerido")

        if not self.marca_id:
            raise ValueError("marca_id es requerido")

        if not self.modelo_comercial_id:
            raise ValueError("modelo_comercial_id es requerido")

        if not self.detalle_recepcion:
            raise ValueError("detalle_recepcion es requerido")

        if not self.referencia:
            raise ValueError("referencia es requerido")

        if not self.boleta_tienda:
            raise ValueError("boleta_tienda es requerido")

    def validate_for_api(self) -> List[str]:
        """
        Validar que tenga todos los campos requeridos para la API
        
        Returns:
            Lista de errores (vacía si es válido)
        """
        errors = []

        # Campos requeridos
        required_fields = {
            "codigo_sucursal": self.codigo_sucursal,
            "tipo_preingreso_id": self.tipo_preingreso_id,
            "nombres_propietario": self.nombres_propietario,
            "apellidos_propietario": self.apellidos_propietario,
            "correo_propietario": self.correo_propietario,
            "telefono1_propietario": self.telefono1_propietario,
            "division_1": self.division_1,
            "division_2": self.division_2,
            "division_3": self.division_3,
            "descripcion_division": self.descripcion_division,
            "serie": self.serie,
            "marca_id": self.marca_id,
            "modelo_comercial_id": self.modelo_comercial_id,
            "garantia_id": self.garantia_id,
            "detalle_recepcion": self.detalle_recepcion,
            "referencia": self.referencia
        }

        for field_name, field_value in required_fields.items():
            if not field_value or (isinstance(field_value, str) and not field_value.strip()):
                errors.append(f"Campo requerido faltante: {field_name}")

        # Validar PDF
        if not self.pdf_content:
            errors.append("PDF es requerido")
        elif len(self.pdf_content) == 0:
            errors.append("PDF está vacío")

        return errors

    def to_api_body(self) -> Dict[str, str]:
        """
        Convierte a formato esperado por la API (sin archivos)
        
        Returns:
            Diccionario con los campos para el body
        """
        return {
            "codigo_sucursal": self.codigo_sucursal,
            "tipo_preingreso_id": self.tipo_preingreso_id,
            "es_persona_juridica": False,
            "nombres_propietario": self.nombres_propietario,
            "apellidos_propietario": self.apellidos_propietario,
            "correo_propietario": self.correo_propietario,
            "telefono1_propietario": self.telefono1_propietario,
            "telefono1_ext_propietario": "0",
            "otro_telefono_propietario": self.otro_telefono_propietario or "0",
            "otro_telefono_ext_propietario": "0",
            "division_1": self.division_1,
            "division_2": self.division_2,
            "division_3": self.division_3,
            "descripcion_division": self.descripcion_division,
            "propietario_contactos_ids": "[]",
            "imei_prestamo": "",
            "numero_factura": self.numero_factura or "N/A",
            "fecha_compra": self.fecha_compra,
            "imei": "",
            "serie": self.serie,
            "marca_id": str(self.marca_id),
            "modelo_comercial_id": str(self.modelo_comercial_id),
            "modelo_fabrica_id": "",
            "operador_id": "11",  # Genérico
            "garantia_id": self.garantia_id,
            "categoria_id": "5",  # Desconocido
            "tipo_dispositivo_id": "7",  # Desconocido
            "motivo_recepcion_id": "72",  # Otro problema
            "detalle_recepcion": self.detalle_recepcion,
            "referencia": self.referencia
        }

    def to_file_tuple(self) -> Optional[tuple]:
        """
        Convierte el PDF a formato esperado por requests
        
        Returns:
            Tupla (field_name, (filename, content, content_type))
        """
        if not self.pdf_content:
            return None

        filename = self.pdf_filename or f"boleta_{self.boleta_tienda}.pdf"

        return (
            "imagen_otra",  # Nombre del campo
            (filename, self.pdf_content, "application/pdf")
        )
