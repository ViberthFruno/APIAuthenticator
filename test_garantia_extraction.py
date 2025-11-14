#!/usr/bin/env python3
"""
Script de prueba para la función extract_garantia_from_email_body
Prueba diferentes variantes de escritura de garantías en correos
"""

import sys
import logging
from case1 import extract_garantia_from_email_body

# Configurar logger simple
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Casos de prueba
test_cases = [
    # Formato: (nombre_test, cuerpo_correo, garantia_esperada)

    # Casos con "Garantía" seguido de opciones válidas
    ("Garantía Normal", "Estimado, la Garantía Normal aplica en este caso.", "Normal"),
    ("GARANTIA NORMAL mayúsculas", "La GARANTIA NORMAL es aplicable.", "Normal"),
    ("garantia normal minúsculas", "garantia normal por favor", "Normal"),
    ("Garantía: Normal con dos puntos", "Por favor procesar con Garantía: Normal", "Normal"),

    # Casos con "No"
    ("Garantía No", "La Garantía No aplica", "No"),
    ("GARANTIA NO mayúsculas", "GARANTIA NO", "No"),
    ("Garantía: No con dos puntos", "Garantía: No es aplicable", "No"),

    # Casos con C.S.R
    ("Garantía C.S.R con puntos", "Garantía C.S.R para este equipo", "C.S.R"),
    ("Garantía CSR sin puntos", "Garantía CSR aplicable", "C.S.R"),
    ("GARANTIA CSR mayúsculas", "GARANTIA CSR", "C.S.R"),
    ("garantia csr minúsculas", "garantia csr por favor", "C.S.R"),
    ("Garantía: C.S.R con dos puntos", "Garantía: C.S.R", "C.S.R"),

    # Casos con DOA
    ("Garantía DOA", "La Garantía DOA aplica aquí", "DOA"),
    ("GARANTIA DOA mayúsculas", "GARANTIA DOA", "DOA"),
    ("garantia doa minúsculas", "garantia doa", "DOA"),

    # Casos con STOCK
    ("Garantía STOCK", "Garantía STOCK para reemplazo", "STOCK"),
    ("garantia stock minúsculas", "garantia stock", "STOCK"),
    ("Garantía: STOCK con dos puntos", "Garantía: STOCK", "STOCK"),

    # Casos con DAP
    ("Garantía DAP", "Garantía DAP aplicable", "DAP"),
    ("GARANTIA DAP mayúsculas", "GARANTIA DAP", "DAP"),
    ("garantia dap minúsculas", "garantia dap", "DAP"),

    # Casos con espacios y caracteres extra
    ("Garantía con espacios", "Hola, la   Garantía    Normal   está disponible", "Normal"),
    ("Garantía al inicio", "Garantía CSR\nResto del mensaje...", "C.S.R"),

    # Casos con acento
    ("Garantía con acento", "La Garantía Normal es aplicable", "Normal"),

    # Casos donde NO debe encontrar nada
    ("Sin palabra Garantía", "Por favor procesar Normal", None),
    ("Garantía sin opción válida", "La Garantía es importante", None),
    ("Garantía con opción inválida", "Garantía Extendida", None),
    ("Solo la palabra No sin Garantía", "No puedo procesarlo", None),

    # Casos complejos
    ("Múltiples menciones", "La Garantía es importante. Garantía Normal aplica.", "Normal"),
    ("Correo largo", """
    Estimado equipo de soporte,

    Les escribo para solicitar el procesamiento de la siguiente boleta.
    La Garantía CSR debe ser aplicada en este caso según lo acordado.

    Muchas gracias por su atención.
    """, "C.S.R"),
]

print("=" * 100)
print("PRUEBAS DE EXTRACCIÓN DE GARANTÍA DEL CORREO")
print("=" * 100)
print()

passed = 0
failed = 0
test_results = []

for i, (nombre, cuerpo, esperado) in enumerate(test_cases, 1):
    print(f"\n{'=' * 100}")
    print(f"TEST {i}/{len(test_cases)}: {nombre}")
    print(f"{'=' * 100}")
    print(f"Cuerpo del correo (primeros 100 chars): {cuerpo[:100]}...")
    print(f"Garantía esperada: {esperado}")
    print()

    resultado = extract_garantia_from_email_body(cuerpo, logger)

    print()
    print(f"Resultado obtenido: {resultado}")

    if resultado == esperado:
        print("✅ TEST PASÓ")
        passed += 1
        test_results.append((nombre, "✅ PASÓ"))
    else:
        print(f"❌ TEST FALLÓ - Esperado: {esperado}, Obtenido: {resultado}")
        failed += 1
        test_results.append((nombre, f"❌ FALLÓ (esperado: {esperado}, obtenido: {resultado})"))

# Resumen final
print("\n\n")
print("=" * 100)
print("RESUMEN DE PRUEBAS")
print("=" * 100)
print()

for nombre, status in test_results:
    print(f"{status:50} - {nombre}")

print()
print("=" * 100)
print(f"TOTAL: {len(test_cases)} pruebas")
print(f"PASADAS: {passed} ✅")
print(f"FALLADAS: {failed} ❌")
print(f"PORCENTAJE DE ÉXITO: {(passed/len(test_cases)*100):.1f}%")
print("=" * 100)

# Retornar código de salida apropiado
sys.exit(0 if failed == 0 else 1)
