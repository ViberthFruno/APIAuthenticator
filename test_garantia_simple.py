#!/usr/bin/env python3
"""
Script de prueba simplificado para la lógica de extracción de garantía
"""

import re

class SimpleLogger:
    def info(self, msg):
        print(f"[INFO] {msg}")

    def exception(self, msg):
        print(f"[ERROR] {msg}")

def extract_garantia_from_email_body(email_body, logger):
    """
    Extrae la garantía del cuerpo del correo electrónico de forma robusta.
    (Copia de la función implementada en case1.py)
    """
    try:
        if not email_body:
            logger.info("📧 Cuerpo del correo vacío, no se puede extraer garantía")
            return None

        logger.info("=" * 80)
        logger.info("📧 INICIANDO EXTRACCIÓN DE GARANTÍA DEL CORREO")
        logger.info("=" * 80)

        # Normalizar el texto del correo
        email_body_normalized = re.sub(r'\s+', ' ', email_body)

        # Buscar la palabra "Garantia" con variantes (case-insensitive)
        garantia_pattern = r'garant[ií]a'

        # Encontrar todas las coincidencias de "Garantia" en el correo
        garantia_matches = list(re.finditer(garantia_pattern, email_body_normalized, re.IGNORECASE))

        if not garantia_matches:
            logger.info("❌ No se encontró la palabra 'Garantia' en el correo")
            return None

        logger.info(f"✓ Se encontraron {len(garantia_matches)} coincidencias de 'Garantia' en el correo")

        # Opciones válidas de garantía con sus variantes
        opciones_garantia = [
            ('Normal', [r'normal']),
            ('No', [r'\bno\b']),
            ('C.S.R', [r'c\.?s\.?r\.?']),
            ('DOA', [r'd\.?o\.?a\.?']),
            ('STOCK', [r'stock']),
            ('DAP', [r'd\.?a\.?p\.?'])
        ]

        # Buscar después de cada coincidencia de "Garantia"
        for match in garantia_matches:
            start_pos = match.end()
            texto_despues = email_body_normalized[start_pos:start_pos + 100]

            logger.info(f"🔍 Analizando texto después de 'Garantia': '{texto_despues[:50]}...'")

            # Buscar cada opción válida
            for nombre_normalizado, patrones in opciones_garantia:
                for patron in patrones:
                    match_opcion = re.search(patron, texto_despues[:50], re.IGNORECASE)
                    if match_opcion:
                        logger.info("=" * 80)
                        logger.info(f"✅ GARANTÍA ENCONTRADA EN EL CORREO: {nombre_normalizado}")
                        logger.info(f"   Texto detectado: '{match_opcion.group()}'")
                        logger.info(f"   Normalizado a: '{nombre_normalizado}'")
                        logger.info("=" * 80)
                        return nombre_normalizado

        logger.info("❌ No se encontró ninguna opción válida de garantía después de 'Garantia'")
        logger.info("   Opciones válidas: Normal, No, C.S.R, DOA, STOCK, DAP")
        return None

    except Exception as e:
        logger.exception(f"❌ Error extrayendo garantía del correo: {e}")
        return None


# Casos de prueba
test_cases = [
    ("Garantía Normal", "Estimado, la Garantía Normal aplica en este caso.", "Normal"),
    ("GARANTIA NORMAL mayúsculas", "La GARANTIA NORMAL es aplicable.", "Normal"),
    ("garantia normal minúsculas", "garantia normal por favor", "Normal"),
    ("Garantía No", "La Garantía No aplica", "No"),
    ("Garantía C.S.R con puntos", "Garantía C.S.R para este equipo", "C.S.R"),
    ("Garantía CSR sin puntos", "Garantía CSR aplicable", "C.S.R"),
    ("GARANTIA CSR mayúsculas", "GARANTIA CSR", "C.S.R"),
    ("Garantía DOA", "La Garantía DOA aplica aquí", "DOA"),
    ("Garantía STOCK", "Garantía STOCK para reemplazo", "STOCK"),
    ("Garantía DAP", "Garantía DAP aplicable", "DAP"),
    ("Sin palabra Garantía", "Por favor procesar Normal", None),
    ("Garantía sin opción válida", "La Garantía es importante", None),
]

logger = SimpleLogger()

print("\n" + "=" * 100)
print("PRUEBAS DE EXTRACCIÓN DE GARANTÍA DEL CORREO")
print("=" * 100 + "\n")

passed = 0
failed = 0

for i, (nombre, cuerpo, esperado) in enumerate(test_cases, 1):
    print(f"\nTEST {i}: {nombre}")
    print("-" * 100)
    resultado = extract_garantia_from_email_body(cuerpo, logger)

    if resultado == esperado:
        print(f"✅ PASÓ - Esperado: {esperado}, Obtenido: {resultado}\n")
        passed += 1
    else:
        print(f"❌ FALLÓ - Esperado: {esperado}, Obtenido: {resultado}\n")
        failed += 1

print("\n" + "=" * 100)
print(f"RESUMEN: {passed}/{len(test_cases)} pruebas pasadas ({failed} falladas)")
print("=" * 100 + "\n")
