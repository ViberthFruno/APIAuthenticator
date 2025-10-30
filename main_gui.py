#!/usr/bin/env python3
"""
main_gui.py - Interfaz gráfica para el servicio de autenticación API iFR Pro

Este archivo proporciona una interfaz gráfica de usuario (GUI) moderna usando tkinter
para interactuar con el servicio de autenticación API de forma visual e intuitiva.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Añadir api_ifrpro al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api_ifrpro'))

# Cargar variables de entorno
load_dotenv()

from api_ifrpro import APIClient, FileHandler
from config.settings import Settings


class TextHandler(logging.Handler):
    """Handler personalizado para mostrar logs en el widget de texto"""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.see(tk.END)

        self.text_widget.after(0, append)


class APIAuthGUI:
    """Interfaz gráfica principal para el servicio de autenticación API"""

    def __init__(self, root):
        self.root = root
        self.root.title("API iFR Pro - Servicio de Autenticación")
        self.root.geometry("1000x700")

        # Configurar estilo
        self.setup_style()

        # Inicializar configuración
        self.settings = Settings()

        # Configurar logging
        self.setup_logging()

        # Inicializar servicio
        self.client = None
        self.initialize_client()

        # Variables de UI
        self.selected_files = []
        self.selected_directory = None

        # Crear interfaz
        self.create_widgets()

        # Log inicial
        self.log_info("=" * 60)
        self.log_info("API iFR Pro - Servicio de Autenticación Iniciado")
        self.log_info("=" * 60)
        self.show_service_info()

    def setup_style(self):
        """Configura el estilo de la interfaz"""
        style = ttk.Style()
        style.theme_use('clam')

        # Colores personalizados
        style.configure('Title.TLabel',
                        font=('Helvetica', 16, 'bold'),
                        foreground='#2c3e50')

        style.configure('Subtitle.TLabel',
                        font=('Helvetica', 10, 'bold'),
                        foreground='#34495e')

        style.configure('Action.TButton',
                        font=('Helvetica', 10),
                        padding=10)

        style.configure('Success.TLabel',
                        foreground='#27ae60',
                        font=('Helvetica', 9, 'bold'))

        style.configure('Error.TLabel',
                        foreground='#e74c3c',
                        font=('Helvetica', 9, 'bold'))

    def setup_logging(self):
        """Configura el sistema de logging"""
        # Crear directorio de logs si no existe
        os.makedirs(self.settings.LOG_DIR, exist_ok=True)

        # Configurar formato
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        date_format = '%H:%M:%S'

        # Configurar logger raíz
        logging.basicConfig(
            level=getattr(logging, self.settings.LOG_LEVEL),
            format=log_format,
            datefmt=date_format,
            handlers=[
                logging.FileHandler(
                    os.path.join(self.settings.LOG_DIR, 'api_gui.log'),
                    mode='a',
                    encoding='utf-8'
                )
            ]
        )

        # Reducir verbosidad de bibliotecas externas
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('PIL').setLevel(logging.WARNING)

    def initialize_client(self):
        """Inicializa el cliente de API"""
        try:
            self.client = APIClient(
                cuenta_api=self.settings.API_CUENTA,
                llave_api=self.settings.API_LLAVE,
                codigo_servicio=self.settings.API_CODIGO_SERVICIO,
                pais=self.settings.API_PAIS,
                base_url=self.settings.API_BASE_URL,
                timeout=self.settings.API_TIMEOUT,
                verify=self.settings.ENABLE_SSL_VERIFY
            )
            logging.info("Cliente API inicializado correctamente")
        except Exception as e:
            logging.error(f"Error inicializando cliente: {e}")
            messagebox.showerror("Error", f"Error inicializando cliente API:\n{e}")

    def create_widgets(self):
        """Crea todos los widgets de la interfaz"""

        # Frame principal con padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # === SECCIÓN SUPERIOR: TÍTULO E INFORMACIÓN ===
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(
            header_frame,
            text="🔐 API iFR Pro - Servicio de Autenticación",
            style='Title.TLabel'
        ).pack(side=tk.LEFT)

        # Botón de información
        ttk.Button(
            header_frame,
            text="ℹ️ Info",
            command=self.show_service_info,
            width=10
        ).pack(side=tk.RIGHT, padx=5)

        # Estado de conexión
        self.status_label = ttk.Label(
            header_frame,
            text="⚪ No conectado",
            font=('Helvetica', 9)
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # === SECCIÓN MEDIA: BOTONES DE ACCIÓN ===
        actions_frame = ttk.LabelFrame(main_frame, text="Acciones", padding="10")
        actions_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Crear grid de botones
        buttons = [
            ("🔌 Probar Conexión", self.test_authentication, 0, 0),
            ("📄 Subir Archivos de Prueba", self.upload_test_files, 0, 1),
            ("📁 Seleccionar Archivos", self.select_files, 1, 0),
            ("📂 Seleccionar Directorio", self.select_directory, 1, 1),
            ("🚀 Subir Archivos", self.upload_files, 2, 0),
            ("⚙️ Procesar en Lote", self.batch_process, 2, 1),
            ("🗑️ Limpiar Log", self.clear_log, 3, 0),
            ("❌ Salir", self.quit_app, 3, 1)
        ]

        for text, command, row, col in buttons:
            btn = ttk.Button(
                actions_frame,
                text=text,
                command=command,
                style='Action.TButton',
                width=25
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky=(tk.W, tk.E))

        # Configurar columnas para expandir
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)

        # === SECCIÓN INFERIOR: LOG Y ESTADO ===
        log_frame = ttk.LabelFrame(main_frame, text="Registro de Actividad", padding="5")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # Área de texto con scroll
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=100,
            height=20,
            font=('Consolas', 9),
            bg='#2c3e50',
            fg='#ecf0f1',
            insertbackground='white'
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.log_text.configure(state='disabled')

        # Agregar handler de logging al widget de texto
        text_handler = TextHandler(self.log_text)
        text_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        ))
        logging.getLogger().addHandler(text_handler)

        # Barra de progreso
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            length=300
        )
        self.progress.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

    def log_info(self, message):
        """Registra un mensaje de información"""
        logging.info(message)

    def log_error(self, message):
        """Registra un mensaje de error"""
        logging.error(message)

    def log_success(self, message):
        """Registra un mensaje de éxito"""
        logging.info(f"✅ {message}")

    def start_progress(self):
        """Inicia la barra de progreso"""
        self.progress.start(10)

    def stop_progress(self):
        """Detiene la barra de progreso"""
        self.progress.stop()

    def run_in_thread(self, func, *args):
        """Ejecuta una función en un hilo separado"""

        def wrapper():
            try:
                self.start_progress()
                func(*args)
            except Exception as e:
                self.log_error(f"Error: {e}")
                messagebox.showerror("Error", str(e))
            finally:
                self.stop_progress()

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()

    def show_service_info(self):
        """Muestra información del servicio"""
        info = f"""
╔══════════════════════════════════════════════════════════════╗
║              INFORMACIÓN DEL SERVICIO                        ║
╠══════════════════════════════════════════════════════════════╣
║ Cuenta API:        {self.settings.API_CUENTA:<39} ║
║ Servicio:          {self.settings.API_CODIGO_SERVICIO:<39} ║
║ País:              {self.settings.API_PAIS:<39} ║
║ URL Base:          {self.settings.API_BASE_URL:<39} ║
║ Timeout:           {self.settings.API_TIMEOUT} segundos{' ' * 32} ║
║ Log Level:         {self.settings.LOG_LEVEL:<39} ║
║ Entorno:           {self.settings.API_ENV:<39} ║
║ Max Archivos:      {self.settings.MAX_FILES_PER_REQUEST:<39} ║
║ Max Tamaño:        {self.settings.MAX_FILE_SIZE // (1024 * 1024)} MB{' ' * 36} ║
╚══════════════════════════════════════════════════════════════╝
        """
        self.log_info(info)

    def test_authentication(self):
        """Prueba la autenticación con la API"""

        def test():
            self.log_info("🔌 Probando autenticación...")

            try:
                if self.client.health_check():
                    self.log_success("Autenticación exitosa")
                    self.status_label.config(text="🟢 Conectado")
                    messagebox.showinfo("Éxito", "✅ Autenticación exitosa")
                else:
                    self.log_error("Fallo en autenticación")
                    self.status_label.config(text="🔴 Error")
                    messagebox.showerror("Error", "❌ Fallo en autenticación")
            except Exception as e:
                self.log_error(f"Error en autenticación: {e}")
                self.status_label.config(text="🔴 Error")
                messagebox.showerror("Error", f"Error en autenticación:\n{e}")

        self.run_in_thread(test)

    def upload_test_files(self):
        """Crea y sube archivos de prueba"""

        def upload():
            self.log_info("📄 Creando archivos de prueba...")

            # Crear directorio temporal
            test_dir = os.path.join(self.settings.TEMP_DIR, "test_files")
            os.makedirs(test_dir, exist_ok=True)

            try:
                # Crear archivos
                file_paths = FileHandler.create_test_files(
                    directory=test_dir,
                    count={'png': 2, 'jpg': 1, 'jpeg': 1, 'pdf': 1}
                )

                self.log_info(f"✅ Creados {len(file_paths)} archivos de prueba")

                # Preparar datos
                form_data = {
                    "titulo": "Prueba desde GUI",
                    "descripcion": f"Carga de {len(file_paths)} archivos",
                    "usuario": "gui_user",
                    "tipo": "test"
                }

                # Subir archivos
                self.log_info("📤 Subiendo archivos...")
                response = self.client.upload_files(
                    endpoint="/v1/upload",
                    data=form_data,
                    file_paths=file_paths,
                    field_name="archivos"
                )

                if response.status_code == 200:
                    self.log_success("Archivos subidos exitosamente")
                    try:
                        result = response.json()
                        self.log_info(f"Respuesta: {result}")
                    except:
                        self.log_info(f"Respuesta: {response.text[:200]}")

                    messagebox.showinfo("Éxito", "✅ Archivos subidos correctamente")
                else:
                    self.log_error(f"Error en subida: Status {response.status_code}")
                    messagebox.showerror("Error", f"Error: Status {response.status_code}")

            except Exception as e:
                self.log_error(f"Error: {e}")
                messagebox.showerror("Error", str(e))
            finally:
                # Limpiar
                if os.path.exists(test_dir):
                    FileHandler.cleanup_directory(test_dir)
                    self.log_info("🗑️ Archivos temporales eliminados")

        self.run_in_thread(upload)

    def select_files(self):
        """Permite seleccionar archivos para subir"""
        extensions = self.settings.get_allowed_extensions_list()
        filetypes = [
            ("Archivos permitidos", " ".join(f"*{ext}" for ext in extensions)),
            ("Todos los archivos", "*.*")
        ]

        files = filedialog.askopenfilenames(
            title="Seleccionar archivos",
            filetypes=filetypes
        )

        if files:
            self.selected_files = list(files)
            self.log_info(f"📁 Seleccionados {len(self.selected_files)} archivos:")
            for f in self.selected_files:
                self.log_info(f"   - {os.path.basename(f)}")
            messagebox.showinfo("Archivos Seleccionados",
                                f"✅ {len(self.selected_files)} archivos seleccionados")

    def select_directory(self):
        """Permite seleccionar un directorio"""
        directory = filedialog.askdirectory(
            title="Seleccionar directorio"
        )

        if directory:
            self.selected_directory = directory

            # Contar archivos válidos
            extensions = self.settings.get_allowed_extensions_list()
            count = 0
            for file in os.listdir(directory):
                if any(file.lower().endswith(ext) for ext in extensions):
                    count += 1

            self.log_info(f"📂 Directorio seleccionado: {directory}")
            self.log_info(f"   Archivos válidos encontrados: {count}")
            messagebox.showinfo("Directorio Seleccionado",
                                f"✅ Directorio: {os.path.basename(directory)}\n"
                                f"Archivos válidos: {count}")

    def upload_files(self):
        """Sube los archivos seleccionados"""
        if not self.selected_files:
            messagebox.showwarning("Advertencia", "⚠️ No hay archivos seleccionados")
            return

        def upload():
            self.log_info(f"📤 Subiendo {len(self.selected_files)} archivos...")

            try:
                # Preparar datos
                form_data = {
                    "titulo": "Carga desde GUI",
                    "descripcion": f"Subida de {len(self.selected_files)} archivos",
                    "usuario": "gui_user",
                    "origen": "manual"
                }

                # Subir
                response = self.client.upload_files(
                    endpoint="/v1/upload",
                    data=form_data,
                    file_paths=self.selected_files,
                    field_name="archivos"
                )

                if response.status_code == 200:
                    self.log_success("Archivos subidos exitosamente")
                    try:
                        result = response.json()
                        self.log_info(f"Respuesta: {result}")
                    except:
                        self.log_info(f"Respuesta: {response.text[:200]}")

                    messagebox.showinfo("Éxito", "✅ Archivos subidos correctamente")
                    self.selected_files = []
                else:
                    self.log_error(f"Error: Status {response.status_code}")
                    messagebox.showerror("Error", f"Error: Status {response.status_code}")

            except Exception as e:
                self.log_error(f"Error: {e}")
                messagebox.showerror("Error", str(e))

        self.run_in_thread(upload)

    def batch_process(self):
        """Procesa archivos en lote desde el directorio seleccionado"""
        if not self.selected_directory:
            messagebox.showwarning("Advertencia",
                                   "⚠️ No hay directorio seleccionado")
            return

        def process():
            self.log_info(f"⚙️ Procesando archivos en lote desde: {self.selected_directory}")

            try:
                # Buscar archivos
                extensions = self.settings.get_allowed_extensions_list()
                file_paths = []

                for file in os.listdir(self.selected_directory):
                    file_path = os.path.join(self.selected_directory, file)
                    if os.path.isfile(file_path):
                        if any(file_path.lower().endswith(ext) for ext in extensions):
                            file_paths.append(file_path)

                if not file_paths:
                    self.log_error("No se encontraron archivos válidos")
                    messagebox.showwarning("Advertencia",
                                           "⚠️ No se encontraron archivos válidos")
                    return

                self.log_info(f"📊 Encontrados {len(file_paths)} archivos")

                # Procesar en lotes
                batch_size = self.settings.BATCH_SIZE
                success_count = 0

                for i in range(0, len(file_paths), batch_size):
                    batch = file_paths[i:i + batch_size]
                    batch_num = i // batch_size + 1

                    self.log_info(f"📦 Procesando lote {batch_num}: {len(batch)} archivos")

                    form_data = {
                        "lote": str(batch_num),
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
                        self.log_success(f"Lote {batch_num} procesado")
                    else:
                        self.log_error(f"Error en lote {batch_num}: Status {response.status_code}")

                # Resumen
                self.log_info("=" * 60)
                self.log_info(f"✅ Procesamiento completado: {success_count}/{len(file_paths)} archivos")
                self.log_info("=" * 60)

                messagebox.showinfo("Completado",
                                    f"✅ Procesamiento completado\n"
                                    f"Exitosos: {success_count}/{len(file_paths)}")

            except Exception as e:
                self.log_error(f"Error: {e}")
                messagebox.showerror("Error", str(e))

        self.run_in_thread(process)

    def clear_log(self):
        """Limpia el área de log"""
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        self.log_info("=" * 60)
        self.log_info("Log limpiado")
        self.log_info("=" * 60)

    def quit_app(self):
        """Cierra la aplicación"""
        if messagebox.askokcancel("Salir", "¿Desea cerrar la aplicación?"):
            self.log_info("👋 Cerrando aplicación...")
            if self.client:
                self.client.close()
            self.root.quit()


def main():
    """Función principal para ejecutar la GUI"""
    root = tk.Tk()
    app = APIAuthGUI(root)

    # Centrar ventana
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    # Manejar cierre de ventana
    root.protocol("WM_DELETE_WINDOW", app.quit_app)

    # Iniciar loop
    root.mainloop()


if __name__ == "__main__":
    main()