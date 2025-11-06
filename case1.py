# Archivo: case1.py
# Ubicación: raíz del proyecto
# Descripción: Caso 1 - Procesa PDFs de boletas de reparación y crea preingresos en la API

import re
import tempfile
from datetime import datetime

from base_case import BaseCase
from gui_async_helper import run_async_from_sync
from api_integration.application.dtos import (
    DatosExtraidosPDF,
    CreatePreingresoInput,
    ArchivoAdjunto
)
from api_integration.application.use_cases.crear_preingreso_use_case import CreatePreingresoUseCase
from api_integration.infrastructure.api_ifrpro_repository import ApiIfrProRepository
from api_integration.infrastructure.authenticator_adapter import AuthenticatorAdapter
from api_integration.infrastructure.retry_policy import ExponentialRetryPolicy
from api_integration.infrastructure.http_client import HttpClient
from config_manager import ConfigManager


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


def _generate_success_message(preingreso_results, failed_files, non_pdf_files):
    """
    Genera el mensaje de éxito con los preingresos creados y estado de archivos

    Args:
        preingreso_results: Lista de dicts con {filename, boleta, preingreso_id, numero_transaccion}
        failed_files: Lista de dicts con {filename, error}
        non_pdf_files: Lista de nombres de archivos que no son PDF
    """
    timestamp = datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")

    message_lines = ["¡Estimado Usuario!", "",
                     "Fruno, Centro de Servicio Técnico de Reparación, le informa que se han procesado exitosamente las siguientes solicitudes de reparación:",
                     ""]

    # Mostrar preingresos creados exitosamente
    if preingreso_results:
        for idx, result in enumerate(preingreso_results, 1):
            message_lines.append(f"{idx}. Archivo: {result['filename']}")
            message_lines.append(f"   ✓ Boleta: {result['boleta']}")
            if result.get('preingreso_id'):
                message_lines.append(f"   ✓ ID Preingreso: {result['preingreso_id']}")
            if result.get('numero_transaccion'):
                message_lines.append(f"   ✓ No. Transacción: {result['numero_transaccion']}")
            message_lines.append("")

    # Mostrar archivos que no se pudieron procesar
    if failed_files:
        message_lines.append("⚠ Archivos que no se pudieron procesar:")
        for failed in failed_files:
            message_lines.append(f"  ✗ {failed['filename']}")
            if failed.get('error'):
                message_lines.append(f"    Motivo: {failed['error']}")
        message_lines.append("")
        message_lines.append("Por favor, revise los archivos que no se procesaron y reenvíelos si es necesario.")
        message_lines.append("")

    # Mostrar archivos que no son PDF
    if non_pdf_files:
        message_lines.append("ℹ Archivos recibidos que no son PDF (no procesados):")
        for file in non_pdf_files:
            message_lines.append(f"  • {file}")
        message_lines.append("")

    message_lines.append("Los preingresos han sido creados exitosamente en el sistema.")
    message_lines.append("")
    message_lines.append("Saludos cordiales,")
    message_lines.append("Fruno - Centro de Servicio Técnico de Reparación")
    message_lines.append("")
    message_lines.append(f"Fecha y hora de procesamiento: {timestamp}")

    return "\n".join(message_lines)


def _generate_all_failed_message(failed_files, non_pdf_files):
    """
    Genera el mensaje cuando todos los PDFs fallan al procesarse

    Args:
        failed_files: Lista de dicts con {filename, error}
        non_pdf_files: Lista de nombres de archivos que no son PDF
    """
    timestamp = datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")

    message_lines = ["Estimado Usuario,", "",
                     "Se recibió su correo, sin embargo no fue posible procesar los archivos adjuntos.", ""]

    if failed_files:
        message_lines.append("Archivos PDF que no se pudieron procesar:")
        for failed in failed_files:
            message_lines.append(f"  • {failed['filename']}")
            if failed.get('error'):
                message_lines.append(f"    Motivo: {failed['error']}")
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
    message_lines.append("  • La información del PDF sea correcta (fecha de compra, garantía, etc.)")
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


def _strip_if_string(value):
    """Retorna None si es None, sino retorna el string sin espacios"""
    if value is None:
        return None
    return str(value).strip() if value else None


def _crear_preingreso_desde_pdf(pdf_content, pdf_filename, logger):
    """
    Crea un preingreso en la API a partir del contenido de un PDF

    Args:
        pdf_content: Bytes del archivo PDF
        pdf_filename: Nombre del archivo PDF
        logger: Logger para registrar eventos

    Returns:
        dict con {success, preingreso_id, boleta, numero_transaccion, error}
    """
    try:
        # Extraer texto del PDF
        logger.info(f"Extrayendo texto del PDF: {pdf_filename}")
        pdf_text = _extract_text_from_pdf(pdf_content, logger)

        if not pdf_text:
            return {
                'success': False,
                'error': 'No se pudo extraer texto del PDF',
                'filename': pdf_filename
            }

        # Extraer datos del PDF
        logger.info(f"Extrayendo datos del PDF: {pdf_filename}")
        extracted_data = extract_repair_data(pdf_text, logger)

        if not extracted_data or len(extracted_data) < 3:
            return {
                'success': False,
                'error': 'PDF sin información válida (menos de 3 campos extraídos)',
                'filename': pdf_filename
            }

        # Crear archivo temporal para el PDF
        temp_pdf = tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False)
        temp_pdf.write(pdf_content)
        temp_pdf.close()

        # Crear DTO con los datos extraídos
        datos_pdf = DatosExtraidosPDF(
            numero_boleta=_strip_if_string(extracted_data.get('numero_boleta', '')),
            referencia=_strip_if_string(extracted_data.get('referencia', '')),
            nombre_sucursal=_strip_if_string(extracted_data.get('sucursal', '')),
            numero_transaccion=_strip_if_string(extracted_data.get('numero_transaccion', '')),
            cliente_nombre=_strip_if_string(extracted_data.get('nombre_cliente', '')),
            cliente_contacto=_strip_if_string(extracted_data.get('nombre_contacto', '')),
            cliente_telefono=_strip_if_string(extracted_data.get('telefono_cliente', '')),
            cliente_correo=_strip_if_string(extracted_data.get('correo_cliente', '')),
            serie=_strip_if_string(extracted_data.get('serie', '')),
            garantia_nombre=_strip_if_string(extracted_data.get('tipo_garantia', '')),
            fecha_compra=_strip_if_string(extracted_data.get('fecha_compra')),
            factura=_strip_if_string(extracted_data.get('numero_factura')),
            cliente_cedula=_strip_if_string(extracted_data.get('cedula_cliente')),
            cliente_direccion=_strip_if_string(extracted_data.get('direccion_cliente')),
            cliente_telefono2=_strip_if_string(extracted_data.get('telefono_adicional')),
            fecha_transaccion=_strip_if_string(extracted_data.get('fecha')),
            transaccion_gestionada_por=_strip_if_string(extracted_data.get('gestionada_por')),
            telefono_sucursal=_strip_if_string(extracted_data.get('telefono_sucursal')),
            producto_codigo=_strip_if_string(extracted_data.get('codigo_producto')),
            producto_descripcion=_strip_if_string(extracted_data.get('descripcion_producto')),
            marca_nombre=_strip_if_string(extracted_data.get('marca')),
            modelo_nombre=_strip_if_string(extracted_data.get('modelo')),
            garantia_fecha=_strip_if_string(extracted_data.get('fecha_garantia')),
            danos=_strip_if_string(extracted_data.get('danos')),
            observaciones=_strip_if_string(extracted_data.get('observaciones')),
            hecho_por=_strip_if_string(extracted_data.get('hecho_por'))
        )

        # Crear archivo adjunto
        archivo_adjunto = ArchivoAdjunto(
            nombre_archivo=pdf_filename,
            ruta_archivo=temp_pdf.name,
            tipo_mime="application/pdf"
        )

        # Crear instancias necesarias para el use case
        config_manager = ConfigManager()
        authenticator = AuthenticatorAdapter(config_manager)
        http_client = HttpClient(authenticator)
        repository = ApiIfrProRepository(http_client)
        retry_policy = ExponentialRetryPolicy(max_retries=2)

        # Crear caso de uso
        use_case = CreatePreingresoUseCase(repository, retry_policy)

        # Crear input para el use case
        input_dto = CreatePreingresoInput(
            datos_pdf=datos_pdf,
            retry_on_failure=True,
            validate_before_send=True,
            archivo_adjunto=archivo_adjunto
        )

        logger.info(f"Creando preingreso para: {pdf_filename}")

        # Ejecutar caso de uso de forma asíncrona (desde código síncrono)
        async def ejecutar_creacion():
            return await use_case.execute(input_dto)

        result = run_async_from_sync(ejecutar_creacion())

        # Limpiar archivo temporal
        import os
        try:
            os.unlink(temp_pdf.name)
        except:
            pass

        if result.success:
            logger.info(f"✅ Preingreso creado exitosamente: {result.preingreso_id}")
            return {
                'success': True,
                'preingreso_id': result.preingreso_id,
                'boleta': result.boleta_usada,
                'numero_transaccion': extracted_data.get('numero_transaccion'),
                'filename': pdf_filename
            }
        else:
            error_msg = result.message or "Error desconocido al crear preingreso"
            logger.error(f"❌ Error al crear preingreso: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'filename': pdf_filename
            }

    except Exception as e:
        logger.exception(f"Error al crear preingreso desde PDF {pdf_filename}: {str(e)}")
        return {
            'success': False,
            'error': f"Error inesperado: {str(e)}",
            'filename': pdf_filename
        }


class Case(BaseCase):
    def __init__(self):
        super().__init__(
            name="Caso 1",
            description="Procesa PDFs de boletas de reparación y crea preingresos en la API",
            config_key="caso1",
            response_message="Los preingresos han sido creados exitosamente en el sistema.",
        )

    def process_email(self, email_data, logger):
        """Procesa el email, crea preingresos en la API y genera una respuesta"""
        try:
            sender = email_data.get('sender', '')
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

            # Procesar todos los PDFs encontrados y crear preingresos
            logger.info(f"Total de PDFs a procesar: {len(pdf_attachments)}")

            preingreso_results = []  # Lista de preingresos creados exitosamente
            failed_files = []  # Lista de archivos que fallaron

            for idx, pdf_attachment in enumerate(pdf_attachments, 1):
                pdf_content = pdf_attachment.get('data')
                pdf_filename = pdf_attachment.get('filename', f'documento_{idx}.pdf')

                logger.info(f"Procesando PDF {idx}/{len(pdf_attachments)}: {pdf_filename}")

                # Crear preingreso desde el PDF
                result = _crear_preingreso_desde_pdf(pdf_content, pdf_filename, logger)

                if result['success']:
                    preingreso_results.append({
                        'filename': pdf_filename,
                        'boleta': result.get('boleta'),
                        'preingreso_id': result.get('preingreso_id'),
                        'numero_transaccion': result.get('numero_transaccion')
                    })
                    logger.info(f"✅ Preingreso creado para: {pdf_filename}")
                else:
                    failed_files.append({
                        'filename': pdf_filename,
                        'error': result.get('error', 'Error desconocido')
                    })
                    logger.error(f"❌ Falló el procesamiento de: {pdf_filename}")

            # Validar si se creó al menos un preingreso correctamente
            if not preingreso_results:
                logger.error("No se pudo crear ningún preingreso correctamente")
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                response = {
                    'recipient': sender,
                    'subject': f"Confirmación de Preingreso - Error en Procesamiento - {timestamp}",
                    'body': _generate_all_failed_message(failed_files, non_pdf_files)
                }
                return response

            # Generar mensaje de éxito con los preingresos creados
            body_message = _generate_success_message(
                preingreso_results,
                failed_files,
                non_pdf_files
            )

            # Generar subject personalizado con números de boleta y timestamp
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            boleta_numbers = [r.get('boleta') for r in preingreso_results if r.get('boleta')]

            if boleta_numbers:
                if len(boleta_numbers) == 1:
                    subject_line = f"Confirmación de Preingreso Creado - Boleta {boleta_numbers[0]} - {timestamp}"
                else:
                    boletas_str = ", ".join(boleta_numbers[:3])  # Mostrar solo las primeras 3
                    if len(boleta_numbers) > 3:
                        boletas_str += f" (y {len(boleta_numbers) - 3} más)"
                    subject_line = f"Confirmación de Preingresos Creados - {boletas_str} - {timestamp}"
            else:
                subject_line = f"Confirmación de Preingreso - {timestamp}"

            response = {
                'recipient': sender,
                'subject': subject_line,
                'body': body_message,
                'attachments': []  # No enviamos archivos adjuntos, solo el mensaje
            }

            logger.info(f"Procesamiento completado: {len(preingreso_results)} preingreso(s) creado(s)")
            return response

        except Exception as e:
            logger.error(f"Error al procesar email: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
