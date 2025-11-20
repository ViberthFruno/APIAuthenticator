# crear_preingreso_builder.py

import re
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from uuid import UUID

from dateutil.relativedelta import relativedelta

from api_integration.application.dtos import SucursalDTO, DatosExtraidosPDF, ArchivoAdjunto
from api_integration.domain.entities import PreingresoData
# Importar función global para cargar configuración de categorías
# IMPORTANTE: Esta función maneja correctamente las rutas tanto en PyInstaller como en desarrollo
from config_manager import get_categorias_config


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

    @staticmethod
    def _detectar_garantia_en_correo(cuerpo_correo: str | None) -> Tuple[bool, str | None]:
        """
        Detecta si en el cuerpo del correo viene la palabra 'Garantia' y una opción válida.

        Args:
            cuerpo_correo: Texto del cuerpo del correo electrónico

        Returns:
            Tuple[bool, str | None]: (encontrada, garantia)
                - encontrada: True si se encontró una garantía válida en el correo
                - garantia: Nombre de la garantía encontrada (normalizado) o None
        """
        if not cuerpo_correo:
            return False, None

        # Opciones válidas de garantía (case insensitive)
        # Mapeo: CLAVE_BUSQUEDA -> Valor normalizado
        opciones_validas = {
            'NORMAL': 'Normal',
            'NO': 'No',
            'C.S.R.': 'C.S.R.',
            'C.S.R': 'C.S.R.',
            'CSR': 'C.S.R.',
            'DOA': 'DOA',
            'STOCK': 'STOCK',
            'DAP': 'DAP'
        }

        try:
            # Normalizar el texto a mayúsculas para búsqueda
            cuerpo_upper = cuerpo_correo.upper()

            # Buscar "GARANTIA" o "GARANTÍA" en el texto
            if re.search(r'GARANT[IÍ]A', cuerpo_upper):
                # Buscar una de las opciones válidas
                for opcion_upper, opcion_normalizada in opciones_validas.items():
                    # Buscar la opción con límites de palabra
                    pattern = r'\b' + re.escape(opcion_upper) + r'\b'
                    if re.search(pattern, cuerpo_upper):
                        return True, opcion_normalizada

                # Se encontró 'Garantia' pero sin opción válida
                return False, None
            else:
                return False, None

        except Exception:
            return False, None

    # Definir las constantes como atributos de clase
    _TIPO_PREINGRESO_MAP: Dict[str, int] = {
        _normalizar_clave('Normal'): 7,
        _normalizar_clave('No'): 92,
        _normalizar_clave('C.S.R.'): 92,
        _normalizar_clave('C.S.R'): 92,
        _normalizar_clave('CSR'): 92,
        _normalizar_clave('DOA'): 8,
        _normalizar_clave('STOCK'): 8,
        _normalizar_clave('DAP'): 9,
    }

    _GARANTIA_ID_MAP: Dict[str, int] = {
        _normalizar_clave('Normal'): 1,
        _normalizar_clave('No'): 2,
        _normalizar_clave('C.S.R.'): 4,
        _normalizar_clave('C.S.R'): 4,
        _normalizar_clave('CSR'): 4,
        _normalizar_clave('DOA'): 1,
        _normalizar_clave('STOCK'): 1,
        _normalizar_clave('DAP'): 1,
    }

    # Tipos de dispositivo hardcodeados (lista fija que no cambia)
    # Estos son los únicos IDs válidos que la API acepta
    TIPOS_DISPOSITIVO_IDS: Dict[str, int] = {
        'Celulares y Tablets': 1,
        'Monitores': 2,
        'Cocinas': 3,
        'Refrigeradoras': 4,
        'Licuadoras': 6,
        'Desconocido': 7,
        'Audífonos': 8,
        'Relojes': 9,
        'Cable USB': 10,
        'Cubo': 11,
        'Proyector': 13,
        'Parlante': 15,
        'Mouse': 16,
        'Scooter': 17,
        'Robot de Limpieza': 18,
        'Pantallas': 19,
        'Impresora': 20,
        'Laptop': 21,
        'Cámaras de seguridad': 23,
        'Router': 24,
        'Drones': 25,
        'Baterías': 26,
        'Gaming': 27,
        'Teclado': 28,
        'Estuches': 29,
        'Audio/video': 32,
        'Internet Satelital': 33,
        'Tarjeta de memoria externa': 34,
        'No encontrado': 36
    }

    # Categorías hardcodeadas (solo categoria_id, sin tipo_dispositivo_id)
    _CATEGORIAS_CONFIG: Dict = {
        "Móviles": {"id": 1, "palabras_clave": []},
        "Hogar": {"id": 3, "palabras_clave": []},
        "Cómputo": {"id": 4, "palabras_clave": []},
        "Desconocido": {"id": 5, "palabras_clave": []},
        "Accesorios": {"id": 6, "palabras_clave": []},
        "Transporte": {"id": 7, "palabras_clave": []},
        "Seguridad": {"id": 8, "palabras_clave": []},
        "Entretenimiento": {"id": 10, "palabras_clave": []},
        "Telecomunicaciones": {"id": 11, "palabras_clave": []},
        "No encontrado": {"id": 12, "palabras_clave": []}
    }

    @staticmethod
    def _cargar_config_categorias() -> Dict:
        """
        Carga la configuración de categorías usando la función global de config_manager.
        Compatible con PyInstaller y desarrollo.

        Returns:
            Dict: Configuración de categorías con IDs y palabras clave
        """
        # Crear una copia de las categorías hardcodeadas por defecto
        categorias = {nombre: {"id": datos["id"], "palabras_clave": datos["palabras_clave"].copy()}
                      for nombre, datos in CrearPreingresoBuilder._CATEGORIAS_CONFIG.items()}

        try:
            # Usar la función global que maneja correctamente las rutas en PyInstaller y desarrollo
            config = get_categorias_config()
            categorias_guardadas = config.get('categorias', {})

            # Importar solo las palabras clave de las categorías guardadas
            for nombre_cat, datos_cat in categorias_guardadas.items():
                if nombre_cat in categorias:
                    palabras_guardadas = datos_cat.get('palabras_clave', [])
                    # Mantener estructura completa con tipo_dispositivo_id
                    palabras_completas = []
                    for palabra_data in palabras_guardadas:
                        if isinstance(palabra_data, str):
                            # Formato antiguo: solo string, usar tipo desconocido
                            palabras_completas.append({
                                'palabra': palabra_data,
                                'tipo_dispositivo_id': 7  # Desconocido
                            })
                        elif isinstance(palabra_data, dict):
                            # Formato nuevo: dict con palabra y tipo_dispositivo_id
                            palabras_completas.append({
                                'palabra': palabra_data.get('palabra', ''),
                                'tipo_dispositivo_id': palabra_data.get('tipo_dispositivo_id', 7)  # Default: Desconocido
                            })
                    categorias[nombre_cat]['palabras_clave'] = palabras_completas

            print(f"[DEBUG CrearPreingresoBuilder] ✓ Configuración de categorías cargada correctamente")
            print(f"[DEBUG CrearPreingresoBuilder] Total categorías: {len(categorias)}")
            for nombre_cat, datos_cat in categorias.items():
                num_palabras = len(datos_cat.get('palabras_clave', []))
                print(f"[DEBUG CrearPreingresoBuilder]   - {nombre_cat}: {num_palabras} palabras clave")

        except Exception as e:
            # Si hay error, usar categorías hardcodeadas sin palabras clave
            print(f"[DEBUG CrearPreingresoBuilder] ⚠️ Error al cargar config: {str(e)}")
            print(f"[DEBUG CrearPreingresoBuilder] Usando categorías hardcodeadas sin palabras clave")

        return categorias

    @staticmethod
    def _detectar_categoria(descripcion_producto: Optional[str]) -> Tuple[int, int]:
        """
        Detecta la categoría y tipo de dispositivo del producto basándose en palabras clave en la descripción.
        Prioriza coincidencias más largas (más específicas) sobre coincidencias cortas.

        Args:
            descripcion_producto: Descripción del producto extraída del PDF

        Returns:
            Tuple[int, int]: (categoria_id, tipo_dispositivo_id)
                           - categoria_id: ID de la categoría detectada (12 = "No encontrado" si no hay coincidencia)
                           - tipo_dispositivo_id: ID del tipo de dispositivo configurado en el JSON para esa palabra clave
                                                 (7 = "Desconocido" si no hay coincidencia)
        """
        # Tipo de dispositivo por defecto (cuando no se encuentra coincidencia)
        TIPO_DISPOSITIVO_DESCONOCIDO = 7

        # Si no hay descripción, retornar "No encontrado"
        if not descripcion_producto:
            return 12, TIPO_DISPOSITIVO_DESCONOCIDO  # Categoría "No encontrado", Tipo Dispositivo Desconocido

        # Cargar configuración de categorías hardcodeadas
        categorias_config = CrearPreingresoBuilder._cargar_config_categorias()

        if not categorias_config:
            # Si no hay configuración, retornar "No encontrado"
            return 12, TIPO_DISPOSITIVO_DESCONOCIDO

        # Normalizar la descripción para búsqueda case-insensitive
        descripcion_normalizada = descripcion_producto.upper().strip()

        # Recopilar todas las palabras clave con sus categorías y tipos de dispositivo
        # y ordenarlas por longitud descendente (más largas primero)
        todas_palabras = []
        for nombre_categoria, config_categoria in categorias_config.items():
            categoria_id = config_categoria.get('id')
            palabras_clave = config_categoria.get('palabras_clave', [])

            for palabra_data in palabras_clave:
                # Las palabras clave ahora son diccionarios con palabra y tipo_dispositivo_id
                if isinstance(palabra_data, dict):
                    palabra = palabra_data.get('palabra', '')
                    tipo_dispositivo_id = palabra_data.get('tipo_dispositivo_id', TIPO_DISPOSITIVO_DESCONOCIDO)

                    palabra_normalizada = palabra.upper().strip()
                    if palabra_normalizada:  # Ignorar palabras vacías
                        todas_palabras.append((palabra_normalizada, categoria_id, tipo_dispositivo_id))

        # Ordenar por longitud descendente (más largas primero)
        todas_palabras.sort(key=lambda x: len(x[0]), reverse=True)

        # Buscar coincidencias con palabras clave ordenadas
        for palabra_normalizada, categoria_id, tipo_dispositivo_id in todas_palabras:
            # Si la palabra clave está contenida en la descripción, retornar la categoría y tipo de dispositivo
            if palabra_normalizada in descripcion_normalizada:
                return categoria_id, tipo_dispositivo_id

        # Si no se encontró ninguna coincidencia, retornar "No encontrado"
        return 12, TIPO_DISPOSITIVO_DESCONOCIDO  # Categoría "No encontrado", Tipo Dispositivo Desconocido

    @staticmethod
    async def build(datos_pdf: DatosExtraidosPDF, info_sucursal: SucursalDTO,
                    archivo_adjunto: ArchivoAdjunto) -> PreingresoData:
        """Construye la instancia final inmutable de PreingresoData"""

        # Obtener id y nombre canónico de la marca
        marca_id, marca_nombre_canonico = CrearPreingresoBuilder._obtener_marca(datos_pdf.marca_nombre)

        # Obtener id del modelo comercial
        modelo_comercial_id = UUID('910f491b-6c99-4225-bef8-83c85a83ae44')  # Desconocido

        numero_factura = CrearPreingresoBuilder._limpiar_texto(datos_pdf.factura, True)

        if not numero_factura:
            numero_factura = "N/A"

        # Detectar categoría y tipo de dispositivo automáticamente basándose en la descripción del producto
        categoria_id, tipo_dispositivo_id = CrearPreingresoBuilder._detectar_categoria(datos_pdf.producto_descripcion)

        cuerpo_correo = CrearPreingresoBuilder._limpiar_texto(datos_pdf.cuerpo_correo)

        pdf_tiene_fecha_compra = datos_pdf.fecha_compra is not None and datos_pdf.fecha_compra != ""

        fecha_compra = CrearPreingresoBuilder._convertir_fecha(
            datos_pdf.fecha_compra) if pdf_tiene_fecha_compra else '1970-01-01'

        tipo_preingreso_id, garantia_id, msg_fecha_compra = (
            CrearPreingresoBuilder._determinar_tipo_garantia(
                pdf_tiene_fecha_compra,
                fecha_compra,
                CrearPreingresoBuilder._limpiar_texto(datos_pdf.garantia_nombre),
                cuerpo_correo,
                numero_factura,
                CrearPreingresoBuilder._limpiar_texto(datos_pdf.observaciones)
            )
        )

        # detalle_recepcion = nombre marca + nombre modelo + Daños + observaciones + cuerpo del correo.
        # Usar el nombre canónico de la marca (no el del PDF que puede venir en mayúsculas/minúsculas)
        modelo_nombre = CrearPreingresoBuilder._limpiar_texto(datos_pdf.modelo_nombre)
        danos = CrearPreingresoBuilder._limpiar_texto(datos_pdf.danos)
        observaciones = CrearPreingresoBuilder._limpiar_texto(datos_pdf.observaciones)

        # Construir detalle base
        detalle_recepcion = f"Marca:{marca_nombre_canonico} | Modelo:{modelo_nombre} | Daño:{danos} | Obs:{observaciones} | {msg_fecha_compra}".rstrip(
            ' |')

        # Agregar cuerpo del correo si existe
        if cuerpo_correo:
            detalle_recepcion += f" | Correo:{cuerpo_correo}"

        # Agregar punto final
        detalle_recepcion += "."

        # Obtener nombres y apellidos del propietario
        propietario = CrearPreingresoBuilder._extraer_nombres_apellidos(
            CrearPreingresoBuilder._limpiar_texto(datos_pdf.cliente_nombre, True),
            CrearPreingresoBuilder._limpiar_texto(datos_pdf.cliente_contacto, True)
        )

        # Si es DOA entonces la factura va en blanco:
        if tipo_preingreso_id == 8:
            numero_factura = ""

        # TODO distribuidor_id no debe venir de datos_pdf, ya que se está mezclando lógica de negocios
        # entre la capa gui/pdf y la de crear preingreso (código espagueti).
        # La función _detectar_proveedor_en_correo que está en email_manager.py debe ir en este archivo.
        distribuidor_id = datos_pdf.distribuidor_id

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
            distribuidor_id=distribuidor_id,
            otro_telefono_propietario=CrearPreingresoBuilder._limpiar_texto(datos_pdf.cliente_telefono2, True),
            numero_factura=numero_factura,

            # Archivo adjunto
            pdf_filename=CrearPreingresoBuilder._limpiar_texto(archivo_adjunto.nombre_archivo),
            pdf_content=pdf_content
        )

    @staticmethod
    def _determinar_tipo_garantia(
            pdf_tiene_fecha_compra: bool,
            fecha_compra: str,
            garantia_desde_pdf: str,
            cuerpo_correo: str | None,
            factura: str | None,
            observaciones: str | None
    ) -> Tuple[int, int, str]:
        """
        Determina el tipo de preingreso y garantía basándose en múltiples fuentes de información.

        JERARQUÍA DE PRIORIDADES:
        1. Garantía del correo electrónico (si el usuario la especifica en el correo)
        2. Casos especiales (STOCK en factura/observaciones)
        3. Garantía del PDF (valor extraído del documento)
        4. Validaciones de fecha (DAP, sin fecha, mayor a 1 año)

        Args:
            pdf_tiene_fecha_compra: Si el PDF contiene fecha de compra
            fecha_compra: Fecha de compra en formato YYYY-MM-DD
            garantia_desde_pdf: Tipo de garantía extraído del PDF
            cuerpo_correo: Texto completo del cuerpo del correo (opcional)
            factura: Número de factura (opcional)
            observaciones: Observaciones del PDF (opcional)

        Returns:
            Tuple[int, int, str]: (tipo_preingreso_id, garantia_id, mensaje)
                - tipo_preingreso_id: ID del tipo de preingreso (7=Normal, 8=DOA/STOCK, 9=DAP, 92=Sin Garantía)
                - garantia_id: ID de la garantía (1=Normal, 2=Sin Garantía, 4=C.S.R.)
                - mensaje: Mensaje descriptivo del proceso de determinación
        """

        # ========================================================================
        # PRIORIDAD 1: Garantía del correo electrónico
        # ========================================================================
        # Si el usuario especifica garantía en el cuerpo del correo, tiene prioridad máxima
        garantia_encontrada_correo, garantia_correo = CrearPreingresoBuilder._detectar_garantia_en_correo(cuerpo_correo)

        if garantia_encontrada_correo and garantia_correo:
            # Normalizar y mapear la garantía del correo
            clave_normalizada = CrearPreingresoBuilder._normalizar_clave(garantia_correo)
            tipo_preingreso_id = CrearPreingresoBuilder._TIPO_PREINGRESO_MAP.get(clave_normalizada, 92)
            garantia_id = CrearPreingresoBuilder._GARANTIA_ID_MAP.get(clave_normalizada, 2)

            # Aplicar validaciones de fecha incluso si viene del correo
            # Si no es 'C.S.R.' (92) y es DAP, retornar como DAP
            if tipo_preingreso_id != 92 and CrearPreingresoBuilder._es_dap(fecha_compra):
                return 9, 1, f"Garantía '{garantia_correo}' detectada en correo, ajustada a DAP por fecha de compra"

            # Si no hay fecha de compra, ingresar como "Sin Garantía" excepto si es C.S.R.
            if not pdf_tiene_fecha_compra and tipo_preingreso_id != 92:
                return 92, 2, f"Garantía '{garantia_correo}' detectada en correo, pero sin fecha de compra → 'Sin Garantía'"

            # Si la fecha excede un año, ingresar como "Sin Garantía" excepto si es C.S.R.
            if pdf_tiene_fecha_compra and tipo_preingreso_id != 92 and CrearPreingresoBuilder._es_mayor_a_un_ano(fecha_compra):
                return 92, 2, f"Garantía '{garantia_correo}' detectada en correo, pero fecha excede 1 año → 'Sin Garantía'"

            return tipo_preingreso_id, garantia_id, f"Garantía '{garantia_correo}' detectada en cuerpo del correo (prioridad alta)"

        # ========================================================================
        # PRIORIDAD 2: Casos especiales - STOCK
        # ========================================================================
        # Si en factura u observaciones viene "STOCK", es DOA/STOCK
        la_factura = factura if factura else ""
        la_factura = CrearPreingresoBuilder._normalizar_clave(la_factura)

        la_observacion = observaciones if observaciones else ""
        la_observacion = CrearPreingresoBuilder._normalizar_clave(la_observacion)

        if 'stock' in la_factura or 'stock' in la_observacion:
            return 8, 1, "Detectado 'STOCK' en factura/observaciones → DOA/STOCK"

        # ========================================================================
        # PRIORIDAD 3: Garantía del PDF
        # ========================================================================
        # Si no hay garantía del correo, usar la del PDF
        clave_normalizada = CrearPreingresoBuilder._normalizar_clave(garantia_desde_pdf)
        tipo_preingreso_id = CrearPreingresoBuilder._TIPO_PREINGRESO_MAP.get(clave_normalizada, 92)
        garantia_id = CrearPreingresoBuilder._GARANTIA_ID_MAP.get(clave_normalizada, 2)

        # ========================================================================
        # PRIORIDAD 4: Validaciones de fecha
        # ========================================================================
        # Si no es 'C.S.R.' (92) y es DAP (< 7 días), retornar como DAP
        if tipo_preingreso_id != 92 and CrearPreingresoBuilder._es_dap(fecha_compra):
            return 9, 1, f"Garantía del PDF: '{garantia_desde_pdf}', ajustada a DAP por fecha de compra < 7 días"

        # Si la fecha de compra no viene, ingresar como "Sin Garantía"
        if not pdf_tiene_fecha_compra:
            return 92, 2, "La fecha de compra no viene en el documento PDF → 'Sin Garantía'"

        # Si la fecha de compra ha excedido un año, ingresar como "Sin Garantía"
        if CrearPreingresoBuilder._es_mayor_a_un_ano(fecha_compra):
            return 92, 2, f"La fecha de compra '{fecha_compra}' excede un año → 'Sin Garantía'"

        # Si todo está OK, retornar los IDs correspondientes
        return tipo_preingreso_id, garantia_id, f"Garantía del PDF: '{garantia_desde_pdf}'"

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

    # Mapeo de marcas conocidas: clave normalizada -> (UUID, nombre_canónico)
    _MARCA_MAP: Dict[str, Tuple[UUID, str]] = {
        'acer': (UUID('850f6072-e272-42e5-83ff-31ce2f058178'), 'Acer'),
        'alcatel': (UUID('ae81eeff-28b8-4a54-b10a-d622ee60634c'), 'Alcatel'),
        'amazon': (UUID('d5f45248-8370-49cb-bc87-34053aed1e76'), 'AMAZON'),
        'apple': (UUID('25db474e-90b3-4e4c-8a69-3d1c78ffe836'), 'Apple'),
        'dell': (UUID('2b50b001-b4f5-44ed-8a3e-e81a84003543'), 'Dell'),
        'dji': (UUID('097054cc-2b8a-42a1-ac19-7c83b2dfee86'), 'DJI'),
        'epson': (UUID('e56bb0c8-b06b-4c14-889b-880ab46848f2'), 'Epson'),
        'ezviz': (UUID('372474e1-ba9c-4000-a942-cab0265dea3e'), 'EZVIZ'),
        'forza': (UUID('96ae0653-b21e-447d-95bb-b1adbfe1c10a'), 'FORZA'),
        'fuji': (UUID('a9e615f6-f03d-41cb-9ff6-b7e950c9db87'), 'FUJI'),
        'google': (UUID('689a255c-75e5-46b9-b9b6-b8855f639782'), 'Google'),
        'gopro': (UUID('eddc053f-1b63-4270-80d3-bfbf4f3346ea'), 'GoPro'),
        'harman': (UUID('b8264f25-7cf1-41fb-8e90-fa295bf98840'), 'Harman'),
        'honor': (UUID('8e34a6fd-74a3-4d78-bac2-02b4634d1e8d'), 'Honor'),
        'house of marley': (UUID('80d0ec6e-b80b-4f3b-8429-4d69e7ff0876'), 'House Of Marley'),
        'hp': (UUID('ada6f0eb-c1dc-4402-9d40-29fc2d285937'), 'HP'),
        'huawei': (UUID('498175ed-ef26-4132-9652-72c92e16bd96'), 'Huawei'),
        'infinix': (UUID('59c3667b-e03a-43fc-8ae4-9cd65f778085'), 'Infinix'),
        'jabra': (UUID('44146bc5-4004-4b5e-b4d6-075376fc5735'), 'JABRA'),
        'jbl': (UUID('607c9785-0cd9-4b7d-9fb0-d6920a0043fe'), 'JBL'),
        'kingston': (UUID('bfc3b084-e71c-48a6-9928-f23c8a63fa91'), 'Kingston'),
        'klip xtreme': (UUID('119d5b6c-526d-4831-8add-78a69fd68633'), 'Klip Xtreme'),
        'lenovo': (UUID('c86b5fef-f861-4b0f-aedf-9956492efdea'), 'Lenovo'),
        'lg electronics': (UUID('fe112900-6b24-4b15-94fc-766ddc2c5163'), 'LG Electronics'),
        'lg': (UUID('fe112900-6b24-4b15-94fc-766ddc2c5163'), 'LG Electronics'),
        'linksys': (UUID('16964600-d7a2-4a34-89c3-51b22d203b2c'), 'Linksys'),
        'logitech': (UUID('86a0db06-35a1-411c-8f82-43318cfaf03b'), 'Logitech'),
        'marley': (UUID('48e8b2ca-6091-487c-9650-bea2cddea6f6'), 'Marley'),
        'motorola': (UUID('762729da-aad5-4afd-8992-a6be607b36a2'), 'Motorola'),
        'nexts': (UUID('2e58ebd9-a905-45f7-adf2-bac38667087f'), 'Nexts'),
        'nexxt solution': (UUID('95a92712-ccee-4dc9-ac5f-27a7f56ac504'), 'NEXXT SOLUTION'),
        'nexxt': (UUID('95a92712-ccee-4dc9-ac5f-27a7f56ac504'), 'NEXXT SOLUTION'),
        'nokia': (UUID('c418968e-8c1e-4df8-907f-ef4a57ff3d7f'), 'Nokia'),
        'oppo': (UUID('86912284-be1e-4121-83e4-f213cfc76689'), 'Oppo'),
        'primus': (UUID('00cdc7bc-fc02-4692-8668-b8fe15b52f90'), 'PRIMUS'),
        'realme': (UUID('327e29bc-645e-4bd4-8246-c221c3d37a61'), 'Realme'),
        'samsung': (UUID('699177a3-d4bb-4569-9eed-25cc2a062e61'), 'Samsung'),
        'starlink': (UUID('5a140b3b-2fb9-4cee-90c8-09a0f238c979'), 'Starlink'),
        'tcl': (UUID('b0ff71bd-ac26-42db-b7f9-61cb36ca6573'), 'TCL'),
        'tecno': (UUID('9773f251-639a-4aa7-886f-1ad55c38cf0a'), 'Tecno'),
        'toch mobile': (UUID('17158ec4-d8c4-4872-9ec7-caffdeb2dc02'), 'Toch Mobile'),
        'toch': (UUID('17158ec4-d8c4-4872-9ec7-caffdeb2dc02'), 'Toch Mobile'),
        'tp-link': (UUID('82da3186-bb48-479e-819c-208cc0582165'), 'TP-link'),
        'tplink': (UUID('82da3186-bb48-479e-819c-208cc0582165'), 'TP-link'),
        'xiaomi': (UUID('f2a569c3-1f5f-4657-8774-d0666e5c043f'), 'Xiaomi'),
        'zte': (UUID('9e7d3e2c-c404-414f-8dee-e28e513ce46b'), 'ZTE'),
    }

    @staticmethod
    def _obtener_marca(nombre_marca_pdf: str | None) -> Tuple[UUID, str]:
        """
        Obtiene el UUID y nombre canónico de la marca basándose en el nombre extraído del PDF.

        Args:
            nombre_marca_pdf: Nombre de la marca extraído del PDF (puede venir en cualquier capitalización)

        Returns:
            Tupla (UUID, nombre_canónico) de la marca si se encuentra coincidencia,
            (UUID genérico, "Desconocido") si no coincide

        """
        # UUID y nombre para marca desconocida
        UUID_GENERICO = UUID('77983d40-5af3-417b-aef3-bcc9efc06a4f')
        NOMBRE_GENERICO = 'Desconocida'

        if not nombre_marca_pdf:
            return UUID_GENERICO, NOMBRE_GENERICO

        # Normalizar el nombre de la marca del PDF para la búsqueda
        marca_normalizada = CrearPreingresoBuilder._normalizar_clave(nombre_marca_pdf)

        # Buscar en el mapeo
        if marca_normalizada in CrearPreingresoBuilder._MARCA_MAP:
            return CrearPreingresoBuilder._MARCA_MAP[marca_normalizada]

        return UUID_GENERICO, NOMBRE_GENERICO

    @staticmethod
    def _es_dap(fecha_str: str, formato_fecha: str = "%Y-%m-%d") -> bool:
        """
        Determina si una fecha es menor a 7 días (DAP).
        Incluye el día actual (hoy cuenta como día 0).

        Args:
            fecha_str: Fecha en formato string
            formato_fecha: Formato de la fecha (por defecto: YYYY-MM-DD)

        Returns:
            True si es menor a 7 días (0-6 días), False en caso contrario o si da error

        """
        try:
            fecha = datetime.strptime(fecha_str, formato_fecha)
            diferencia = datetime.now() - fecha
            return timedelta(0) <= diferencia < timedelta(days=7)
        except ValueError:
            return False
