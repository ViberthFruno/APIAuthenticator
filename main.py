import os
from dotenv import load_dotenv
import sys
import argparse
import logging
from typing import List
import json

# Añadir api_ifrpro al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api_ifrpro'))

# Cargar las variables del archivo .env
load_dotenv()

from api_ifrpro import APIClient, FileHandler
from config.settings import Settings


def setup_logging(level: str, log_dir: str):
    """Configura el sistema de logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(log_dir,'api_auth.log'), mode='a', encoding='utf-8')
        ]
    )

    # Reducir verbosidad de urllib3
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    return logging.getLogger(__name__)


class APIAuthService:
    """Servicio principal de autenticación API"""

    def __init__(self, settings: Settings):
        """
        Inicializa el servicio

        Args:
            settings: Configuración del servicio
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        # Inicializar cliente API
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
        """
        Prueba la autenticación con la API

        Returns:
            True si la autenticación es exitosa
        """
        self.logger.info("Probando autenticación...")

        try:
            # Intentar health check
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
        """
        Ejemplo de subida de archivos

        Args:
            file_paths: Lista de archivos a subir

        Returns:
            True si la subida es exitosa
        """
        self.logger.info("Iniciando ejemplo de subida de archivos...")

        # Si no hay archivos, crear de prueba
        if not file_paths:
            self.logger.info("Creando archivos de prueba...")
            test_dir = "/app/temp/test_files"
            file_paths = FileHandler.create_test_files(
                directory=test_dir,
                count={'png': 2, 'jpg': 1, 'jpeg': 1, 'pdf': 1}
            )

        if not file_paths:
            self.logger.error("No hay archivos para subir")
            return False

        # Preparar datos del formulario
        form_data = {
            "titulo": "Prueba de carga",
            "descripcion": f"Carga de {len(file_paths)} archivos",
            "usuario": "api_test",
            "tipo": "multifile"
        }

        try:
            # Subir archivos
            self.logger.info(f"Subiendo {len(file_paths)} archivos...")

            response = self.client.upload_files(
                endpoint="/v1/upload",
                data=form_data,
                file_paths=file_paths,
                field_name="archivos"
            )

            if response.status_code == 200:
                self.logger.info("✅ Archivos subidos exitosamente")

                # Mostrar respuesta
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
            # Limpiar archivos de prueba
            if "/temp/test_files" in str(file_paths[0] if file_paths else ""):
                FileHandler.cleanup_directory("/app/temp/test_files")
                self.logger.info("Archivos de prueba eliminados")

    def batch_process(self, input_dir: str, output_dir: str = None) -> bool:
        """
        Procesa archivos en lote

        Args:
            input_dir: Directorio de entrada
            output_dir: Directorio de salida (opcional)

        Returns:
            True si el procesamiento es exitoso
        """
        self.logger.info(f"Procesando archivos desde: {input_dir}")

        if not os.path.exists(input_dir):
            self.logger.error(f"Directorio no encontrado: {input_dir}")
            return False

        # Buscar archivos
        extensions = self.settings.ALLOWED_EXTENSIONS.split(',')
        extensions = [f".{ext.strip()}" for ext in extensions]

        file_paths = []
        for file in os.listdir(input_dir):
            file_path = os.path.join(input_dir, file)
            if os.path.isfile(file_path):
                if any(file_path.lower().endswith(ext) for ext in extensions):
                    file_paths.append(file_path)

        if not file_paths:
            self.logger.warning("No se encontraron archivos válidos")
            return False

        self.logger.info(f"Encontrados {len(file_paths)} archivos")

        # Procesar en lotes
        batch_size = 5
        success_count = 0

        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i+batch_size]
            self.logger.info(f"Procesando lote {i//batch_size + 1}: {len(batch)} archivos")

            try:
                form_data = {
                    "lote": f"{i//batch_size + 1}",
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
        """Modo interactivo para pruebas"""
        self.logger.info("Iniciando modo interactivo...")

        while True:
            print("\n" + "="*60)
            print("API Authentication Service - Modo Interactivo")
            print("="*60)
            print("1. Probar autenticación")
            print("2. Subir archivos de prueba")
            print("3. Subir archivos desde directorio")
            print("4. Procesar archivos en lote")
            print("5. Información del servicio")
            print("0. Salir")
            print("-"*60)

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
                        self.batch_process(dir_path)
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
        """Muestra información del servicio"""
        info = f"""
        ╔═══════════════════════════════════════════════════════════════════╗
        ║   API Authentication Service Info                                 ║
        ╠═══════════════════════════════════════════════════════════════════╣
        ║ Cuenta API: {self.settings.API_CUENTA:<29}    ║
        ║ Servicio: {self.settings.API_CODIGO_SERVICIO:<31}                    ║
        ║ País: {self.settings.API_PAIS:<35}                         ║
        ║ URL Base: {self.settings.API_BASE_URL:<31}                 ║
        ║ Timeout: {self.settings.API_TIMEOUT} segundos{' '*23}                       ║
        ║ Log Level: {self.settings.LOG_LEVEL:<30}                         ║
        ║ Entorno: {self.settings.API_ENV:<32}                         ║
        ╚═══════════════════════════════════════════════════════════════════╝
        """
        print(info)

    def cleanup(self):
        """Limpia recursos"""
        if hasattr(self, 'client'):
            self.client.close()
        self.logger.info("Servicio finalizado")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='API Authentication Service')
    parser.add_argument('--mode', choices=['test', 'upload', 'batch', 'interactive'],
                       default='interactive', help='Modo de operación')
    parser.add_argument('--input', help='Directorio o archivos de entrada')
    parser.add_argument('--output', help='Directorio de salida')
    parser.add_argument('--config', help='Archivo de configuración')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        #default='DEBUG',
                          help='Nivel de logging')

    args = parser.parse_args()

    # Cargar configuración
    settings = Settings()

    # Configurar logging
    logger = setup_logging(args.log_level or settings.LOG_LEVEL, settings.LOG_DIR)


    # Actualizar con argumentos de línea de comandos si están presentes
    if args.config:
        settings.load_from_file(args.config)

    # Crear servicio
    service = APIAuthService(settings)

    try:
        # Ejecutar según el modo
        if args.mode == 'test':
            success = service.test_authentication()
            sys.exit(0 if success else 1)

        elif args.mode == 'upload':
            file_paths = []
            if args.input:
                if os.path.isdir(args.input):
                    # Es un directorio
                    for file in os.listdir(args.input):
                        file_path = os.path.join(args.input, file)
                        if os.path.isfile(file_path):
                            file_paths.append(file_path)
                elif os.path.isfile(args.input):
                    # Es un archivo
                    file_paths = [args.input]
                else:
                    # Múltiples archivos separados por comas
                    file_paths = [f.strip() for f in args.input.split(',')]

            success = service.upload_files_example(file_paths)
            sys.exit(0 if success else 1)

        elif args.mode == 'batch':
            if not args.input:
                logger.error("Se requiere --input para modo batch")
                sys.exit(1)

            success = service.batch_process(args.input, args.output)
            sys.exit(0 if success else 1)

        else:  # interactive
            service.interactive_mode()

    except KeyboardInterrupt:
        logger.info("\nInterrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error no manejado: {e}", exc_info=True)
        sys.exit(1)
    finally:
        service.cleanup()


if __name__ == "__main__":
    main()
