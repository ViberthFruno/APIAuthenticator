# Archivo: email_manager.py
# Ubicación: raíz del proyecto
# Descripción: Gestiona las operaciones de correo electrónico (SMTP e IMAP)

import email
import imaplib
import os
import smtplib
import ssl
import tempfile
from datetime import date, timedelta
from email import encoders
from email.header import decode_header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from case_handler import CaseHandler


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
    Detecta si en el cuerpo del correo viene la palabra 'Garantia' y una opción válida

    Retorna:
        dict con {'encontrada': bool, 'garantia': str o None}
    """
    if not body_text:
        return {'encontrada': False, 'garantia': None}

    # Opciones válidas de garantía (case insensitive)
    opciones_validas = {
        'NORMAL': 'Normal',
        'NO': 'No',
        'C.S.R': 'C.S.R',
        'CSR': 'C.S.R',
        'DOA': 'DOA',
        'STOCK': 'Stock',
        'DAP': 'DAP'
    }

    try:
        # Buscar la palabra "Garantia" o "Garantía" (case insensitive)
        import re

        # Normalizar el texto a mayúsculas para búsqueda
        body_upper = body_text.upper()

        # Buscar "GARANTIA" en el texto
        if re.search(r'GARANT[IÍ]A', body_upper):
            logger.info("✓ Palabra 'Garantia' encontrada en el cuerpo del correo")

            # Buscar una de las opciones válidas
            for opcion_upper, opcion_normalizada in opciones_validas.items():
                # Buscar la opción con límites de palabra
                pattern = r'\b' + re.escape(opcion_upper) + r'\b'
                if re.search(pattern, body_upper):
                    logger.info(f"✓ Garantía detectada en correo: '{opcion_normalizada}'")
                    return {'encontrada': True, 'garantia': opcion_normalizada}

            logger.info("⚠ Se encontró 'Garantia' pero sin opción válida")
            return {'encontrada': False, 'garantia': None}
        else:
            return {'encontrada': False, 'garantia': None}

    except Exception as e:
        logger.error(f"Error al detectar garantía en correo: {str(e)}")
        return {'encontrada': False, 'garantia': None}


def _detectar_proveedor_en_correo(body_text, logger):
    """
    Detecta si en el cuerpo del correo viene la palabra 'Proveedor' (que representa distribuidor)
    y busca un match con los distribuidores disponibles

    Retorna:
        dict con {'encontrado': bool, 'distribuidor_id': str o None, 'distribuidor_nombre': str o None}
    """
    if not body_text:
        return {'encontrado': False, 'distribuidor_id': None, 'distribuidor_nombre': None}

    # Nota: En el correo viene como "proveedor" pero internamente representa "distribuidor"
    # Lista de distribuidores disponibles (key = ID, value = nombre)
    distribuidores = {
        "235b222e-ad2d-4493-9e0d-24eae244f8f9": "CTC GROUP",
        "b24941fa-955f-4a66-9326-da6aaf8b18d1": "Distribuidor Mobiltech",
        "66e20464-0afa-4d7e-9e33-8cb7a358731f": "Distribuidor INTCOMEX",
        "796b6e10-539d-479b-89d8-644c564308c6": "Distribuidor MAJICAL",
        "88f9f5fd-4569-40dd-bc20-9a34097dcedd": "Distribuidor OSL",
        "497c7e40-7e8a-45bd-962f-a79f5f5fe641": "Distribuidor CTC GRUP",
        "560600c2-60d5-42a7-9478-e9d1fef48a97": "Distribuidor Liberty",
        "af3e8a46-cd6a-4eae-a1d1-8b6c1a8111d7": "Distribuidor Suplidora Movil",
        "4d368873-4488-416f-9996-a95c416eaec2": "MobilePro"
    }

    try:
        import re

        # Normalizar el texto a mayúsculas para búsqueda
        body_upper = body_text.upper()

        # Buscar la palabra "PROVEEDOR" en el texto
        if re.search(r'PROVEEDOR', body_upper):
            logger.info("✓ Palabra 'Proveedor' encontrada en el cuerpo del correo")

            # Buscar match con algún distribuidor (case insensitive, matching flexible)
            for distribuidor_id, distribuidor_nombre in distribuidores.items():
                # Normalizar nombre del distribuidor para comparación
                nombre_normalizado = distribuidor_nombre.upper()

                # Crear variantes del nombre para buscar (sin prefijo "Distribuidor", solo nombre base)
                nombre_base = nombre_normalizado.replace("DISTRIBUIDOR ", "").strip()

                # Buscar el nombre base en el cuerpo del correo
                # Usar \b para límites de palabra y hacer matching flexible
                pattern = r'\b' + re.escape(nombre_base) + r'\b'

                if re.search(pattern, body_upper):
                    logger.info(f"✓ Proveedor (distribuidor) detectado en correo: '{distribuidor_nombre}' (ID: {distribuidor_id})")
                    return {
                        'encontrado': True,
                        'distribuidor_id': distribuidor_id,
                        'distribuidor_nombre': distribuidor_nombre
                    }

            logger.info("⚠ Se encontró 'Proveedor' pero no coincide con ningún distribuidor conocido")
            return {'encontrado': False, 'distribuidor_id': None, 'distribuidor_nombre': None}
        else:
            return {'encontrado': False, 'distribuidor_id': None, 'distribuidor_nombre': None}

    except Exception as e:
        logger.error(f"Error al detectar proveedor en correo: {str(e)}")
        return {'encontrado': False, 'distribuidor_id': None, 'distribuidor_nombre': None}


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

    def check_and_process_emails(self, provider, email_addr, password, search_titles, logger, cc_list=None):
        """Función principal que revisa emails y procesa los que coinciden"""
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

                        attachments = _extract_attachments(email_message, logger)

                        matching_case = self.case_handler.find_matching_case(subject, logger)

                        if matching_case:
                            logger.info(f"Email encontrado para caso: {matching_case}")

                            email_data_for_case = {
                                'sender': sender,
                                'subject': subject,
                                'msg_id': msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                                'attachments': attachments,
                                'body_text': body_text,
                                'garantia_correo': garantia_correo,
                                'proveedor_correo': proveedor_correo  # proveedor = distribuidor
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
                    cc_body = f"""Estimado/a Usuario,

Se le envía esta notificación automática como parte del proceso de gestión de la boleta de reparación.

Adjunto encontrará:
• Archivo de texto con todos los datos extraídos del PDF procesado
• PDF original de la boleta de reparación

Detalles de la boleta:
- Número de Boleta: {extracted_data.get('numero_boleta', 'N/A')}
- Número de Transacción: {extracted_data.get('numero_transaccion', 'N/A')}
- Cliente: {extracted_data.get('nombre_cliente', 'N/A')}
- Fecha: {extracted_data.get('fecha', 'N/A')}

Este es un correo automático generado por GolloBot.

Atentamente,
Sistema Automatizado de Gestión de Reparaciones
"""

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

            elif cc_list and len(cc_list) > 0 and not extracted_data:
                logger.warning("⚠️ Hay usuarios CC configurados, pero no hay datos extraídos para enviar")

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