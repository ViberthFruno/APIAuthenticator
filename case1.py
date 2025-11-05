# Archivo: case1.py
# Ubicación: raíz del proyecto
# Descripción: Caso 1 - Procesa PDFs de boletas de reparación y genera archivo de texto ordenado

import re
import tempfile
from datetime import datetime

from base_case import BaseCase


def _generate_formatted_text(data):
    """Genera el archivo de texto formateado"""
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
        if 'nombre_cliente' in data:
            lines.append(f"Nombre: {data['nombre_cliente']}")
        if 'nombre_contacto' in data:
            lines.append(f"Nombre: {data['nombre_contacto']}")
        if 'cedula_cliente' in data:
            lines.append(f"Cédula: {data['cedula_cliente']}")
        if 'telefono_cliente' in data:
            lines.append(f"Teléfono: {data['telefono_cliente']}")
        if 'telefono_adicional' in data:
            lines.append(f"Teléfono Adicional: {data['telefono_adicional']}")
        if 'correo_cliente' in data:
            lines.append(f"Correo: {data['correo_cliente']}")
        if 'direccion_cliente' in data:
            lines.append(f"Dirección: {data['direccion_cliente']}")
        lines.append("")

    producto_keys = ['codigo_producto', 'descripcion_producto', 'marca',
                     'modelo', 'serie', 'codigo_distribuidor']
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


def extract_repair_data(text, logger):
    """Extrae los campos relevantes del texto del PDF"""
    data = {}

    try:
        match = re.search(r'No\.Transaccion:\s*(\S+)', text)
        if match:
            data['numero_transaccion'] = match.group(1).strip()

        match = re.search(r'No\.\s*Boleta:\s*(\S+)', text)
        if match:
            data['numero_boleta'] = match.group(1).strip()
            data['referencia'] = data['numero_boleta'].split('-')[0].zfill(3)
            logger.info(f"Boleta: {data['numero_boleta']}")

        match = re.search(r'Fecha:\s*(\d{2}/\d{2}/\d{4})', text)
        if match:
            data['fecha'] = match.group(1).strip()

        match = re.search(r'Gestionada por:\s*(.+?)(?:\n|$)', text)
        if match:
            data['gestionada_por'] = match.group(1).strip()

        match = re.search(r'(\d{3}\s+[\w\-]+)', text)
        if match:
            data['sucursal'] = match.group(1).strip()

        match = re.search(r'Telefonos:\s*(\d+)', text)
        if match:
            data['telefono_sucursal'] = match.group(1).strip()

        match = re.search(r'C L I E N T E:\s*(.+?)\s+Tel:', text)
        if match:
            data['nombre_cliente'] = match.group(1).strip()
            logger.info(f"Cliente: {data['nombre_cliente']}")

        match = re.search(r'C O N T A C T O:\s*(.+?)\s+Tel:', text)
        if match:
            data['nombre_contacto'] = match.group(1).strip()
            logger.info(f"Contacto: {data['nombre_contacto']}")

        # Cédula del cliente (la correcta está en CED)
        match = re.search(r'CED\s*([\d\-]+)', text)
        if match:
            data['cedula_cliente'] = match.group(1).strip()

        match = re.search(r'C L I E N T E:.*?Tel:\s*(\d+)', text)
        if match:
            data['telefono_cliente'] = match.group(1).strip()

        match = re.search(r'Correo:\s*([\w.\-]+@[\w.\-]+\.\w+)', text)
        if match:
            data['correo_cliente'] = match.group(1).strip()

        match = re.search(r'NUMERO ADICIONAL\s*(\d+)', text)
        if match:
            data['telefono_adicional'] = match.group(1).strip()

        match = re.search(r'Direcc:\s*(.+?)(?=\n.*?No\. Factura|\nNo\. Factura)', text, re.DOTALL)
        if match:
            direccion = match.group(1).strip()
            direccion = ' '.join(direccion.split())
            data['direccion_cliente'] = direccion

        match = re.search(r'Código:\s*(\d+)', text)
        if match:
            data['codigo_producto'] = match.group(1).strip()

        match = re.search(r'Código:\s*\d+\s+([A-Z\s]+?)\s+Serie:', text)
        if match:
            data['descripcion_producto'] = match.group(1).strip()

        match = re.search(r'Serie:\s*(\S+)', text)
        if match:
            data['serie'] = match.group(1).strip()

        match = re.search(r'Marca:\s*(\S+)', text)
        if match:
            data['marca'] = match.group(1).strip()

        match = re.search(r'Modelo:\s*(.+?)(?=\n|$)', text)
        if match:
            data['modelo'] = match.group(1).strip()

        match = re.search(r'Distrib:\s*(\d+)\s+(.+?)(?=\n|$)', text)
        if match:
            data['codigo_distribuidor'] = match.group(1).strip()
            data['distribuidor'] = match.group(2).strip()

        match = re.search(r'No\.\s*Factura:\s*(\S+)', text)
        if match:
            data['numero_factura'] = match.group(1).strip()

        match = re.search(r'Fecha de Compra:\s*(\d{2}/\d{2}/\d{4})', text)
        if match:
            data['fecha_compra'] = match.group(1).strip()

        match = re.search(r'Fechas-->Garantia\s+(\d{2}/\d{2}/\d{4})', text)
        if match:
            data['fecha_garantia'] = match.group(1).strip()

        match = re.search(r'Garantia:\s*(.+?)(?=\n|$)', text)
        if match:
            data['tipo_garantia'] = match.group(1).strip()

        match = re.search(r'Hecho por:\s*(.+?)\s+_', text)
        if match:
            nombre_completo = match.group(1).strip()
            nombre_completo = ' '.join(nombre_completo.split())
            data['hecho_por'] = nombre_completo

        match = re.search(r'D A Ñ O S:\s*(.+?)(?=\n={5,}|\n-{5,}|$)', text, re.DOTALL)
        if match:
            danos = match.group(1).strip()
            danos = ' '.join(danos.split())
            data['danos'] = danos
            logger.info(f"Daños: {data['danos']}")

        match = re.search(r'O B S E R V A C I O N E S:\s*(.+?)(?=\nNUMERO ADICIONAL|\nD A Ñ O S:)', text, re.DOTALL)
        if match:
            obs = match.group(1).strip()
            obs = ' '.join(obs.split())
            data['observaciones'] = obs

        logger.info(f"Total campos extraídos: {len(data)}")
        return data

    except Exception as e:
        logger.exception(f"Error en extracción de datos: {e}")
        return data


def _extract_text_from_pdf(pdf_data, logger):
    """Extrae texto plano del PDF usando pdfplumber"""
    try:
        import io
        try:
            import pdfplumber
        except ImportError:
            logger.warning("Instalando pdfplumber...")
            import subprocess
            subprocess.check_call(['pip', 'install', 'pdfplumber', '--break-system-packages'])
            import pdfplumber

        pdf_file = io.BytesIO(pdf_data)

        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        return text if text.strip() else None

    except Exception as e:
        logger.exception(f"Error al extraer texto: {e}")
        return None


def _generate_success_message(transaction_numbers, processed_files, failed_files, non_pdf_files):
    """Genera el mensaje de éxito con los números de transacción y estado de archivos"""
    timestamp = datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")

    message_lines = ["¡Estimado Usuario!", "",
                     "Fruno, Centro de Servicio Técnico de Reparación, le informa que se ha creado una solicitud de reparación para:",
                     ""]

    if transaction_numbers:
        if len(transaction_numbers) == 1:
            message_lines.append(f"• Unidad con No. Transacción: {transaction_numbers[0]}")
        else:
            message_lines.append("Las siguientes unidades:")
            for i, trans_num in enumerate(transaction_numbers, 1):
                message_lines.append(f"  {i}. Unidad con No. Transacción: {trans_num}")
    else:
        message_lines.append("• La(s) unidad(es) correspondiente(s)")

    message_lines.append("")

    # Mostrar archivos procesados exitosamente
    if processed_files:
        if len(processed_files) == 1:
            message_lines.append(f"Archivo procesado exitosamente: {processed_files[0]}")
        else:
            message_lines.append("Archivos procesados exitosamente:")
            for file in processed_files:
                message_lines.append(f"  ✓ {file}")
        message_lines.append("")

    # Mostrar archivos que no se pudieron procesar
    if failed_files:
        message_lines.append("⚠ Archivos que no se pudieron procesar:")
        for file in failed_files:
            message_lines.append(f"  ✗ {file}")
        message_lines.append("")
        message_lines.append("Por favor, revise los archivos que no se procesaron y reenvíelos si es necesario.")
        message_lines.append("")

    # Mostrar archivos que no son PDF
    if non_pdf_files:
        message_lines.append("ℹ Archivos recibidos que no son PDF (no procesados):")
        for file in non_pdf_files:
            message_lines.append(f"  • {file}")
        message_lines.append("")

    message_lines.append(
        "Adjunto encontrará el/los archivo(s) procesado(s) con la información detallada de la(s) boleta(s) de reparación.")
    message_lines.append("")
    message_lines.append("Saludos cordiales,")
    message_lines.append("Fruno - Centro de Servicio Técnico de Reparación")
    message_lines.append("")
    message_lines.append(f"Fecha y hora de procesamiento: {timestamp}")

    return "\n".join(message_lines)


def _generate_all_failed_message(failed_files, non_pdf_files):
    """Genera el mensaje cuando todos los PDFs fallan al procesarse"""
    timestamp = datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")

    message_lines = ["Estimado Usuario,", "",
                     "Se recibió su correo, sin embargo no fue posible procesar los archivos adjuntos.", ""]

    if failed_files:
        message_lines.append("Archivos PDF que no se pudieron procesar:")
        for file in failed_files:
            message_lines.append(f"  • {file}")
        message_lines.append("")

    if non_pdf_files:
        message_lines.append("Archivos recibidos que no son PDF:")
        for file in non_pdf_files:
            message_lines.append(f"  • {file}")
        message_lines.append("")

    message_lines.append("Por favor, verifique que:")
    message_lines.append("  • Los archivos PDF no estén dañados o corruptos")
    message_lines.append("  • Los archivos sean boletas de reparación válidas")
    message_lines.append("  • Los archivos contengan información legible")
    message_lines.append("")
    message_lines.append("Si el problema persiste, contacte al Centro de Servicio.")
    message_lines.append("")
    message_lines.append("Saludos cordiales,")
    message_lines.append("Fruno - Centro de Servicio Técnico de Reparación")
    message_lines.append("")
    message_lines.append(f"Fecha y hora de procesamiento: {timestamp}")

    return "\n".join(message_lines)


def _generate_no_pdf_message(non_pdf_files):
    """Genera el mensaje cuando no se adjunta ningún PDF"""
    timestamp = datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")

    message_lines = ["Estimado Usuario,", "",
                     "Se ha recibido su correo, sin embargo no se detectó ningún archivo PDF adjunto.", ""]

    if non_pdf_files:
        message_lines.append("Archivos recibidos (no son PDF):")
        for file in non_pdf_files:
            message_lines.append(f"  • {file}")
        message_lines.append("")

    message_lines.append(
        "Para procesar su solicitud de reparación, es necesario que adjunte el archivo PDF de la boleta de reparación.")
    message_lines.append("")
    message_lines.append(
        "Por favor, revise si adjuntó el archivo correcto y reenvíe el correo con el archivo PDF correspondiente.")
    message_lines.append("")
    message_lines.append("Saludos cordiales,")
    message_lines.append("Fruno - Centro de Servicio Técnico de Reparación")
    message_lines.append("")
    message_lines.append(f"Fecha y hora de procesamiento: {timestamp}")

    return "\n".join(message_lines)


class Case(BaseCase):
    def __init__(self):
        super().__init__(
            name="Caso 1",
            description="Procesa PDFs de boletas de reparación y genera archivo de texto ordenado",
            config_key="caso1",
            response_message="Adjunto encontrará el archivo procesado con la información de la boleta de reparación.",
        )

    def process_email(self, email_data, logger):
        """Procesa el email y genera una respuesta con el archivo de texto ordenado"""
        try:
            sender = email_data.get('sender', '')
            # subject = email_data.get('subject', '')
            attachments = email_data.get('attachments', [])

            logger.info(f"Procesando {self._config_key} para email de {sender}")

            # Clasificar archivos adjuntos
            pdf_attachments = []
            non_pdf_files = []

            for attachment in attachments:
                content_type = attachment.get('content_type', '').lower()
                filename = attachment.get('filename', 'archivo_sin_nombre')

                if 'pdf' in content_type or filename.lower().endswith('.pdf'):
                    pdf_attachments.append(attachment)
                    logger.info(f"PDF encontrado: {filename}")
                else:
                    non_pdf_files.append(filename)
                    logger.warning(f"Archivo no-PDF detectado: {filename}")

            # Validación: Si no hay PDFs adjuntos
            if not pdf_attachments:
                logger.warning("No se encontró ningún archivo PDF adjunto")
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                response = {
                    'recipient': sender,
                    'subject': f"Confirmación de Preingreso - Sin PDF - {timestamp}",
                    'body': _generate_no_pdf_message(non_pdf_files)
                }
                return response

            # Procesar todos los PDFs encontrados
            logger.info(f"Total de PDFs a procesar: {len(pdf_attachments)}")

            all_attachments = []
            transaction_numbers = []
            boleta_numbers = []  # Nueva lista para números de boleta
            processed_files = []
            failed_files = []

            for idx, pdf_attachment in enumerate(pdf_attachments, 1):
                pdf_content = pdf_attachment.get('data')
                pdf_filename = pdf_attachment.get('filename', f'documento_{idx}.pdf')

                logger.info(f"Procesando PDF {idx}/{len(pdf_attachments)}: {pdf_filename}")

                pdf_text = _extract_text_from_pdf(pdf_content, logger)

                if not pdf_text:
                    logger.error(f"No se pudo extraer texto del PDF: {pdf_filename}")
                    failed_files.append(pdf_filename)
                    continue

                logger.info(f"Texto extraído ({len(pdf_text)} caracteres)")

                extracted_data = extract_repair_data(pdf_text, logger)
                logger.info(f"Campos extraídos: {len(extracted_data)}")

                # Verificar si se extrajo información útil (al menos 3 campos)
                if not extracted_data or len(extracted_data) < 3:
                    logger.error(f"PDF sin información válida: {pdf_filename}")
                    failed_files.append(pdf_filename)
                    continue

                # Guardar número de transacción para el mensaje
                if 'numero_transaccion' in extracted_data:
                    transaction_numbers.append(extracted_data['numero_transaccion'])

                # Guardar número de boleta para el subject
                if 'numero_boleta' in extracted_data:
                    boleta_numbers.append(extracted_data['numero_boleta'])

                txt_content = _generate_formatted_text(extracted_data)

                temp_file = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False)
                temp_file.write(txt_content)
                temp_file.close()

                with open(temp_file.name, 'rb') as f:
                    file_data = f.read()

                # Generar nombre de archivo con timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                boleta_num = extracted_data.get("numero_boleta", "procesada").replace("-", "_")
                filename = f'boleta_{boleta_num}_{timestamp}.txt'

                all_attachments.append({
                    'filename': filename,
                    'data': file_data,
                    'path': temp_file.name
                })

                processed_files.append(pdf_filename)
                logger.info(f"Archivo generado: {filename}")

            # Validar si se procesó al menos un PDF correctamente
            if not all_attachments:
                logger.error("No se pudo procesar ningún PDF correctamente")
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                response = {
                    'recipient': sender,
                    'subject': f"Confirmación de Preingreso - Error en Procesamiento - {timestamp}",
                    'body': _generate_all_failed_message(failed_files, non_pdf_files)
                }
                return response

            # Generar mensaje de éxito con los números de transacción
            body_message = _generate_success_message(
                transaction_numbers,
                processed_files,
                failed_files,
                non_pdf_files
            )

            # Generar subject personalizado con número de boleta y timestamp
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            if boleta_numbers:
                if len(boleta_numbers) == 1:
                    subject_line = f"Confirmación de Preingreso - Boleta {boleta_numbers[0]} - {timestamp}"
                else:
                    boletas_str = ", ".join(boleta_numbers)
                    subject_line = f"Confirmación de Preingreso - Boletas {boletas_str} - {timestamp}"
            else:
                subject_line = f"Confirmación de Preingreso - {timestamp}"

            response = {
                'recipient': sender,
                'subject': subject_line,
                'body': body_message,
                'attachments': all_attachments
            }

            logger.info(f"Procesamiento completado: {len(all_attachments)} archivo(s) generado(s)")
            return response

        except Exception as e:
            logger.error(f"Error al procesar email: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
