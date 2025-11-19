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
        # Buscar primero CONTACTO, luego CLIENTE como alternativa
        match = re.search(r'C\s*O\s*N\s*T\s*A\s*C\s*T\s*O\s*:?\s+([A-Z\s]+?)(?=\s+Tel|CED)', text, re.IGNORECASE)
        if not match:
            # Si no se encontró CONTACTO, buscar CLIENTE
            match = re.search(r'C\s*L\s*I\s*E\s*N\s*T\s*E\s*:?\s+([A-Z\s]+?)(?=\s+Tel|CED)', text, re.IGNORECASE)

        if match:
            # Limpiar espacios múltiples del nombre encontrado
            nombre_limpio = re.sub(r'\s+', ' ', match.group(1).strip())
            data['nombre_contacto'] = nombre_limpio
            data['nombre_cliente'] = nombre_limpio
            logger.info(f"Cliente/Contacto: {nombre_limpio}")

        # Cédula (más flexible)
        match = re.search(r'CED\s*:?\s*([\d\-]+)', text, re.IGNORECASE)
        if match:
            data['cedula_cliente'] = match.group(1).strip()

        # Teléfono cliente (más flexible)
        match = re.search(r'Tel\s*:?\s*(\d{8,})', text, re.IGNORECASE)
        if match:
            data['telefono_cliente'] = match.group(1).strip()

        # ============================================================================
        # EXTRACCIÓN DE CORREO ELECTRÓNICO - VERSIÓN ULTRA ROBUSTA
        # ============================================================================
        # Estrategia multi-nivel:
        # 1. Regex estándar (para correos bien formados)
        # 2. Búsqueda de "@" + reconstrucción de tokens adyacentes (para OCR fragmentado)
        # 3. Búsqueda sin puntos en extensión
        # 4. Búsqueda con espacios internos
        # ============================================================================

        correo_encontrado = None
        logger.info("🔍 Iniciando búsqueda ULTRA ROBUSTA de correo electrónico...")

        # ============================================================================
        # NIVEL 1: Regex estándar (método rápido para correos bien formados)
        # ============================================================================
        logger.info("📍 NIVEL 1: Búsqueda con regex estándar...")
        patron_email = r'([a-zA-Z0-9][a-zA-Z0-9\.\-_]{0,63})\s*@\s*([a-zA-Z0-9][a-zA-Z0-9\.\-]{0,253})\s*\.\s*([a-zA-Z]{2,6})'
        matches = re.findall(patron_email, text, re.IGNORECASE)

        if matches:
            logger.info(f"✓ Encontrados {len(matches)} posibles correos en el documento")

            # Lista de dominios comunes (para priorización)
            dominios_comunes = [
                'gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com',
                'hotmail.es', 'outlook.es', 'yahoo.es',
                'live.com', 'icloud.com', 'aol.com',
                'gollo.com', 'fruno.com'
            ]

            # Procesar cada coincidencia encontrada
            correos_candidatos = []
            for match in matches:
                # Reconstruir el correo (match es una tupla: (local, dominio, extensión))
                local_part = match[0].strip()
                domain_part = match[1].strip()
                extension_part = match[2].strip()

                # Eliminar todos los espacios internos
                correo_temp = f"{local_part}@{domain_part}.{extension_part}"
                correo_temp = re.sub(r'\s+', '', correo_temp)
                correo_temp = correo_temp.lower()

                # Validaciones básicas
                if len(correo_temp) < 6:  # Muy corto
                    continue
                if correo_temp.count('@') != 1:  # Debe tener exactamente 1 @
                    continue
                if '..' in correo_temp:  # No debe tener puntos consecutivos
                    continue
                if correo_temp.startswith('.') or correo_temp.endswith('.'):  # No debe empezar/terminar con punto
                    continue

                # Validar parte local (antes del @)
                local = correo_temp.split('@')[0]
                if not local or local.startswith('.') or local.endswith('.'):
                    continue

                # Validar dominio (después del @)
                domain_full = correo_temp.split('@')[1]
                if '.' not in domain_full:
                    continue

                # Corrección de typos comunes en dominios
                correo_corregido = correo_temp
                typos_dominios = {
                    '@gmal.': '@gmail.',
                    '@g mail.': '@gmail.',
                    '@gmial.': '@gmail.',
                    '@hotmial.': '@hotmail.',
                    '@hotmil.': '@hotmail.',
                    '@outloo.': '@outlook.',
                    '@outlok.': '@outlook.',
                    '@yaho.': '@yahoo.',
                    '@yahooo.': '@yahoo.'
                }

                for typo, correcto in typos_dominios.items():
                    if typo in correo_corregido:
                        correo_corregido = correo_corregido.replace(typo, correcto)
                        logger.info(f"   ✓ Typo corregido: {correo_temp} → {correo_corregido}")

                # Verificar si es un dominio común (mayor prioridad)
                es_dominio_comun = any(correo_corregido.endswith('@' + dominio) or
                                       correo_corregido.endswith(dominio)
                                       for dominio in dominios_comunes)

                correos_candidatos.append({
                    'correo': correo_corregido,
                    'es_dominio_comun': es_dominio_comun,
                    'original': correo_temp
                })

                logger.info(f"   • Candidato: {correo_corregido} {'(dominio común)' if es_dominio_comun else ''}")

            if correos_candidatos:
                # Ordenar: primero los de dominios comunes, luego los demás
                correos_candidatos.sort(key=lambda x: (not x['es_dominio_comun'], x['correo']))

                # Seleccionar el primer candidato válido
                correo_encontrado = correos_candidatos[0]['correo']

                if correos_candidatos[0]['es_dominio_comun']:
                    logger.info(f"✅ Correo seleccionado (dominio común): {correo_encontrado}")
                else:
                    logger.info(f"✅ Correo seleccionado: {correo_encontrado}")

                # Si se encontraron múltiples, informar
                if len(correos_candidatos) > 1:
                    logger.info(
                        f"ℹ️ Se encontraron {len(correos_candidatos)} correos válidos, se seleccionó el primero")

        # ============================================================================
        # NIVEL 2: Reconstrucción de tokens fragmentados (para OCR que separa el correo)
        # ============================================================================
        # Si el NIVEL 1 no encontró nada, buscar "@" aislados y reconstruir tokens
        if not correo_encontrado:
            logger.info("📍 NIVEL 2: Reconstruyendo correos de tokens fragmentados...")
            logger.info("   Buscando símbolos '@' en el documento...")

            # Buscar TODAS las posiciones del símbolo "@" en el texto
            arroba_positions = [m.start() for m in re.finditer(r'@', text)]

            if arroba_positions:
                logger.info(f"   ✓ Encontrados {len(arroba_positions)} símbolos '@' en el documento")

                for arroba_pos in arroba_positions:
                    # Definir ventana de búsqueda alrededor del "@"
                    WINDOW_SIZE_BEFORE = 80  # caracteres antes del @
                    WINDOW_SIZE_AFTER = 80  # caracteres después del @

                    # Extraer ventana de texto alrededor del "@"
                    start = max(0, arroba_pos - WINDOW_SIZE_BEFORE)
                    end = min(len(text), arroba_pos + WINDOW_SIZE_AFTER)
                    window_text = text[start:end]

                    logger.info(f"   🔍 Analizando ventana alrededor de '@' en posición {arroba_pos}")
                    logger.info(f"      Ventana: ...{window_text[:30]}...@...{window_text[-30:]}...")

                    # Buscar parte local (antes del @) en la ventana
                    # Buscar hacia atrás desde el "@" hasta encontrar un espacio o inicio
                    local_pattern = r'([a-zA-Z0-9][a-zA-Z0-9\.\-_]*)\s*$'
                    text_before_arroba = text[start:arroba_pos]
                    match_local = re.search(local_pattern, text_before_arroba)

                    if not match_local:
                        # Si no se encontró con patrón estricto, intentar con más flexibilidad
                        # Capturar CUALQUIER secuencia alfanumérica antes del @
                        local_pattern_flexible = r'([a-zA-Z0-9]+(?:[\.\-_][a-zA-Z0-9]+)*)\s*$'
                        match_local = re.search(local_pattern_flexible, text_before_arroba)

                    if match_local:
                        local_part = match_local.group(1).strip()
                        logger.info(f"      ✓ Parte local encontrada: {local_part}")
                    else:
                        logger.info(f"      ✗ No se encontró parte local válida")
                        continue

                    # Buscar dominio + extensión (después del @) en la ventana
                    # Buscar hacia adelante desde el "@" hasta encontrar un espacio o final
                    text_after_arroba = text[arroba_pos + 1:end]

                    # Intentar primero con punto en la extensión
                    domain_pattern = r'^\s*([a-zA-Z0-9][a-zA-Z0-9\.\-]*)\s*\.\s*([a-zA-Z]{2,6})'
                    match_domain = re.search(domain_pattern, text_after_arroba)

                    if match_domain:
                        domain_part = match_domain.group(1).strip()
                        extension_part = match_domain.group(2).strip()
                        logger.info(f"      ✓ Dominio encontrado: {domain_part}.{extension_part}")

                        # Reconstruir el correo
                        correo_temp = f"{local_part}@{domain_part}.{extension_part}"
                        correo_temp = re.sub(r'\s+', '', correo_temp).lower()

                        logger.info(f"      ✓ Correo reconstruido: {correo_temp}")

                        # Validar el correo reconstruido
                        if '@' in correo_temp and '.' in correo_temp.split('@')[1]:
                            if 6 <= len(correo_temp) <= 254:
                                # Validaciones adicionales
                                if correo_temp.count('@') == 1 and not '..' in correo_temp:
                                    correo_encontrado = correo_temp
                                    logger.info(
                                        f"✅ NIVEL 2 exitoso: Correo reconstruido de tokens fragmentados: {correo_encontrado}")
                                    break
                    else:
                        # Intentar buscar dominio SIN punto (ej: "gmailcom")
                        logger.info(f"      🔍 No se encontró dominio con punto, buscando sin punto...")

                        # Buscar dominio+extensión juntos (sin punto)
                        # Lista de extensiones comunes
                        extensiones_comunes = ['com', 'net', 'org', 'es', 'mx', 'co', 'ar', 'cl', 'pe', 'ec']
                        dominios_base = ['gmail', 'hotmail', 'outlook', 'yahoo', 'live', 'icloud', 'aol', 'gollo',
                                         'fruno']

                        # Intentar detectar dominio+extensión sin punto
                        domain_pattern_no_dot = r'^\s*([a-zA-Z0-9][a-zA-Z0-9\-]{1,50})'
                        match_domain_no_dot = re.search(domain_pattern_no_dot, text_after_arroba)

                        if match_domain_no_dot:
                            dominio_ext_junto = match_domain_no_dot.group(1).strip().lower()
                            logger.info(f"      ✓ Cadena después de '@': {dominio_ext_junto}")

                            # Intentar separar el dominio de la extensión
                            for ext in extensiones_comunes:
                                if dominio_ext_junto.endswith(ext):
                                    # Separar dominio de extensión
                                    dominio_parte = dominio_ext_junto[:-len(ext)]
                                    if len(dominio_parte) >= 2:  # El dominio debe tener al menos 2 caracteres
                                        # Reconstruir con punto
                                        correo_temp = f"{local_part}@{dominio_parte}.{ext}"
                                        correo_temp = re.sub(r'\s+', '', correo_temp).lower()

                                        logger.info(f"      ✓ Correo reconstruido (sin punto original): {correo_temp}")

                                        # Validar
                                        if '@' in correo_temp and '.' in correo_temp.split('@')[1]:
                                            if 6 <= len(correo_temp) <= 254:
                                                if correo_temp.count('@') == 1 and not '..' in correo_temp:
                                                    correo_encontrado = correo_temp
                                                    logger.info(
                                                        f"✅ NIVEL 2 exitoso: Correo reconstruido sin punto: {correo_encontrado}")
                                                    break

                            if correo_encontrado:
                                break
                        else:
                            logger.info(f"      ✗ No se encontró dominio válido después de '@'")
            else:
                logger.info("   ✗ No se encontró ningún símbolo '@' en el documento")

        # ============================================================================
        # NIVEL 3: Búsqueda de patrones sin punto antes de la extensión
        # ============================================================================
        # Si no se encontró correo, buscar patrones SIN punto antes de la extensión
        # Ejemplo: "maxjoca_200S@hotmailcom" → "maxjoca_200S@hotmail.com"
        if not correo_encontrado:
            logger.info("📍 NIVEL 3: Buscando patrones sin punto en extensión...")

            # Lista de extensiones comunes a buscar
            extensiones_comunes = [
                'com', 'net', 'org', 'es', 'mx', 'co', 'ar', 'cl', 'pe', 'ec',
                'edu', 'gov', 'mil', 'info', 'biz', 'io', 'us', 'uk', 'ca'
            ]

            # Construir lista de dominios + extensiones comunes (sin punto)
            # Ejemplo: "hotmailcom", "gmailcom", "outlookcom"
            dominios_base = ['gmail', 'hotmail', 'outlook', 'yahoo', 'live', 'icloud', 'aol', 'gollo', 'fruno']
            patrones_sin_punto = []
            for dominio in dominios_base:
                for ext in extensiones_comunes:
                    patrones_sin_punto.append(f"{dominio}{ext}")

            # Patrón para buscar: parte_local @ dominio_sin_punto
            # Ejemplo: algo@hotmailcom
            for patron_dominio_ext in patrones_sin_punto:
                # Crear patrón regex que busque este dominio+extensión sin punto
                # Patrón: ([correo_local])@(hotmailcom)
                patron_busqueda = rf'([a-zA-Z0-9][a-zA-Z0-9\.\-_]{{0,63}})\s*@\s*({re.escape(patron_dominio_ext)})'

                match = re.search(patron_busqueda, text, re.IGNORECASE)
                if match:
                    local_part = match.group(1).strip()
                    dominio_ext_sin_punto = match.group(2).strip().lower()

                    logger.info(f"   ✓ Patrón sin punto encontrado: {local_part}@{dominio_ext_sin_punto}")

                    # Buscar dónde insertar el punto
                    # Intentar encontrar la extensión dentro del dominio
                    dominio_corregido = None
                    for ext in extensiones_comunes:
                        if dominio_ext_sin_punto.endswith(ext):
                            # Encontramos la extensión, insertar el punto
                            # Ejemplo: "hotmailcom" → "hotmail" + "." + "com"
                            dominio_parte = dominio_ext_sin_punto[:-len(ext)]
                            dominio_corregido = f"{dominio_parte}.{ext}"
                            break

                    if dominio_corregido:
                        # Reconstruir el correo con el punto
                        correo_temp = f"{local_part}@{dominio_corregido}"
                        correo_temp = re.sub(r'\s+', '', correo_temp).lower()

                        logger.info(f"   ✓ Correo corregido (punto agregado): {correo_temp}")

                        # Validaciones básicas
                        if len(correo_temp) >= 6 and correo_temp.count('@') == 1:
                            correo_encontrado = correo_temp
                            logger.info(f"✅ Correo extraído con corrección de punto: {correo_encontrado}")
                            break

            # Si aún no se encontró, intentar búsqueda genérica de @ seguido de texto sin punto
            if not correo_encontrado:
                logger.info("🔍 Buscando cualquier patrón sin punto con extensiones comunes...")

                # Patrón más general: algo@algoext donde ext es una extensión común
                # Construir patrón que busque @ seguido de letras/números y luego una extensión conocida
                extensiones_pattern = '|'.join(extensiones_comunes)
                patron_generico = rf'([a-zA-Z0-9][a-zA-Z0-9\.\-_]{{2,63}})\s*@\s*([a-zA-Z0-9][a-zA-Z0-9\-]{{2,63}})({extensiones_pattern})'

                match = re.search(patron_generico, text, re.IGNORECASE)
                if match:
                    local_part = match.group(1).strip()
                    dominio_parte = match.group(2).strip()
                    extension = match.group(3).strip()

                    # Reconstruir con el punto
                    correo_temp = f"{local_part}@{dominio_parte}.{extension}"
                    correo_temp = re.sub(r'\s+', '', correo_temp).lower()

                    logger.info(f"   ✓ Patrón genérico sin punto encontrado: {correo_temp}")

                    # Validaciones básicas
                    if len(correo_temp) >= 6 and correo_temp.count('@') == 1:
                        correo_encontrado = correo_temp
                        logger.info(f"✅ Correo extraído con patrón genérico: {correo_encontrado}")

        # ============================================================================
        # NIVEL 4: Búsqueda con espacios internos (para OCR muy deteriorado)
        # ============================================================================
        # Si no se encontró correo con patrones anteriores, intentar con espacios
        if not correo_encontrado:
            logger.info("📍 NIVEL 4: Búsqueda con espacios internos (OCR deteriorado)...")
            # Patrón que permite más espacios (para OCR muy deteriorado)
            patron_espacios = r'([a-zA-Z0-9][a-zA-Z0-9\.\-_\s]{2,63})\s*@\s*([a-zA-Z0-9][a-zA-Z0-9\.\-\s]{2,253})\s*\.\s*([a-zA-Z]{2,6})'
            match = re.search(patron_espacios, text, re.IGNORECASE)

            if match:
                # Limpiar espacios y reconstruir
                correo_encontrado = f"{match.group(1)}@{match.group(2)}.{match.group(3)}"
                correo_encontrado = re.sub(r'\s+', '', correo_encontrado).lower()
                logger.info(f"✓ Correo encontrado con espacios internos: {correo_encontrado}")
            else:
                # ============================================================================
                # NIVEL 5: Patrón extremo (letras individuales separadas por espacios)
                # ============================================================================
                logger.info("📍 NIVEL 5: Patrón extremo (letras muy separadas)...")
                # Buscar patrones como: m a r i a @ g m a i l . c o m
                patron_extremo = r'([a-z]\s+){3,}@\s+([a-z]\s+){3,}\.\s*[a-z]{2,6}'
                match_extremo = re.search(patron_extremo, text, re.IGNORECASE)

                if match_extremo:
                    correo_encontrado = match_extremo.group(0)
                    correo_encontrado = re.sub(r'\s+', '', correo_encontrado).lower()
                    logger.info(f"✅ NIVEL 5 exitoso: {correo_encontrado}")

        # Validación final y asignación
        if correo_encontrado:
            # Validación final del formato
            if '@' in correo_encontrado and '.' in correo_encontrado.split('@')[1]:
                # Validar longitud razonable
                if 6 <= len(correo_encontrado) <= 254:
                    data['correo_cliente'] = correo_encontrado
                    # NUEVO: Guardar el texto original extraído del OCR para diagnóstico
                    data['correo_ocr_raw'] = correo_encontrado
                    logger.info(f"✅ Correo extraído y validado exitosamente: {correo_encontrado}")
                else:
                    logger.warning(
                        f"⚠️ Correo con longitud inválida ({len(correo_encontrado)} caracteres): {correo_encontrado}")
                    data['correo_cliente'] = "correo_no_encontrado@gollo.com"
                    data['correo_ocr_raw'] = f"INVALIDO (longitud {len(correo_encontrado)}): {correo_encontrado}"
            else:
                logger.warning(f"⚠️ Correo con formato inválido: {correo_encontrado}")
                data['correo_cliente'] = "correo_no_encontrado@gollo.com"
                data['correo_ocr_raw'] = f"INVALIDO (formato): {correo_encontrado}"
        else:
            logger.warning("⚠️ No se pudo extraer el correo del cliente - usando correo por defecto")
            data['correo_cliente'] = "correo_no_encontrado@gollo.com"
            data['correo_ocr_raw'] = "NO_ENCONTRADO_EN_PDF"

        logger.info("=" * 80)

        # Dirección (más flexible)
        match = re.search(r'Direcc\s*:?\s*(.+?)(?=\s*No\.\s*Factura|\s*Factura)', text, re.IGNORECASE)
        if match:
            direccion = re.sub(r'\s+', ' ', match.group(1).strip())
            data['direccion_cliente'] = direccion

        # ============================================================================
        # EXTRACCIÓN DE CÓDIGO PRODUCTO Y DESCRIPCIÓN - VERSIÓN ULTRA ROBUSTA
        # ============================================================================
        # Estrategia multi-nivel:
        # 1. Patrón optimizado (código ~10 dígitos + descripción en misma línea)
        # 2. Búsqueda con espacios fragmentados por OCR
        # 3. Búsqueda basada en posición relativa a "Marca:"
        # ============================================================================

        codigo_encontrado = None
        descripcion_encontrada = None

        # NIVEL 1: Búsqueda estándar optimizada
        # Busca código de 8-12 dígitos (centrado en 10) seguido de descripción
        # La descripción puede contener letras mayúsculas, espacios, y algunas minúsculas
        match = re.search(
            r'C[óo]digo\s*:?\s*(\d{8,12})\s+([A-Z][A-Z0-9\s]+?)(?=\s+(?:Serie|Marca|Modelo))',
            text,
            re.IGNORECASE
        )
        if match:
            codigo_encontrado = match.group(1).strip()
            descripcion_encontrada = re.sub(r'\s+', ' ', match.group(2).strip())
            logger.info(f"✓ [NIVEL 1] Código y descripción encontrados: {codigo_encontrado} - {descripcion_encontrada}")

        # NIVEL 2: Si no se encontró, buscar código solo y luego descripción por separado
        if not codigo_encontrado:
            # Primero buscar el código (permitir 6-14 dígitos para ser más flexible)
            match_codigo = re.search(r'C[óo]digo\s*:?\s*(\d{6,14})', text, re.IGNORECASE)
            if match_codigo:
                codigo_encontrado = match_codigo.group(1).strip()
                logger.info(f"✓ [NIVEL 2] Código encontrado: {codigo_encontrado}")

                # Buscar descripción después del código
                # Intentar capturar texto alfanumérico después del código hasta Serie/Marca/Modelo
                pos_codigo = match_codigo.end()
                texto_despues = text[pos_codigo:pos_codigo + 200]  # Buscar en siguientes 200 caracteres

                match_desc = re.search(
                    r'^\s*([A-Z][A-Z0-9\s]+?)(?=\s+(?:Serie|Marca|Modelo))',
                    texto_despues,
                    re.IGNORECASE
                )
                if match_desc:
                    descripcion_encontrada = re.sub(r'\s+', ' ', match_desc.group(1).strip())
                    logger.info(f"✓ [NIVEL 2] Descripción encontrada: {descripcion_encontrada}")

        # NIVEL 3: Búsqueda basada en posición relativa a "Marca:"
        # El código siempre está ARRIBA de "Marca:", así que buscar en el texto previo
        if not codigo_encontrado:
            match_marca = re.search(r'Marca\s*:?\s*\w+', text, re.IGNORECASE)
            if match_marca:
                # Obtener texto antes de "Marca:"
                texto_antes_marca = text[:match_marca.start()]

                # Buscar patrón de código en las últimas 300 caracteres antes de "Marca:"
                texto_busqueda = texto_antes_marca[-300:] if len(texto_antes_marca) > 300 else texto_antes_marca

                # Buscar código con descripción
                match = re.search(
                    r'C[óo]digo\s*:?\s*(\d{6,14})\s+([A-Z][A-Z0-9\s]+?)$',
                    texto_busqueda,
                    re.IGNORECASE
                )
                if match:
                    codigo_encontrado = match.group(1).strip()
                    descripcion_encontrada = re.sub(r'\s+', ' ', match.group(2).strip())
                    logger.info(
                        f"✓ [NIVEL 3] Código y descripción encontrados antes de Marca: {codigo_encontrado} - {descripcion_encontrada}")
                else:
                    # Solo buscar código
                    match_codigo = re.search(r'C[óo]digo\s*:?\s*(\d{6,14})', texto_busqueda, re.IGNORECASE)
                    if match_codigo:
                        codigo_encontrado = match_codigo.group(1).strip()
                        logger.info(f"✓ [NIVEL 3] Código encontrado antes de Marca: {codigo_encontrado}")

        # NIVEL 4: Búsqueda ultra-flexible con espacios fragmentados (OCR deteriorado)
        # Busca "C ó d i g o" o "C o d i g o" con espacios
        if not codigo_encontrado:
            match = re.search(
                r'C\s*[óo]?\s*d\s*i\s*g\s*o\s*:?\s*(\d[\s\d]{10,30})',
                text,
                re.IGNORECASE
            )
            if match:
                # Eliminar espacios del código extraído
                codigo_encontrado = re.sub(r'\s+', '', match.group(1))
                # Filtrar para obtener solo números de 6-14 dígitos
                if 6 <= len(codigo_encontrado) <= 14:
                    logger.info(f"✓ [NIVEL 4] Código encontrado (OCR fragmentado): {codigo_encontrado}")
                else:
                    codigo_encontrado = None

        # Asignar valores encontrados
        if codigo_encontrado:
            data['codigo_producto'] = codigo_encontrado
            logger.info(f"Código producto final: {codigo_encontrado}")

        if descripcion_encontrada:
            data['descripcion_producto'] = descripcion_encontrada
            logger.info(f"Descripción producto final: {descripcion_encontrada}")

        # Si no se encontró descripción, intentar buscarla de forma independiente
        # entre el código y Marca/Serie
        if not descripcion_encontrada and codigo_encontrado:
            match = re.search(
                rf'{re.escape(codigo_encontrado)}\s+([A-Z][A-Z0-9\s]+?)(?=\s+(?:Serie|Marca|Modelo))',
                text,
                re.IGNORECASE
            )
            if match:
                descripcion_encontrada = re.sub(r'\s+', ' ', match.group(1).strip())
                data['descripcion_producto'] = descripcion_encontrada
                logger.info(f"Descripción producto (búsqueda post-código): {descripcion_encontrada}")

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
        # Actualizado para detenerse también antes de "Fecha de Compra:"
        match = re.search(r'No\s*\.?\s*Factura\s*:?\s*([^\s]+(?:\s+[^\s]+){0,5}?)(?=\s+Correo|\s+Fecha\s+de\s+Compra)',
                          text,
                          re.IGNORECASE)
        if match:
            data['numero_factura'] = re.sub(r'\s+', ' ', match.group(1).strip())

        # Fecha de compra (específico - debe tener el campo explícito "Fecha de Compra:")
        # Solo extrae si el campo "Fecha de Compra:" está presente en el PDF
        match = re.search(r'Fecha\s+de\s+Compra\s*:?\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
        if match:
            data['fecha_compra'] = match.group(1).strip()
            logger.info(f"✓ Fecha de compra encontrada: {data['fecha_compra']}")
        else:
            # Si no hay campo "Fecha de Compra:" explícito, no extraer ninguna fecha
            logger.info("ℹ️ No se encontró campo 'Fecha de Compra:' en el PDF - no se extraerá fecha")

        # Fecha de garantía (más flexible)
        match = re.search(r'Garant[ií]a\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
        if match:
            data['fecha_garantia'] = match.group(1).strip()

        # Tipo de garantía (más flexible)
        match = re.search(r'Garant[ií]a\s*:?\s*([A-Z][^\s]*(?:\.[A-Z][^\s]*)*)', text, re.IGNORECASE)
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


def _extract_text_from_pdf(pdf_data, logger):
    """Extrae texto del PDF usando OCR con EasyOCR"""
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

        logger.info("🤖 Iniciando extracción de texto con OCR (EasyOCR)...")

        # Detectar si hay GPU disponible e inicializar EasyOCR
        try:
            import torch
            gpu_available = torch.cuda.is_available()
            if gpu_available:
                logger.info("🎮 GPU detectado - Inicializando EasyOCR con aceleración GPU...")
                reader = easyocr.Reader(['es', 'en'], gpu=True)
                logger.info("✅ EasyOCR configurado con GPU (procesamiento acelerado)")
            else:
                logger.info("💻 GPU no disponible - Inicializando EasyOCR con CPU")
                reader = easyocr.Reader(['es', 'en'], gpu=False)
                logger.info("✅ EasyOCR configurado con CPU")
        except ImportError:
            logger.warning("⚠️ PyTorch no instalado - usando CPU para OCR")
            reader = easyocr.Reader(['es', 'en'], gpu=False)
        except Exception as e:
            logger.warning(f"⚠️ Error al detectar GPU: {e} - fallback a CPU")
            reader = easyocr.Reader(['es', 'en'], gpu=False)

        # Abrir PDF con PyMuPDF
        logger.info("📄 Abriendo PDF con PyMuPDF...")
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        total_pages = len(pdf_document)
        logger.info(f"📄 Documento tiene {total_pages} página(s) para procesar con OCR")

        text = ""
        for page_num in range(total_pages):
            logger.info(f"🔍 Procesando página {page_num + 1}/{total_pages} con OCR...")

            # Renderizar página como imagen
            logger.info(f"   📸 Convirtiendo página {page_num + 1} a imagen (300 DPI)...")
            page = pdf_document[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))  # 300 DPI

            # Convertir a numpy array para EasyOCR
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            logger.info(f"   🤖 Ejecutando OCR en página {page_num + 1} (imagen {pix.width}x{pix.height}px)...")

            # Extraer texto con EasyOCR
            try:
                results = reader.readtext(img_array, detail=0, paragraph=True)

                # Combinar los resultados en texto
                if results:
                    page_text = '\n'.join(results)
                    if page_text:
                        text += page_text + "\n"
                        logger.info(f"   ✅ Página {page_num + 1} procesada: {len(page_text)} caracteres extraídos")
                else:
                    logger.warning(f"   ⚠️ Página {page_num + 1}: No se encontró texto")

            except Exception as ocr_error:
                logger.warning(f"   ❌ Error en OCR de página {page_num + 1}: {ocr_error}")

        pdf_document.close()

        if not text.strip():
            logger.warning("⚠️ EasyOCR no extrajo ningún texto - intentando método alternativo (PyMuPDF directo)")
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
                    logger.info(f"✅ Texto extraído usando método alternativo PyMuPDF ({len(text)} caracteres)")
            except Exception as fallback_error:
                logger.error(f"❌ Error en método alternativo: {fallback_error}")
        else:
            logger.info(f"✅ OCR completado exitosamente - Total extraído: {len(text)} caracteres")

        return text if text.strip() else None

    except Exception as e:
        logger.exception(f"Error al extraer texto con OCR: {e}")
        return None


def _generate_success_message(preingreso_results, failed_files, non_pdf_files, api_base_url=None):
    """
    Genera el mensaje de éxito con el preingreso creado

    Args:
        preingreso_results: Lista con 1 elemento dict con {filename, boleta, preingreso_id, numero_transaccion, garantia_viene_de_correo}
        failed_files: Lista de dicts con {filename, error} (vacía si fue exitoso)
        non_pdf_files: Lista de nombres de archivos que no son PDF
        api_base_url: URL base de la API para generar links de consulta
    """
    message_lines = [
        "Estimado/a Usuario,",
        "",
        "Fruno, Centro de Servicio Técnico de Reparación, le informa que su solicitud de reparación ha sido procesada exitosamente en nuestro sistema.",
        ""
    ]

    # Mostrar preingreso creado exitosamente (solo 1)
    if preingreso_results and len(preingreso_results) > 0:
        result = preingreso_results[0]

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
        if result.get('tipo_preingreso_nombre'):
            message_lines.append(f"   Tipo de preingreso: {result['tipo_preingreso_nombre']}")
        if result.get('garantia_nombre'):
            # Si la garantía viene del correo, mostrar "recibida"
            if result.get('garantia_viene_de_correo'):
                message_lines.append(f"   Garantía de preingreso recibida: {result['garantia_nombre']}")
            else:
                message_lines.append(f"   Garantía de preingreso: {result['garantia_nombre']}")

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

    # Mostrar archivos que no son PDF (si hay)
    if non_pdf_files:
        message_lines.append("")
        message_lines.append("ℹ️ Archivos recibidos que no son PDF (no procesados):")
        message_lines.append("")
        for file in non_pdf_files:
            message_lines.append(f"   • {file}")
        message_lines.append("")

    # Agregar sección de recordatorio de funcionamiento
    message_lines.append("")
    message_lines.append("⭐ Recordatorio de Funcionamiento:")
    message_lines.append("")
    message_lines.append("   Si necesita especificar información adicional en futuros correos, puede utilizar las siguientes palabras clave:")
    message_lines.append("")
    message_lines.append("   • Para indicar el tipo de garantía:")
    message_lines.append("     Escriba en el cuerpo del correo: garantia: [tipo]")
    message_lines.append("     Ejemplo: garantia: normal")
    message_lines.append("")
    message_lines.append("   • Para indicar un proveedor específico:")
    message_lines.append("     Escriba en el cuerpo del correo: proveedor: [nombre]")
    message_lines.append("     Ejemplo: proveedor: Fruno")
    message_lines.append("")

    # Cierre del mensaje
    message_lines.append("")
    message_lines.append("El preingreso se ha creado correctamente en nuestro sistema.")
    message_lines.append("")
    message_lines.append("Gracias por confiar en Fruno Centro de Servicio Técnico.")
    message_lines.append("")
    message_lines.append(
        "Si tiene alguna duda o necesita asistencia adicional, nuestro equipo de soporte y técnicos especializados están disponibles para ayudarle.")

    return "\n".join(message_lines)


def _generate_all_failed_message(failed_files, non_pdf_files, subject):
    """
    Genera el mensaje cuando el PDF falla al procesarse

    Args:
        failed_files: Lista con 1 elemento dict con {filename, error}
        non_pdf_files: Lista de nombres de archivos que no son PDF
        subject: Asunto del correo recibido
    """
    timestamp = datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")

    message_lines = ["Estimado Usuario,", "",
                     f"Se ha recibido su correo bajo el asunto \"{subject}\", sin embargo no se pudo procesar el archivo PDF adjunto.",
                     ""]

    if failed_files:
        message_lines.append("Archivo PDF que no se pudo procesar:")
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
    message_lines.append("  • El archivo PDF no esté dañado o corrupto")
    message_lines.append("  • El archivo sea una boleta de reparación válida")
    message_lines.append("  • El archivo contenga información legible")
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


def _generate_multiple_pdfs_message(pdf_files):
    """Genera el mensaje cuando se envían múltiples PDFs"""
    timestamp = datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")

    message_lines = ["Estimado Usuario,", "",
                     f"Se ha recibido su correo con {len(pdf_files)} archivos PDF adjuntos.", ""]

    message_lines.append("Archivos PDF recibidos:")
    for file in pdf_files:
        message_lines.append(f"  • {file}")
    message_lines.append("")

    message_lines.append("⚠️ IMPORTANTE: Actualmente el sistema solo acepta 1 archivo PDF por correo.")
    message_lines.append("")
    message_lines.append("Para procesar su solicitud de reparación, por favor:")
    message_lines.append("  1. Reenvíe el correo adjuntando únicamente UN archivo PDF")
    message_lines.append("  2. Si tiene múltiples boletas, envíe un correo separado por cada una")
    message_lines.append("")
    message_lines.append("Gracias por su comprensión.")

    return "\n".join(message_lines)


def _strip_if_string(value):
    """Retorna None si es None, sino retorna el string sin espacios"""
    if value is None:
        return None
    return str(value).strip() if value else None


def _normalizar_cuerpo_correo(body_text):
    """
    Normaliza el cuerpo del correo eliminando espacios extras y caracteres innecesarios

    Args:
        body_text: Texto del cuerpo del correo

    Returns:
        str: Texto normalizado o None si está vacío
    """
    if not body_text:
        return None

    # Eliminar espacios al inicio y final
    texto = body_text.strip()

    # Reemplazar múltiples saltos de línea por uno solo
    texto = re.sub(r'\n\s*\n+', '\n', texto)

    # Reemplazar múltiples espacios por uno solo
    texto = re.sub(r' {2,}', ' ', texto)

    # Reemplazar tabulaciones por espacios
    texto = texto.replace('\t', ' ')

    # Limitar la longitud a 1000 caracteres para no exceder límites de la API
    if len(texto) > 1000:
        texto = texto[:1000] + "..."

    return texto if texto else None


def _crear_preingreso_desde_pdf(pdf_content, pdf_filename, logger, garantia_correo=None, proveedor_correo_id=None, cuerpo_correo=None):
    """
    Crea un preingreso en la API a partir del contenido de un PDF

    Args:
        pdf_content: Bytes del archivo PDF
        pdf_filename: Nombre del archivo PDF
        logger: Logger para registrar eventos
        garantia_correo: Garantía recibida del cuerpo del correo (opcional)
        proveedor_correo_id: ID del distribuidor (proveedor) recibido del cuerpo del correo (opcional)
        cuerpo_correo: Cuerpo del correo normalizado (opcional)

    Returns:
        dict con {success, preingreso_id, boleta, numero_transaccion, consultar_reparacion, consultar_guia, tipo_preingreso_nombre, garantia_nombre, error}
    """
    try:
        logger.info("=" * 80)
        logger.info(f"📄 INICIANDO ANÁLISIS DE PDF: {pdf_filename}")
        logger.info("=" * 80)

        # Extraer texto del PDF
        logger.info(f"🔍 Paso 1/4: Extrayendo texto del PDF...")
        pdf_text = _extract_text_from_pdf(pdf_content, logger)

        if not pdf_text:
            logger.error("❌ No se pudo extraer texto del PDF")
            return {
                'success': False,
                'error': 'No se pudo extraer texto del PDF',
                'filename': pdf_filename
            }

        logger.info(f"✅ Texto extraído correctamente ({len(pdf_text)} caracteres)")

        # Extraer datos del PDF
        logger.info(f"🔍 Paso 2/4: Analizando y extrayendo datos del PDF...")
        extracted_data = extract_repair_data(pdf_text, logger)

        if not extracted_data or len(extracted_data) < 3:
            logger.error(
                f"❌ PDF sin información válida (solo {len(extracted_data) if extracted_data else 0} campos extraídos)")
            return {
                'success': False,
                'error': 'PDF sin información válida (menos de 3 campos extraídos)',
                'filename': pdf_filename
            }

        logger.info(f"✅ Datos extraídos correctamente ({len(extracted_data)} campos)")

        # Mostrar datos clave extraídos
        if 'numero_boleta' in extracted_data:
            logger.info(f"   📋 Boleta: {extracted_data['numero_boleta']}")
        if 'numero_transaccion' in extracted_data:
            logger.info(f"   📋 Transacción: {extracted_data['numero_transaccion']}")
        if 'nombre_cliente' in extracted_data:
            logger.info(f"   👤 Cliente: {extracted_data['nombre_cliente']}")

        # Crear archivo temporal para el PDF
        logger.info(f"🔍 Paso 3/4: Preparando archivo temporal para envío a API...")
        temp_pdf = tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False)
        temp_pdf.write(pdf_content)
        temp_pdf.close()
        logger.info(f"   📁 Archivo temporal creado: {temp_pdf.name}")

        # Determinar qué garantía usar (prioridad: correo > PDF)
        garantia_a_usar = None
        garantia_viene_de_correo = False

        if garantia_correo:
            garantia_a_usar = garantia_correo
            garantia_viene_de_correo = True
            logger.info(f"   ✓ Usando garantía del correo: '{garantia_correo}'")
        else:
            garantia_a_usar = extracted_data.get('tipo_garantia', '')
            logger.info(f"   ℹ Usando garantía del PDF: '{garantia_a_usar}'")

        # Determinar qué distribuidor usar (proveedor = distribuidor)
        # Si viene proveedor_correo_id, usarlo; si no, dejar como None
        distribuidor_id_a_usar = None

        if proveedor_correo_id:
            distribuidor_id_a_usar = proveedor_correo_id
            logger.info(f"   ✓ Usando proveedor (distribuidor) del correo - ID: '{proveedor_correo_id}'")
        else:
            logger.info(f"   ℹ No se detectó proveedor en el correo - distribuidor_id será None")

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
            garantia_nombre=_strip_if_string(garantia_a_usar),
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
            hecho_por=_strip_if_string(extracted_data.get('hecho_por')),
            distribuidor_id=_strip_if_string(distribuidor_id_a_usar),  # proveedor = distribuidor
            cuerpo_correo=cuerpo_correo  # Cuerpo del correo normalizado
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

        logger.info(f"🔍 Paso 4/4: Creando preingreso en la API...")
        logger.info(f"   📄 Archivo: {pdf_filename}")
        logger.info(f"   🌐 API Base URL: {settings.API_BASE_URL}")

        # Ejecutar caso de uso de forma asíncrona (desde código síncrono)
        async def ejecutar_creacion():
            return await use_case.execute(input_dto)

        logger.info("   ⏳ Enviando datos a la API iFR Pro...")
        result = run_async_from_sync(ejecutar_creacion())

        # Limpiar archivo temporal
        import os
        try:
            os.unlink(temp_pdf.name)
            logger.info(f"   🧹 Archivo temporal eliminado")
        except Exception as cleanup_error:
            logger.warning(f"   ⚠️ No se pudo eliminar archivo temporal: {cleanup_error}")

        if result.success:
            # Verificar si la API devolvió un JSON válido
            if not result.response.body:
                logger.warning("⚠️ La API no devolvió un json válido")
                logger.error("=" * 80)
                return {
                    'success': False,
                    'error': "La API no devolvió un json válido",
                    'filename': pdf_filename
                }
            else:
                logger.info("=" * 80)
                logger.info("✅ PREINGRESO CREADO EXITOSAMENTE")
                logger.info("=" * 80)
                logger.info(f"   📄 Archivo procesado: {pdf_filename}")
                logger.info(f"   🎫 Boleta Fruno: {result.preingreso_id}")
                logger.info(f"   📋 Boleta Gollo: {extracted_data.get('numero_boleta')}")
                if extracted_data.get('numero_transaccion'):
                    logger.info(f"   🔢 Transacción: {extracted_data.get('numero_transaccion')}")
                if result.tipo_preingreso_nombre:
                    logger.info(f"   📝 Tipo: {result.tipo_preingreso_nombre}")
                if result.garantia_nombre:
                    logger.info(f"   🛡️ Garantía: {result.garantia_nombre}")
                logger.info("=" * 80)

                return {
                    'success': True,
                    'preingreso_id': result.preingreso_id,
                    'boleta': extracted_data.get('numero_boleta'),
                    'numero_transaccion': extracted_data.get('numero_transaccion'),
                    'consultar_reparacion': result.consultar_reparacion,
                    'consultar_guia': result.consultar_guia,
                    'tipo_preingreso_nombre': result.tipo_preingreso_nombre,
                    'garantia_nombre': result.garantia_nombre,
                    'filename': pdf_filename,
                    'extracted_data': extracted_data,  # Incluir todos los datos extraídos
                    'garantia_viene_de_correo': garantia_viene_de_correo  # Flag para indicar origen de la garantía
                }
        else:
            error_msg = result.message or "Error desconocido al crear preingreso"
            logger.error("=" * 80)
            logger.error("❌ ERROR AL CREAR PREINGRESO")
            logger.error("=" * 80)
            logger.error(f"   📄 Archivo: {pdf_filename}")
            logger.error(f"   💥 Error: {error_msg}")
            logger.error("=" * 80)

            # Detectar error 409 Conflict (preingreso duplicado)
            is_409_conflict = '[409]' in error_msg or '409 Conflict' in error_msg

            return {
                'success': False,
                'error': error_msg,
                'filename': pdf_filename,
                'is_409_conflict': is_409_conflict,
                'numero_boleta': extracted_data.get('numero_boleta') if is_409_conflict else None,
                'numero_transaccion': extracted_data.get('numero_transaccion') if is_409_conflict else None,
                'extracted_data': extracted_data  # Incluir datos extraídos completos para adjuntos en correos de error
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
            description="Procesa 1 PDF de boleta de reparación y crea preingreso en la API (solo acepta 1 PDF por correo)",
            config_key="caso1",
            response_message="El preingreso ha sido creado exitosamente en el sistema.",
        )

    def process_email(self, email_data, logger):
        """Procesa el email, crea preingresos en la API y genera una respuesta"""
        try:
            sender = email_data.get('sender', '')
            subject = email_data.get('subject', 'Sin asunto')
            attachments = email_data.get('attachments', [])
            garantia_correo_info = email_data.get('garantia_correo', {})
            proveedor_correo_info = email_data.get('proveedor_correo', {})  # proveedor = distribuidor

            logger.info(f"Procesando {self._config_key} para email de {sender}")

            # Extraer garantía del correo si existe
            garantia_del_correo = None
            if garantia_correo_info.get('encontrada'):
                garantia_del_correo = garantia_correo_info.get('garantia')
                logger.info(
                    f"🛡️ Garantía del correo detectada: '{garantia_del_correo}' - Se usará en lugar de la del PDF")

            # Extraer proveedor (distribuidor) del correo si existe
            proveedor_id_del_correo = None
            if proveedor_correo_info.get('encontrado'):
                proveedor_id_del_correo = proveedor_correo_info.get('distribuidor_id')
                proveedor_nombre = proveedor_correo_info.get('distribuidor_nombre')
                logger.info(
                    f"📦 Proveedor (distribuidor) del correo detectado: '{proveedor_nombre}' (ID: {proveedor_id_del_correo}) - Se enviará a la API")

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

            # Validación: Si hay más de 1 PDF adjunto
            if len(pdf_attachments) > 1:
                logger.warning(f"Se recibieron {len(pdf_attachments)} archivos PDF - solo se acepta 1 por correo")
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                pdf_filenames = [att.get('filename', 'archivo_sin_nombre') for att in pdf_attachments]
                response = {
                    'recipient': sender,
                    'subject': f"Error: Múltiples PDFs Detectados - {timestamp}",
                    'body': _generate_multiple_pdfs_message(pdf_filenames)
                }
                return response

            # Procesar el único PDF adjunto
            logger.info("Procesando PDF adjunto...")

            pdf_attachment = pdf_attachments[0]  # Solo hay 1 PDF en este punto
            pdf_content = pdf_attachment.get('data')
            pdf_filename = pdf_attachment.get('filename', 'documento.pdf')

            # Crear estructura de PDF para incluir en todos los responses (éxito y error)
            pdf_data = {
                'filename': pdf_filename,
                'data': pdf_content
            }

            logger.info(f"Procesando PDF: {pdf_filename}")

            # Normalizar el cuerpo del correo
            body_text = email_data.get('body_text', '')
            cuerpo_normalizado = _normalizar_cuerpo_correo(body_text)

            if cuerpo_normalizado:
                logger.info(f"📧 Cuerpo del correo normalizado ({len(cuerpo_normalizado)} caracteres) - Se incluirá en el detalle")
            else:
                logger.info("📧 No hay cuerpo de correo para incluir")

            # Crear preingreso desde el PDF (pasando garantía, proveedor y cuerpo del correo si existen)
            result = _crear_preingreso_desde_pdf(
                pdf_content,
                pdf_filename,
                logger,
                garantia_correo=garantia_del_correo,
                proveedor_correo_id=proveedor_id_del_correo,  # proveedor = distribuidor
                cuerpo_correo=cuerpo_normalizado  # Cuerpo del correo normalizado
            )

            preingreso_results = []
            failed_files = []
            extracted_data = None  # Variable para guardar los datos extraídos

            if result['success']:
                preingreso_results.append({
                    'filename': pdf_filename,
                    'boleta': result.get('boleta'),
                    'numero_transaccion': result.get('numero_transaccion'),
                    'preingreso_id': result.get('preingreso_id'),
                    'consultar_reparacion': result.get('consultar_reparacion'),
                    'consultar_guia': result.get('consultar_guia'),
                    'tipo_preingreso_nombre': result.get('tipo_preingreso_nombre'),
                    'garantia_nombre': result.get('garantia_nombre'),
                    'garantia_viene_de_correo': result.get('garantia_viene_de_correo', False)
                })
                # Guardar los datos extraídos para enviar a usuarios CC
                extracted_data = result.get('extracted_data')
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

            # Validar si se creó el preingreso correctamente
            if not preingreso_results:
                logger.error("No se pudo crear el preingreso correctamente")
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
                        ),
                        'pdf_original': pdf_data,  # Incluir PDF original para adjuntos
                        'extracted_data': first_conflict.get('extracted_data')  # Incluir datos extraídos si existen
                    }
                    return response

                # Si no hay errores 409, usar el mensaje de error general
                response = {
                    'recipient': sender,
                    'subject': f"Error en Procesamiento de Preingreso - {timestamp}",
                    'body': _generate_all_failed_message(failed_files, non_pdf_files, subject),
                    'pdf_original': pdf_data,  # Incluir PDF original para adjuntos
                    'extracted_data': failed_files[0].get('extracted_data') if failed_files else None  # Incluir datos extraídos si existen
                }
                return response

            # Generar mensaje de éxito con el preingreso creado
            settings = Settings()
            body_message = _generate_success_message(
                preingreso_results,
                failed_files,
                non_pdf_files,
                api_base_url=settings.API_BASE_URL
            )

            # Generar subject con número de boleta y timestamp
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            if preingreso_results and len(preingreso_results) > 0:
                boleta = preingreso_results[0].get('boleta')
                if boleta:
                    subject_line = f"Confirmación de Preingreso Creado - Boleta {boleta} - {timestamp}"
                else:
                    subject_line = f"Confirmación de Preingreso - {timestamp}"
            else:
                subject_line = f"Confirmación de Preingreso - {timestamp}"

            response = {
                'recipient': sender,
                'subject': subject_line,
                'body': body_message,
                'attachments': [],  # No enviamos archivos adjuntos en el correo principal
                'extracted_data': extracted_data,  # Datos extraídos para usuarios CC
                'preingreso_results': preingreso_results,  # Resultados del preingreso para usuarios CC
                'pdf_original': pdf_data  # PDF original para adjuntar en notificaciones a usuarios CC
            }

            logger.info("Procesamiento completado: 1 preingreso creado exitosamente")
            return response

        except Exception as e:
            logger.error(f"Error al procesar email: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None