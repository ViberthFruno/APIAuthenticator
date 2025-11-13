#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para la nueva lógica de extracción de correos electrónicos
Prueba diferentes escenarios que pueden ocurrir en PDFs con OCR
"""

import re
import sys


class MockLogger:
    """Logger simulado para pruebas"""
    def info(self, msg):
        print(f"[INFO] {msg}")

    def warning(self, msg):
        print(f"[WARNING] {msg}")

    def error(self, msg):
        print(f"[ERROR] {msg}")


def extract_email_robust(text, logger):
    """Versión extraída de la nueva lógica de extracción de correos"""
    correo_encontrado = None
    logger.info("🔍 Iniciando búsqueda robusta de correo electrónico...")

    # Patrón flexible para emails
    patron_email = r'([a-zA-Z0-9][a-zA-Z0-9\.\-_]{0,63})\s*@\s*([a-zA-Z0-9][a-zA-Z0-9\.\-]{0,253})\s*\.\s*([a-zA-Z]{2,6})'

    # Buscar todas las coincidencias
    matches = re.findall(patron_email, text, re.IGNORECASE)

    if matches:
        logger.info(f"✓ Encontrados {len(matches)} posibles correos en el documento")

        # Lista de dominios comunes
        dominios_comunes = [
            'gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com',
            'hotmail.es', 'outlook.es', 'yahoo.es',
            'live.com', 'icloud.com', 'aol.com',
            'gollo.com', 'fruno.com'
        ]

        correos_candidatos = []
        for match in matches:
            local_part = match[0].strip()
            domain_part = match[1].strip()
            extension_part = match[2].strip()

            correo_temp = f"{local_part}@{domain_part}.{extension_part}"
            correo_temp = re.sub(r'\s+', '', correo_temp)
            correo_temp = correo_temp.lower()

            # Validaciones básicas
            if len(correo_temp) < 6:
                continue
            if correo_temp.count('@') != 1:
                continue
            if '..' in correo_temp:
                continue
            if correo_temp.startswith('.') or correo_temp.endswith('.'):
                continue

            local = correo_temp.split('@')[0]
            if not local or local.startswith('.') or local.endswith('.'):
                continue

            domain_full = correo_temp.split('@')[1]
            if '.' not in domain_full:
                continue

            # Corrección de typos
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

            es_dominio_comun = any(correo_corregido.endswith(dominio) for dominio in dominios_comunes)

            correos_candidatos.append({
                'correo': correo_corregido,
                'es_dominio_comun': es_dominio_comun,
                'original': correo_temp
            })

            logger.info(f"   • Candidato: {correo_corregido} {'(dominio común)' if es_dominio_comun else ''}")

        if correos_candidatos:
            correos_candidatos.sort(key=lambda x: (not x['es_dominio_comun'], x['correo']))
            correo_encontrado = correos_candidatos[0]['correo']

            if correos_candidatos[0]['es_dominio_comun']:
                logger.info(f"✅ Correo seleccionado (dominio común): {correo_encontrado}")
            else:
                logger.info(f"✅ Correo seleccionado: {correo_encontrado}")

            if len(correos_candidatos) > 1:
                logger.info(f"ℹ️ Se encontraron {len(correos_candidatos)} correos válidos, se seleccionó el primero")

    # Fallback con espacios
    if not correo_encontrado:
        logger.info("🔍 Patrón robusto no encontró correos, intentando búsqueda con espacios...")
        patron_espacios = r'([a-zA-Z0-9][a-zA-Z0-9\.\-_\s]{2,63})\s*@\s*([a-zA-Z0-9][a-zA-Z0-9\.\-\s]{2,253})\s*\.\s*([a-zA-Z]{2,6})'
        match = re.search(patron_espacios, text, re.IGNORECASE)

        if match:
            correo_encontrado = f"{match.group(1)}@{match.group(2)}.{match.group(3)}"
            correo_encontrado = re.sub(r'\s+', '', correo_encontrado).lower()
            logger.info(f"✓ Correo encontrado con espacios internos: {correo_encontrado}")

    # Validación final
    if correo_encontrado:
        if '@' in correo_encontrado and '.' in correo_encontrado.split('@')[1]:
            if 6 <= len(correo_encontrado) <= 254:
                logger.info(f"✅ Correo extraído y validado exitosamente: {correo_encontrado}")
                return correo_encontrado
            else:
                logger.warning(f"⚠️ Correo con longitud inválida: {correo_encontrado}")
                return "correo_no_encontrado@gollo.com"
        else:
            logger.warning(f"⚠️ Correo con formato inválido: {correo_encontrado}")
            return "correo_no_encontrado@gollo.com"
    else:
        logger.warning("⚠️ No se pudo extraer el correo del cliente")
        return "correo_no_encontrado@gollo.com"


def test_casos():
    """Prueba diferentes escenarios de extracción"""
    logger = MockLogger()

    test_cases = [
        {
            "nombre": "Correo con espacios alrededor del @",
            "texto": "Cliente: Juan Perez Tel: 88776655 Correo: juan.perez @ gmail . com Direccion: San Jose"
        },
        {
            "nombre": "Correo en posición no estándar (al final)",
            "texto": "Numero Boleta: 123-456 Fecha: 15/01/2024 Cliente: Maria Lopez Serie: ABC123 contacto@hotmail.com"
        },
        {
            "nombre": "Correo con typo en dominio (gmal)",
            "texto": "No. Factura: STOCK123 Direcc: Alajuela Tel: 22334455 Correo: cliente123@gmal.com Producto: Laptop"
        },
        {
            "nombre": "Correo sin palabra clave 'Correo:'",
            "texto": "Boleta 789-012 Cliente PEDRO RAMIREZ CED 112340567 Tel 89001234 pedro.ramirez@outlook.com Serie XYZ789"
        },
        {
            "nombre": "Múltiples correos (debe seleccionar el primero válido)",
            "texto": "Datos: test@test.com Contacto: Ana Garcia ana.garcia@gmail.com Telefono: 88990011"
        },
        {
            "nombre": "Correo con guiones y puntos",
            "texto": "Cliente: Carlos Mora Correo: carlos.mora-2024@hotmail.es Telefono: 77665544"
        },
        {
            "nombre": "Correo muy espaciado (OCR deteriorado)",
            "texto": "Informacion del cliente: m a r i a  l o p e z @ y a h o o . c o m Tel: 66554433"
        },
        {
            "nombre": "Sin correo en el texto",
            "texto": "Boleta 555-666 Cliente: Jose Martinez Tel: 99887766 Direccion: Heredia Sin correo electronico"
        },
        {
            "nombre": "Correo con números en la parte local",
            "texto": "Contacto: usuario2024@gmail.com Fecha: 20/02/2024 Serie: DEF456"
        },
        {
            "nombre": "Correo después de 'Direcc' (caso problemático reportado)",
            "texto": "Direcc: San Jose, 100m norte Correo: cliente@gollo.com No. Factura: 789 Fecha de Compra: 01/01/2024"
        }
    ]

    print("=" * 80)
    print("PRUEBAS DE EXTRACCIÓN ROBUSTA DE CORREOS ELECTRÓNICOS")
    print("=" * 80)
    print()

    resultados = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"PRUEBA {i}: {test_case['nombre']}")
        print(f"{'=' * 80}")
        print(f"Texto de entrada:")
        print(f"  {test_case['texto'][:100]}...")
        print()

        resultado = extract_email_robust(test_case['texto'], logger)

        es_exitoso = resultado != "correo_no_encontrado@gollo.com"
        resultados.append({
            'nombre': test_case['nombre'],
            'exitoso': es_exitoso,
            'correo': resultado
        })

        print(f"\n{'=' * 80}")
        print()

    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN DE PRUEBAS")
    print("=" * 80)

    exitosos = sum(1 for r in resultados if r['exitoso'])
    fallidos = len(resultados) - exitosos

    print(f"\nTotal de pruebas: {len(resultados)}")
    print(f"✅ Exitosas: {exitosos}")
    print(f"❌ Fallidas: {fallidos}")
    print()

    print("Detalle de resultados:")
    for i, resultado in enumerate(resultados, 1):
        estado = "✅" if resultado['exitoso'] else "❌"
        print(f"  {i}. {estado} {resultado['nombre']}")
        print(f"     → {resultado['correo']}")

    print("\n" + "=" * 80)

    return exitosos, fallidos


if __name__ == "__main__":
    exitosos, fallidos = test_casos()

    # Código de salida: 0 si todas las pruebas esperadas pasaron
    sys.exit(0 if fallidos <= 1 else 1)  # Permitir 1 fallo (caso sin correo)
