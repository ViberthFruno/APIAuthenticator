#!/usr/bin/env python3
"""
main_integrado.py - Punto de entrada principal del sistema integrado
API iFR Pro + Bot de Correo Electrónico
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Asegurar que los módulos estén disponibles
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


def launch_gui():
    """Lanza la interfaz gráfica integrada"""
    try:
        import tkinter as tk
        from main_gui_integrado import IntegratedGUI

        print("🚀 Iniciando Sistema Integrado...")
        print("   - API iFR Pro")
        print("   - Bot de Correo Electrónico")
        print()

        root = tk.Tk()
        app = IntegratedGUI(root)

        # Centrar ventana
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')

        # Cierre seguro
        root.protocol("WM_DELETE_WINDOW", app.quit_app)

        print("✅ Sistema inicializado correctamente")
        print("=" * 60)
        root.mainloop()

    except ImportError as e:
        print(f"❌ Error: No se pudo cargar la interfaz gráfica")
        print(f"   Detalles: {e}")
        print()
        print("💡 Verifique que todos los módulos necesarios estén instalados:")
        print("   - tkinter (incluido con Python)")
        print("   - PIL/Pillow: pip install pillow")
        print("   - requests: pip install requests")
        print("   - python-dotenv: pip install python-dotenv")
        print("   - pdfplumber: pip install pdfplumber")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_cli_mode():
    """Ejecuta en modo CLI (línea de comandos)"""
    try:
        from settings import Settings
        from config_manager import ConfigManager
        from email_manager import EmailManager
        from case_handler import CaseHandler

        print("=" * 60)
        print("Sistema Integrado - Modo CLI")
        print("=" * 60)
        print()

        settings = Settings()
        config_manager = ConfigManager()
        email_manager = EmailManager()
        case_handler = CaseHandler()

        # Mostrar información
        print("📊 Estado del Sistema:")
        print(f"   API Cuenta: {settings.API_CUENTA}")
        print(f"   API URL: {settings.API_BASE_URL}")
        print()

        email_config = config_manager.get_email_config()
        if config_manager.has_email_config():
            print(f"   ✅ Email configurado: {email_config.get('email')}")
        else:
            print("   ❌ Email no configurado")

        cases = case_handler.get_available_cases()
        print(f"   📁 Casos disponibles: {len(cases)}")
        for case in cases:
            print(f"      - {case}")

        print()
        print("=" * 60)
        print()
        print("💡 Para usar la interfaz gráfica, ejecute sin argumentos:")
        print("   python main_integrado.py")
        print()

    except Exception as e:
        print(f"❌ Error en modo CLI: {e}")
        sys.exit(1)


def check_dependencies():
    """Verifica las dependencias necesarias"""
    dependencies = {
        'tkinter': 'Tkinter (interfaz gráfica)',
        'PIL': 'Pillow (manejo de imágenes)',
        'requests': 'Requests (peticiones HTTP)',
        'dotenv': 'python-dotenv (variables de entorno)',
        'pdfplumber': 'pdfplumber (procesamiento de PDFs - opcional para Caso 1)'
    }

    missing = []
    optional_missing = []

    for module, description in dependencies.items():
        try:
            if module == 'dotenv':
                __import__('dotenv')
            else:
                __import__(module)
        except ImportError:
            if module == 'pdfplumber':
                optional_missing.append(f"   - {description}")
            else:
                missing.append(f"   - {description}")

    if missing:
        print("❌ Faltan las siguientes dependencias requeridas:")
        for dep in missing:
            print(dep)
        print()
        print("Instale con:")
        print("   pip install pillow requests python-dotenv")
        return False

    if optional_missing:
        print("⚠️  Dependencias opcionales faltantes:")
        for dep in optional_missing:
            print(dep)
        print()
        print("Para usar el Caso 1 (procesamiento de PDFs), instale:")
        print("   pip install pdfplumber")
        print()

    return True


def create_example_env():
    """Crea un archivo .env de ejemplo si no existe"""
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    example_file = os.path.join(os.path.dirname(__file__), '.env.example')

    if not os.path.exists(env_file) and not os.path.exists(example_file):
        example_content = """# Configuración de API iFR Pro
API_BASE_URL=https://pruebas.api.ifrpro.nargallo.com
API_CUENTA=CD2D
API_LLAVE=ifr-pruebas-F7EC2E
API_CODIGO_SERVICIO=cd85e
API_PAIS=CR
API_TIMEOUT=30

# Configuración de la aplicación
API_ENV=development
LOG_LEVEL=INFO
DEBUG=true

# Configuración de archivos
MAX_FILE_SIZE=5242880
ALLOWED_EXTENSIONS=png,jpg,jpeg,pdf,gif
MAX_FILES_PER_REQUEST=6

# Seguridad
ENABLE_SSL_VERIFY=true
REQUEST_RETRY_COUNT=3
REQUEST_RETRY_DELAY=1

# Performance
BATCH_SIZE=5
PARALLEL_UPLOADS=false
CONNECTION_POOL_SIZE=10
"""
        try:
            with open(example_file, 'w', encoding='utf-8') as f:
                f.write(example_content)
            print(f"✅ Creado archivo de ejemplo: {example_file}")
            print("   Copie este archivo a .env y configure sus valores")
            print()
        except Exception as e:
            print(f"⚠️  No se pudo crear .env.example: {e}")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Sistema Integrado: API iFR Pro + Bot de Correo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main_integrado.py              # Lanza la interfaz gráfica (por defecto)
  python main_integrado.py --cli        # Muestra información en modo CLI
  python main_integrado.py --check      # Verifica dependencias

Para más información, visite: https://github.com/tu-repo
        """
    )

    parser.add_argument(
        '--cli',
        action='store_true',
        help='Ejecutar en modo CLI (sin interfaz gráfica)'
    )

    parser.add_argument(
        '--check',
        action='store_true',
        help='Verificar dependencias del sistema'
    )

    parser.add_argument(
        '--create-env',
        action='store_true',
        help='Crear archivo .env.example'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='Sistema Integrado v1.0.0'
    )

    args = parser.parse_args()

    # Banner de inicio
    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                                                           ║")
    print("║         Sistema Integrado - API iFR Pro + Correo          ║")
    print("║                        v1.0.0                             ║")
    print("║                                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Crear .env.example si se solicita
    if args.create_env:
        create_example_env()
        sys.exit(0)

    # Verificar dependencias si se solicita
    if args.check:
        print("🔍 Verificando dependencias...")
        print()
        if check_dependencies():
            print("✅ Todas las dependencias requeridas están instaladas")
        else:
            print("❌ Faltan dependencias requeridas")
            sys.exit(1)
        sys.exit(0)

    # Verificar dependencias antes de continuar
    if not check_dependencies():
        sys.exit(1)

    # Ejecutar en modo CLI o GUI
    if args.cli:
        run_cli_mode()
    else:
        # Crear .env.example si no existe
        if not os.path.exists('.env') and not os.path.exists('.env.example'):
            create_example_env()

        # Lanzar GUI
        launch_gui()


if __name__ == "__main__":
    main()