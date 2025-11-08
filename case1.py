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


def _preprocess_ocr_text(text):
    """
    Preprocesa el texto extraído por OCR para mejorar la extracción de datos

    Args:
        text: Texto extraído por OCR

    Returns:
        Texto preprocesado
    """
    if not text:
        return text

    # Normalizar espacios múltiples a uno solo
    text = re.sub(r'\s+', ' ', text)

    # Normalizar saltos de línea múltiples
    text = re.sub(r'\n\s*\n', '\n', text)

    # Corregir errores comunes de OCR
    # (0 → O en contextos de letras, O → 0 en contextos de números)
    # Esto es delicado, por ahora solo normalizamos espacios

    return text


def extract_repair_data(text, logger):
    """Extrae los campos relevantes del texto del PDF"""
    data = {}
    campos_encontrados = []
    campos_faltantes = []

    try:
        # Preprocesar el texto
        text = _preprocess_ocr_text(text)

        logger.info("=" * 60)
        logger.info("INICIANDO EXTRACCIÓN DE DATOS")
        logger.info(f"Longitud del texto: {len(text)} caracteres")
        logger.info("=" * 60)
        # Número de Transacción (más flexible con espacios)
        match = re.search(r'No\.?\s*Transacci[oó]n:?\s*(\S+)', text, re.IGNORECASE)
        if match:
            data['numero_transaccion'] = match.group(1).strip()
            campos_encontrados.append('numero_transaccion')
            logger.info(f"✓ numero_transaccion: {data['numero_transaccion']}")
        else:
            campos_faltantes.append('numero_transaccion')
            logger.warning("✗ numero_transaccion: No encontrado")

        # Número de Boleta (más flexible, crítico)
        match = re.search(r'No\.?\s*Boleta:?\s*(\S+)', text, re.IGNORECASE)
        if match:
            data['numero_boleta'] = match.group(1).strip()
            data['referencia'] = data['numero_boleta'].split('-')[0].zfill(3)
            campos_encontrados.append('numero_boleta')
            logger.info(f"✓ numero_boleta: {data['numero_boleta']}")
            logger.info(f"  referencia: {data['referencia']}")
        else:
            campos_faltantes.append('numero_boleta')
            logger.warning("✗ numero_boleta: No encontrado")

        # Fecha (más flexible)
        match = re.search(r'Fecha:?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text, re.IGNORECASE)
        if match:
            data['fecha'] = match.group(1).strip().replace('/', '/')
            campos_encontrados.append('fecha')
            logger.info(f"✓ fecha: {data['fecha']}")
        else:
            campos_faltantes.append('fecha')
            logger.warning("✗ fecha: No encontrado")

        # Gestionada por (más flexible)
        match = re.search(r'Gestionada\s+por:?\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if match:
            data['gestionada_por'] = match.group(1).strip()
            campos_encontrados.append('gestionada_por')
            logger.info(f"✓ gestionada_por: {data['gestionada_por']}")
        else:
            campos_faltantes.append('gestionada_por')
            logger.warning("✗ gestionada_por: No encontrado")

        # Sucursal (más flexible con código y nombre)
        match = re.search(r'(\d{3}\s+[\w\-\sÁ-ú]+?)(?=\s*Tel[eé]fono|$)', text, re.IGNORECASE)
        if match:
            data['sucursal'] = match.group(1).strip()
            campos_encontrados.append('sucursal')
            logger.info(f"✓ sucursal: {data['sucursal']}")
        else:
            campos_faltantes.append('sucursal')
            logger.warning("✗ sucursal: No encontrado")

        # Teléfono sucursal (múltiples patrones)
        match = re.search(r'Tel[eé]fono[s]?:?\s*(\d+)', text, re.IGNORECASE)
        if match:
            data['telefono_sucursal'] = match.group(1).strip()
            campos_encontrados.append('telefono_sucursal')
            logger.info(f"✓ telefono_sucursal: {data['telefono_sucursal']}")
        else:
            campos_faltantes.append('telefono_sucursal')
            logger.warning("✗ telefono_sucursal: No encontrado")

        # Nombre del Cliente (más flexible con espacios y caracteres)
        match = re.search(r'C\s*L\s*I\s*E\s*N\s*T\s*E:?\s*(.+?)\s+Tel', text, re.IGNORECASE)
        if match:
            data['nombre_cliente'] = match.group(1).strip()
            campos_encontrados.append('nombre_cliente')
            logger.info(f"✓ nombre_cliente: {data['nombre_cliente']}")
        else:
            campos_faltantes.append('nombre_cliente')
            logger.warning("✗ nombre_cliente: No encontrado")

        # Nombre del Contacto (más flexible)
        match = re.search(r'C\s*O\s*N\s*T\s*A\s*C\s*T\s*O:?\s*(.+?)\s+Tel', text, re.IGNORECASE)
        if match:
            data['nombre_contacto'] = match.group(1).strip()
            campos_encontrados.append('nombre_contacto')
            logger.info(f"✓ nombre_contacto: {data['nombre_contacto']}")
        else:
            campos_faltantes.append('nombre_contacto')
            logger.warning("✗ nombre_contacto: No encontrado")

        # Cédula del cliente (más flexible)
        match = re.search(r'CED[UuÚú]?LA?:?\s*([\d\-]+)', text, re.IGNORECASE)
        if not match:
            match = re.search(r'CED\s*([\d\-]+)', text, re.IGNORECASE)
        if match:
            data['cedula_cliente'] = match.group(1).strip()
            campos_encontrados.append('cedula_cliente')
            logger.info(f"✓ cedula_cliente: {data['cedula_cliente']}")
        else:
            campos_faltantes.append('cedula_cliente')
            logger.warning("✗ cedula_cliente: No encontrado")

        # Teléfono del cliente (más flexible)
        match = re.search(r'C\s*L\s*I\s*E\s*N\s*T\s*E:.*?Tel:?\s*(\d+)', text, re.IGNORECASE)
        if match:
            data['telefono_cliente'] = match.group(1).strip()
            campos_encontrados.append('telefono_cliente')
            logger.info(f"✓ telefono_cliente: {data['telefono_cliente']}")
        else:
            campos_faltantes.append('telefono_cliente')
            logger.warning("✗ telefono_cliente: No encontrado")

        # Correo del cliente (más flexible)
        match = re.search(r'Correo:?\s*([\w.\-]+@[\w.\-]+\.\w+)', text, re.IGNORECASE)
        if match:
            data['correo_cliente'] = match.group(1).strip()
            campos_encontrados.append('correo_cliente')
            logger.info(f"✓ correo_cliente: {data['correo_cliente']}")
        else:
            campos_faltantes.append('correo_cliente')
            logger.warning("✗ correo_cliente: No encontrado")

        # Teléfono adicional (más flexible)
        match = re.search(r'N[UuÚú]?MERO\s+ADICIONAL:?\s*(\d+)', text, re.IGNORECASE)
        if match:
            data['telefono_adicional'] = match.group(1).strip()
            campos_encontrados.append('telefono_adicional')
            logger.info(f"✓ telefono_adicional: {data['telefono_adicional']}")
        else:
            campos_faltantes.append('telefono_adicional')

        # Dirección (más flexible)
        match = re.search(r'Direcc[ióon]{1,3}:?\s*(.+?)(?=\n.*?No\.?\s*Factura|\nNo\.?\s*Factura)', text,
                          re.DOTALL | re.IGNORECASE)
        if match:
            direccion = match.group(1).strip()
            direccion = ' '.join(direccion.split())
            data['direccion_cliente'] = direccion
            campos_encontrados.append('direccion_cliente')
            logger.info(f"✓ direccion_cliente: {data['direccion_cliente'][:50]}...")
        else:
            campos_faltantes.append('direccion_cliente')

        # Código del producto (más flexible)
        match = re.search(r'C[óo]digo:?\s*(\d+)', text, re.IGNORECASE)
        if match:
            data['codigo_producto'] = match.group(1).strip()
            campos_encontrados.append('codigo_producto')
            logger.info(f"✓ codigo_producto: {data['codigo_producto']}")
        else:
            campos_faltantes.append('codigo_producto')

        # Descripción del producto (más flexible)
        match = re.search(r'C[óo]digo:?\s*\d+\s+([A-ZÁ-Ú\s]+?)\s+Serie', text, re.IGNORECASE)
        if match:
            data['descripcion_producto'] = match.group(1).strip()
            campos_encontrados.append('descripcion_producto')
            logger.info(f"✓ descripcion_producto: {data['descripcion_producto']}")
        else:
            campos_faltantes.append('descripcion_producto')

        # Serie (más flexible)
        match = re.search(r'Serie:?\s*(\S+)', text, re.IGNORECASE)
        if match:
            data['serie'] = match.group(1).strip()
            campos_encontrados.append('serie')
            logger.info(f"✓ serie: {data['serie']}")
        else:
            campos_faltantes.append('serie')

        # Marca (más flexible)
        match = re.search(r'Marca:?\s*(\S+)', text, re.IGNORECASE)
        if match:
            data['marca'] = match.group(1).strip()
            campos_encontrados.append('marca')
            logger.info(f"✓ marca: {data['marca']}")
        else:
            campos_faltantes.append('marca')
            logger.warning("✗ marca: No encontrado")

        # Modelo (más flexible)
        match = re.search(r'Modelo:?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
        if match:
            data['modelo'] = match.group(1).strip()
            campos_encontrados.append('modelo')
            logger.info(f"✓ modelo: {data['modelo']}")
        else:
            campos_faltantes.append('modelo')
            logger.warning("✗ modelo: No encontrado")

        # Distribuidor (más flexible)
        match = re.search(r'Distrib:?\s*(\d+)\s+(.+?)(?=\n|$)', text, re.IGNORECASE)
        if match:
            data['codigo_distribuidor'] = match.group(1).strip()
            data['distribuidor'] = match.group(2).strip()
            campos_encontrados.append('distribuidor')
            logger.info(f"✓ distribuidor: {data['distribuidor']}")
        else:
            campos_faltantes.append('distribuidor')

        # Número de Factura (más flexible con múltiples patrones)
        match = re.search(r'No\.?\s*Factura:?\s*([^\n]+?)(?=\s*Fecha\s+de\s+Compra|$)', text, re.IGNORECASE)
        if match:
            data['numero_factura'] = match.group(1).strip()
            campos_encontrados.append('numero_factura')
            logger.info(f"✓ numero_factura: {data['numero_factura']}")
        else:
            campos_faltantes.append('numero_factura')

        # Fecha de Compra (más flexible)
        match = re.search(r'Fecha\s+de\s+Compra:?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text, re.IGNORECASE)
        if match:
            data['fecha_compra'] = match.group(1).strip().replace('-', '/')
            campos_encontrados.append('fecha_compra')
            logger.info(f"✓ fecha_compra: {data['fecha_compra']}")
        else:
            campos_faltantes.append('fecha_compra')

        # Fecha de Garantía (más flexible)
        match = re.search(r'Fechas?-->?Garant[íi]a:?\s+(\d{2}[/-]\d{2}[/-]\d{4})', text, re.IGNORECASE)
        if match:
            data['fecha_garantia'] = match.group(1).strip().replace('-', '/')
            campos_encontrados.append('fecha_garantia')
            logger.info(f"✓ fecha_garantia: {data['fecha_garantia']}")
        else:
            campos_faltantes.append('fecha_garantia')

        # Tipo de Garantía (más flexible)
        match = re.search(r'Garant[íi]a:?\s*(.+?)(?=\n|$)', text, re.IGNORECASE)
        if match:
            data['tipo_garantia'] = match.group(1).strip()
            campos_encontrados.append('tipo_garantia')
            logger.info(f"✓ tipo_garantia: {data['tipo_garantia']}")
        else:
            campos_faltantes.append('tipo_garantia')

        # Hecho por (más flexible)
        match = re.search(r'Hecho\s+por:?\s*(.+?)\s+_', text, re.IGNORECASE)
        if match:
            nombre_completo = match.group(1).strip()
            nombre_completo = ' '.join(nombre_completo.split())
            data['hecho_por'] = nombre_completo
            campos_encontrados.append('hecho_por')
            logger.info(f"✓ hecho_por: {data['hecho_por']}")
        else:
            campos_faltantes.append('hecho_por')

        # Daños (más flexible)
        match = re.search(r'D\s*A\s*[ÑN]\s*O\s*S:?\s*(.+?)(?=\n={5,}|\n-{5,}|$)', text, re.DOTALL | re.IGNORECASE)
        if match:
            danos = match.group(1).strip()
            danos = ' '.join(danos.split())
            data['danos'] = danos
            campos_encontrados.append('danos')
            logger.info(f"✓ danos: {data['danos'][:50]}...")
        else:
            campos_faltantes.append('danos')
            logger.warning("✗ danos: No encontrado")

        # Observaciones (más flexible)
        match = re.search(
            r'O\s*B\s*S\s*E\s*R\s*V\s*A\s*C\s*I\s*O\s*N\s*E\s*S:?\s*(.+?)(?=\nN[UuÚú]?MERO ADICIONAL|\nD\s*A\s*[ÑN]\s*O\s*S)',
            text, re.DOTALL | re.IGNORECASE)
        if match:
            obs = match.group(1).strip()
            obs = ' '.join(obs.split())
            data['observaciones'] = obs
            campos_encontrados.append('observaciones')
            logger.info(f"✓ observaciones: {data['observaciones'][:50]}...")
        else:
            campos_faltantes.append('observaciones')

        # Resumen de extracción
        logger.info("=" * 60)
        logger.info(f"RESUMEN DE EXTRACCIÓN:")
        logger.info(f"  ✓ Campos encontrados: {len(campos_encontrados)}")
        logger.info(f"  ✗ Campos faltantes: {len(campos_faltantes)}")

        if campos_faltantes:
            logger.warning(f"  Campos no encontrados: {', '.join(campos_faltantes[:10])}")
            if len(campos_faltantes) > 10:
                logger.warning(f"  ... y {len(campos_faltantes) - 10} más")

        logger.info("=" * 60)

        return data

    except Exception as e:
        logger.exception(f"Error en extracción de datos: {e}")
        logger.info(f"Campos extraídos antes del error: {len(data)}")
        return data


def _extract_text_from_pdf(pdf_data, logger):
    """
    Extrae texto del PDF usando PyMuPDF + PaddleOCR (robusto y multiplataforma)

    Este método funciona en Windows, Linux y macOS sin requerir instalaciones
    del sistema operativo (no necesita Tesseract, Poppler, etc.)

    Estrategia:
    1. Intenta extraer texto nativo del PDF con PyMuPDF (rápido)
    2. Si no hay texto, usa PaddleOCR en las imágenes renderizadas (preciso)
    """
    import io
    import warnings

    # Silenciar warnings
    warnings.filterwarnings('ignore')

    try:
        # Importar dependencias
        try:
            import fitz  # PyMuPDF
            from paddleocr import PaddleOCR
            from PIL import Image
            import numpy as np
        except ImportError as import_err:
            logger.warning(f"Instalando dependencias de OCR (PyMuPDF, PaddleOCR)...")
            logger.warning(f"Error de importación: {import_err}")
            import subprocess
            import sys

            # Instalar paquetes necesarios
            packages = ['pymupdf', 'paddlepaddle', 'paddleocr', 'Pillow', 'numpy']
            for package in packages:
                try:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '--break-system-packages'])
                except:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

            # Importar nuevamente después de la instalación
            import fitz
            from paddleocr import PaddleOCR
            from PIL import Image
            import numpy as np

        logger.info("=" * 60)
        logger.info("🚀 EXTRACCIÓN DE TEXTO DEL PDF")
        logger.info("=" * 60)

        # Abrir PDF con PyMuPDF
        pdf_stream = io.BytesIO(pdf_data)
        pdf_document = fitz.open(stream=pdf_stream, filetype="pdf")
        total_pages = pdf_document.page_count

        logger.info(f"📄 PDF cargado: {total_pages} página(s)")

        # ===== PASO 1: Intentar extraer texto nativo =====
        logger.info("🔍 PASO 1: Intentando extracción de texto nativo...")
        native_text = ""
        pages_with_native_text = 0

        for page_num in range(total_pages):
            page = pdf_document[page_num]
            page_text = page.get_text("text")

            if page_text and len(page_text.strip()) > 50:  # Al menos 50 caracteres
                native_text += page_text + "\n"
                pages_with_native_text += 1

        # Si encontramos suficiente texto nativo, usarlo
        if pages_with_native_text >= total_pages * 0.8:  # Al menos 80% de las páginas
            logger.info(f"✅ ÉXITO con texto nativo")
            logger.info(f"   📊 Páginas con texto: {pages_with_native_text}/{total_pages}")
            logger.info(f"   📝 Total caracteres: {len(native_text):,}")
            logger.info("=" * 60)
            pdf_document.close()
            return native_text

        logger.info(f"⚠️  Texto nativo insuficiente ({pages_with_native_text}/{total_pages} páginas)")
        logger.info("🔄 PASO 2: Usando OCR en imágenes renderizadas...")

        # ===== PASO 2: Usar PaddleOCR en imágenes renderizadas =====
        # Inicializar PaddleOCR (español e inglés)
        logger.info("🤖 Inicializando PaddleOCR (puede tardar en la primera ejecución)...")
        ocr = PaddleOCR(
            use_angle_cls=True,  # Detectar orientación del texto
            lang='es',           # Idioma principal: español
            use_gpu=False,       # No usar GPU (compatibilidad)
            show_log=False       # No mostrar logs internos
        )

        ocr_text = ""
        pages_with_ocr_text = 0

        for page_num in range(total_pages):
            logger.info(f"   📃 Procesando página {page_num + 1}/{total_pages}...")

            try:
                page = pdf_document[page_num]

                # Renderizar página a imagen (alta resolución para mejor OCR)
                zoom = 2.0  # 2x zoom = 144 DPI (mejor calidad OCR)
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                # Convertir a PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))

                # Convertir a numpy array para PaddleOCR
                img_array = np.array(img)

                # Ejecutar OCR
                result = ocr.ocr(img_array, cls=True)

                # Extraer texto de los resultados
                if result and result[0]:
                    page_texts = []
                    for line in result[0]:
                        if line and len(line) >= 2:
                            # line[1] contiene (texto, confianza)
                            text_content = line[1][0] if isinstance(line[1], (list, tuple)) else line[1]
                            page_texts.append(str(text_content))

                    page_text = '\n'.join(page_texts)

                    if page_text and page_text.strip():
                        ocr_text += page_text + "\n\n"
                        pages_with_ocr_text += 1
                        logger.info(f"      ✓ Extraídos {len(page_text)} caracteres")
                    else:
                        logger.warning(f"      ⚠️  No se extrajo texto")
                else:
                    logger.warning(f"      ⚠️  OCR no detectó texto")

            except Exception as page_error:
                logger.warning(f"      ✗ Error en página {page_num + 1}: {page_error}")
                continue

        pdf_document.close()

        # Verificar si se extrajo texto
        if ocr_text.strip():
            logger.info("=" * 60)
            logger.info(f"✅ ÉXITO con PaddleOCR")
            logger.info(f"   📊 Páginas procesadas: {pages_with_ocr_text}/{total_pages}")
            logger.info(f"   📝 Total caracteres: {len(ocr_text):,}")
            logger.info("=" * 60)
            return ocr_text
        else:
            logger.error("✗ No se pudo extraer texto con OCR")
            return None

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"✗ ERROR EN EXTRACCIÓN DE TEXTO")
        logger.error("=" * 60)
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.error("=" * 60)
        logger.error("💡 Solución: Instale las dependencias con:")
        logger.error("   pip install pymupdf paddlepaddle paddleocr --break-system-packages")
        logger.error("=" * 60)
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
    timestamp = datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")

    message_lines = ["¡Estimado Usuario!", "",
                     "Fruno, Centro de Servicio Técnico de Reparación, le informa que se han procesado exitosamente las siguientes solicitudes de reparación:",
                     ""]

    # Mostrar preingresos creados exitosamente
    if preingreso_results:
        for idx, result in enumerate(preingreso_results, 1):
            message_lines.append(f"{idx}. Archivo: {result['filename']}")
            message_lines.append(f"   ✓ Boleta Gollo: {result['boleta']}")
            if result.get('numero_transaccion'):
                message_lines.append(f"   ✓ No. Transacción Gollo: {result['numero_transaccion']}")
            if result.get('preingreso_id'):
                message_lines.append(f"   ✓ Boleta Fruno: {result['preingreso_id']}")
            if result.get('consultar_guia'):
                message_lines.append(f"   ✓ Guía Fruno: {result['consultar_guia']}")
            if result.get('consultar_reparacion'):
                message_lines.append(
                    f"   🔗 Para consultar el estado de la unidad haga clic en: {result['consultar_reparacion']}")

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

        # Guardar texto extraído para debugging
        try:
            debug_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            debug_file.write(f"=== TEXTO EXTRAÍDO DE: {pdf_filename} ===\n\n")
            debug_file.write(pdf_text)
            debug_file.close()
            logger.info(f"📝 Texto extraído guardado en: {debug_file.name}")
        except Exception as e:
            logger.warning(f"No se pudo guardar el texto para debugging: {e}")

        # Extraer datos del PDF
        logger.info(f"Extrayendo datos del PDF: {pdf_filename}")
        extracted_data = extract_repair_data(pdf_text, logger)

        # Validación mejorada: solo verificar que haya datos mínimos
        if not extracted_data:
            return {
                'success': False,
                'error': 'No se pudieron extraer datos del PDF (diccionario vacío)',
                'filename': pdf_filename
            }

        # Verificar que al menos se haya extraído el número de boleta
        if not extracted_data.get('numero_boleta'):
            logger.error(f"❌ No se encontró el número de boleta (campo crítico)")
            logger.error(f"   Campos extraídos: {list(extracted_data.keys())}")
            return {
                'success': False,
                'error': f'No se encontró el número de boleta. Campos extraídos: {len(extracted_data)}',
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