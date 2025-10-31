# Archivo: email_manager.py
# Ubicación: raíz del proyecto
# Descripción: Gestiona las operaciones de correo electrónico (SMTP e IMAP)

import smtplib
import imaplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
import email
from datetime import date, timedelta
from case_handler import CaseHandler


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

            email_addr = self._sanitize_string(email_addr)
            password = self._sanitize_string(password)

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

            email_addr = self._sanitize_string(email_addr)
            password = self._sanitize_string(password)

            context = ssl.create_default_context()

            imap = imaplib.IMAP4_SSL(server, port, ssl_context=context)
            imap.login(email_addr, password)
            imap.logout()

            return True

        except Exception as e:
            print(f"Error en la conexión IMAP: {str(e)}")
            return False

    def send_email(self, provider, email_addr, password, to, subject, body, cc_list=None, attachments=None):
        """Envía un correo electrónico a través de SMTP"""
        try:
            config = self.get_provider_config(provider)
            server = config['smtp_server']
            port = config['smtp_port']

            email_addr = self._sanitize_string(email_addr)
            password = self._sanitize_string(password)

            msg = MIMEMultipart()
            msg['From'] = email_addr
            msg['To'] = to
            msg['Subject'] = subject

            if cc_list:
                msg['Cc'] = ", ".join(cc_list)

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            if attachments:
                for attachment in attachments:
                    self._attach_file(msg, attachment)

            context = ssl.create_default_context()

            with smtplib.SMTP(server, port) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(email_addr, password)
                smtp.send_message(msg)

            return True

        except Exception as e:
            print(f"Error al enviar correo: {str(e)}")
            return False

    def _attach_file(self, msg, attachment):
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

    def check_and_process_emails(self, provider, email_addr, password, search_titles, logger, cc_list=None):
        """Función principal que revisa emails y procesa los que coinciden"""
        try:
            config = self.get_provider_config(provider)
            server = config['imap_server']
            port = config['imap_port']

            email_addr = self._sanitize_string(email_addr)
            password = self._sanitize_string(password)

            context = ssl.create_default_context()

            with imaplib.IMAP4_SSL(server, port, ssl_context=context) as imap:
                imap.login(email_addr, password)
                imap.select('INBOX')

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
                logger.log(f"Ejecutando búsqueda IMAP: {final_query}", level="INFO")

                try:
                    status, messages = imap.search('UTF-8', final_query)
                except:
                    logger.log("Reintentando búsqueda sin UTF-8...", level="WARNING")
                    status, messages = imap.search(None, final_query)

                message_ids = messages[0].split()

                if not message_ids:
                    logger.log("No se encontraron correos nuevos que coincidan.", level="INFO")
                    return

                logger.log(f"Encontrados {len(message_ids)} emails que coinciden", level="INFO")

                for msg_id in message_ids:
                    try:
                        logger.log(f"Procesando email ID: {msg_id}", level="INFO")

                        status, email_data = imap.fetch(msg_id, '(RFC822)')

                        if status != 'OK' or not email_data:
                            logger.log(f"No se pudo obtener el email {msg_id}", level="WARNING")
                            continue

                        raw_email = email_data[0][1]
                        email_message = email.message_from_bytes(raw_email, policy=email.policy.default)

                        subject = self._decode_header_value(email_message.get('Subject', ''))
                        sender = email_message.get('From', '')

                        logger.log(f"Revisando email: '{subject}' de {sender}", level="INFO")

                        attachments = self._extract_attachments(email_message, logger)

                        matching_case = self.case_handler.find_matching_case(subject, logger)

                        if matching_case:
                            logger.log(f"Email encontrado para caso: {matching_case}", level="INFO")

                            email_data_for_case = {
                                'sender': sender,
                                'subject': subject,
                                'msg_id': msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                                'attachments': attachments
                            }

                            response_data = self.case_handler.execute_case(matching_case, email_data_for_case, logger)

                            if response_data:
                                self._mark_as_read(imap, msg_id, logger)

                                response_attachments = response_data.get('attachments', [])
                                if self._send_case_reply(provider, email_addr, password, response_data, logger,
                                                         cc_list, response_attachments):
                                    logger.log(f"Respuesta automática enviada usando {matching_case}", level="INFO")
                                else:
                                    logger.log("Error al enviar respuesta automática", level="ERROR")
                            else:
                                logger.log(f"Error al procesar {matching_case}", level="ERROR")
                        else:
                            logger.log(f"Email no coincide con ningún caso: '{subject}'", level="INFO")

                    except Exception as e:
                        logger.log(f"Error al procesar email individual {msg_id}: {str(e)}", level="ERROR")

        except Exception as e:
            logger.log(f"Error en check_and_process_emails: {str(e)}", level="ERROR")

    def _extract_attachments(self, email_message, logger):
        """Extrae los archivos adjuntos de un email"""
        attachments = []

        try:
            if not email_message.is_multipart():
                return attachments

            for part in email_message.walk():
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    filename = part.get_filename()

                    if filename:
                        filename = self._decode_header_value(filename)
                        file_data = part.get_payload(decode=True)

                        if file_data:
                            attachments.append({
                                'filename': filename,
                                'data': file_data,
                                'content_type': part.get_content_type()
                            })

            return attachments

        except Exception as e:
            logger.log(f"Error extrayendo adjuntos: {str(e)}", level="ERROR")
            return []

    def _send_case_reply(self, provider, email_addr, password, response_data, logger, cc_list=None, attachments=None):
        """Envía una respuesta automática usando los datos del caso"""
        try:
            recipient = response_data.get('recipient', '')
            subject = response_data.get('subject', '')
            body = response_data.get('body', '')

            if '<' in recipient and '>' in recipient:
                recipient = recipient.split('<')[1].split('>')[0].strip()

            temp_files_to_clean = []
            if attachments:
                for attachment in attachments:
                    if 'path' in attachment:
                        temp_files_to_clean.append(attachment['path'])

            result = self.send_email(provider, email_addr, password, recipient, subject, body, cc_list, attachments)

            for temp_path in temp_files_to_clean:
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception:
                    pass

            return result

        except Exception as e:
            logger.log(f"Error al enviar respuesta del caso: {str(e)}", level="ERROR")
            return False

    def _mark_as_read(self, imap_connection, msg_id, logger):
        """Marca un email específico como leído"""
        try:
            status, result = imap_connection.store(msg_id, '+FLAGS', '\\Seen')

            if status == 'OK':
                logger.log(f"Email {msg_id} marcado como leído", level="INFO")
                return True, "Email marcado como leído"
            else:
                return False, f"Estado no OK del servidor: {status}"

        except Exception as e:
            logger.log(f"Excepción al marcar email como leído: {str(e)}", level="ERROR")
            return False, f"Error: {str(e)}"

    def _sanitize_string(self, text):
        """Sanitiza un string para evitar problemas de codificación"""
        if not isinstance(text, str):
            return str(text)

        text = ''.join(c for c in text if c.isprintable() and ord(c) != 0xA0)
        return text

    def _decode_header_value(self, header_value):
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