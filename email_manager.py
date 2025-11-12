# Archivo: email_manager.py
# Ubicación: raíz del proyecto
# Descripción: Gestiona las operaciones de correo electrónico (SMTP e IMAP)

import email
import imaplib
import os
import smtplib
import ssl
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

                        logger.info(f"📎 Adjunto encontrado: {filename} | Tipo: {content_type} | Tamaño: {file_size_kb:.2f} KB")

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

    def send_email(self, provider, email_addr, password, to, subject, body, cc_list=None, attachments=None, logger=None):
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
                        logger.info(f"📨 Procesando email ID: {msg_id.decode() if isinstance(msg_id, bytes) else msg_id}")

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

                        attachments = _extract_attachments(email_message, logger)

                        matching_case = self.case_handler.find_matching_case(subject, logger)

                        if matching_case:
                            logger.info(f"Email encontrado para caso: {matching_case}")

                            email_data_for_case = {
                                'sender': sender,
                                'subject': subject,
                                'msg_id': msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                                'attachments': attachments
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

            result = self.send_email(provider, email_addr, password, recipient, subject, body, cc_list, attachments, logger)

            # Limpiar archivos temporales
            if temp_files_to_clean:
                logger.info("🧹 Limpiando archivos temporales...")
                for temp_path in temp_files_to_clean:
                    try:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                            logger.info(f"   • Eliminado: {temp_path}")
                    except Exception:
                        pass

            if result:
                logger.info("✅ Respuesta automática enviada correctamente")
            else:
                logger.error("❌ Fallo al enviar respuesta automática")

            return result

        except Exception as e:
            logger.exception(f"❌ Error al enviar respuesta del caso: {str(e)}")
            return False
