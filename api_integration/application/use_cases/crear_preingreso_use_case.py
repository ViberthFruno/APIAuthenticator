# crear_preingreso_use_case.py

"""
API Integration Context - Use Cases (Application Layer)
Casos de uso para crear un preingreso
"""
from datetime import datetime
from typing import Optional

from api_integration.application.dtos import CreatePreingresoInput, CreatePreingresoOutput, SucursalDTO
from api_integration.domain.builders.crear_preingreso_builder import CrearPreingresoBuilder
from api_integration.domain.exceptions import (
    APIException,
    APIValidationError
)
from api_integration.ports.interfaces import (
    IApiIfrProRepository,
    IRetryPolicy
)
from logger import get_logger, log_execution_time

logger = get_logger(__name__)


class CreatePreingresoUseCase:
    """
    Caso de uso: Crear preingreso en API

    Responsabilidades:
    - Validar datos del preingreso
    - Construir la petición
    - Enviar a la API
    - Procesar respuesta
    - Manejar errores y reintentos
    """

    def __init__(
            self,
            api_ifrpro_repository: IApiIfrProRepository,
            retry_policy: Optional[IRetryPolicy] = None
    ):
        self.repository = api_ifrpro_repository
        self.retry_policy = retry_policy
        self.logger = logger.bind(use_case="CreatePreingreso")

    @log_execution_time
    async def execute(self, input_dto: CreatePreingresoInput) -> CreatePreingresoOutput:
        """
        Ejecuta el caso de uso

        Args:
            input_dto: Datos de entrada

        Returns:
            CreatePreingresoOutput con el resultado
        """
        self.logger.info(
            "Preparando la creación del preingreso",
            numero_boleta=input_dto.datos_pdf.numero_boleta,
            sucursal=input_dto.datos_pdf.nombre_sucursal,
            numero_transaccion=input_dto.datos_pdf.numero_transaccion
        )

        try:
            # Obtener la tienda
            tienda = await self._obtener_tienda_por_referencia(input_dto.datos_pdf.referencia)
            if not tienda:
                return CreatePreingresoOutput(
                    success=False,
                    response=None,
                    preingreso_id=None,
                    message=f"No se encontró la tienda #{input_dto.datos_pdf.referencia}",
                    timestamp=datetime.now(),
                    boleta_usada=input_dto.datos_pdf.numero_boleta
                )

            # Construir el DTO inmutable
            preingreso_data = await CrearPreingresoBuilder.build(
                input_dto.datos_pdf,
                tienda,
                input_dto.archivo_adjunto
            )

            # Debug - datos enviados a la API:
            print("")
            print("🏷️Datos del PDF:")
            print(input_dto.datos_pdf)
            print("")
            print("🏷️Datos que serán enviados:")
            print(preingreso_data.to_api_body())
            print("")

            # Validar datos si se solicita
            if input_dto.validate_before_send:
                validation_errors = preingreso_data.validate_for_api()

                if validation_errors:
                    self.logger.warning(
                        "Validación de parámetros de crear preingreso fallida",
                        errors=validation_errors
                    )

                    return CreatePreingresoOutput(
                        success=False,
                        response=None,
                        preingreso_id=None,
                        message="Errores de validación en los parámetros",
                        errors=validation_errors,
                        timestamp=datetime.now(),
                        boleta_usada=input_dto.datos_pdf.numero_boleta
                    )

            # Crear preingreso en la API
            if self.retry_policy and input_dto.retry_on_failure:
                # Con política de reintentos
                response = await self.retry_policy.execute_with_retry(
                    self.repository.create_preingreso,
                    preingreso_data
                )
            else:
                # Sin reintentos
                response = await self.repository.create_preingreso(
                    preingreso_data
                )

            # Validar respuesta exitosa
            response.validate_success()

            # Extraer ID del preingreso creado
            preingreso_id = None
            consultar_reparacion = None
            consultar_guia = None
            tipo_preingreso_nombre = None
            garantia_nombre = None
            if response.has_json_body():
                consultar_reparacion = response.extract_data("consultar_reparacion", required=False)
                consultar_guia = response.extract_data("guia", required=False)
                tipo_preingreso_nombre = response.extract_data("tipo_preingreso", required=False)
                garantia_nombre = response.extract_data("garantia", required=False)
                preingreso_id = response.extract_data("boleta", required=False)
                if not preingreso_id:
                    preingreso_id = response.extract_data("orden_de_servicio", required=False)

            self.logger.info(
                "✅ Preingreso creado correctamente",
                numero_boleta=input_dto.datos_pdf.numero_boleta,
                preingreso_id=preingreso_id,
                response_time_ms=response.response_time_ms
            )

            return CreatePreingresoOutput(
                success=True,
                response=response,
                preingreso_id=preingreso_id,
                consultar_reparacion=consultar_reparacion,
                consultar_guia=consultar_guia,
                tipo_preingreso_nombre=tipo_preingreso_nombre,
                garantia_nombre=garantia_nombre,
                timestamp=datetime.now(),
                boleta_usada=input_dto.datos_pdf.numero_boleta
            )

        except APIValidationError as e:
            self.logger.error(
                "API validation error",
                numero_boleta=input_dto.datos_pdf.numero_boleta,
                error=str(e),
                code=e.code
            )

            return CreatePreingresoOutput(
                success=False,
                response=None,
                preingreso_id=None,
                message=str(e),
                errors=[str(e)],
                timestamp=datetime.now(),
                boleta_usada=input_dto.datos_pdf.numero_boleta
            )

        except APIException as e:
            self.logger.error(
                "API error",
                numero_boleta=input_dto.datos_pdf.numero_boleta,
                error=str(e),
                code=e.code
            )

            return CreatePreingresoOutput(
                success=False,
                response=None,
                preingreso_id=None,
                message=str(e),
                errors=[str(e)],
                timestamp=datetime.now(),
                boleta_usada=input_dto.datos_pdf.numero_boleta
            )

        except Exception as e:
            self.logger.exception(
                "Error inesperado creando el preingreso",
                numero_boleta=input_dto.datos_pdf.numero_boleta,
                error=str(e)
            )

            return CreatePreingresoOutput(
                success=False,
                response=None,
                preingreso_id=None,
                message=f"Error inesperado: {str(e)}",
                errors=[str(e)],
                timestamp=datetime.now(),
                boleta_usada=input_dto.datos_pdf.numero_boleta
            )

    async def _obtener_tienda_por_referencia(self, referencia: str) -> SucursalDTO | None:
        """
       Busca una tienda por su referencia y retorna solo los campos necesarios.

        Args:
            referencia: La referencia a buscar, obtenida desde el PDF

        Returns:
            Optional[SucursalDTO]
        """

        self.logger.info(
            "Busca la sucursal en la API",
            referencia=referencia
        )

        try:
            # Ejemplo de llamada a API
            response = await self.repository.listar_sucursales()

            if response.status_code == 200:

                # Buscar en la lista de tiendas
                tiendas = response.body.get("data", [])

                for tienda in tiendas:
                    if tienda.get("referencia") == referencia:
                        return SucursalDTO(
                            sucursal_codigo=tienda.get("codigo_sucursal"),
                            sucursal_division_1=tienda.get("tienda_division_1"),
                            sucursal_division_2=tienda.get("tienda_division_2"),
                            sucursal_division_3=tienda.get("tienda_division_3"),
                            sucursal_nombre=tienda.get("tienda_nombre"),
                            sucursal_direccion=tienda.get("tienda_direccion")
                        )

                # No se encontró
                return None

            elif response.status_code == 404:
                # Marca no existe
                return None

            else:
                self.logger.warning(f"Respuesta inesperada de API: {response.status_code}")
                return None

        except (AttributeError, TypeError, KeyError):
            # Si data no tiene el formato esperado
            return None
        except Exception as e:
            self.logger.error(f"Error en _buscar_en_api: {e}")
            raise
