import re
from typing import Dict, Tuple
from uuid import UUID

from api_integration.application.dtos import SucursalDTO, DatosExtraidosPDF, ArchivoAdjunto
from api_integration.domain.entities import PreingresoData


class CrearPreingresoBuilder:
    """Builder para construir PreingresoData paso a paso"""

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
    _TIPO_PREINGRESO_MAP: Dict[str, int] = {
        _normalizar_clave('Normal'): 7,
        _normalizar_clave('No'): 92,
        _normalizar_clave('C.S.R.'): 92,
        _normalizar_clave('C.S.R'): 92,
        _normalizar_clave('CSR'): 92,
        _normalizar_clave('DOA'): 8,
        _normalizar_clave('DAP'): 9,
    }

    _GARANTIA_ID_MAP: Dict[str, int] = {
        _normalizar_clave('Normal'): 1,
        _normalizar_clave('No'): 2,
        _normalizar_clave('C.S.R.'): 4,
        _normalizar_clave('C.S.R'): 4,
        _normalizar_clave('CSR'): 4,
        _normalizar_clave('DOA'): 1,
        _normalizar_clave('DAP'): 1,
    }

    @staticmethod
    async def build(datos_pdf: DatosExtraidosPDF, info_sucursal: SucursalDTO,
                    archivo_adjunto: ArchivoAdjunto) -> PreingresoData:
        """Construye la instancia final inmutable de PreingresoData"""

        # Obtener id de la marca
        marca_id = UUID('77983d40-5af3-417b-aef3-bcc9efc06a4f')  # Desconocida

        # Obtener id del modelo comercial
        modelo_comercial_id = UUID('910f491b-6c99-4225-bef8-83c85a83ae44')  # Desconocido

        # Obtener el tipo de preingreso y garantía (Llamas a la fn y desempaqueta directamente)
        tipo_preingreso_id, garantia_id = CrearPreingresoBuilder._get_garantia_tipo_preingreso("Normal")

        # detalle_recepcion = nombre marca + nombre modelo + Daños + observaciones.
        detalle_recepcion = f"Marca:{datos_pdf.marca_nombre if datos_pdf.marca_nombre is not None else ""}. Modelo:{datos_pdf.modelo_nombre if datos_pdf.modelo_nombre is not None else ""} Daño:{datos_pdf.danos if datos_pdf.danos is not None else ""}. Obs:{datos_pdf.observaciones if datos_pdf.observaciones is not None else ""}."

        # Obtener nombres y apellidos del propietario
        propietario = CrearPreingresoBuilder._extraer_nombres_apellidos(datos_pdf.cliente_nombre,
                                                                        datos_pdf.cliente_contacto)

        # Extraer contenido del pdf que será enviado al request
        pdf_content = await archivo_adjunto.leer_contenido()

        return PreingresoData(
            codigo_sucursal=info_sucursal.sucursal_codigo,
            tipo_preingreso_id=str(tipo_preingreso_id),
            garantia_id=str(garantia_id),
            nombres_propietario=propietario["nombres"],
            apellidos_propietario=propietario["apellidos"],
            correo_propietario=datos_pdf.cliente_correo,
            telefono1_propietario=datos_pdf.cliente_telefono,
            division_1=info_sucursal.sucursal_division_1,  # código provincia
            division_2=info_sucursal.sucursal_division_2,  # código cantón
            division_3=info_sucursal.sucursal_division_3,  # código distrito
            descripcion_division=info_sucursal.sucursal_direccion,  # Dirección exacta de la tienda
            serie=datos_pdf.serie,
            marca_id=marca_id,
            modelo_comercial_id=modelo_comercial_id,
            detalle_recepcion=detalle_recepcion,
            referencia=datos_pdf.numero_transaccion,

            boleta_tienda=datos_pdf.numero_boleta,

            fecha_compra=datos_pdf.fecha_compra,
            otro_telefono_propietario=datos_pdf.cliente_telefono2,
            numero_factura=datos_pdf.factura,

            # Archivo adjunto
            pdf_filename=archivo_adjunto.nombre_archivo,
            pdf_content=pdf_content
        )

    @staticmethod
    def _get_garantia_tipo_preingreso(nombre_garantia: str) -> Tuple[int, int]:
        """
        Mapea un nombre de garantía a su ID correspondiente de tipo de preingreso y garantía.

        Returns:
            Tuple[int, int]: Una tupla (tipo_preingreso_id, garantia_id).
                             Por defecto, (7, 1) si no se encuentra coincidencia.
        """
        clave_normalizada = CrearPreingresoBuilder._normalizar_clave(nombre_garantia)
        tipo_preingreso_id = CrearPreingresoBuilder._TIPO_PREINGRESO_MAP.get(clave_normalizada, 7)
        garantia_id = CrearPreingresoBuilder._GARANTIA_ID_MAP.get(clave_normalizada, 1)
        return tipo_preingreso_id, garantia_id
