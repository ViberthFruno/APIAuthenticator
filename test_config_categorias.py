#!/usr/bin/env python3
"""
test_config_categorias.py - Script de prueba para verificar la carga de categorías
Ejecuta este script ANTES y DESPUÉS de compilar con PyInstaller

Uso:
  En desarrollo:     python test_config_categorias.py
  En ejecutable:     ./dist/GolloBot && python test_config_categorias.py
"""

import sys
import os

print("=" * 80)
print("TEST DE CONFIGURACIÓN DE CATEGORÍAS")
print("=" * 80)
print()

# Información del sistema
print("📋 INFORMACIÓN DEL SISTEMA:")
print(f"   Sistema operativo: {sys.platform}")
print(f"   Python version: {sys.version}")
print(f"   Ejecutable frozen: {getattr(sys, 'frozen', False)}")
print(f"   Directorio de trabajo: {os.getcwd()}")

if getattr(sys, 'frozen', False):
    print(f"   Directorio ejecutable: {os.path.dirname(sys.executable)}")
    print(f"   sys._MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
else:
    print(f"   Directorio script: {os.path.dirname(os.path.abspath(__file__))}")

print()

# Verificar que config_manager existe
print("=" * 80)
print("1️⃣  VERIFICANDO MÓDULO config_manager")
print("=" * 80)
try:
    from config_manager import get_categorias_config, get_categorias_config_path
    print("   ✓ Módulo config_manager importado correctamente")
except ImportError as e:
    print(f"   ❌ ERROR: No se pudo importar config_manager: {e}")
    sys.exit(1)

print()

# Verificar ruta del archivo
print("=" * 80)
print("2️⃣  VERIFICANDO RUTA DEL ARCHIVO config_categorias.json")
print("=" * 80)
try:
    config_path = get_categorias_config_path()
    print(f"   Ruta esperada: {config_path}")
    print(f"   ¿Existe el archivo? {os.path.exists(config_path)}")

    if os.path.exists(config_path):
        print(f"   ✓ Archivo encontrado")
        # Mostrar tamaño del archivo
        file_size = os.path.getsize(config_path)
        print(f"   Tamaño: {file_size} bytes")
    else:
        print(f"   ⚠️  Archivo NO encontrado - se creará automáticamente")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()

# Cargar configuración
print("=" * 80)
print("3️⃣  CARGANDO CONFIGURACIÓN DE CATEGORÍAS")
print("=" * 80)
try:
    config = get_categorias_config()
    print("   ✓ Configuración cargada correctamente")

    if not config:
        print("   ⚠️  Configuración está vacía")
    else:
        print(f"   Estructura: {list(config.keys())}")

        categorias = config.get('categorias', {})
        print(f"   Total de categorías: {len(categorias)}")
        print()

        # Listar todas las categorías
        print("   📂 CATEGORÍAS CARGADAS:")
        for nombre_cat, datos_cat in categorias.items():
            cat_id = datos_cat.get('id', 'N/A')
            palabras_clave = datos_cat.get('palabras_clave', [])
            num_palabras = len(palabras_clave)

            print(f"      • {nombre_cat} (ID: {cat_id}) - {num_palabras} palabras clave")

            # Mostrar las primeras 5 palabras clave
            if num_palabras > 0:
                for i, palabra_data in enumerate(palabras_clave[:5]):
                    if isinstance(palabra_data, str):
                        palabra = palabra_data
                    elif isinstance(palabra_data, dict):
                        palabra = palabra_data.get('palabra', 'N/A')
                    else:
                        palabra = str(palabra_data)

                    print(f"         - {palabra}")

                if num_palabras > 5:
                    print(f"         ... y {num_palabras - 5} más")

        print()

        # Verificar categorías esperadas
        print("   🔍 VERIFICANDO CATEGORÍAS ESPERADAS:")
        categorias_esperadas = [
            "Móviles", "Hogar", "Cómputo", "Desconocido", "Accesorios",
            "Transporte", "Seguridad", "Entretenimiento", "Telecomunicaciones", "No encontrado"
        ]

        for cat_nombre in categorias_esperadas:
            if cat_nombre in categorias:
                num_palabras = len(categorias[cat_nombre].get('palabras_clave', []))
                print(f"      ✓ {cat_nombre} (con {num_palabras} palabras clave)")
            else:
                print(f"      ❌ {cat_nombre} - NO ENCONTRADA")

except Exception as e:
    print(f"   ❌ ERROR al cargar configuración: {e}")
    import traceback
    traceback.print_exc()

print()

# Prueba de detección de categoría
print("=" * 80)
print("4️⃣  PRUEBA DE DETECCIÓN DE CATEGORÍA")
print("=" * 80)
try:
    from api_integration.domain.builders.crear_preingreso_builder import CrearPreingresoBuilder

    # Casos de prueba
    casos_prueba = [
        ("LAPTOP DELL INSPIRON", "Cómputo"),
        ("CELULAR SAMSUNG GALAXY", "Móviles"),
        ("CABLE USB TIPO C", "Accesorios"),
        ("ROUTER WIFI TP-LINK", "Telecomunicaciones"),
        ("TV SAMSUNG 55 PULGADAS", "Entretenimiento"),
        ("CAMARA DE SEGURIDAD", "Seguridad"),
        ("PRODUCTO DESCONOCIDO XYZ123", "No encontrado"),
    ]

    print("   Probando detección de categorías con descripciones de ejemplo:")
    print()

    for descripcion, categoria_esperada in casos_prueba:
        categoria_id, tipo_dispositivo_id = CrearPreingresoBuilder._detectar_categoria(descripcion)

        # Buscar el nombre de la categoría por ID
        config = get_categorias_config()
        categorias = config.get('categorias', {})
        categoria_nombre = "Desconocida"
        for nombre_cat, datos_cat in categorias.items():
            if datos_cat.get('id') == categoria_id:
                categoria_nombre = nombre_cat
                break

        # Verificar si la detección fue correcta
        if categoria_nombre == categoria_esperada:
            resultado = "✓"
        else:
            resultado = "❌"

        print(f"   {resultado} '{descripcion}'")
        print(f"      → Detectado: {categoria_nombre} (ID: {categoria_id}, Tipo: {tipo_dispositivo_id})")
        print(f"      → Esperado: {categoria_esperada}")
        print()

except ImportError as e:
    print(f"   ⚠️  No se pudo importar CrearPreingresoBuilder: {e}")
    print(f"   (Esto es normal si no tienes todos los módulos instalados)")
except Exception as e:
    print(f"   ❌ ERROR en prueba de detección: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("✅ PRUEBA COMPLETADA")
print("=" * 80)
print()
print("💡 INSTRUCCIONES:")
print("   1. Si estás en desarrollo (PyCharm), este test debe pasar sin errores")
print("   2. Después de compilar con PyInstaller, ejecuta este test nuevamente")
print("   3. Si ambos tests pasan, el problema está solucionado")
print()
print("=" * 80)
