# Archivo: email_manager.py
# Ubicación: raíz del proyecto
# Descripción: Gestiona las operaciones de correo electrónico (SMTP e IMAP)

import email
import imaplib
import os
import smtplib
import ssl
import tempfile
from datetime import date, datetime, timedelta
from email import encoders
from email.header import decode_header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from case_handler import CaseHandler
from case1 import _traducir_mensaje_garantia_usuario


def _mark_as_read(imap_connection, msg_id, logger):
    """Marca un email específico como leído"""
    try:
        status, result = imap_connection.store(msg_id, '+FLAGS', '\\Seen')

        if status == 'OK':
            logger.info(f"Email {msg_id} marcado como leído")
            return True, "Email marcado como leído"
        else:
            return False, f"Estado no OK del servidor: {status}"

    except Exception as e:
        logger.exception(f"Excepción al marcar email como leído: {str(e)}")
        return False, f"Error: {str(e)}"


def _sanitize_string(text):
    """Sanitiza un string para evitar problemas de codificación"""
    if not isinstance(text, str):
        return str(text)

    text = ''.join(c for c in text if c.isprintable() and ord(c) != 0xA0)
    return text


def _decode_header_value(header_value):
    """Decodifica un valor de cabecera que puede estar codificado"""
    if not header_value:
        return ""

    try:
        decoded_parts = decode_header(header_value)
        decoded_text = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    decoded_text += part.decode(encoding)
                else:
                    decoded_text += part.decode('utf-8', errors='ignore')
            else:
                decoded_text += part

        return decoded_text
    except Exception as e:
        print(f"Error al decodificar cabecera: {str(e)}")
        return str(header_value)


def _extract_body_text(email_message):
    """Extrae el texto del cuerpo del correo"""
    body_text = ""

    try:
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Solo extraer texto plano, no adjuntos
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body_text += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            # Correo simple, no multipart
            try:
                body_text = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body_text = str(email_message.get_payload())
    except Exception as e:
        print(f"Error al extraer cuerpo del correo: {str(e)}")

    return body_text


def _detectar_garantia_en_correo(body_text, logger):
    """
    Detecta si en el cuerpo del correo viene alguna palabra clave de garantía.

    Busca directamente las palabras clave sin necesidad de que el usuario escriba "Garantia:" primero.
    Esto evita problemas con tildes y encoding UTF-8.

    Palabras clave soportadas (case insensitive):
    - "sin garantia", "sin" → No
    - "normal" → Normal
    - "csr", "c.s.r.", "c.s.r" → C.S.R
    - "doa" → DOA
    - "no" → No
    - "stock" → Stock
    - "dap" → DAP

    Retorna:
        dict con {'encontrada': bool, 'garantia': str o None}
    """
    if not body_text:
        return {'encontrada': False, 'garantia': None}

    try:
        import re

        # Normalizar el texto a mayúsculas para búsqueda case-insensitive
        body_upper = body_text.upper()

        # Definir patrones de búsqueda en orden de prioridad
        # Primero frases completas, luego palabras individuales
        # Formato: (patrón_regex, nombre_garantía_normalizado)
        patrones_garantia = [
            # Frases completas primero (más específicas)
            (r'\bSIN\s+GARANT[IÍ]A\b', 'No'),  # "sin garantia" o "sin garantía"
            (r'\bC\.?\s*S\.?\s*R\.?\b', 'C.S.R'),  # "CSR", "C.S.R", "C.S.R.", "C S R"

            # Palabras individuales
            (r'\bNORMAL\b', 'Normal'),
            (r'\bDOA\b', 'DOA'),
            (r'\bSTOCK\b', 'Stock'),
            (r'\bDAP\b', 'DAP'),
            (r'\bSIN\b', 'No'),  # "sin" solo
            (r'\bNO\b', 'No'),   # "no" solo (al final para evitar falsos positivos)
        ]

        # Buscar cada patrón en orden de prioridad
        for patron, garantia_nombre in patrones_garantia:
            if re.search(patron, body_upper):
                logger.info(f"✓ Palabra clave de garantía detectada en correo: '{garantia_nombre}'")
                logger.info(f"  Patrón encontrado: {patron}")
                return {'encontrada': True, 'garantia': garantia_nombre}

        # No se encontró ninguna palabra clave de garantía
        return {'encontrada': False, 'garantia': None}

    except Exception as e:
        logger.error(f"Error al detectar garantía en correo: {str(e)}")
        return {'encontrada': False, 'garantia': None}


def _detectar_proveedor_en_correo(body_text, logger):
    """
    Detecta si en el cuerpo del correo viene el campo 'Proveedor' (que representa distribuidor)
    y busca un match con los distribuidores disponibles usando palabras clave configurables.

    NUEVO: Ahora usa config_proveedores.json para cargar:
    1. 'palabras_clave_campo': variaciones de la palabra "proveedor" (ej: PROVEEDOR, PROBEDOR, PROVEDOR)
       para detectar el campo incluso con errores de escritura
    2. 'proveedores': lista de proveedores con sus palabras clave de búsqueda,
       permitiendo agregar variantes sin modificar el código.

    Retorna:
        dict con {'encontrado': bool, 'distribuidor_id': str o None, 'distribuidor_nombre': str o None}
    """
    if not body_text:
        return {'encontrado': False, 'distribuidor_id': None, 'distribuidor_nombre': None}

    try:
        import re
        from config_manager import get_proveedores_config

        # Cargar configuración de proveedores desde archivo JSON
        config_data = get_proveedores_config()
        proveedores = config_data.get('proveedores', {})
        palabras_clave_campo = config_data.get('palabras_clave_campo', ['PROVEEDOR'])

        if not proveedores:
            logger.warning("⚠ No se pudieron cargar los proveedores desde config_proveedores.json")
            return {'encontrado': False, 'distribuidor_id': None, 'distribuidor_nombre': None}

        # Normalizar el texto a mayúsculas para búsqueda
        body_upper = body_text.upper()

        # Buscar cualquiera de las palabras clave del campo "proveedor" en el texto
        palabra_encontrada = None
        for palabra in palabras_clave_campo:
            palabra_upper = palabra.upper().strip()
            pattern = r'\b' + re.escape(palabra_upper) + r'\b'
            if re.search(pattern, body_upper):
                palabra_encontrada = palabra
                break

        if palabra_encontrada:
            logger.info(f"✓ Campo de proveedor detectado usando palabra clave: '{palabra_encontrada}'")

            # Buscar match con algún proveedor usando sus palabras clave configuradas
            for nombre_proveedor, datos_proveedor in proveedores.items():
                distribuidor_id = datos_proveedor.get('id')
                palabras_clave = datos_proveedor.get('palabras_clave', [])

                if not distribuidor_id or not palabras_clave:
                    continue

                # Buscar cada palabra clave en el cuerpo del correo
                for palabra_clave in palabras_clave:
                    # Las palabras ya están en mayúsculas en el config
                    palabra_normalizada = palabra_clave.upper().strip()

                    # Buscar la palabra clave en el cuerpo del correo
                    # Usar \b para límites de palabra para matching exacto
                    pattern = r'\b' + re.escape(palabra_normalizada) + r'\b'

                    if re.search(pattern, body_upper):
                        logger.info(
                            f"✓ Proveedor (distribuidor) detectado en correo: '{nombre_proveedor}' "
                            f"(ID: {distribuidor_id}) usando palabra clave: '{palabra_clave}'")
                        return {
                            'encontrado': True,
                            'distribuidor_id': distribuidor_id,
                            'distribuidor_nombre': nombre_proveedor
                        }

            logger.info(f"⚠ Se encontró campo de proveedor ('{palabra_encontrada}') pero no coincide con ningún distribuidor conocido")
            return {'encontrado': False, 'distribuidor_id': None, 'distribuidor_nombre': None}
        else:
            logger.info("ℹ No se encontró ninguna palabra clave del campo proveedor en el correo")
            return {'encontrado': False, 'distribuidor_id': None, 'distribuidor_nombre': None}

    except Exception as e:
        logger.error(f"Error al detectar proveedor en correo: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'encontrado': False, 'distribuidor_id': None, 'distribuidor_nombre': None}


def _detectar_servitotal_en_correo(body_text, logger):
    """
    Detecta si en el cuerpo del correo viene la palabra clave 'servitotal'
    seguida de un código de sucursal (1-4 dígitos, opcionalmente seguido de nombre).

    Ahora con soporte para mapeo de códigos configurables:
    - Si se detecta "servitotal" con un código, busca en los mapeos configurados
    - Si encuentra un mapeo para ese código, lo reemplaza con el código configurado
    - Si no hay mapeo, usa el código tal como viene en el correo

    Formatos soportados:
    - servitotal: 123
    - servitotal: 045 CIUDAD NEILY
    - servitotal: 1234
    - SERVITOTAL 123

    Args:
        body_text: Texto del cuerpo del correo
        logger: Logger para registrar eventos

    Retorna:
        dict con {'encontrado': bool, 'codigo_sucursal': str o None}
    """
    if not body_text:
        return {'encontrado': False, 'codigo_sucursal': None}

    try:
        import re
        from config_manager import get_servitotal_config

        # Normalizar el texto a mayúsculas para búsqueda case-insensitive
        body_upper = body_text.upper()

        # Patrón para buscar "servitotal" seguido de código de sucursal
        # Formato: servitotal[:] [espacio] (1-4 dígitos) [opcionalmente nombre]
        # Captura solo los dígitos, ignorando el nombre si existe
        pattern = r'\bSERVITOTAL\s*:?\s*(\d{1,4})(?:\s+[\w\s\-]+)?'

        match = re.search(pattern, body_upper)

        if match:
            codigo_original = match.group(1)
            logger.info(f"✓ Palabra clave 'servitotal' detectada en correo con código original: '{codigo_original}'")

            # Cargar configuración de mapeos
            config_data = get_servitotal_config()
            mapeos = config_data.get('mapeos', [])

            # Buscar si existe un mapeo para este código
            codigo_final = codigo_original
            mapeo_encontrado = False

            for mapeo in mapeos:
                codigo_buscar = mapeo.get('codigo_buscar', '')
                codigo_enviar = mapeo.get('codigo_enviar', '')

                if codigo_buscar == codigo_original:
                    codigo_final = codigo_enviar
                    mapeo_encontrado = True
                    logger.info(f"  ✓ Mapeo encontrado: '{codigo_original}' → '{codigo_final}'")
                    break

            if not mapeo_encontrado:
                logger.info(f"  ℹ No se encontró mapeo para '{codigo_original}', usando código original")

            logger.info(f"  Se usará código de sucursal: '{codigo_final}'")
            return {
                'encontrado': True,
                'codigo_sucursal': codigo_final
            }

        # No se encontró la palabra clave servitotal
        return {'encontrado': False, 'codigo_sucursal': None}

    except Exception as e:
        logger.error(f"Error al detectar servitotal en correo: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'encontrado': False, 'codigo_sucursal': None}


def _extract_attachments(email_message, logger):
    """Extrae los archivos adjuntos de un email"""
    attachments = []

    try:
        logger.info("📎 Extrayendo archivos adjuntos del correo...")

        if not email_message.is_multipart():
            logger.info("ℹ️ El correo no tiene adjuntos (no es multipart)")
            return attachments

        for part in email_message.walk():
            content_disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in content_disposition:
                filename = part.get_filename()

                if filename:
                    filename = _decode_header_value(filename)
                    file_data = part.get_payload(decode=True)

                    if file_data:
                        content_type = part.get_content_type()
                        file_size_kb = len(file_data) / 1024

                        attachments.append({
                            'filename': filename,
                            'data': file_data,
                            'content_type': content_type
                        })

                        logger.info(
                            f"📎 Adjunto encontrado: {filename} | Tipo: {content_type} | Tamaño: {file_size_kb:.2f} KB")

        if attachments:
            logger.info(f"✅ Total de adjuntos extraídos: {len(attachments)}")
        else:
            logger.info("ℹ️ No se encontraron adjuntos en el correo")

        return attachments

    except Exception as e:
        logger.error(f"❌ Error extrayendo adjuntos: {str(e)}")
        return []


def _attach_file(msg, attachment):
    """Adjunta un archivo al mensaje MIME"""
    try:
        filename = attachment.get('filename', 'archivo_adjunto')
        file_data = attachment.get('data')

        if not file_data:
            print(f"No hay datos para el archivo {filename}")
            return

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file_data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {filename}')

        msg.attach(part)

    except Exception as e:
        print(f"Error al adjuntar archivo {attachment.get('filename', 'desconocido')}: {str(e)}")


def _generate_formatted_text_for_cc(data):
    """Genera el archivo de texto formateado con los datos extraídos del PDF"""
    from datetime import datetime

    lines = ["=" * 80, "BOLETA DE REPARACIÓN - INFORMACIÓN PROCESADA", "=" * 80, ""]

    if any(k in data for k in ['numero_transaccion', 'numero_boleta', 'fecha', 'gestionada_por']):
        lines.append("INFORMACIÓN DE LA TRANSACCIÓN")
        lines.append("-" * 80)
        if 'numero_transaccion' in data:
            lines.append(f"Número de Transacción: {data['numero_transaccion']}")
        if 'numero_boleta' in data:
            lines.append(f"Número de Boleta: {data['numero_boleta']}")
        if 'fecha' in data:
            lines.append(f"Fecha: {data['fecha']}")
        if 'gestionada_por' in data:
            lines.append(f"Gestionada por: {data['gestionada_por']}")
        lines.append("")

    if any(k in data for k in ['sucursal', 'telefono_sucursal']):
        lines.append("INFORMACIÓN DE LA SUCURSAL")
        lines.append("-" * 80)
        if 'sucursal' in data:
            lines.append(f"Sucursal: {data['sucursal']}")
        if 'telefono_sucursal' in data:
            lines.append(f"Teléfono: {data['telefono_sucursal']}")
        lines.append("")

    cliente_keys = ['nombre_cliente', 'nombre_contacto', 'cedula_cliente', 'telefono_cliente',
                    'telefono_adicional', 'correo_cliente', 'direccion_cliente']
    if any(k in data for k in cliente_keys):
        lines.append("INFORMACIÓN DEL CLIENTE")
        lines.append("-" * 80)
        # Solo mostrar el nombre una vez (priorizar nombre_cliente sobre nombre_contacto)
        if 'nombre_cliente' in data:
            lines.append(f"Nombre: {data['nombre_cliente']}")
        elif 'nombre_contacto' in data:
            lines.append(f"Nombre: {data['nombre_contacto']}")
        if 'cedula_cliente' in data:
            lines.append(f"Cédula: {data['cedula_cliente']}")
        if 'telefono_cliente' in data:
            lines.append(f"Teléfono: {data['telefono_cliente']}")
        if 'telefono_adicional' in data:
            lines.append(f"Teléfono Adicional: {data['telefono_adicional']}")
        if 'correo_cliente' in data:
            lines.append(f"Correo: {data['correo_cliente']}")
        # NUEVO: Mostrar cómo se extrajo el correo con OCR (para diagnóstico)
        if 'correo_ocr_raw' in data:
            lines.append(f"Correo (OCR Raw): {data['correo_ocr_raw']}")
        if 'direccion_cliente' in data:
            lines.append(f"Dirección: {data['direccion_cliente']}")
        lines.append("")

    producto_keys = ['codigo_producto', 'descripcion_producto', 'marca',
                     'modelo', 'serie', 'garantia', 'codigo_distribuidor']
    if any(k in data for k in producto_keys):
        lines.append("INFORMACIÓN DEL PRODUCTO")
        lines.append("-" * 80)
        if 'codigo_producto' in data:
            lines.append(f"Código: {data['codigo_producto']}")
        if 'descripcion_producto' in data:
            lines.append(f"Descripción: {data['descripcion_producto']}")
        if 'marca' in data:
            lines.append(f"Marca: {data['marca']}")
        if 'modelo' in data:
            lines.append(f"Modelo: {data['modelo']}")
        if 'garantia' in data:
            lines.append(f"Garantía: {data['garantia']}")
        if 'serie' in data:
            lines.append(f"Serie: {data['serie']}")
        if 'codigo_distribuidor' in data:
            lines.append(f"Código Distribuidor: {data['codigo_distribuidor']}")
        lines.append("")

    compra_keys = ['numero_factura', 'fecha_compra', 'fecha_garantia',
                   'tipo_garantia', 'distribuidor']
    if any(k in data for k in compra_keys):
        lines.append("INFORMACIÓN DE COMPRA")
        lines.append("-" * 80)
        if 'numero_factura' in data:
            lines.append(f"Número de Factura: {data['numero_factura']}")
        if 'fecha_compra' in data:
            lines.append(f"Fecha de Compra: {data['fecha_compra']}")
        if 'fecha_garantia' in data:
            lines.append(f"Fecha de Garantía: {data['fecha_garantia']}")
        if 'tipo_garantia' in data:
            lines.append(f"Tipo de Garantía: {data['tipo_garantia']}")
        if 'distribuidor' in data:
            lines.append(f"Distribuidor: {data['distribuidor']}")
        lines.append("")

    if any(k in data for k in ['hecho_por', 'danos', 'observaciones']):
        lines.append("INFORMACIÓN TÉCNICA")
        lines.append("-" * 80)
        if 'hecho_por' in data:
            lines.append(f"Hecho por: {data['hecho_por']}")
        if 'danos' in data:
            lines.append(f"Daños Reportados: {data['danos']}")
        if 'observaciones' in data:
            lines.append(f"Observaciones: {data['observaciones']}")
        lines.append("")

    lines.append("=" * 80)
    lines.append("Documento procesado automáticamente por GolloBot")
    lines.append(f"Fecha de procesamiento: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)

    return "\n".join(lines)


def _generate_console_format_data_text(preingreso_results):
    """
    Genera el archivo de texto con el formato de consola (igual que se ve en el terminal)

    Args:
        preingreso_results: Lista con resultados del preingreso que incluyen datos_pdf_raw y datos_api_raw

    Returns:
        str: Contenido del archivo con formato de consola
    """
    from datetime import datetime

    lines = ["=" * 80, "DATOS DE PROCESAMIENTO - FORMATO CONSOLA", "=" * 80, ""]

    if not preingreso_results or len(preingreso_results) == 0:
        lines.append("No hay información disponible.")
        lines.append("")
        lines.append("=" * 80)
        return "\n".join(lines)

    # Tomar el primer resultado (normalmente solo hay uno)
    result = preingreso_results[0]

    # Agregar datos del PDF en formato raw (tal como se ve en consola)
    datos_pdf_raw = result.get('datos_pdf_raw')
    if datos_pdf_raw:
        lines.append("🏷️Datos del PDF:")
        lines.append(datos_pdf_raw)
        lines.append("")
    else:
        lines.append("🏷️Datos del PDF:")
        lines.append("No disponibles")
        lines.append("")

    # Agregar datos enviados a la API en formato raw (tal como se ve en consola)
    datos_api_raw = result.get('datos_api_raw')
    if datos_api_raw:
        lines.append("🏷️Datos que serán enviados:")
        lines.append(datos_api_raw)
        lines.append("")
    else:
        lines.append("🏷️Datos que serán enviados:")
        lines.append("No disponibles")
        lines.append("")

    lines.append("=" * 80)
    lines.append("Documento generado automáticamente por GolloBot")
    lines.append(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)

    return "\n".join(lines)


def _generate_api_sent_data_text(preingreso_results):
    """Genera el texto formateado con los datos que fueron enviados al API"""
    from datetime import datetime

    lines = ["=" * 80, "DATOS ENVIADOS AL SISTEMA iFR Pro", "=" * 80, ""]

    if not preingreso_results or len(preingreso_results) == 0:
        lines.append("No hay información disponible sobre los datos enviados al sistema.")
        lines.append("")
        lines.append("=" * 80)
        return "\n".join(lines)

    # Tomar el primer resultado (normalmente solo hay uno)
    result = preingreso_results[0]

    lines.append("RESULTADO DE LA CREACIÓN DEL PREINGRESO")
    lines.append("-" * 80)

    if result.get('preingreso_id'):
        lines.append(f"ID Preingreso (Boleta Fruno): {result['preingreso_id']}")

    if result.get('boleta'):
        lines.append(f"Número de Boleta Gollo: {result['boleta']}")

    if result.get('numero_transaccion'):
        lines.append(f"Número de Transacción: {result['numero_transaccion']}")

    if result.get('tipo_preingreso_nombre'):
        lines.append(f"Tipo de Preingreso: {result['tipo_preingreso_nombre']}")

    if result.get('garantia_nombre'):
        lines.append(f"Garantía Aplicada: {result['garantia_nombre']}")

    # Indicar si la garantía viene del correo
    if result.get('garantia_viene_de_correo'):
        lines.append(f"Origen de Garantía: Detectada en el cuerpo del correo")

    lines.append("")

    # Enlaces de consulta
    if result.get('consultar_reparacion') or result.get('consultar_guia'):
        lines.append("ENLACES DE CONSULTA")
        lines.append("-" * 80)

        if result.get('consultar_reparacion'):
            lines.append(f"Consultar Estado de Reparación:")
            lines.append(f"  {result['consultar_reparacion']}")

        if result.get('consultar_guia'):
            lines.append(f"Consultar Guía:")
            lines.append(f"  {result['consultar_guia']}")

        lines.append("")

    # Información adicional del resultado
    if result.get('extracted_data'):
        extracted = result['extracted_data']

        lines.append("DATOS ADICIONALES ENVIADOS")
        lines.append("-" * 80)

        if extracted.get('nombre_cliente') or extracted.get('nombre_contacto'):
            nombre = extracted.get('nombre_cliente') or extracted.get('nombre_contacto')
            lines.append(f"Cliente: {nombre}")

        if extracted.get('correo_cliente'):
            lines.append(f"Correo Cliente: {extracted['correo_cliente']}")

        if extracted.get('telefono_cliente'):
            lines.append(f"Teléfono Cliente: {extracted['telefono_cliente']}")

        if extracted.get('serie'):
            lines.append(f"Serie del Producto: {extracted['serie']}")

        if extracted.get('marca'):
            lines.append(f"Marca: {extracted['marca']}")

        if extracted.get('modelo'):
            lines.append(f"Modelo: {extracted['modelo']}")

        if extracted.get('descripcion_producto'):
            lines.append(f"Descripción del Producto: {extracted['descripcion_producto']}")

        lines.append("")

    lines.append("=" * 80)
    lines.append("Datos enviados exitosamente al sistema iFR Pro")
    lines.append(f"Fecha de envío: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)

    return "\n".join(lines)


class EmailManager:
    def __init__(self):
        """Inicializa el gestor de correo electrónico"""
        self.provider_configs = {
            'Gmail': {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'imap_server': 'imap.gmail.com',
                'imap_port': 993
            },
            'Outlook': {
                'smtp_server': 'smtp-mail.outlook.com',
                'smtp_port': 587,
                'imap_server': 'outlook.office365.com',
                'imap_port': 993
            },
            'Yahoo': {
                'smtp_server': 'smtp.mail.yahoo.com',
                'smtp_port': 587,
                'imap_server': 'imap.mail.yahoo.com',
                'imap_port': 993
            },
            'Otro': {
                'smtp_server': '',
                'smtp_port': 587,
                'imap_server': '',
                'imap_port': 993
            }
        }

        self.case_handler = CaseHandler()

    def get_provider_config(self, provider):
        """Obtiene la configuración para un proveedor específico"""
        return self.provider_configs.get(provider, self.provider_configs['Otro'])

    def test_smtp_connection(self, provider, email_addr, password):
        """Prueba la conexión SMTP con los parámetros proporcionados"""
        try:
            config = self.get_provider_config(provider)
            server = config['smtp_server']
            port = config['smtp_port']

            email_addr = _sanitize_string(email_addr)
            password = _sanitize_string(password)

            context = ssl.create_default_context()

            smtp = smtplib.SMTP(server, port)
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(email_addr, password)
            smtp.quit()

            return True

        except Exception as e:
            print(f"Error en la conexión SMTP: {str(e)}")
            return False

    def test_imap_connection(self, provider, email_addr, password):
        """Prueba la conexión IMAP con los parámetros proporcionados"""
        try:
            config = self.get_provider_config(provider)
            server = config['imap_server']
            port = config['imap_port']

            email_addr = _sanitize_string(email_addr)
            password = _sanitize_string(password)

            context = ssl.create_default_context()

            imap = imaplib.IMAP4_SSL(server, port, ssl_context=context)
            imap.login(email_addr, password)
            imap.logout()

            return True

        except Exception as e:
            print(f"Error en la conexión IMAP: {str(e)}")
            return False

    def send_email(self, provider, email_addr, password, to, subject, body, cc_list=None, attachments=None,
                   logger=None):
        """Envía un correo electrónico a través de SMTP"""
        try:
            # Si no se proporciona logger, usar print como fallback
            if not logger:
                logger = type('obj', (object,), {
                    'info': lambda msg: print(msg),
                    'warning': lambda msg: print(f"WARNING: {msg}"),
                    'error': lambda msg: print(f"ERROR: {msg}")
                })()

            config = self.get_provider_config(provider)
            server = config['smtp_server']
            port = config['smtp_port']

            email_addr = _sanitize_string(email_addr)
            password = _sanitize_string(password)

            logger.info(f"📤 Preparando correo para enviar...")
            logger.info(f"   Destinatario: {to}")
            logger.info(f"   Asunto: {subject}")

            msg = MIMEMultipart()
            msg['From'] = email_addr
            msg['To'] = to
            msg['Subject'] = subject

            if cc_list:
                logger.info(f"   CC: {', '.join(cc_list)}")
                msg['Cc'] = ", ".join(cc_list)

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            if attachments:
                logger.info(f"📎 Adjuntando {len(attachments)} archivo(s)...")
                for attachment in attachments:
                    _attach_file(msg, attachment)
                    filename = attachment.get('filename', 'archivo_sin_nombre')
                    logger.info(f"   • {filename}")

            context = ssl.create_default_context()

            logger.info(f"📧 Conectando al servidor SMTP: {server}:{port}")

            with smtplib.SMTP(server, port) as smtp:
                smtp.ehlo()
                logger.info("🔐 Estableciendo conexión segura (TLS)...")
                smtp.starttls(context=context)
                smtp.ehlo()
                logger.info(f"🔐 Autenticando cuenta: {email_addr}")
                smtp.login(email_addr, password)
                logger.info("📨 Enviando correo...")
                smtp.send_message(msg)

            logger.info("✅ Correo enviado exitosamente")
            return True

        except Exception as e:
            if logger:
                logger.error(f"❌ Error al enviar correo: {str(e)}")
            else:
                print(f"Error al enviar correo: {str(e)}")
            return False

    def check_and_process_emails(self, provider, email_addr, password, search_titles, logger, cc_list=None,
                                 allowed_domains=None):
        """
        Función principal que revisa emails y procesa los que coinciden

        Args:
            provider: Proveedor de correo
            email_addr: Dirección de correo
            password: Contraseña
            search_titles: Lista de palabras clave para buscar en asunto
            logger: Logger
            cc_list: Lista de correos para CC
            allowed_domains: String con dominios permitidos separados por comas (ej: "@fruno.com, @unicomer.com")
        """
        try:
            config = self.get_provider_config(provider)
            server = config['imap_server']
            port = config['imap_port']

            email_addr = _sanitize_string(email_addr)
            password = _sanitize_string(password)

            context = ssl.create_default_context()

            logger.info(f"📧 Conectando al servidor IMAP: {server}:{port}")

            with imaplib.IMAP4_SSL(server, port, ssl_context=context) as imap:
                logger.info(f"🔐 Autenticando cuenta: {email_addr}")
                imap.login(email_addr, password)
                logger.info("✅ Conexión IMAP establecida correctamente")

                logger.info("📬 Seleccionando bandeja INBOX")
                imap.select('INBOX')
                logger.info("✅ Bandeja INBOX seleccionada")

                today = date.today()
                yesterday = (today - timedelta(days=1)).strftime("%d-%b-%Y")

                search_criteria = ['(UNSEEN)', f'(SINCE "{yesterday}")']

                if search_titles:
                    subject_queries = [f'(SUBJECT "{title.strip()}")' for title in search_titles if title.strip()]

                    if len(subject_queries) > 1:
                        search_criteria.append(f'(OR {" ".join(subject_queries)})')
                    elif subject_queries:
                        search_criteria.append(subject_queries[0])

                final_query = ' '.join(search_criteria)
                logger.info(f"Ejecutando búsqueda IMAP: {final_query}")

                try:
                    status, messages = imap.search('UTF-8', final_query)
                except:
                    logger.warning("Reintentando búsqueda sin UTF-8...")
                    status, messages = imap.search(None, final_query)

                message_ids = messages[0].split()

                if not message_ids:
                    logger.info("No se encontraron correos nuevos que coincidan.")
                    return

                logger.info(f"Encontrados {len(message_ids)} emails que coinciden")

                for msg_id in message_ids:
                    try:
                        logger.info(
                            f"📨 Procesando email ID: {msg_id.decode() if isinstance(msg_id, bytes) else msg_id}")

                        logger.info("📥 Descargando contenido del correo desde el servidor...")
                        status, email_data = imap.fetch(msg_id, '(RFC822)')

                        if status != 'OK' or not email_data:
                            logger.warning(f"⚠️ No se pudo obtener el email {msg_id}")
                            continue

                        logger.info("✅ Correo descargado correctamente")

                        logger.info("📖 Leyendo y decodificando el correo...")
                        raw_email = email_data[0][1]
                        email_message = email.message_from_bytes(raw_email, policy=email.policy.default)

                        subject = _decode_header_value(email_message.get('Subject', ''))
                        sender = email_message.get('From', '')

                        logger.info(f"📧 Email leído: Asunto='{subject}' | Remitente={sender}")

                        # Extraer cuerpo del correo
                        body_text = _extract_body_text(email_message)

                        # Detectar si viene garantía en el correo
                        garantia_correo = _detectar_garantia_en_correo(body_text, logger)

                        # Detectar si viene proveedor (distribuidor) en el correo
                        proveedor_correo = _detectar_proveedor_en_correo(body_text, logger)

                        # Detectar si viene código de sucursal con palabra clave 'servitotal' en el correo
                        servitotal_correo = _detectar_servitotal_en_correo(body_text, logger)

                        attachments = _extract_attachments(email_message, logger)

                        # Pasar sender y allowed_domains a find_matching_case
                        matching_case = self.case_handler.find_matching_case(subject, sender, allowed_domains, logger)

                        if matching_case:
                            logger.info(f"Email encontrado para caso: {matching_case}")

                            email_data_for_case = {
                                'sender': sender,
                                'subject': subject,
                                'msg_id': msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                                'attachments': attachments,
                                'body_text': body_text,
                                'garantia_correo': garantia_correo,
                                'proveedor_correo': proveedor_correo,  # proveedor = distribuidor
                                'servitotal_correo': servitotal_correo  # código de sucursal del correo
                            }

                            response_data = self.case_handler.execute_case(matching_case, email_data_for_case, logger)

                            if response_data:
                                _mark_as_read(imap, msg_id, logger)

                                response_attachments = response_data.get('attachments', [])
                                if self._send_case_reply(provider, email_addr, password, response_data, logger,
                                                         cc_list, response_attachments):
                                    logger.info(f"Respuesta automática enviada usando {matching_case}")
                                else:
                                    logger.error("Error al enviar respuesta automática")
                            else:
                                logger.error(f"Error al procesar {matching_case}")
                        else:
                            logger.info(f"Email no coincide con ningún caso: '{subject}'")

                    except Exception as e:
                        logger.exception(f"Error al procesar email individual {msg_id}: {str(e)}")

        except Exception as e:
            logger.exception(f"Error en check_and_process_emails: {str(e)}")

    def _send_case_reply(self, provider, email_addr, password, response_data, logger, cc_list=None, attachments=None):
        """Envía una respuesta automática usando los datos del caso"""
        try:
            logger.info("📧 Iniciando envío de respuesta automática...")

            recipient = response_data.get('recipient', '')
            subject = response_data.get('subject', '')
            body = response_data.get('body', '')
            extracted_data = response_data.get('extracted_data')
            pdf_original = response_data.get('pdf_original')  # PDF original para CC
            preingreso_results = response_data.get('preingreso_results')  # Resultados del preingreso para usuarios CC

            if '<' in recipient and '>' in recipient:
                recipient = recipient.split('<')[1].split('>')[0].strip()

            logger.info(f"   Destinatario: {recipient}")
            logger.info(f"   Asunto: {subject}")

            temp_files_to_clean = []
            if attachments:
                logger.info(f"   Adjuntos: {len(attachments)} archivo(s)")
                for attachment in attachments:
                    if 'path' in attachment:
                        temp_files_to_clean.append(attachment['path'])

            # CAMBIO: Enviar correo principal SIN CC
            logger.info("📤 Enviando correo principal al remitente (sin CC)...")
            result = self.send_email(provider, email_addr, password, recipient, subject, body, None, attachments,
                                     logger)

            if not result:
                logger.error("❌ Fallo al enviar correo principal")
                return False

            logger.info("✅ Correo principal enviado correctamente")

            # Verificar si el correo es de error (no tiene extracted_data)
            is_error = not extracted_data

            # NUEVO: Enviar correos separados a usuarios CC con archivo de texto adjunto
            if cc_list and len(cc_list) > 0 and extracted_data:
                logger.info("")
                logger.info("=" * 80)
                logger.info(f"📧 Enviando correos separados a {len(cc_list)} usuario(s) CC...")
                logger.info("=" * 80)

                # Generar el archivo de texto con los datos extraídos
                logger.info("📝 Generando archivo de texto con datos extraídos del PDF...")
                text_content = _generate_formatted_text_for_cc(extracted_data)

                # Crear archivo temporal
                temp_text_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
                temp_text_file.write(text_content)
                temp_text_file.close()
                temp_files_to_clean.append(temp_text_file.name)

                # Determinar nombre del archivo basado en boleta
                boleta_numero = extracted_data.get('numero_boleta', 'datos')
                text_filename = f"Datos_Extraidos_Boleta_{boleta_numero}.txt"

                logger.info(f"✅ Archivo de texto creado: {text_filename}")

                # Leer el contenido del archivo para adjuntar
                with open(temp_text_file.name, 'rb') as f:
                    text_file_data = f.read()

                # Crear lista de adjuntos (archivo de texto + PDF original)
                cc_attachments = [{
                    'filename': text_filename,
                    'data': text_file_data
                }]

                # Generar archivo de texto con datos en formato consola (una sola vez)
                logger.info("📝 Generando archivo de texto con datos en formato consola...")
                console_data_text = _generate_console_format_data_text(preingreso_results)

                # Crear archivo temporal para los datos en formato consola
                temp_console_data_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
                temp_console_data_file.write(console_data_text)
                temp_console_data_file.close()
                temp_files_to_clean.append(temp_console_data_file.name)

                # Determinar nombre del archivo basado en boleta
                boleta_numero = extracted_data.get('numero_boleta', 'datos')
                console_data_filename = f"Datos_Consola_Boleta_{boleta_numero}.txt"
                logger.info(f"✅ Archivo de datos de consola creado: {console_data_filename}")

                # Leer el contenido del archivo para adjuntar
                with open(temp_console_data_file.name, 'rb') as f:
                    console_data_file_data = f.read()

                # Agregar el archivo de datos de consola a los adjuntos (al inicio de la lista)
                cc_attachments.insert(0, {
                    'filename': console_data_filename,
                    'data': console_data_file_data
                })

                # Agregar PDF original si está disponible
                if pdf_original and pdf_original.get('data'):
                    pdf_filename = pdf_original.get('filename', 'boleta.pdf')
                    pdf_data = pdf_original.get('data')
                    cc_attachments.append({
                        'filename': pdf_filename,
                        'data': pdf_data
                    })
                    logger.info(f"✅ PDF original incluido: {pdf_filename}")

                # Enviar a cada usuario CC por separado
                cc_success_count = 0
                cc_failed_count = 0

                for cc_email in cc_list:
                    cc_email = cc_email.strip()
                    if not cc_email:
                        continue

                    logger.info("")
                    logger.info(f"📧 Enviando correo a: {cc_email}")

                    # Asunto específico para usuarios CC
                    cc_subject = f"Notificación: {subject}"

                    # Construir el cuerpo del correo (simplificado, sin las secciones de datos)
                    cc_body_lines = [
                        "Estimado/a Usuario,",
                        "",
                        "Se le envía esta notificación automática como parte del proceso de gestión de la boleta de reparación.",
                        "",
                        "Adjunto encontrará:",
                        "• Archivo de texto con los datos del PDF y datos enviados al sistema (formato consola)",
                        "• Archivo de texto con información detallada de los datos extraídos",
                        "• PDF original de la boleta de reparación",
                        ""
                    ]

                    # Agregar sección de consulta del estado si está disponible
                    if preingreso_results and len(preingreso_results) > 0:
                        consultar_reparacion = preingreso_results[0].get('consultar_reparacion')
                        if consultar_reparacion:
                            cc_body_lines.extend([
                                "🔗 Consulta del estado:",
                                "",
                                "   Puede verificar el progreso de la reparación en cualquier momento haciendo clic en el siguiente enlace:",
                                "",
                                f"   👉 {consultar_reparacion}",
                                ""
                            ])

                        # Agregar sección de información sobre la garantía
                        msg_garantia = preingreso_results[0].get('msg_garantia')
                        if msg_garantia:
                            mensaje_usuario = _traducir_mensaje_garantia_usuario(msg_garantia)
                            if mensaje_usuario:
                                cc_body_lines.extend([
                                    "ℹ️ Información sobre la garantía:",
                                    "",
                                    f"   {mensaje_usuario}",
                                    ""
                                ])

                        # Agregar sección de información sobre el código de sucursal usado (servitotal)
                        sucursal_info = preingreso_results[0].get('sucursal_usada_info')
                        if sucursal_info:
                            origen = sucursal_info.get('origen')
                            codigo = sucursal_info.get('codigo')
                            nombre_sucursal = sucursal_info.get('nombre_sucursal')
                            codigo_correo_intentado = sucursal_info.get('codigo_correo_intentado')

                            # Solo mostrar mensaje si el usuario proporcionó un código con servitotal
                            if codigo_correo_intentado:
                                cc_body_lines.extend([
                                    "🏪 Código de sucursal:",
                                    ""
                                ])

                                if origen == 'correo':
                                    # Se usó el código del correo exitosamente
                                    cc_body_lines.append(f"   Se utilizó el código de sucursal '{codigo}' que usted proporcionó en el correo con la palabra clave 'servitotal'.")
                                    if nombre_sucursal:
                                        cc_body_lines.append(f"   Sucursal identificada: {nombre_sucursal}")
                                elif origen == 'pdf':
                                    # El código del correo falló, se usó el del PDF como fallback
                                    cc_body_lines.append(f"   El código de sucursal '{codigo_correo_intentado}' que proporcionó en el correo no pudo ser validado.")
                                    cc_body_lines.append(f"   Se utilizó el código '{codigo}' extraído del PDF adjunto.")
                                    if nombre_sucursal:
                                        cc_body_lines.append(f"   Sucursal identificada: {nombre_sucursal}")

                                cc_body_lines.append("")

                    # Agregar alertas si hay datos no encontrados
                    if extracted_data:
                        # Alerta de correo no encontrado
                        if extracted_data.get('correo_cliente') == "correo_no_encontrado@gollo.com":
                            cc_body_lines.extend([
                                "📌 Correo no encontrado en el documento",
                                "",
                                "   El sistema no pudo extraer el correo electrónico del PDF adjunto.",
                                "   Se ha asignado temporalmente correo_no_encontrado@gollo.com para permitir",
                                "   el registro del preingreso.",
                                "",
                                "   Por favor, contacte con soporte técnico de Fruno para asistencia.",
                                ""
                            ])

                        # Alerta de nombre no encontrado
                        if not extracted_data.get('nombre_cliente'):
                            cc_body_lines.extend([
                                "📌 Nombre del cliente no encontrado en el documento",
                                "",
                                "   El sistema no pudo extraer el nombre del propietario del PDF adjunto.",
                                "   Se ha asignado temporalmente 'N/A' para permitir el registro del preingreso.",
                                "",
                                "   Por favor, contacte con soporte técnico de Fruno para asistencia.",
                                ""
                            ])

                    cc_body_lines.extend([
                        "",
                        "Este es un correo automático generado por GolloBot.",
                        "",
                        "Atentamente,",
                        "Sistema Automatizado de Gestión de Reparaciones"
                    ])

                    cc_body = "\n".join(cc_body_lines)

                    cc_result = self.send_email(
                        provider, email_addr, password,
                        cc_email, cc_subject, cc_body,
                        None,  # Sin CC
                        cc_attachments,  # Incluye archivo de texto + PDF original
                        logger
                    )

                    if cc_result:
                        cc_success_count += 1
                        logger.info(f"   ✅ Correo enviado exitosamente a {cc_email}")
                    else:
                        cc_failed_count += 1
                        logger.error(f"   ❌ Error al enviar correo a {cc_email}")

                logger.info("")
                logger.info("=" * 80)
                logger.info(f"📊 Resumen de envíos a usuarios CC:")
                logger.info(f"   ✅ Exitosos: {cc_success_count}")
                if cc_failed_count > 0:
                    logger.info(f"   ❌ Fallidos: {cc_failed_count}")
                logger.info("=" * 80)

            elif cc_list and len(cc_list) > 0 and is_error:
                # Enviar notificaciones de error a usuarios CC
                logger.info("")
                logger.info("=" * 80)
                logger.info(f"⚠️ Enviando notificaciones de ERROR a {len(cc_list)} usuario(s) CC...")
                logger.info("=" * 80)

                # Crear lista de adjuntos
                cc_attachments = []

                # Si hay datos extraídos, generar archivo con datos del PDF (aunque haya fallado la creación)
                if extracted_data:
                    logger.info("📝 Generando archivo de texto con datos extraídos del PDF...")
                    text_content = _generate_formatted_text_for_cc(extracted_data)

                    # Crear archivo temporal para datos extraídos
                    temp_text_file_datos = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
                    temp_text_file_datos.write(text_content)
                    temp_text_file_datos.close()
                    temp_files_to_clean.append(temp_text_file_datos.name)

                    # Determinar nombre del archivo basado en boleta
                    boleta_numero = extracted_data.get('numero_boleta', 'datos')
                    text_filename_datos = f"Datos_Extraidos_Boleta_{boleta_numero}.txt"
                    logger.info(f"✅ Archivo de datos extraídos creado: {text_filename_datos}")

                    # Leer el contenido del archivo para adjuntar
                    with open(temp_text_file_datos.name, 'rb') as f:
                        text_file_data_datos = f.read()

                    cc_attachments.append({
                        'filename': text_filename_datos,
                        'data': text_file_data_datos
                    })

                # Generar archivo de texto con información del error
                logger.info("📝 Generando archivo de texto con información del error...")
                error_text_content = f"""NOTIFICACIÓN DE ERROR - PROCESAMIENTO DE PRE-INGRESO
{'=' * 80}

Se ha detectado un error durante el procesamiento del documento PDF.

DETALLES DEL ERROR:
{'-' * 80}

{body}

{'-' * 80}

INFORMACIÓN ADICIONAL:
- Fecha de procesamiento: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Este correo es solo informativo para que esté al tanto de los problemas detectados
- El usuario que envió el correo original ya ha sido notificado del error

{'=' * 80}

Este archivo fue generado automáticamente por GolloBot.
Sistema Automatizado de Gestión de Reparaciones
"""

                # Crear archivo temporal con la información del error
                temp_text_file_error = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
                temp_text_file_error.write(error_text_content)
                temp_text_file_error.close()
                temp_files_to_clean.append(temp_text_file_error.name)

                text_filename_error = f"Error_Procesamiento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                logger.info(f"✅ Archivo de error creado: {text_filename_error}")

                # Leer el contenido del archivo para adjuntar
                with open(temp_text_file_error.name, 'rb') as f:
                    text_file_data_error = f.read()

                cc_attachments.append({
                    'filename': text_filename_error,
                    'data': text_file_data_error
                })

                # Agregar PDF original si está disponible
                if pdf_original and pdf_original.get('data'):
                    pdf_filename = pdf_original.get('filename', 'documento_error.pdf')
                    pdf_data = pdf_original.get('data')
                    cc_attachments.append({
                        'filename': pdf_filename,
                        'data': pdf_data
                    })
                    logger.info(f"✅ PDF original incluido: {pdf_filename}")
                else:
                    logger.warning("⚠️ PDF original no disponible para adjuntar")

                cc_success_count = 0
                cc_failed_count = 0

                for cc_email in cc_list:
                    cc_email = cc_email.strip()
                    if not cc_email:
                        continue

                    logger.info("")
                    logger.info(f"📧 Enviando notificación de error a: {cc_email}")

                    # Asunto específico para notificación de error
                    cc_subject = f"⚠️ Notificación de Error: {subject}"

                    # Construir el cuerpo del correo de error
                    cc_body_lines = [
                        "Estimado/a Usuario,",
                        "",
                        "Se le envía esta notificación automática para informarle que se ha detectado un ERROR durante el procesamiento de un pre-ingreso.",
                        "",
                        "Adjunto encontrará:"
                    ]

                    # Agregar lista de archivos adjuntos según lo que esté disponible
                    if extracted_data:
                        cc_body_lines.append("• Archivo de texto con datos extraídos del PDF")
                    cc_body_lines.append("• Archivo de texto con información detallada del error")
                    cc_body_lines.append("• PDF original que causó el error (si está disponible)")

                    cc_body_lines.extend([
                        "",
                        "⚠️ DETALLES DEL ERROR:",
                        "",
                        "---",
                        body,  # Incluir el mensaje de error completo
                        "---",
                        "",
                        "Este correo es solo informativo para que esté al tanto de los problemas detectados.",
                        "El usuario que envió el correo original ya ha sido notificado del error.",
                        "",
                        "",
                        "Este es un correo automático generado por GolloBot.",
                        "",
                        "Atentamente,",
                        "Sistema Automatizado de Gestión de Reparaciones"
                    ])

                    cc_body = "\n".join(cc_body_lines)

                    cc_result = self.send_email(
                        provider, email_addr, password,
                        cc_email, cc_subject, cc_body,
                        None,  # Sin CC
                        cc_attachments,  # Incluye archivo de texto + PDF original
                        logger
                    )

                    if cc_result:
                        cc_success_count += 1
                        logger.info(f"   ✅ Notificación de error enviada exitosamente a {cc_email}")
                    else:
                        cc_failed_count += 1
                        logger.error(f"   ❌ Error al enviar notificación a {cc_email}")

                logger.info("")
                logger.info("=" * 80)
                logger.info(f"📊 Resumen de notificaciones de error:")
                logger.info(f"   ✅ Exitosas: {cc_success_count}")
                if cc_failed_count > 0:
                    logger.info(f"   ❌ Fallidas: {cc_failed_count}")
                logger.info("=" * 80)

            # Limpiar archivos temporales
            if temp_files_to_clean:
                logger.info("")
                logger.info("🧹 Limpiando archivos temporales...")
                for temp_path in temp_files_to_clean:
                    try:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                            logger.info(f"   • Eliminado: {os.path.basename(temp_path)}")
                    except Exception as cleanup_error:
                        logger.warning(f"   ⚠️ No se pudo eliminar {os.path.basename(temp_path)}: {cleanup_error}")

            logger.info("")
            logger.info("✅ Proceso de envío de correos completado")
            return True

        except Exception as e:
            logger.exception(f"❌ Error al enviar respuesta del caso: {str(e)}")
            return False