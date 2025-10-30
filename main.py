#!/usr/bin/env python3
"""
main.py - Punto de entrada principal del servicio de autenticación API iFR Pro
"""

import os
from dotenv import load_dotenv
import sys
import argparse
import logging
from typing import List
import json

# Añadir api_ifrpro al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api_ifrpro'))

# Cargar variables de entorno
load_dotenv()

from api_ifrpro import APIClient, FileHandler
from config.settings import Settings


def setup_logging(level: str, log_dir: str):
    """Configura el sistema de logging para CLI"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(log_dir, 'api_auth.log'), mode='a', encoding='utf-8')
        ]
    )
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    return logging.getLogger(__name__)


class APIAuthService:
    """Servicio principal de autenticación API (para modo CLI)"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        self.client = APIClient(
            cuenta_api=settings.API_CUENTA,
            llave_api=settings.API_LLAVE,
            codigo_servicio=settings.API_CODIGO_SERVICIO,
            pais=settings.API_PAIS,
            base_url=settings.API_BASE_URL,
            timeout=settings.API_TIMEOUT,
            verify=settings.ENABLE_SSL_VERIFY
        )
        self.logger.info("Servicio de autenticación API inicializado")

    def test_authentication(self) -> bool:
        self.logger.info("Probando autenticación...")
        try:
            if self.client.health_check():
                self.logger.info("✅ Autenticación exitosa")
                return True
            else:
                self.logger.error("❌ Fallo en autenticación")
                return False
        except Exception as e:
            self.logger.error(f"❌ Error en autenticación: {e}")
            return False

    def upload_files_example(self, file_paths: List[str] = None) -> bool:
        self.logger.info("Iniciando ejemplo de subida de archivos...")

        if not file_paths:
            self.logger.info("Creando archivos de prueba...")
            test_dir = os.path.join(self.settings.TEMP_DIR, "test_files")
            os.makedirs(test_dir, exist_ok=True)
            file_paths = FileHandler.create_test_files(
                directory=test_dir,
                count={'png': 2, 'jpg': 1, 'jpeg': 1, 'pdf': 1}
            )

        if not file_paths:
            self.logger.error("No hay archivos para subir")
            return False

        form_data = {
            "titulo": "Prueba de carga",
            "descripcion": f"Carga de {len(file_paths)} archivos",
            "usuario": "api_test",
            "tipo": "multifile"
        }

        try:
            self.logger.info(f"Subiendo {len(file_paths)} archivos...")

            response = self.client.upload_files(
                endpoint="/v1/upload",
                data=form_data,
                file_paths=file_paths,
                field_name="archivos"
            )

            if response.status_code == 200:
                self.logger.info("✅ Archivos subidos exitosamente")
                try:
                    result = response.json()
                    self.logger.info(f"Respuesta: {json.dumps(result, indent=2)}")
                except:
                    self.logger.info(f"Respuesta (texto): {response.text[:200]}")
                return True
            else:
                self.logger.error(f"❌ Error en subida: Status {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error subiendo archivos: {e}")
            return False
        finally:
            if file_paths and "test_files" in str(file_paths[0]):
                test_dir = os.path.join(self.settings.TEMP_DIR, "test_files")
                if os.path.exists(test_dir):
                    FileHandler.cleanup_directory(test_dir)
                    self.logger.info("Archivos de prueba eliminados")

    def batch_process(self, input_dir: str, output_dir: str = None) -> bool:
        self.logger.info(f"Procesando archivos desde: {input_dir}")
        if not os.path.exists(input_dir):
            self.logger.error(f"Directorio no encontrado: {input_dir}")
            return False

        extensions = self.settings.get_allowed_extensions_list()
        file_paths = [os.path.join(input_dir, f) for f in os.listdir(input_dir)
                      if any(f.lower().endswith(ext) for ext in extensions)]

        if not file_paths:
            self.logger.warning("No se encontraron archivos válidos")
            return False

        batch_size = self.settings.BATCH_SIZE
        success_count = 0
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            self.logger.info(f"Procesando lote {i // batch_size + 1}: {len(batch)} archivos")

            try:
                form_data = {
                    "lote": f"{i // batch_size + 1}",
                    "total_archivos": str(len(batch)),
                    "origen": "batch_process"
                }

                response = self.client.upload_files(
                    endpoint="/v1/batch/upload",
                    data=form_data,
                    file_paths=batch,
                    field_name="archivos"
                )

                if response.status_code == 200:
                    success_count += len(batch)
                    self.logger.info(f"✅ Lote procesado exitosamente")
                else:
                    self.logger.error(f"❌ Error en lote: Status {response.status_code}")

            except Exception as e:
                self.logger.error(f"❌ Error procesando lote: {e}")

        self.logger.info(f"Procesamiento completado: {success_count}/{len(file_paths)} archivos exitosos")
        return success_count == len(file_paths)

    def interactive_mode(self):
        self.logger.info("Iniciando modo interactivo...")
        while True:
            print("\n" + "=" * 60)
            print("API Authentication Service - Modo Interactivo CLI")
            print("=" * 60)
            print("1. Probar autenticación")
            print("2. Subir archivos de prueba")
            print("3. Subir archivos desde directorio")
            print("4. Procesar archivos en lote")
            print("5. Información del servicio")
            print("0. Salir")
            print("-" * 60)

            try:
                opcion = input("Seleccione una opción: ").strip()
                if opcion == "0":
                    break
                elif opcion == "1":
                    self.test_authentication()
                elif opcion == "2":
                    self.upload_files_example()
                elif opcion == "3":
                    dir_path = input("Ingrese la ruta del directorio: ").strip()
                    if dir_path:
                        files = [os.path.join(dir_path, f) for f in os.listdir(dir_path)
                                 if os.path.isfile(os.path.join(dir_path, f))]
                        if files:
                            self.upload_files_example(files)
                elif opcion == "4":
                    input_dir = input("Directorio de entrada: ").strip()
                    if input_dir:
                        self.batch_process(input_dir)
                elif opcion == "5":
                    self.show_info()
                else:
                    print("Opción no válida")
            except KeyboardInterrupt:
                print("\nInterrumpido por el usuario")
                break
            except Exception as e:
                self.logger.error(f"Error: {e}")
        self.logger.info("Modo interactivo finalizado")

    def show_info(self):
        info = f"""
╔═══════════════════════════════════════════════════════════════╗
║   API Authentication Service Info                             ║
╠═══════════════════════════════════════════════════════════════╣
║ Cuenta API:       {self.settings.API_CUENTA:<45}║
║ Servicio:         {self.settings.API_CODIGO_SERVICIO:<45}║
║ País:             {self.settings.API_PAIS:<45}║
║ URL Base:         {self.settings.API_BASE_URL:<45}║
║ Timeout:          {self.settings.API_TIMEOUT} segundos{' ' * 35}║
║ Log Level:        {self.settings.LOG_LEVEL:<45}║
║ Entorno:          {self.settings.API_ENV:<45}║
╚═══════════════════════════════════════════════════════════════╝
        """
        print(info)

    def cleanup(self):
        if hasattr(self, 'client'):
            self.client.close()
        self.logger.info("Servicio finalizado")


def launch_gui():
    """Lanza la interfaz gráfica"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        from main_gui import APIAuthGUI

        print("🚀 Iniciando interfaz gráfica...")
        root = tk.Tk()
        app = APIAuthGUI(root)

        # Centrar ventana
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')

        # Cierre seguro
        if hasattr(app, "quit_app"):
            root.protocol("WM_DELETE_WINDOW", app.quit_app)
        else:
            root.protocol("WM_DELETE_WINDOW", root.quit)

        print("✅ Interfaz gráfica lista")
        root.mainloop()

    except ImportError as e:
        print(f"❌ Error: No se pudo cargar main_gui.py\nDetalles: {e}")
        print("\n💡 Usa el modo CLI: python main.py --cli")
        sys.exit(1)


def main():
    """Punto de entrada principal"""
    parser = argparse.ArgumentParser(description='API iFR Pro - Servicio de Autenticación (GUI y CLI)')
    parser.add_argument('--cli', action='store_true', help='Ejecutar en modo CLI')
    parser.add_argument('--mode', choices=['test', 'upload', 'batch', 'interactive'])
    parser.add_argument('--input', help='Directorio o archivo de entrada')
    parser.add_argument('--output', help='Directorio de salida')
    parser.add_argument('--config', help='Archivo de configuración JSON')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    args = parser.parse_args()

    if len(sys.argv) == 1:
        print("🚀 Iniciando interfaz gráfica...")
        launch_gui()
        return

    if args.cli or args.mode:
        settings = Settings()
        logger = setup_logging(args.log_level or settings.LOG_LEVEL, settings.LOG_DIR)
        service = APIAuthService(settings)

        try:
            if args.mode == 'test':
                success = service.test_authentication()
                sys.exit(0 if success else 1)
            elif args.mode == 'upload':
                paths = [args.input] if args.input else None
                success = service.upload_files_example(paths)
                sys.exit(0 if success else 1)
            elif args.mode == 'batch':
                if not args.input:
                    logger.error("❌ Se requiere --input para modo batch")
                    sys.exit(1)
                success = service.batch_process(args.input, args.output)
                sys.exit(0 if success else 1)
            else:
                service.interactive_mode()
        except KeyboardInterrupt:
            logger.info("Interrumpido por el usuario")
        finally:
            service.cleanup()
    else:
        launch_gui()


if __name__ == "__main__":
    main()
