import re
from datetime import datetime
from typing import Dict, Tuple
from uuid import UUID

from dateutil.relativedelta import relativedelta

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
        marca_id = CrearPreingresoBuilder._obtener_marca(datos_pdf.marca_nombre)

        # Obtener id del modelo comercial
        modelo_comercial_id = UUID('910f491b-6c99-4225-bef8-83c85a83ae44')  # Desconocido


        fecha_compra = datos_pdf.fecha_compra if datos_pdf.fecha_compra else "01/01/1970"

        fecha_compra = CrearPreingresoBuilder._convertir_fecha(fecha_compra)

        categoria_id = 5 # Desconocido
        tipo_dispositivo_id = 7 # Desconocido

        # Por default están sin garantía
        tipo_preingreso_id = 92
        garantia_id = 2
        msg_fecha_compra = ""

        if not datos_pdf.fecha_compra:
            # Si la fecha de compra no viene, entonces ingresa como "Sin Garantía"
            msg_fecha_compra = "La fecha de compra no viene en el documento PDF, ingresa 'Sin Garantía'"

        else:
            # Si la fecha de compra No ha excedido un año
            if not CrearPreingresoBuilder._es_mayor_a_un_ano(fecha_compra):

                # Intenta obtener los datos desde el nombre de la Garantía del PDF
                tipo_preingreso_id, garantia_id = (
                    CrearPreingresoBuilder._validar_garantia(
                        CrearPreingresoBuilder._limpiar_texto(datos_pdf.garantia_nombre)
                    )
                )
            else:
                # Si la fecha de compra excede un año, entonces ingresa como "Sin Garantía".
                msg_fecha_compra = f"La fecha de compra '{fecha_compra}' excede un año, ingresa 'Sin Garantía'"

        # detalle_recepcion = nombre marca + nombre modelo + Daños + observaciones.
        marca_nombre = CrearPreingresoBuilder._limpiar_texto(datos_pdf.marca_nombre)
        modelo_nombre = CrearPreingresoBuilder._limpiar_texto(datos_pdf.modelo_nombre)
        danos = CrearPreingresoBuilder._limpiar_texto(datos_pdf.danos)
        observaciones = CrearPreingresoBuilder._limpiar_texto(datos_pdf.observaciones)

        detalle_recepcion = f"Marca:{marca_nombre} | Modelo:{modelo_nombre} | Daño:{danos} | Obs:{observaciones} | {msg_fecha_compra}".rstrip(
            ' |') + "."

        # Obtener nombres y apellidos del propietario
        propietario = CrearPreingresoBuilder._extraer_nombres_apellidos(
            CrearPreingresoBuilder._limpiar_texto(datos_pdf.cliente_nombre, True),
            CrearPreingresoBuilder._limpiar_texto(datos_pdf.cliente_contacto, True)
        )

        # Extraer contenido del pdf que será enviado al request
        pdf_content = await archivo_adjunto.leer_contenido()

        return PreingresoData(
            codigo_sucursal=info_sucursal.sucursal_codigo,
            tipo_preingreso_id=str(tipo_preingreso_id),
            garantia_id=str(garantia_id),
            categoria_id=str(categoria_id),
            tipo_dispositivo_id=str(tipo_dispositivo_id),
            nombres_propietario=propietario["nombres"],
            apellidos_propietario=propietario["apellidos"],
            correo_propietario=CrearPreingresoBuilder._limpiar_texto(datos_pdf.cliente_correo),
            telefono1_propietario=CrearPreingresoBuilder._limpiar_texto(datos_pdf.cliente_telefono),
            division_1=info_sucursal.sucursal_division_1,  # código provincia
            division_2=info_sucursal.sucursal_division_2,  # código cantón
            division_3=info_sucursal.sucursal_division_3,  # código distrito
            descripcion_division=info_sucursal.sucursal_direccion,  # Dirección exacta de la tienda
            serie=CrearPreingresoBuilder._agregar_sufijo_si_pend(datos_pdf.serie, datos_pdf.numero_boleta),
            marca_id=marca_id,
            modelo_comercial_id=modelo_comercial_id,
            detalle_recepcion=detalle_recepcion,
            referencia=f"{datos_pdf.numero_boleta}/{datos_pdf.numero_transaccion}",

            boleta_tienda=datos_pdf.numero_boleta,

            fecha_compra=fecha_compra,
            otro_telefono_propietario=CrearPreingresoBuilder._limpiar_texto(datos_pdf.cliente_telefono2, True),
            numero_factura=CrearPreingresoBuilder._limpiar_texto(datos_pdf.factura, True),

            # Archivo adjunto
            pdf_filename=CrearPreingresoBuilder._limpiar_texto(archivo_adjunto.nombre_archivo),
            pdf_content=pdf_content
        )

    @staticmethod
    def _validar_garantia(nombre_garantia: str) -> Tuple[int, int]:
        """
        Mapea un nombre de garantía a su ID correspondiente de tipo de preingreso y garantía.
        Si no se encuentra coincidencia, entonces por defecto devuelve los ids de 'Sin garantía'.

        Returns:
            Tuple[int, int]: Una tupla (tipo_preingreso_id, garantia_id).
                             Por defecto, (92, 2) si no se encuentra coincidencia.
        """
        clave_normalizada = CrearPreingresoBuilder._normalizar_clave(nombre_garantia)
        tipo_preingreso_id = CrearPreingresoBuilder._TIPO_PREINGRESO_MAP.get(clave_normalizada, 92)
        garantia_id = CrearPreingresoBuilder._GARANTIA_ID_MAP.get(clave_normalizada, 2)
        return tipo_preingreso_id, garantia_id

    @staticmethod
    def _convertir_fecha(fecha_ddmmyyyy: str) -> str:
        """
        Convierte una fecha del formato DD/MM/YYYY al formato YYYY-MM-DD.

        Args:
            fecha_ddmmyyyy (str): La fecha en formato DD/MM/YYYY.

        Returns:
            str: La fecha en formato YYYY-MM-DD.

        Raises:
            ValueError: Si la cadena de entrada no coincide con el formato esperado.
        """
        fecha_dt = datetime.strptime(fecha_ddmmyyyy, "%d/%m/%Y")
        return fecha_dt.strftime("%Y-%m-%d")

    @staticmethod
    def _agregar_sufijo_si_pend(valor: str, sufijo: str) -> str:
        """
        Añade un sufijo a una cadena si su valor es 'PEND'.

        Args:
            valor (str): La cadena a evaluar.
            sufijo (str): El sufijo a añadir si valor es 'PEND'.

        Returns:
            str: La cadena original con el sufijo añadido si era 'PEND',
                 o la cadena original sin cambios en caso contrario.
        """
        if valor == 'PEND':
            return f"{valor}::{sufijo}"
        else:
            return valor

    @staticmethod
    def _limpiar_texto(texto: str, mantener_none: bool = False) -> str | None:
        """
        Limpia un texto aplicando las siguientes operaciones:
        1. Si el texto es None y mantener_none es True, lo devuelve como None.
               Si el texto es None y mantener_none es False, lo devuelve como una cadena vacía.
               Si el texto es una cadena vacía, lo devuelve como una cadena vacía.
        2. Elimina el BOM (Byte Order Mark) de UTF-8.
        3. Reemplaza caracteres invisibles (como tabulaciones, saltos de línea, etc.) con un solo espacio.
        4. Elimina espacios en blanco al inicio y al final del texto.
        5. Elimina puntos finales al final del texto.

        Args:
            texto (Optional[str]): El texto a limpiar. Puede ser None.
            mantener_none (bool): Si es True y 'texto' es None, retorna None.
                                  Si es False (por defecto) o 'texto' no es None, limpia normalmente.

        Returns:
            Optional[str]: El texto limpio, una cadena vacía, o None si mantener_none=True y texto era None.
        """

        # Si el texto es None o una cadena vacía
        if not texto:  # Esto evalúa a True si texto es None, "", 0, [], {}, etc.
            if texto is None and mantener_none:
                return None
            return ""

        # Eliminar el BOM de UTF-8
        if texto.startswith('\ufeff'):
            texto = texto[1:]

        # Reemplazar uno o más caracteres invisibles (espacios, tabs, newlines, etc.) con un solo espacio
        texto = re.sub(r'\s+', ' ', texto)

        # 4. Eliminar espacios al inicio y final
        texto = texto.strip()

        # 5. Eliminar puntos finales
        texto = texto.rstrip('.')

        return texto

    @staticmethod
    def _es_mayor_a_un_ano(fecha_str: str, formato_fecha: str = "%Y-%m-%d") -> bool:
        """
        Verifica si una fecha es mayor a un año desde hoy (considera años bisiestos).

        Args:
            fecha_str: Fecha en formato "dd/mm/yyyy"

        Returns:
            True si han pasado más de un año
        """
        try:
            fecha = datetime.strptime(fecha_str, formato_fecha)
            hoy = datetime.now()

            # Calcular la fecha hace exactamente un año usando relativedelta (más preciso con años bisiestos)
            hace_un_ano = hoy - relativedelta(years=1)

            # Verificar si la fecha es anterior a hace un año
            return fecha < hace_un_ano

        except ValueError:
            return False

    @staticmethod
    def _obtener_marca(nombre_marca_pdf: str|None) -> UUID:
        if not nombre_marca_pdf:
            return UUID('77983d40-5af3-417b-aef3-bcc9efc06a4f')
        else:
            # TODO: Crear logica para determinar el id de la marca...
            return UUID('77983d40-5af3-417b-aef3-bcc9efc06a4f')
