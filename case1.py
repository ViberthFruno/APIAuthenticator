# Archivo: case1.py
# Ubicación: raíz del proyecto
# Descripción: Caso 1 - Procesa PDFs de boletas de reparación y crea preingresos en la API

import re
import tempfile
from datetime import datetime

from api_integration.application.dtos import (
    DatosExtraidosPDF,
    CreatePreingresoInput,
    ArchivoAdjunto
)
from api_integration.application.use_cases.crear_preingreso_use_case import CreatePreingresoUseCase
from api_integration.domain.entities import ApiCredentials
from api_integration.infrastructure.api_ifrpro_repository import create_ifrpro_repository
from api_integration.infrastructure.authenticator_adapter import create_api_authenticator
from api_integration.infrastructure.http_client import create_api_client, TenacityRetryPolicy
from base_case import BaseCase
from gui_async_helper import run_async_from_sync
from settings import Settings


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
    """Extrae los campos relevantes del texto del PDF (optimizado para OCR)"""
    data = {}

    try:
        # Normalizar texto para OCR: eliminar espacios múltiples
        text = re.sub(r'\s+', ' ', text)

        # Número de transacción (más flexible)
        match = re.search(r'No\s*\.?\s*Transacci[oó]n\s*:?\s*(\d+)', text, re.IGNORECASE)
        if match:
            data['numero_transaccion'] = match.group(1).strip()

        # Número de boleta (más flexible)
        match = re.search(r'No\s*\.?\s*Boleta\s*:?\s*(\d+-\d+)', text, re.IGNORECASE)
        if match:
            data['numero_boleta'] = match.group(1).strip()
            data['referencia'] = data['numero_boleta'].split('-')[0].zfill(3)
            logger.info(f"Boleta: {data['numero_boleta']}")

        # Fecha (más flexible)
        match = re.search(r'Fecha\s*:?\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
        if match:
            data['fecha'] = match.group(1).strip()

        # Gestionada por (más flexible)
        match = re.search(r'Gestionada\s+por\s*:?\s*Taller\s+Local', text, re.IGNORECASE)
        if match:
            data['gestionada_por'] = "Taller Local"

        # Sucursal (buscar código de 3 dígitos seguido de nombre)
        match = re.search(r'(\d{3})\s+([\w\s\-]+?)(?=\s+Telefonos?|Tel)', text, re.IGNORECASE)
        if match:
            data['sucursal'] = f"{match.group(1)} {match.group(2).strip()}"

        # Teléfono sucursal (más flexible)
        match = re.search(r'Telefonos?\s*:?\s*(\d+)', text, re.IGNORECASE)
        if match:
            data['telefono_sucursal'] = match.group(1).strip()

        # Cliente/Contacto (más flexible para OCR que puede separar con espacios)
        match = re.search(r'C\s*O\s*N\s*T\s*A\s*C\s*T\s*O\s*:?\s*([A-Z\s]+?)(?=\s+Tel|CED)', text, re.IGNORECASE)
        if match:
            data['nombre_contacto'] = re.sub(r'\s+', ' ', match.group(1).strip())
            data['nombre_cliente'] = data['nombre_contacto']  # Usar el mismo
            logger.info(f"Cliente/Contacto: {data['nombre_contacto']}")

        # Cédula (más flexible)
        match = re.search(r'CED\s*:?\s*([\d\-]+)', text, re.IGNORECASE)
        if match:
            data['cedula_cliente'] = match.group(1).strip()

        # Teléfono cliente (más flexible)
        match = re.search(r'Tel\s*:?\s*(\d{8,})', text, re.IGNORECASE)
        if match:
            data['telefono_cliente'] = match.group(1).strip()

        # Correo electrónico (CRÍTICO - muy flexible para OCR)
        correo_encontrado = None

        # Patrón 1: Buscar después de la palabra "Correo" con espacios flexibles
        match = re.search(r'Correo\s*:?\s*([\w\.\-_]+\s*@\s*[\w\.\-]+\s*\.\s*\w+)', text, re.IGNORECASE)
        if match:
            correo_encontrado = match.group(1).strip()
            logger.info(f"Correo encontrado (patrón 1 - después de 'Correo:'): {correo_encontrado}")

        # Patrón 2: Buscar en la sección del cliente/contacto (más específico)
        if not correo_encontrado:
            # Buscar en un contexto de 200 caracteres después de "CLIENTE" o "CONTACTO"
            cliente_section = re.search(r'(?:CLIENTE|CONTACTO).{0,200}', text, re.IGNORECASE | re.DOTALL)
            if cliente_section:
                section_text = cliente_section.group(0)
                match = re.search(r'([\w\.\-_]+@[\w\.\-]+\.\w+)', section_text, re.IGNORECASE)
                if match:
                    correo_encontrado = match.group(1).strip()
                    logger.info(f"Correo encontrado (patrón 2 - en sección cliente): {correo_encontrado}")

        # Patrón 3: Búsqueda agresiva en todo el documento (formato email válido)
        if not correo_encontrado:
            # Buscar cualquier cosa que parezca un email (incluye typos comunes)
            match = re.search(r'\b([\w\.\-_]+@[\w\.\-]+\.\w{2,})\b', text, re.IGNORECASE)
            if match:
                correo_encontrado = match.group(1).strip()
                logger.info(f"Correo encontrado (patrón 3 - búsqueda global): {correo_encontrado}")

        # Patrón 3.5: Buscar correos con typos comunes (gmal, hotmial, etc)
        if not correo_encontrado:
            match = re.search(r'\b([\w\.\-_]+@(?:gmal|g mail|hotmial|outloo|yaho)\.com)\b', text, re.IGNORECASE)
            if match:
                correo_encontrado = match.group(1).strip()
                # Corregir typos automáticamente
                correo_encontrado = correo_encontrado.replace('gmal', 'gmail')
                correo_encontrado = correo_encontrado.replace('g mail', 'gmail')
                correo_encontrado = correo_encontrado.replace('hotmial', 'hotmail')
                correo_encontrado = correo_encontrado.replace('outloo', 'outlook')
                correo_encontrado = correo_encontrado.replace('yaho', 'yahoo')
                logger.info(f"Correo encontrado con typo corregido (patrón 3.5): {correo_encontrado}")

        # Patrón 4: Búsqueda con espacios internos (para OCR mal formateado)
        if not correo_encontrado:
            match = re.search(r'([\w\.\-_]+\s*@\s*[\w\.\-]+\s*\.\s*\w+)', text, re.IGNORECASE)
            if match:
                correo_encontrado = match.group(1).strip()
                logger.info(f"Correo encontrado (patrón 4 - con espacios): {correo_encontrado}")

        # Limpiar y validar el correo encontrado
        if correo_encontrado:
            # Eliminar todos los espacios internos
            correo_encontrado = re.sub(r'\s+', '', correo_encontrado)

            # Validar que el correo tenga formato básico válido
            if '@' in correo_encontrado and '.' in correo_encontrado.split('@')[1]:
                data['correo_cliente'] = correo_encontrado
                logger.info(f"✅ Correo extraído y validado: {correo_encontrado}")
            else:
                logger.warning(f"⚠️ Correo con formato inválido: {correo_encontrado}")
                # Si el formato es inválido, usar correo por defecto
                data['correo_cliente'] = "sin-correo@gollo.com"
        else:
            logger.warning("⚠️ No se pudo extraer el correo del cliente - usando correo por defecto")
            # Asignar correo por defecto cuando no se encuentra ninguno
            data['correo_cliente'] = "sin-correo@gollo.com"

        # Dirección (más flexible)
        match = re.search(r'Direcc\s*:?\s*(.+?)(?=\s*No\.\s*Factura|\s*Factura)', text, re.IGNORECASE)
        if match:
            direccion = re.sub(r'\s+', ' ', match.group(1).strip())
            data['direccion_cliente'] = direccion

        # Código producto (más flexible)
        match = re.search(r'C[óo]digo\s*:?\s*(\d+)', text, re.IGNORECASE)
        if match:
            data['codigo_producto'] = match.group(1).strip()

        # Descripción producto (más flexible)
        match = re.search(r'C[óo]digo\s*:?\s*\d+\s+([A-Z\s]+?)\s+(?:Serie|Marca)', text, re.IGNORECASE)
        if match:
            data['descripcion_producto'] = re.sub(r'\s+', ' ', match.group(1).strip())

        # Serie (más flexible)
        match = re.search(r'Serie\s*:?\s*([A-Z0-9\-]+)', text, re.IGNORECASE)
        if match:
            data['serie'] = match.group(1).strip()

        # Marca (más flexible)
        match = re.search(r'Marca\s*:?\s*(\w+)', text, re.IGNORECASE)
        if match:
            data['marca'] = match.group(1).strip()

        # Modelo (más flexible)
        match = re.search(r'Modelo\s*:?\s*([A-Z0-9]+)', text, re.IGNORECASE)
        if match:
            data['modelo'] = match.group(1).strip()

        # Distribuidor (más flexible)
        match = re.search(r'Distrib\s*:?\s*(\d+)\s+([A-Z]+)', text, re.IGNORECASE)
        if match:
            data['codigo_distribuidor'] = match.group(1).strip()
            data['distribuidor'] = match.group(2).strip()

        # Número de factura (más flexible - captura STOCK)
        match = re.search(r'No\s*\.?\s*Factura\s*:?\s*([^\s]+(?:\s+[^\s]+){0,5}?)(?=\s+Correo|\s+Fechas?)', text,
                          re.IGNORECASE)
        if match:
            data['numero_factura'] = re.sub(r'\s+', ' ', match.group(1).strip())

        # Fecha de compra (más flexible)
        match = re.search(r'(?:Fechas?|Compra)\s*[-:>]*\s*(?:Garantia|Garant[ií]a)?\s*(\d{2}/\d{2}/\d{4})', text,
                          re.IGNORECASE)
        if match:
            data['fecha_compra'] = match.group(1).strip()

        # Fecha de garantía (más flexible)
        match = re.search(r'Garant[ií]a\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
        if match:
            data['fecha_garantia'] = match.group(1).strip()

        # Tipo de garantía (más flexible)
        match = re.search(r'Garant[ií]a\s*:?\s*([A-Za-z\s]+?)(?=\s+C\.S\.R|$)', text, re.IGNORECASE)
        if match:
            data['tipo_garantia'] = re.sub(r'\s+', ' ', match.group(1).strip())

        # Hecho por (más flexible)
        match = re.search(r'Hecho\s+por\s*:?\s*([A-Z\s]+?)(?=\s+Firma|Cliente)', text, re.IGNORECASE)
        if match:
            data['hecho_por'] = re.sub(r'\s+', ' ', match.group(1).strip())

        # Daños (más flexible - captura frases completas)
        match = re.search(r'D\s*A\s*[NÑ]\s*O\s*S\s*:?\s*(.+?)(?=\s*={3,}|Hecho\s+por|$)', text, re.IGNORECASE)
        if match:
            danos = re.sub(r'\s+', ' ', match.group(1).strip())
            data['danos'] = danos
            logger.info(f"Daños: {danos}")

        # Observaciones (más flexible)
        match = re.search(
            r'O\s*B\s*S\s*E\s*R\s*V\s*A\s*C\s*I\s*O\s*N\s*E\s*S\s*:?\s*(.+?)(?=\s*D\s*A\s*[NÑ]\s*O\s*S|$)', text,
            re.IGNORECASE)
        if match:
            obs = re.sub(r'\s+', ' ', match.group(1).strip())
            data['observaciones'] = obs

        logger.info(f"Total campos extraídos: {len(data)}")
        return data

    except Exception as e:
        logger.exception(f"Error en extracción de datos: {e}")
        return data


def _is_oracle_reports_pdf(pdf_data):
    """
    Detecta si el PDF es generado por Oracle Reports
    Estos PDFs tienen una estructura especial que causa loops infinitos en pdfplumber
    """
    try:
        import io
        from PyPDF2 import PdfReader

        pdf_file = io.BytesIO(pdf_data)
        reader = PdfReader(pdf_file)

        # Verificar el productor del PDF
        if reader.metadata:
            producer = reader.metadata.get('/Producer', '')
            creator = reader.metadata.get('/Creator', '')

            # Oracle Reports típicamente se identifica en estos campos
            if 'Oracle' in str(producer) or 'Oracle' in str(creator):
                return True

        # Verificar la primera página - PDFs de Oracle Reports tienen una estructura específica
        if len(reader.pages) > 0:
            first_page = reader.pages[0]
            content = first_page.extract_text()

            # Si no hay texto extraíble o muy poco, probablemente es Oracle Reports
            if not content or len(content.strip()) < 50:
                return True

        return False

    except Exception:
        # Si hay error detectando, asumir que NO es Oracle Reports
        return False


def _extract_text_with_ocr(pdf_data, logger):
    """Extrae texto del PDF usando OCR con EasyOCR (para PDFs de Oracle Reports)"""
    try:
        import io
        import numpy as np
        from PIL import Image

        # Instalar EasyOCR si no está
        try:
            import easyocr
        except ImportError:
            logger.warning("Instalando EasyOCR (puede tardar unos minutos la primera vez)...")
            import subprocess
            subprocess.check_call(['pip', 'install', 'easyocr', '--break-system-packages'])
            import easyocr

        # Intentar con PyMuPDF (fitz)
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("Instalando PyMuPDF...")
            import subprocess
            subprocess.check_call(['pip', 'install', 'PyMuPDF', '--break-system-packages'])
            import fitz

        logger.info("Usando EasyOCR para extraer texto del PDF...")

        # Inicializar EasyOCR (solo una vez)
        # La primera vez descarga los modelos (~100MB), luego es rápido
        logger.info("Inicializando EasyOCR con español...")
        reader = easyocr.Reader(['es', 'en'], gpu=False)  # español e inglés

        # Abrir PDF con PyMuPDF
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")

        text = ""
        for page_num in range(len(pdf_document)):
            logger.info(f"Procesando página {page_num + 1}/{len(pdf_document)} con OCR...")

            # Renderizar página como imagen
            page = pdf_document[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))  # 300 DPI

            # Convertir a numpy array para EasyOCR
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)

            # Extraer texto con EasyOCR
            try:
                results = reader.readtext(img_array, detail=0, paragraph=True)

                # Combinar los resultados en texto
                if results:
                    page_text = '\n'.join(results)
                    if page_text:
                        text += page_text + "\n"

            except Exception as ocr_error:
                logger.warning(f"Error en OCR de página {page_num + 1}: {ocr_error}")

        pdf_document.close()

        if not text.strip():
            logger.warning("EasyOCR no extrajo ningún texto - intentando método alternativo")
            # Fallback: intentar extraer texto directamente de PyMuPDF
            try:
                pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
                for page_num in range(len(pdf_document)):
                    page = pdf_document[page_num]
                    page_text = page.get_text()
                    if page_text:
                        text += page_text + "\n"
                pdf_document.close()

                if text.strip():
                    logger.info("✅ Texto extraído usando método alternativo (PyMuPDF)")
            except:
                pass

        return text if text.strip() else None

    except Exception as e:
        logger.exception(f"Error al extraer texto con OCR: {e}")
        return None


def _extract_text_from_pdf(pdf_data, logger):
    """Extrae texto plano del PDF usando pdfplumber o OCR si es necesario"""
    try:
        import io
        import signal
        from contextlib import contextmanager

        @contextmanager
        def timeout(seconds):
            """Context manager para timeout"""

            def timeout_handler(signum, frame):
                raise TimeoutError("Timeout al procesar PDF")

            # Configurar timeout solo en Unix/Linux
            if hasattr(signal, 'SIGALRM'):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(seconds)
                try:
                    yield
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
            else:
                # En Windows, no hay timeout
                yield

        # Verificar si es un PDF de Oracle Reports
        is_oracle = _is_oracle_reports_pdf(pdf_data)

        if is_oracle:
            logger.info("PDF de Oracle Reports detectado - usando OCR")
            return _extract_text_with_ocr(pdf_data, logger)

        # Intentar con pdfplumber normal con timeout de 30 segundos
        try:
            import pdfplumber
        except ImportError:
            logger.warning("Instalando pdfplumber...")
            import subprocess
            subprocess.check_call(['pip', 'install', 'pdfplumber', '--break-system-packages'])
            import pdfplumber

        pdf_file = io.BytesIO(pdf_data)
        text = ""

        try:
            with timeout(30):  # Timeout de 30 segundos
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
        except TimeoutError:
            logger.warning("Timeout al extraer texto con pdfplumber - cambiando a OCR")
            return _extract_text_with_ocr(pdf_data, logger)
        except Exception as e:
            logger.warning(f"Error con pdfplumber: {e} - intentando con OCR")
            return _extract_text_with_ocr(pdf_data, logger)

        # Si no se extrajo texto, intentar con OCR
        if not text.strip():
            logger.info("No se extrajo texto con pdfplumber - intentando con OCR")
            return _extract_text_with_ocr(pdf_data, logger)

        return text if text.strip() else None

    except Exception as e:
        logger.exception(f"Error al extraer texto: {e}")
        return None


def _generate_success_message(preingreso_results, failed_files, non_pdf_files, api_base_url=None):
    """
    Genera el mensaje de éxito con los preingresos creados y estado de archivos

    Args:
        preingreso_results: Lista de dicts con {filename, boleta, preingreso_id, numero_transaccion}
        failed_files: Lista de dicts con {filename, error}
        non_pdf_files: Lista de nombres de archivos que no son PDF
        api_base_url: URL base de la API para generar links de consulta
    """
    # Determinar si es plural o singular
    es_plural = len(preingreso_results) > 1
    solicitud_text = "solicitud(es)" if es_plural else "solicitud"
    han_sido = "han sido procesadas" if es_plural else "ha sido procesada"

    message_lines = [
        "Estimado/a Usuario,",
        "",
        f"Fruno, Centro de Servicio Técnico de Reparación, le informa que su(s) {solicitud_text} de reparación {han_sido} exitosamente en nuestro sistema.",
        ""
    ]

    # Mostrar preingresos creados exitosamente
    if preingreso_results:
        for idx, result in enumerate(preingreso_results, 1):
            # Si hay múltiples archivos, agregar separador
            if len(preingreso_results) > 1:
                message_lines.append(f"═══ Solicitud {idx} de {len(preingreso_results)} ═══")
                message_lines.append("")

            message_lines.append("📄 Detalles de la solicitud:")
            message_lines.append("")
            message_lines.append(f"   Archivo: {result['filename']}")
            message_lines.append(f"   Boleta Gollo: {result['boleta']}")
            if result.get('numero_transaccion'):
                message_lines.append(f"   N.º de Transacción Gollo: {result['numero_transaccion']}")
            if result.get('preingreso_id'):
                message_lines.append(f"   Boleta Fruno: {result['preingreso_id']}")
            if result.get('consultar_guia'):
                message_lines.append(f"   Guía Fruno: {result['consultar_guia']}")

            message_lines.append("")

            # Sección de consulta del estado
            if result.get('consultar_reparacion'):
                message_lines.append("🔗 Consulta del estado:")
                message_lines.append("")
                message_lines.append(
                    "   Puede verificar el progreso de la reparación en cualquier momento haciendo clic en el siguiente enlace:")
                message_lines.append("")
                message_lines.append(f"   👉 {result['consultar_reparacion']}")
                message_lines.append("")

    # Mostrar archivos que no se pudieron procesar
    if failed_files:
        message_lines.append("")
        message_lines.append("⚠️ Archivos que no se pudieron procesar:")
        message_lines.append("")
        for failed in failed_files:
            message_lines.append(f"   ✗ {failed['filename']}")
            if failed.get('error'):
                message_lines.append(f"     Motivo: {failed['error']}")
        message_lines.append("")
        message_lines.append("Por favor, revise los archivos que no se procesaron y reenvíelos si es necesario.")
        message_lines.append("")

    # Mostrar archivos que no son PDF
    if non_pdf_files:
        message_lines.append("")
        message_lines.append("ℹ️ Archivos recibidos que no son PDF (no procesados):")
        message_lines.append("")
        for file in non_pdf_files:
            message_lines.append(f"   • {file}")
        message_lines.append("")

    # Cierre del mensaje
    message_lines.append("")
    message_lines.append("Los preingresos se han creado correctamente en nuestro sistema.")
    message_lines.append("")
    message_lines.append("Gracias por confiar en Fruno Centro de Servicio Técnico.")
    message_lines.append("")
    message_lines.append(
        "Si tiene alguna duda o requiere asistencia adicional, puede contactarnos a través de nuestros canales de soporte.")

    return "\n".join(message_lines)


def _generate_all_failed_message(failed_files, non_pdf_files, subject):
    """
    Genera el mensaje cuando todos los PDFs fallan al procesarse

    Args:
        failed_files: Lista de dicts con {filename, error}
        non_pdf_files: Lista de nombres de archivos que no son PDF
        subject: Asunto del correo recibido
    """
    timestamp = datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")

    message_lines = ["Estimado Usuario,", "",
                     f"Se ha recibido su correo bajo el asunto \"{subject}\", sin embargo no se detectó ningún archivo PDF adjunto.",
                     ""]

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

    return "\n".join(message_lines)


def _generate_409_conflict_message(subject, numero_boleta, numero_transaccion):
    """Genera el mensaje cuando hay un error 409 Conflict (preingreso duplicado)"""
    timestamp = datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")

    message_lines = ["Estimado Usuario,", ""]

    # Construir el mensaje con los datos disponibles
    boleta_info = f"número de boleta {numero_boleta}" if numero_boleta else "la boleta indicada"
    transaccion_info = f" y número de transacción {numero_transaccion}" if numero_transaccion else ""

    message_lines.append(
        f"Se ha recibido su correo bajo el asunto \"{subject}\", sin embargo no se pudo realizar, debido a que existe un preingreso en trámite con el {boleta_info}{transaccion_info}.")
    message_lines.append("")
    message_lines.append("Si el problema persiste, contacte al Centro de Servicio.")
    message_lines.append("")
    message_lines.append("Atentamente,")
    message_lines.append("Fruno - Centro de Servicio Técnico de Reparación")

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
        dict con {success, preingreso_id, boleta, numero_transaccion, consultar_reparacion, consultar_guia, error}
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
        settings = Settings()

        # Configurar credenciales desde Settings
        credentials = ApiCredentials(
            cuenta=settings.API_CUENTA,
            llave=settings.API_LLAVE,
            codigo_servicio=settings.API_CODIGO_SERVICIO,
            pais=settings.API_PAIS
        )

        # Crear authenticator
        authenticator = create_api_authenticator()

        # Crear cliente HTTP con políticas
        api_client, _, rate_limiter = create_api_client(
            authenticator=authenticator,
            base_url=settings.API_BASE_URL,
            timeout=settings.API_TIMEOUT,
            verify_ssl=settings.ENABLE_SSL_VERIFY,
            max_attempts=settings.MAX_RETRIES,
            rate_limit_calls=settings.RATE_LIMIT_CALLS
        )

        # Crear repositorio
        repository = create_ifrpro_repository(
            api_client=api_client,
            authenticator=authenticator,
            credentials=credentials,
            base_url=settings.API_BASE_URL,
            rate_limiter=rate_limiter
        )

        # Crear política de reintentos
        retry_policy = TenacityRetryPolicy(max_attempts=2)

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
            # Verificar si la API devolvió un JSON válido
            if not result.response.body:
                logger.warning("⚠️ La API no devolvió un json válido")
                return {
                    'success': False,
                    'error': "La API no devolvió un json válido",
                    'filename': pdf_filename
                }
            else:
                logger.info(f"✅ Preingreso creado exitosamente: {result.preingreso_id}")
                return {
                    'success': True,
                    'preingreso_id': result.preingreso_id,
                    'boleta': extracted_data.get('numero_boleta'),
                    'numero_transaccion': extracted_data.get('numero_transaccion'),
                    'consultar_reparacion': result.consultar_reparacion,
                    'consultar_guia': result.consultar_guia,
                    'filename': pdf_filename
                }
        else:
            error_msg = result.message or "Error desconocido al crear preingreso"
            logger.error(f"❌ Error al crear preingreso: {error_msg}")

            # Detectar error 409 Conflict (preingreso duplicado)
            is_409_conflict = '[409]' in error_msg or '409 Conflict' in error_msg

            return {
                'success': False,
                'error': error_msg,
                'filename': pdf_filename,
                'is_409_conflict': is_409_conflict,
                'numero_boleta': extracted_data.get('numero_boleta') if is_409_conflict else None,
                'numero_transaccion': extracted_data.get('numero_transaccion') if is_409_conflict else None
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
            subject = email_data.get('subject', 'Sin asunto')
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
                    'subject': f"Error: Sin Archivo PDF Adjunto - {timestamp}",
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
                        'numero_transaccion': result.get('numero_transaccion'),
                        'preingreso_id': result.get('preingreso_id'),
                        'consultar_reparacion': result.get('consultar_reparacion'),
                        'consultar_guia': result.get('consultar_guia')
                    })
                    logger.info(f"✅ Preingreso creado para: {pdf_filename}")
                else:
                    failed_files.append({
                        'filename': pdf_filename,
                        'error': result.get('error', 'Error desconocido'),
                        'is_409_conflict': result.get('is_409_conflict', False),
                        'numero_boleta': result.get('numero_boleta'),
                        'numero_transaccion': result.get('numero_transaccion')
                    })
                    logger.error(f"❌ Falló el procesamiento de: {pdf_filename}")

            # Validar si se creó al menos un preingreso correctamente
            if not preingreso_results:
                logger.error("No se pudo crear ningún preingreso correctamente")
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                # Verificar si hay errores 409 Conflict
                conflict_409_errors = [f for f in failed_files if f.get('is_409_conflict', False)]

                if conflict_409_errors:
                    # Si hay errores 409, usar el primero para generar el mensaje
                    first_conflict = conflict_409_errors[0]
                    logger.warning(
                        f"Error 409 detectado - Preingreso duplicado para boleta: {first_conflict.get('numero_boleta')}")

                    response = {
                        'recipient': sender,
                        'subject': f"Error: Preingreso Duplicado - {timestamp}",
                        'body': _generate_409_conflict_message(
                            subject,
                            first_conflict.get('numero_boleta'),
                            first_conflict.get('numero_transaccion')
                        )
                    }
                    return response

                # Si no hay errores 409, usar el mensaje de error general
                response = {
                    'recipient': sender,
                    'subject': f"Error en Procesamiento de Preingreso - {timestamp}",
                    'body': _generate_all_failed_message(failed_files, non_pdf_files, subject)
                }
                return response

            # Generar mensaje de éxito con los preingresos creados
            settings = Settings()
            body_message = _generate_success_message(
                preingreso_results,
                failed_files,
                non_pdf_files,
                api_base_url=settings.API_BASE_URL
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