#!/usr/bin/env python3
"""
Script de prueba para validar el sistema de categorización automática
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_integration.domain.builders.crear_preingreso_builder import CrearPreingresoBuilder

def test_categoria(descripcion: str, categoria_esperada: str, id_esperado: int):
    """Prueba la detección de categoría para una descripción dada"""
    categoria_detectada = CrearPreingresoBuilder._detectar_categoria(descripcion)
    resultado = "✓" if categoria_detectada == id_esperado else "✗"
    print(f"{resultado} Descripción: '{descripcion}'")
    print(f"   Categoría esperada: {categoria_esperada} (ID: {id_esperado})")
    print(f"   Categoría detectada: ID {categoria_detectada}")
    print()
    return categoria_detectada == id_esperado

if __name__ == "__main__":
    print("=" * 80)
    print("PRUEBAS DEL SISTEMA DE CATEGORIZACIÓN AUTOMÁTICA")
    print("=" * 80)
    print()

    pruebas = [
        # (descripción, nombre_categoria_esperada, id_esperado)
        ("TELEFONO CELULAR", "Móviles", 1),
        ("MOBILE TECH INTLA SA", "Telecomunicaciones", 11),
        ("SMARTPHONE SAMSUNG", "Móviles", 1),
        ("LAPTOP HP", "Cómputo", 4),
        ("REFRIGERADOR", "Electrodoméstico", 2),
        ("TELEVISION SAMSUNG", "Entretenimiento", 10),
        ("ROUTER WIFI", "Telecomunicaciones", 11),
        ("CAMARA CCTV", "Seguridad", 8),
        ("CARGADOR USB", "Accesorios", 6),
        ("GPS VEHICULAR", "Transporte", 7),
        ("VENTILADOR", "Hogar", 3),
        ("PRODUCTO DESCONOCIDO XYZ123", "Desconocido", 5),
        ("", "Desconocido", 5),
        (None, "Desconocido", 5),
    ]

    total = len(pruebas)
    exitosos = 0

    for descripcion, categoria, id_cat in pruebas:
        if test_categoria(descripcion, categoria, id_cat):
            exitosos += 1

    print("=" * 80)
    print(f"RESULTADOS: {exitosos}/{total} pruebas exitosas")
    print("=" * 80)

    if exitosos == total:
        print("✓ Todas las pruebas pasaron correctamente")
        sys.exit(0)
    else:
        print(f"✗ {total - exitosos} prueba(s) fallaron")
        sys.exit(1)
