#!/usr/bin/env python3
"""
Script de prueba para verificar la extracción de fecha de compra y correo
"""
import re

# Casos de prueba según lo descrito por el usuario
casos_prueba = [
    {
        'nombre': 'Caso 1: Con Fecha de Compra',
        'texto': 'No. Factura: 083-83511 Fecha de Compra:19/08/2025 Correo: maxjoca_2005@hotmail.com',
        'esperado': {
            'numero_factura': '083-83511',
            'fecha_compra': '19/08/2025',
            'correo': 'maxjoca_2005@hotmail.com'
        }
    },
    {
        'nombre': 'Caso 2: Sin Fecha de Compra',
        'texto': 'No. Factura: Otro tipo de Artículos\nCorreo: grenmadricas28@gmail.com',
        'esperado': {
            'numero_factura': 'Otro tipo de Artículos',
            'fecha_compra': None,
            'correo': 'grenmadricas28@gmail.com'
        }
    },
    {
        'nombre': 'Caso 3: Con espacios en Fecha de Compra',
        'texto': 'No. Factura: 123-456 Fecha de Compra: 15/03/2025 Correo: test@ejemplo.com',
        'esperado': {
            'numero_factura': '123-456',
            'fecha_compra': '15/03/2025',
            'correo': 'test@ejemplo.com'
        }
    },
    {
        'nombre': 'Caso 4: Solo número de factura y correo',
        'texto': 'No. Factura: 999-888 Correo: usuario@test.com',
        'esperado': {
            'numero_factura': '999-888',
            'fecha_compra': None,
            'correo': 'usuario@test.com'
        }
    }
]

def probar_extraccion():
    """Prueba los patrones regex actualizados"""
    print("=" * 80)
    print("PRUEBA DE EXTRACCIÓN DE FECHA DE COMPRA Y CORREO")
    print("=" * 80)

    for i, caso in enumerate(casos_prueba, 1):
        print(f"\n{'=' * 80}")
        print(f"CASO {i}: {caso['nombre']}")
        print(f"{'=' * 80}")
        print(f"Texto: {caso['texto']}")
        print(f"\nEsperado:")
        print(f"  - Número Factura: {caso['esperado']['numero_factura']}")
        print(f"  - Fecha Compra: {caso['esperado']['fecha_compra']}")
        print(f"  - Correo: {caso['esperado']['correo']}")

        data = {}
        text = caso['texto']

        # Extracción de número de factura (patrón actualizado)
        match = re.search(r'No\s*\.?\s*Factura\s*:?\s*([^\s]+(?:\s+[^\s]+){0,5}?)(?=\s+Correo|\s+Fecha\s+de\s+Compra)',
                          text, re.IGNORECASE)
        if match:
            data['numero_factura'] = re.sub(r'\s+', ' ', match.group(1).strip())

        # Extracción de fecha de compra (patrón específico)
        match = re.search(r'Fecha\s+de\s+Compra\s*:?\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
        if match:
            data['fecha_compra'] = match.group(1).strip()
        else:
            data['fecha_compra'] = None

        # Extracción de correo (patrón 0)
        match = re.search(
            r'No\s*\.?\s*Factura\s*:?[^@\n]*?(Correo\s*:?\s*)?([\w\.\-_]+\s*@\s*[\w\.\-]+\s*\.\s*\w+)',
            text,
            re.IGNORECASE
        )
        if match:
            data['correo'] = match.group(2).strip()

        # Si no se encontró con patrón 0, intentar patrón 1
        if 'correo' not in data:
            match = re.search(r'Correo\s*:?\s*([\w\.\-_]+\s*@\s*[\w\.\-]+\s*\.\s*\w+)', text, re.IGNORECASE)
            if match:
                data['correo'] = match.group(1).strip()

        print(f"\nExtraído:")
        print(f"  - Número Factura: {data.get('numero_factura', 'NO EXTRAÍDO')}")
        print(f"  - Fecha Compra: {data.get('fecha_compra', 'NO EXTRAÍDO')}")
        print(f"  - Correo: {data.get('correo', 'NO EXTRAÍDO')}")

        # Verificar resultados
        errores = []
        if data.get('numero_factura') != caso['esperado']['numero_factura']:
            errores.append(f"Número Factura incorrecto: esperado '{caso['esperado']['numero_factura']}', obtenido '{data.get('numero_factura')}'")

        if data.get('fecha_compra') != caso['esperado']['fecha_compra']:
            errores.append(f"Fecha Compra incorrecta: esperado '{caso['esperado']['fecha_compra']}', obtenido '{data.get('fecha_compra')}'")

        if data.get('correo') != caso['esperado']['correo']:
            errores.append(f"Correo incorrecto: esperado '{caso['esperado']['correo']}', obtenido '{data.get('correo')}'")

        if errores:
            print(f"\n❌ FALLÓ:")
            for error in errores:
                print(f"   - {error}")
        else:
            print(f"\n✅ EXITOSO: Todos los campos extraídos correctamente")

    print(f"\n{'=' * 80}")
    print("FIN DE LAS PRUEBAS")
    print("=" * 80)

if __name__ == '__main__':
    probar_extraccion()
