"""
API Integration Context - Use Cases (Application Layer)
Casos de uso para crear un preingreso
"""
import re
from datetime import datetime
from typing import Optional, Dict, Tuple
from uuid import UUID

from api_integration.application.dtos import CreatePreingresoInput, CreatePreingresoOutput, SucursalDTO
from api_integration.domain.entities import PreingresoData
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

    @staticmethod
    def _extraer_nombres_apellidos(
            nombre_completo: str | None,
            nombre_contacto: str | None
    ) -> Dict[str, str]:
        """
        Extrae los apellidos y nombres de un nombre completo.

        - Si hay 3 o más partes: las dos primeras se consideran apellidos, el resto nombres.
        - Si hay 2 o menos partes: la primera es apellido, la segunda (si existe) es nombre.

        Args:
            nombre_completo (str | None): El nombre completo del cliente, como una sola cadena
            nombre_contacto (str | None): El nombre de contacto

        Returns:
            Dict[str, str]: Un diccionario con claves 'apellidos' y 'nombres'.
        """

        if not nombre_completo:
            return {
                'nombres': nombre_contacto or 'N/A',
                'apellidos': 'N/A'
            }

        partes = nombre_completo.split()
        num_partes = len(partes)

        if num_partes >= 3:
            apellidos = ' '.join(partes[:2])
            nombres = ' '.join(partes[2:])
        else:
            # Usar índices con valor por defecto vacío
            apellidos = partes[0] if num_partes > 0 else ''
            nombres = partes[1] if num_partes > 1 else ''

        return {
            'nombres': nombres,
            'apellidos': apellidos
        }

    # Función auxiliar para normalizar claves
    @staticmethod
    def _normalizar_clave(nombre: str) -> str:
        """
        Normaliza una cadena para ser usada como clave en el mapeo.
        Convierte a minúsculas y elimina espacios innecesarios.
        """
        # Convierte a minúsculas
        nombre_normalizado = nombre.lower()
        # Opcional: Remover espacios extras al inicio/fin y reemplazar múltiples espacios por uno solo
        nombre_normalizado = re.sub(r'\s+', ' ', nombre_normalizado.strip())
        # Opcional: Remover o reemplazar caracteres especiales si aplica
        # nombre_normalizado = re.sub(r'[^\w\s]', '', nombre_normalizado)
        return nombre_normalizado

    # Definir las constantes como atributos de clase
    TIPO_PREINGRESO_MAP: Dict[str, int] = {
        _normalizar_clave('Normal'): 7,
        _normalizar_clave('No'): 92,
        _normalizar_clave('C.S.R.'): 92,
        _normalizar_clave('C.S.R'): 92,
        _normalizar_clave('CSR'): 92,
        _normalizar_clave('DOA'): 8,
        _normalizar_clave('DAP'): 9,
    }

    GARANTIA_ID_MAP: Dict[str, int] = {
        _normalizar_clave('Normal'): 1,
        _normalizar_clave('No'): 2,
        _normalizar_clave('C.S.R.'): 4,
        _normalizar_clave('C.S.R'): 4,
        _normalizar_clave('CSR'): 4,
        _normalizar_clave('DOA'): 1,
        _normalizar_clave('DAP'): 1,
    }

    def __init__(
            self,
            api_ifrpro_repository: IApiIfrProRepository,
            retry_policy: Optional[IRetryPolicy] = None
    ):
        self.repository = api_ifrpro_repository
        self.retry_policy = retry_policy
        self.logger = logger.bind(use_case="CreatePreingreso")

    @log_execution_time
    async def execute(
            self,
            input_dto: CreatePreingresoInput
    ) -> CreatePreingresoOutput:
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
            tienda = await self._obtener_tienda_por_referencia(input_dto.datos_pdf.referencia.strip())
            if not tienda:
                return CreatePreingresoOutput(
                    success=False,
                    response=None,
                    preingreso_id=None,
                    message=f"No se encontró la tienda #{input_dto.datos_pdf.referencia}",
                    timestamp=datetime.now(),
                    boleta_usada=input_dto.datos_pdf.numero_boleta
                )

            # Obtener id de la marca
            marca_id = UUID('77983d40-5af3-417b-aef3-bcc9efc06a4f')  # Desconocida

            # Obtener id del modelo comercial
            modelo_comercial_id = UUID('910f491b-6c99-4225-bef8-83c85a83ae44')  # Desconocido

            # Obtener el tipo de preingreso y garantía (Llamas a la fn y desempaqueta directamente)
            tipo_preingreso_id, garantia_id = self._get_garantia_tipo_preingreso("Normal")

            # detalle_recepcion = nombre marca + nombre modelo + Daños + observaciones.
            detalle_recepcion = f"Marca:{input_dto.datos_pdf.marca_nombre.strip()}. Modelo:{input_dto.datos_pdf.modelo_nombre.strip()} Daño:{input_dto.datos_pdf.danos.strip()}. Obs:{input_dto.datos_pdf.observaciones.strip()}."

            # Obtener nombres y apellidos del propietario
            propietario = self._extraer_nombres_apellidos(input_dto.datos_pdf.cliente_nombre.strip(),
                                                          input_dto.datos_pdf.cliente_contacto.strip())

            # Extraer contenido del pdf que será enviado al request
            pdf_content = await input_dto.archivo_adjunto.leer_contenido()

            # Construir el DTO inmutable
            preingreso_data = PreingresoData(
                codigo_sucursal=tienda.sucursal_codigo,
                tipo_preingreso_id=str(tipo_preingreso_id),
                garantia_id=str(garantia_id),
                nombres_propietario=propietario["nombres"],
                apellidos_propietario=propietario["apellidos"],
                correo_propietario=input_dto.datos_pdf.cliente_correo.strip(),
                telefono1_propietario=input_dto.datos_pdf.cliente_telefono.strip(),
                division_1=tienda.sucursal_division_1,  # código provincia
                division_2=tienda.sucursal_division_2,  # código cantón
                division_3=tienda.sucursal_division_3,  # código distrito
                descripcion_division=tienda.sucursal_direccion,  # Dirección exacta de la tienda
                serie=input_dto.datos_pdf.serie.strip(),
                marca_id=marca_id,
                modelo_comercial_id=modelo_comercial_id,
                detalle_recepcion=detalle_recepcion,
                referencia=input_dto.datos_pdf.numero_transaccion.strip(),

                boleta_tienda=input_dto.datos_pdf.numero_boleta.strip(),

                fecha_compra=input_dto.datos_pdf.fecha_compra.strip(),
                otro_telefono_propietario=input_dto.datos_pdf.cliente_telefono2.strip(),
                numero_factura=input_dto.datos_pdf.factura.strip(),

                # Archivo adjunto
                pdf_filename=input_dto.archivo_adjunto.nombre_archivo,
                pdf_content=pdf_content
            )

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
            if response.has_json_body():
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
                logger.warning(f"Respuesta inesperada de API: {response.status_code}")
                return None

        except (AttributeError, TypeError, KeyError):
            # Si data no tiene el formato esperado
            return None
        except Exception as e:
            logger.error(f"Error en _buscar_en_api: {e}")
            raise

    def _get_garantia_tipo_preingreso(self, nombre_garantia: str) -> Tuple[int, int]:
        """
        Mapea un nombre de garantía a sus IDs correspondientes de tipo de preingreso y garantía.

        Returns:
            Tuple[int, int]: Una tupla (tipo_preingreso_id, garantia_id).
                             Por defecto, (7, 1) si no se encuentra coincidencia.
        """
        clave_normalizada = self._normalizar_clave(nombre_garantia)
        tipo_preingreso_id = self.__class__.TIPO_PREINGRESO_MAP.get(clave_normalizada, 7)
        garantia_id = self.__class__.GARANTIA_ID_MAP.get(clave_normalizada, 1)
        return tipo_preingreso_id, garantia_id
