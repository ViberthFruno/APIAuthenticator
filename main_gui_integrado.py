# main_gui_integrado.py
"""
main_gui_integrado.py - Interfaz gráfica integrada: API iFR Pro + Bot de Correo
Combina autenticación API con procesamiento automático de correos
"""
import tracemalloc
from typing import Any
from api_integration.application.dtos import HealthCheckResult, GetPreingresoOutput, ArchivoAdjunto, DatosExtraidosPDF, \
    CreatePreingresoInput, CreatePreingresoOutput
from api_integration.application.use_cases.crear_preingreso_use_case import CreatePreingresoUseCase
from api_integration.application.use_cases.use_cases import GetPreingresoInput, GetPreingresoUseCase, HealthCheckUseCase
from api_integration.infrastructure.retry_policy import RetryPolicy
from case1 import extract_repair_data, _extract_text_from_pdf
from utils import strip_if_string, formatear_valor

tracemalloc.start()

from dotenv import load_dotenv

from api_integration.domain.entities import ApiCredentials
from api_integration.infrastructure.authenticator_adapter import create_api_authenticator
from api_integration.infrastructure.http_client import create_api_client
from api_integration.infrastructure.api_ifrpro_repository import create_ifrpro_repository

from gui_async_helper import (
    get_async_helper,
    run_async_with_callback
)

# Cargar variables de entorno
load_dotenv()

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
import threading
import time
from datetime import datetime

# Importar módulos necesarios
try:
    from settings import Settings
    from config_manager import ConfigManager
    from email_manager import EmailManager
    from case_handler import CaseHandler
    from logger import setup_logging, LoggerMixin, set_gui_callback
except ImportError as e:
    print(f"Error importando módulos: {e}")
    print("Asegúrese de que todos los archivos necesarios estén en el directorio")

    # Definir variables como None para evitar NameError
    Settings = ConfigManager = None
    EmailManager = CaseHandler = setup_logging = LoggerMixin = None
    sys.exit(1)


class IntegratedGUI(LoggerMixin):
    """Interfaz gráfica integrada para API y Correo"""
    WINDOW_WIDTH = 900
    WINDOW_HEIGHT = 600

    def __init__(self, root, settings):
        self.credentials = None
        self.repository = None
        self.retry_policy = None
        self.case_handler = None
        self.recursos_button = None
        self.preingreso_button = None
        self.marca_button = None
        self.search_button = None
        self.api_config_button = None
        self.cc_users_button = None
        self.search_params_button = None
        self.config_button = None
        self.email_status = None
        self.api_status = None
        self.status_label = None
        self.monitor_button = None
        self.boleta_entry = None
        self.api_log_text = None
        self.top_panel = None
        self.log_text = None
        self.bottom_right_panel = None
        self.bottom_left_panel = None
        self.api_frame = None
        self.main_frame = None
        self.notebook = None
        self.email_manager = None
        self.api_client = None

        self.root = root
        self.root.title("API iFR Pro + Bot de Correo - Sistema Integrado")
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.root.configure(bg="#f0f0f0")

        # Configurar cierre seguro
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

        self._center_window()

        # Configurar fuente predeterminada
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Arial", size=10)
        self.root.option_add("*Font", default_font)

        # Variables de control
        self.monitoring = False
        self.monitor_thread = None

        # Inicializar componentes
        self.settings = settings
        self.config_manager = ConfigManager()

        self.async_helper = get_async_helper()

        # Inicializar clientes
        self.initialize_clients()

        # Crear interfaz
        self.setup_main_frame()
        self.setup_top_panel()
        self.setup_bottom_left_panel()
        self.setup_bottom_right_panel()
        self.initialize_components()

        # Configurar callback de logger para que los logs se muestren en la GUI
        self.setup_logger_gui_callback()

        # Mensaje de bienvenida
        self.logger.info("=" * 60)
        self.logger.info("Sistema Integrado: API iFR Pro + Bot de Correo")
        self.logger.info("=" * 60)

    def _center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def initialize_clients(self):
        """Inicializa los clientes de API y correo"""
        try:
            # Cliente API

            # 1. Configurar credenciales
            self.credentials = ApiCredentials(
                cuenta=self.settings.API_CUENTA,
                llave=self.settings.API_LLAVE,
                codigo_servicio=self.settings.API_CODIGO_SERVICIO,
                pais=self.settings.API_PAIS
            )

            # 3. Crear authenticator
            authenticator = create_api_authenticator()

            # 2. Crear cliente HTTP con políticas
            self.api_client, self.retry_policy, rate_limiter = create_api_client(
                authenticator=authenticator,
                base_url=self.settings.API_BASE_URL,
                timeout=self.settings.API_TIMEOUT,
                verify_ssl=self.settings.ENABLE_SSL_VERIFY,
                max_attempts=self.settings.MAX_RETRIES,
                rate_limit_calls=self.settings.RATE_LIMIT_CALLS
            )

            # 4. Crear repositorio
            self.repository = create_ifrpro_repository(
                api_client=self.api_client,
                authenticator=authenticator,
                credentials=self.credentials,
                base_url=self.settings.API_BASE_URL,
                rate_limiter=rate_limiter
            )

            self.logger.info("Cliente API inicializado correctamente")

            # Gestor de correo
            self.email_manager = EmailManager()

            # Manejador de casos
            self.case_handler = CaseHandler()
            self.logger.info(f"Casos cargados: {self.case_handler.get_available_cases()}")

        except Exception as e:
            self.logger.error(f"Error inicializando clientes: {e}")
            messagebox.showerror("Error", f"Error inicializando sistema:\n{e}")

    def setup_main_frame(self):
        """Configura el marco principal de la aplicación con pestañas"""
        # Crear el notebook (control de pestañas)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Pestaña 1: Panel Principal
        self.main_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="Panel Principal")

        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=2)
        self.main_frame.rowconfigure(1, weight=1)

        # Pestaña 2: API
        self.api_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.api_frame, text="API")

        # Configurar diseño de dos columnas para la pestaña API
        self.api_frame.columnconfigure(0, weight=1)
        self.api_frame.columnconfigure(1, weight=2)
        self.api_frame.rowconfigure(0, weight=1)

        self.setup_api_left_panel()
        self.setup_api_right_panel()

    def setup_top_panel(self):
        """Configura el panel superior principal"""
        self.top_panel = ttk.LabelFrame(self.main_frame, text="Panel Principal")
        self.top_panel.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        self.monitor_button = ttk.Button(
            self.top_panel,
            text="Iniciar Monitoreo",
            command=self.toggle_monitoring
        )
        self.monitor_button.pack(pady=20)

        self.status_label = ttk.Label(self.top_panel, text="Estado: Detenido", foreground="red")
        self.status_label.pack()

        # Indicadores de estado de conexión
        status_frame = ttk.Frame(self.top_panel)
        status_frame.pack(pady=10)

        self.api_status = ttk.Label(
            status_frame,
            text="API: No conectado",
            font=("Arial", 9)
        )
        self.api_status.grid(row=0, column=0, padx=10)

        self.email_status = ttk.Label(
            status_frame,
            text="Email: No conectado",
            font=("Arial", 9)
        )
        self.email_status.grid(row=0, column=1, padx=10)

    def setup_bottom_left_panel(self):
        """Configura el panel inferior izquierdo para configuración"""
        self.bottom_left_panel = ttk.LabelFrame(self.main_frame, text="Configuración")
        self.bottom_left_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.config_button = ttk.Button(
            self.bottom_left_panel,
            text="Configurar Correo",
            command=self.open_email_config_modal
        )
        self.config_button.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self.search_params_button = ttk.Button(
            self.bottom_left_panel,
            text="Parámetros de Búsqueda",
            command=self.open_search_params_modal
        )
        self.search_params_button.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self.cc_users_button = ttk.Button(
            self.bottom_left_panel,
            text="Usuarios Adjuntos (CC)",
            command=self.open_cc_users_modal
        )
        self.cc_users_button.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # Botón para probar conexión API
        self.api_config_button = ttk.Button(
            self.bottom_left_panel,
            text="Probar Conexión API",
            command=self.test_api_connection
        )
        self.api_config_button.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self.bottom_left_panel.columnconfigure(0, weight=1)

    def setup_bottom_right_panel(self):
        """Configura el panel inferior derecho para logs"""
        self.bottom_right_panel = ttk.LabelFrame(self.main_frame, text="Log del Sistema")
        self.bottom_right_panel.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        self.log_text = tk.Text(self.bottom_right_panel, wrap=tk.WORD, height=10, width=40)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(self.bottom_right_panel, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # self.logger.set_text_widget(self.log_text)

    def setup_api_left_panel(self):
        """Configura el panel izquierdo de la pestaña API con controles"""
        left_panel = ttk.LabelFrame(self.api_frame, text="Operaciones API")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Frame para búsqueda de Pre-Ingreso
        search_frame = ttk.LabelFrame(left_panel, text="Buscar Pre-Ingreso", padding="10")
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        # Etiqueta y campo de entrada
        ttk.Label(search_frame, text="Boleta / Orden de Servicio / Guía:").pack(anchor="w", pady=(0, 5))

        self.boleta_entry = ttk.Entry(search_frame, width=30)
        self.boleta_entry.pack(fill=tk.X, pady=(0, 10))

        # Botón de búsqueda
        self.search_button = ttk.Button(
            search_frame,
            text="Buscar",
            command=self.buscar_preingreso
        )
        self.search_button.pack(fill=tk.X)

        # Frame para Preingreso Manual
        preingreso_frame = ttk.LabelFrame(left_panel, text="Crear Preingreso", padding="10")
        preingreso_frame.pack(fill=tk.X, padx=5, pady=5)

        # Botón de preingreso manual
        self.preingreso_button = ttk.Button(
            preingreso_frame,
            text="📄 Preingreso Manual",
            command=self.abrir_preingreso_manual
        )
        self.preingreso_button.pack(fill=tk.X)

        # Frame para Consultar Marca
        marca_frame = ttk.LabelFrame(left_panel, text="Consultar Catálogo", padding="10")
        marca_frame.pack(fill=tk.X, padx=5, pady=5)

        # Botón consultar marca
        self.marca_button = ttk.Button(
            marca_frame,
            text="Consultar Marca",
            command=self.consultar_marca
        )
        self.marca_button.pack(fill=tk.X, pady=(0, 5))

        # Botón consultar recursos
        self.recursos_button = ttk.Button(
            marca_frame,
            text="Consultar Recursos",
            command=self.consultar_recursos
        )
        self.recursos_button.pack(fill=tk.X)

    def setup_api_right_panel(self):
        """Configura el panel derecho de la pestaña API con el log"""
        right_panel = ttk.LabelFrame(self.api_frame, text="Log de Respuestas API")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Crear widget de texto para el log de API
        self.api_log_text = tk.Text(
            right_panel,
            wrap=tk.WORD,
            height=20,
            width=50,
            font=("Courier", 9)
        )
        self.api_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbar para el log
        api_scrollbar = ttk.Scrollbar(right_panel, command=self.api_log_text.yview)
        api_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.api_log_text.config(yscrollcommand=api_scrollbar.set)

        # Estado inicial deshabilitado (solo lectura)
        self.api_log_text.config(state=tk.DISABLED)

    def initialize_components(self):
        """Inicializa componentes adicionales y carga la configuración"""
        config = self.config_manager.load_config()
        if config:
            self.log_api_message("Configuración cargada correctamente.")

    def setup_logger_gui_callback(self):
        """
        Configura el callback del logger para que los mensajes se muestren en la GUI
        Este callback se ejecutará de forma thread-safe usando self.root.after()
        """
        def gui_callback(message: str, level: str):
            """
            Callback que recibe mensajes del logger y los muestra en la GUI
            Se ejecuta de forma thread-safe usando root.after()
            """
            # Usar root.after para ejecutar en el hilo principal de Tkinter
            # Esto es necesario porque el logger puede llamarse desde otros hilos
            try:
                self.root.after(0, self._write_log_to_gui, message, level)
            except Exception:
                # Si hay algún error (ej: la ventana se cerró), ignorarlo
                pass

        # Configurar el callback global del logger
        set_gui_callback(gui_callback)

    def _write_log_to_gui(self, message: str, level: str):
        """
        Escribe un mensaje del logger en los widgets de texto de la GUI
        DEBE ejecutarse en el hilo principal de Tkinter
        """
        try:
            # Habilitar edición temporal
            self.log_text.config(state=tk.NORMAL)

            # Configurar color según nivel
            if level == "ERROR":
                tag = "error"
                self.log_text.tag_config(tag, foreground="#FF0000")
            elif level == "CRITICAL":
                tag = "critical"
                self.log_text.tag_config(tag, foreground="#8B0000")
            elif level == "EXCEPTION":
                tag = "exception"
                self.log_text.tag_config(tag, foreground="#DC143C")
            elif level == "WARNING":
                tag = "warning"
                self.log_text.tag_config(tag, foreground="#FF8C00")
            elif level == "INFO":
                tag = "info"
                self.log_text.tag_config(tag, foreground="#0066CC")
            else:  # DEBUG
                tag = "debug"
                self.log_text.tag_config(tag, foreground="#808080")

            # Agregar mensaje al log del sistema
            self.log_text.insert(tk.END, f"{message}\n", tag)

            # Scroll al final
            self.log_text.see(tk.END)

            # Deshabilitar edición
            self.log_text.config(state=tk.DISABLED)
        except Exception:
            # Si hay algún error (ej: widget destruido), ignorarlo
            pass

    # ===== MÉTODOS DE CONFIGURACIÓN =====

    def open_email_config_modal(self):
        """Abre una ventana modal para la configuración de correo"""
        config = self.config_manager.load_config()

        modal = tk.Toplevel(self.root)
        modal.title("Configuración de Correo")
        modal.geometry("400x250")
        modal.transient(self.root)
        modal.grab_set()
        modal.focus_set()

        # Centrar ventana
        modal.update_idletasks()
        width = modal.winfo_width()
        height = modal.winfo_height()
        x = (modal.winfo_screenwidth() // 2) - (width // 2)
        y = (modal.winfo_screenheight() // 2) - (height // 2)
        modal.geometry(f"{width}x{height}+{x}+{y}")

        config_frame = ttk.Frame(modal, padding="10")
        config_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(config_frame, text="Proveedor de Correo:").grid(row=0, column=0, sticky="w", padx=5, pady=5)

        provider_var = tk.StringVar(value=config.get('provider', 'Gmail'))
        provider_combo = ttk.Combobox(config_frame, textvariable=provider_var)
        provider_combo['values'] = ('Gmail', 'Outlook', 'Yahoo', 'Otro')
        provider_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(config_frame, text="Usuario (email):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        email_var = tk.StringVar(value=config.get('email', ''))
        email_entry = ttk.Entry(config_frame, textvariable=email_var)
        email_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(config_frame, text="Contraseña:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        password_var = tk.StringVar(value=config.get('password', ''))
        password_entry = ttk.Entry(config_frame, textvariable=password_var, show="*")
        password_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        button_frame = ttk.Frame(config_frame)
        button_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=20)

        def test_connection_modal():
            provider = provider_var.get()
            email = email_var.get()
            password = password_var.get()

            if not all([provider, email, password]):
                self.log_api_message("Error: Todos los campos son obligatorios", level="ERROR")
                return

            self.log_api_message("Probando conexión SMTP e IMAP...")
            smtp_result = self.email_manager.test_smtp_connection(provider, email, password)
            imap_result = self.email_manager.test_imap_connection(provider, email, password)

            if smtp_result and imap_result:
                self.log_api_message(f"✅ Conexión exitosa a {provider} (SMTP e IMAP)", level="INFO")
                self.email_status.config(text="Email: Conectado", foreground="green")
            else:
                if not smtp_result:
                    self.log_api_message(f"❌ Error en la conexión SMTP a {provider}", level="ERROR")
                if not imap_result:
                    self.log_api_message(f"❌ Error en la conexión IMAP a {provider}", level="ERROR")
                self.email_status.config(text="Email: Error", foreground="red")

        def save_config_modal():
            current_config = self.config_manager.load_config()
            current_config.update({
                'provider': provider_var.get(),
                'email': email_var.get(),
                'password': password_var.get()
            })

            if not all([current_config['provider'], current_config['email'], current_config['password']]):
                self.log_api_message("Error: Todos los campos son obligatorios para guardar", level="ERROR")
                return

            if self.config_manager.save_config(current_config):
                self.log_api_message("✅ Configuración guardada correctamente", level="INFO")
                modal.destroy()
            else:
                self.log_api_message("❌ Error al guardar la configuración", level="ERROR")

        test_button = ttk.Button(button_frame, text="Probar Conexión", command=test_connection_modal)
        test_button.grid(row=0, column=0, sticky="ew", padx=5)

        save_button = ttk.Button(button_frame, text="Guardar Datos", command=save_config_modal)
        save_button.grid(row=0, column=1, sticky="ew", padx=5)

        cancel_button = ttk.Button(button_frame, text="Cancelar", command=modal.destroy)
        cancel_button.grid(row=0, column=2, sticky="ew", padx=5)

        config_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)

    def open_search_params_modal(self):
        """Abre una ventana modal para configurar parámetros de búsqueda"""
        config = self.config_manager.load_config()
        search_params = config.get('search_params', {})

        modal = tk.Toplevel(self.root)
        modal.title("Parámetros de Búsqueda")
        modal.geometry("400x220")
        modal.transient(self.root)
        modal.grab_set()
        modal.focus_set()

        # Centrar ventana
        modal.update_idletasks()
        width = modal.winfo_width()
        height = modal.winfo_height()
        x = (modal.winfo_screenwidth() // 2) - (width // 2)
        y = (modal.winfo_screenheight() // 2) - (height // 2)
        modal.geometry(f"{width}x{height}+{x}+{y}")

        params_frame = ttk.Frame(modal, padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(params_frame, text="Palabra clave del Caso 1:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        caso1_var = tk.StringVar(value=search_params.get('caso1', ''))
        caso1_entry = ttk.Entry(params_frame, textvariable=caso1_var)
        caso1_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(params_frame, text="Titular de correo (dominio):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        titular_var = tk.StringVar(value=search_params.get('titular_correo', ''))
        titular_entry = ttk.Entry(params_frame, textvariable=titular_var)
        titular_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # Ayuda para el campo titular
        help_label = ttk.Label(
            params_frame,
            text="Ejemplo: @fruno.com (solo procesa correos de ese dominio)",
            font=("Arial", 8),
            foreground="gray"
        )
        help_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 5))

        button_frame = ttk.Frame(params_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=20)

        def save_search_params():
            current_config = self.config_manager.load_config()

            current_config['search_params'] = {
                'caso1': caso1_var.get().strip(),
                'titular_correo': titular_var.get().strip()
            }

            if self.config_manager.save_config(current_config):
                self.log_api_message("✅ Parámetros de búsqueda guardados correctamente", level="INFO")
                modal.destroy()
            else:
                self.log_api_message("❌ Error al guardar parámetros de búsqueda", level="ERROR")

        save_button = ttk.Button(button_frame, text="Guardar", command=save_search_params)
        save_button.grid(row=0, column=0, sticky="ew", padx=5)

        cancel_button = ttk.Button(button_frame, text="Cancelar", command=modal.destroy)
        cancel_button.grid(row=0, column=1, sticky="ew", padx=5)

        params_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

    def open_cc_users_modal(self):
        """Abre una ventana modal para configurar correos en CC"""
        config = self.config_manager.load_config()
        cc_users_list = config.get('cc_users', [])

        modal = tk.Toplevel(self.root)
        modal.title("Configurar Usuarios Adjuntos (CC)")
        modal.geometry("400x300")
        modal.transient(self.root)
        modal.grab_set()
        modal.focus_set()

        # Centrar ventana
        modal.update_idletasks()
        width = modal.winfo_width()
        height = modal.winfo_height()
        x = (modal.winfo_screenwidth() // 2) - (width // 2)
        y = (modal.winfo_screenheight() // 2) - (height // 2)
        modal.geometry(f"{width}x{height}+{x}+{y}")

        cc_frame = ttk.Frame(modal, padding="10")
        cc_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(cc_frame, text="Ingrese los correos a copiar (uno por línea):").pack(anchor="w", padx=5, pady=(0, 5))

        cc_text = tk.Text(cc_frame, wrap=tk.WORD, height=10)
        cc_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        cc_text.insert(tk.END, "\n".join(cc_users_list))

        button_frame = ttk.Frame(cc_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        def save_cc_users():
            emails_text = cc_text.get("1.0", tk.END).strip()
            emails_list = [email.strip() for email in emails_text.split("\n") if email.strip()]

            current_config = self.config_manager.load_config()
            current_config['cc_users'] = emails_list

            if self.config_manager.save_config(current_config):
                self.log_api_message("✅ Lista de usuarios CC guardada correctamente.", level="INFO")
                modal.destroy()
            else:
                self.log_api_message("❌ Error al guardar la lista de usuarios CC.", level="ERROR")

        save_button = ttk.Button(button_frame, text="Guardar", command=save_cc_users)
        save_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        cancel_button = ttk.Button(button_frame, text="Cancelar", command=modal.destroy)
        cancel_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    # ===== MÉTODOS DE ACCIÓN =====

    def test_api_connection(self):
        """Prueba la conexión con la API"""

        self.log_api_message("Probando conexión API...")

        def on_success(result: HealthCheckResult):

            """Callback de éxito"""
            if result.is_healthy:
                self.log_api_message("✅ Conexión API exitosa", level="INFO")
                self.api_status.config(text=f"API: {result.get_message()}", foreground="green")
                messagebox.showinfo(
                    "Éxito",
                    f"✅ Conexión API exitosa\n\n"
                    f"Tiempo de respuesta: {result.response_time_ms:.0f}ms\n"
                    f"Status: {result.status_code}"
                )
            else:
                self.log_api_message(f"❌ Fallo en conexión API: {result.get_message()}", level="ERROR")
                self.api_status.config(text=f"API: {result.get_message()}", foreground="red")
                messagebox.showerror(
                    "Advertencia",
                    f"❌ Error de conexión API\n\n"
                    f"Mensaje: {result.message}\n"
                    f"Tipo: {result.error_type}\n"
                    f"Tiempo: {result.response_time_ms:.0f}ms"
                )

        def on_error(error):
            """Callback de error"""
            error_msg = f"❌ Error inesperado: {str(error)}"
            self.log_api_message(error_msg, level="EXCEPTION")
            self.api_status.config(text="API: Error", foreground="red")
            messagebox.showerror("Error", error_msg)

        policy = RetryPolicy(base_delay=1.0, backoff_factor=2.0, max_delay=10.0)

        use_case = HealthCheckUseCase(
            api_ifrpro_repository=self.repository,
            retry_policy=policy
        )

        # Ejecutar async
        run_async_with_callback(
            use_case.execute(endpoint="/"),
            on_success=on_success,
            on_error=on_error
        )

    def toggle_monitoring(self):
        """Inicia o detiene el monitoreo de emails"""
        if not self.monitoring:
            config = self.config_manager.load_config()
            if not all([config.get('provider'), config.get('email'), config.get('password')]):
                self.log_api_message("❌ Error: Configure primero los datos de correo", level="ERROR")
                messagebox.showwarning("Advertencia", "Configure primero el correo")
                return

            search_params = config.get('search_params', {})
            if not search_params.get('caso1', '').strip():
                self.log_api_message("❌ Error: Configure primero los parámetros de búsqueda", level="ERROR")
                messagebox.showwarning("Advertencia", "Configure los parámetros de búsqueda")
                return

            self.monitoring = True
            self.monitor_button.config(text="Detener Monitoreo")
            self.status_label.config(text="Estado: Monitoreando", foreground="green")

            self.monitor_thread = threading.Thread(target=self.monitor_emails, daemon=True)
            self.monitor_thread.start()

            # Log informativo sobre la configuración activa
            titular_correo = search_params.get('titular_correo', '').strip()
            if titular_correo:
                self.log_api_message(f"✅ Monitoreo iniciado con filtro de dominio: {titular_correo}", level="INFO")
            else:
                self.log_api_message("✅ Monitoreo de emails iniciado (sin filtro de dominio)", level="INFO")
        else:
            self.monitoring = False
            self.monitor_button.config(text="Iniciar Monitoreo")
            self.status_label.config(text="Estado: Detenido", foreground="red")
            self.log_api_message("Monitoreo de emails detenido", level="INFO")

    def monitor_emails(self):
        """Función que se ejecuta en un hilo separado para monitorear emails"""
        while self.monitoring:
            try:
                config = self.config_manager.load_config()
                search_params = config.get('search_params', {})
                cc_list = config.get('cc_users', [])

                search_titles = []
                if search_params.get('caso1', '').strip():
                    search_titles.append(search_params['caso1'].strip())

                if search_titles:
                    self.log_api_message(f"Revisando correos... ({datetime.now().strftime('%H:%M:%S')})")

                    self.email_manager.check_and_process_emails(
                        config['provider'],
                        config['email'],
                        config['password'],
                        search_titles,
                        self.logger,
                        cc_list
                    )

                time.sleep(30)

            except Exception as e:
                self.log_api_message(f"❌ Error en el monitoreo: {str(e)}", level="ERROR")
                time.sleep(60)

    def buscar_preingreso(self):
        """Busca información de pre-ingreso usando el número de boleta, orden de servicio o guía"""
        numero_boleta = self.boleta_entry.get().strip()

        if not numero_boleta:
            self.log_api_message("❌ Error: Debe ingresar un número de boleta", "ERROR")
            messagebox.showwarning("Advertencia", "Ingrese un número de boleta")
            return

        # Deshabilitar botón mientras se procesa
        self.search_button.config(state=tk.DISABLED, text="Buscando...")

        # Definir operación async
        async def search_operation():
            """Operación de búsqueda async"""
            self.log_api_message("=" * 60)
            self.log_api_message(f"Buscando Pre-Ingreso: {numero_boleta}")
            self.log_api_message(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_api_message("-" * 60)

            # Construir endpoint (sin agregar "0" extra)
            endpoint = f"/v1/reparacion/{numero_boleta}/consultar"

            self.log_api_message(f"📡 Endpoint: {endpoint}")
            self.log_api_message(f"🌐 URL completa: {self.settings.API_BASE_URL}{endpoint}")
            self.log_api_message("")

            use_case = GetPreingresoUseCase(self.repository)

            result = await use_case.execute(
                GetPreingresoInput(numero_boleta)
            )

            return result

        # Callbacks
        def on_success(result: GetPreingresoOutput):
            """Callback de éxito"""
            self.log_api_message(f"📥 Status Code: {result.response.status_code}")
            self.log_api_message("")

            if result.found:
                self.log_api_message("✅ Respuesta exitosa")
                try:
                    data = result.response.body
                    import json
                    formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
                    self.log_api_message("📄 Datos recibidos:")
                    self.log_api_message(formatted_json)
                except:
                    self.log_api_message("📄 Respuesta (texto plano):")
                    self.log_api_message(result.response.raw_content)
            else:
                self.log_api_message(f"⚠️ Error: {result.response.status_code}")
                self.log_api_message(result.response.body if result.response.body else "(vacío)")

            self.log_api_message("=" * 60)

            # Rehabilitar botón
            self.search_button.config(state=tk.NORMAL, text="Buscar")

        def on_error(error):
            """Callback de error"""
            self.log_api_message(f"❌ Error: {str(error)}", "ERROR")
            self.log_api_message("=" * 60)

            # Rehabilitar botón
            self.search_button.config(state=tk.NORMAL, text="Buscar")

        # Ejecutar operación async sin bloquear GUI
        run_async_with_callback(
            search_operation(),
            on_success=on_success,
            on_error=on_error
        )

    def consultar_marca(self):
        """Consulta el catálogo de marcas desde la API"""
        self.log_api_message("=" * 60)
        self.log_api_message("🏷️ Consultando Catálogo de Marcas")
        self.log_api_message("=" * 60)

        # Deshabilitar botón mientras se ejecuta
        self.marca_button.config(state=tk.DISABLED, text="Consultando...")

        async def consultar():
            """Operación asíncrona de consulta"""
            self.log_api_message("🔄 Iniciando consulta...")
            endpoint = "/v1/unidad/marca"
            self.log_api_message(f"📡 Endpoint: {endpoint}")
            self.log_api_message(f"🌐 URL completa: {self.settings.API_BASE_URL}{endpoint}")
            self.log_api_message("")

            # Llamar al repositorio
            response = await self.repository.listar_marcas()
            return response

        def on_success(response):
            """Callback de éxito"""
            self.log_api_message(f"📥 Status Code: {response.status_code}")
            self.log_api_message("")

            if response.status_code == 200:
                self.log_api_message("✅ Respuesta exitosa")
                try:
                    data = response.body
                    import json
                    formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
                    self.log_api_message("📄 Datos recibidos:")
                    self.log_api_message(formatted_json)
                except:
                    self.log_api_message("📄 Respuesta (texto plano):")
                    self.log_api_message(response.raw_content)
            else:
                self.log_api_message(f"⚠️ Error: {response.status_code}")
                self.log_api_message(response.body if response.body else "(vacío)")

            self.log_api_message("=" * 60)

            # Rehabilitar botón
            self.marca_button.config(state=tk.NORMAL, text="Consultar Marca")

        def on_error(error):
            """Callback de error"""
            self.log_api_message(f"❌ Error: {str(error)}", "ERROR")
            self.log_api_message("=" * 60)

            # Rehabilitar botón
            self.marca_button.config(state=tk.NORMAL, text="Consultar Marca")

        # Ejecutar operación async
        run_async_with_callback(
            consultar(),
            on_success=on_success,
            on_error=on_error
        )

    def consultar_recursos(self):
        """Consulta recursos iniciales y tipos de dispositivos"""
        self.log_api_message("=" * 60)
        self.log_api_message("📋 Consultando Recursos Iniciales")
        self.log_api_message("=" * 60)

        # Deshabilitar botón
        self.recursos_button.config(state=tk.DISABLED, text="Consultando...")

        async def consultar():
            """Operación asíncrona"""
            self.log_api_message("🔄 Iniciando consulta de recursos...")
            endpoint = "/v1/preingreso/recursos_iniciales"
            self.log_api_message(f"📡 Endpoint: {endpoint}")
            self.log_api_message(f"🌐 URL completa: {self.settings.API_BASE_URL}{endpoint}")
            self.log_api_message("")

            # Llamar al repositorio
            response = await self.repository.listar_recursos_iniciales()

            if response.status_code == 200:
                # Extraer categorías
                categorias = response.body.get("data", {}).get("categorias", [])

                if categorias:
                    # Consultar tipos de dispositivos para cada categoría
                    self.log_api_message(f"\n🔍 Consultando tipos de dispositivos para {len(categorias)} categorías...")

                    tipos_por_categoria = {}
                    for categoria in categorias:
                        categoria_id = categoria.get("categoria_id")
                        if categoria_id:
                            tipos_response = await self.repository.listar_tipos_dispositivo(categoria_id)
                            tipos_por_categoria[categoria_id] = tipos_response

                    return response, tipos_por_categoria

            return response, None

        def on_success(result):
            """Callback de éxito"""
            response, tipos_por_categoria = result

            self.log_api_message(f"📥 Status Code: {response.status_code}")
            self.log_api_message("")

            if response.status_code == 200:
                self.log_api_message("✅ Respuesta exitosa - Recursos Iniciales")
                try:
                    import json
                    formatted_json = json.dumps(response.body, indent=2, ensure_ascii=False)
                    self.log_api_message("📄 Recursos Iniciales:")
                    self.log_api_message(formatted_json)

                    # Mostrar tipos de dispositivos
                    if tipos_por_categoria:
                        self.log_api_message("\n" + "=" * 60)
                        self.log_api_message("📱 Tipos de Dispositivos por Categoría")
                        self.log_api_message("=" * 60)

                        for categoria_id, tipos_response in tipos_por_categoria.items():
                            self.log_api_message(f"\n📂 Categoría ID: {categoria_id}")
                            self.log_api_message(f"   Status Code: {tipos_response.status_code}")

                            if tipos_response.status_code == 200:
                                formatted_tipos = json.dumps(tipos_response.body, indent=2, ensure_ascii=False)
                                self.log_api_message(formatted_tipos)
                            else:
                                self.log_api_message(f"   Error: {tipos_response.body}")

                except:
                    self.log_api_message("📄 Respuesta (texto plano):")
                    self.log_api_message(response.raw_content)
            else:
                self.log_api_message(f"⚠️ Error: {response.status_code}")
                self.log_api_message(response.body if response.body else "(vacío)")

            self.log_api_message("=" * 60)
            self.recursos_button.config(state=tk.NORMAL, text="Consultar Recursos")

        def on_error(error):
            """Callback de error"""
            self.log_api_message(f"❌ Error: {str(error)}", "ERROR")
            self.log_api_message("=" * 60)
            self.recursos_button.config(state=tk.NORMAL, text="Consultar Recursos")

        # Ejecutar operación async
        run_async_with_callback(
            consultar(),
            on_success=on_success,
            on_error=on_error
        )

    def log_api_message(self, message, level="INFO", exc_info=True, **kwargs):

        """Escribe un mensaje en el log de API"""
        # Habilitar edición temporal
        self.log_text.config(state=tk.NORMAL)
        self.api_log_text.config(state=tk.NORMAL)

        if level == "ERROR":
            self.logger.error(message, **kwargs)
            tag = "error"
            self.api_log_text.tag_config(tag, foreground="#FF0000")
            self.log_text.tag_config(tag, foreground="#FF0000")
        elif level == "CRITICAL":
            self.logger.critical(message, **kwargs)
            tag = "critical"
            self.api_log_text.tag_config(tag, foreground="#8B0000")
            self.log_text.tag_config(tag, foreground="#8B0000")
        elif level == "EXCEPTION":
            self.logger.exception(message, exc_info, **kwargs)
            tag = "exception"
            self.api_log_text.tag_config(tag, foreground="#DC143C")
            self.log_text.tag_config(tag, foreground="#DC143C")
        elif level == "WARNING":
            self.logger.warning(message, **kwargs)
            tag = "warning"
            self.api_log_text.tag_config(tag, foreground="#FF8C00")
            self.log_text.tag_config(tag, foreground="#FF8C00")
        elif level == "INFO":
            self.logger.info(message, **kwargs)
            tag = "info"
            self.api_log_text.tag_config(tag, foreground="#0066CC")
            self.log_text.tag_config(tag, foreground="#0066CC")
        else:
            tag = "debug"
            self.logger.debug(message, **kwargs)
            self.api_log_text.tag_config(tag, foreground="#808080")
            self.log_text.tag_config(tag, foreground="#808080")

        # Agregar mensaje
        if message.startswith("=") or message.startswith("-"):
            # Líneas separadoras sin timestamp
            self.api_log_text.insert(tk.END, f"{message}\n", tag)
            self.log_text.insert(tk.END, f"{message}\n", tag)
        else:
            self.api_log_text.insert(tk.END, f"{message}\n", tag)
            self.log_text.insert(tk.END, f"{message}\n", tag)

        # Scroll al final
        self.api_log_text.see(tk.END)
        self.log_text.see(tk.END)

        # Deshabilitar edición
        self.api_log_text.config(state=tk.DISABLED)
        self.log_text.config(state=tk.DISABLED)

    def quit_app(self):
        """Cierra la aplicación de forma segura"""

        # Limpiar callback del logger para evitar errores al cerrar
        set_gui_callback(None)

        # Cerrar cliente httpx
        if hasattr(self, 'api_client'):
            self.api_client.close()

        if self.monitoring:
            if messagebox.askyesno(
                    "Confirmar",
                    "El monitoreo está activo. ¿Desea detenerlo y salir?"
            ):
                self.monitoring = False
                time.sleep(1)

                # Detener async helper
                self.async_helper.stop_loop()

                self.root.quit()
                self.root.destroy()
        else:
            # Detener async helper
            self.async_helper.stop_loop()

            self.root.quit()
            self.root.destroy()

    # ===== MÉTODOS PARA PREINGRESO MANUAL =====

    def abrir_preingreso_manual(self):
        """Abre el diálogo para cargar un PDF y crear un preingreso"""
        from tkinter import filedialog

        self.log_api_message("=" * 60)
        self.log_api_message("Iniciando Preingreso Manual")
        self.log_api_message("=" * 60)

        # Abrir diálogo para seleccionar archivo PDF
        archivo_pdf = filedialog.askopenfilename(
            title="Seleccionar Boleta de Reparación (PDF)",
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")],
            initialdir=os.path.expanduser("~")
        )

        if not archivo_pdf:
            self.log_api_message("❌ No se seleccionó ningún archivo")
            return

        self.log_api_message(f"📄 Archivo seleccionado: {os.path.basename(archivo_pdf)}")

        # ========== CALLBACKS ==========
        def on_success(result: CreatePreingresoOutput):
            """Callback cuando el procesamiento es exitoso"""

            if result.success:
                self.log_api_message("✅ Preingreso creado exitosamente!")
                self.log_api_message(f"   Boleta usada: {result.boleta_usada}")
                self.log_api_message(f"   Preingreso ID: {result.preingreso_id}")
                self.log_api_message(f"   Preingreso Guía: {result.consultar_guia}")
                self.log_api_message(f"   Tipo preingreso: {result.tipo_preingreso_nombre}")
                self.log_api_message(f"   Garantía: {result.garantia_nombre}")
                self.log_api_message(f"   Preingreso link: {result.consultar_reparacion}")
                self.log_api_message(f"   Status: {result.response.status_code}")
                self.log_api_message(f"   Tiempo: {result.response.response_time_ms:.0f}ms")

                if not result.response.body:
                    self.log_api_message("")
                    self.log_api_message("⚠️ La API no devolvió un json válido", "WARNING")
                    self.log_api_message("Raw content:")
                    self.log_api_message(formatear_valor(result.response.raw_content))
                else:
                    # Abrir formulario en el hilo principal de Tkinter
                    self.root.after(0, lambda: self.abrir_formulario_preingreso(
                        result.response.body if result.response else None
                    ))
            else:
                error_msg = f"Error creando preingreso: {result.message}"
                self.log_api_message(f"❌ {formatear_valor(result)}")
                self.log_api_message(f"❌ {error_msg}")
                if result.errors:
                    self.log_api_message("   Errores de validación:")
                    for error in result.errors:
                        self.log_api_message(f"      - {error}")
                # raise RuntimeError(error_msg)

        def on_error(error):
            """Callback cuando hay un error"""
            self.log_api_message(f"❌ Error al procesar el preingreso: {str(error)}", "ERROR")
            import traceback
            self.log_api_message(traceback.format_exc())
            # Mostrar error en el hilo principal de Tkinter
            self.root.after(0, lambda: messagebox.showerror(
                "Error", f"Error al procesar el preingreso:\n{str(error)}"
            ))

        # ========== FUNCIÓN ASÍNCRONA ==========
        async def procesar():
            """Procesa el PDF de forma asíncrona"""

            # Crear referencia al archivo
            archivo_adjunto = ArchivoAdjunto(
                nombre_archivo=os.path.basename(archivo_pdf),
                ruta_archivo=archivo_pdf,
                tipo_mime="application/pdf"
            )

            # Leer el archivo PDF (operación asíncrona)
            pdf_content = await archivo_adjunto.leer_contenido()
            self.log_api_message(f"📊 Tamaño del archivo: {len(pdf_content):,} bytes")

            # Extraer texto del PDF (operación síncrona)
            self.log_api_message("🔍 Extrayendo datos del PDF...")
            datos_extraidos = self.extraer_datos_boleta_pdf(pdf_content)

            if not datos_extraidos:
                raise ValueError("No se pudieron extraer datos del PDF")

            # Crear DTO con los datos extraídos
            datos_pdf = DatosExtraidosPDF(
                numero_boleta=strip_if_string(datos_extraidos.get('numero_boleta', '')),
                referencia=strip_if_string(datos_extraidos.get('referencia', '')),
                nombre_sucursal=strip_if_string(datos_extraidos.get('sucursal', '')),
                numero_transaccion=strip_if_string(datos_extraidos.get('numero_transaccion', '')),
                cliente_nombre=strip_if_string(datos_extraidos.get('nombre_cliente', '')),
                cliente_contacto=strip_if_string(datos_extraidos.get('nombre_contacto', '')),
                cliente_telefono=strip_if_string(datos_extraidos.get('telefono_cliente', '')),
                cliente_correo=strip_if_string(datos_extraidos.get('correo_cliente', '')),
                serie=strip_if_string(datos_extraidos.get('serie', '')),
                garantia_nombre=strip_if_string(datos_extraidos.get('tipo_garantia', '')),
                fecha_compra=strip_if_string(datos_extraidos.get('fecha_compra')),
                factura=strip_if_string(datos_extraidos.get('numero_factura')),
                cliente_cedula=strip_if_string(datos_extraidos.get('cedula_cliente')),
                cliente_direccion=strip_if_string(datos_extraidos.get('direccion_cliente')),
                cliente_telefono2=strip_if_string(datos_extraidos.get('telefono_adicional')),
                fecha_transaccion=strip_if_string(datos_extraidos.get('fecha')),
                transaccion_gestionada_por=strip_if_string(datos_extraidos.get('gestionada_por')),
                telefono_sucursal=strip_if_string(datos_extraidos.get('telefono_sucursal')),
                producto_codigo=strip_if_string(datos_extraidos.get('codigo_producto')),
                producto_descripcion=strip_if_string(datos_extraidos.get('descripcion_producto')),
                marca_nombre=strip_if_string(datos_extraidos.get('marca')),
                modelo_nombre=strip_if_string(datos_extraidos.get('modelo')),
                garantia_fecha=strip_if_string(datos_extraidos.get('fecha_garantia')),
                danos=strip_if_string(datos_extraidos.get('danos')),
                observaciones=strip_if_string(datos_extraidos.get('observaciones')),
                hecho_por=strip_if_string(datos_extraidos.get('hecho_por'))
            )

            # Crear caso de uso
            use_case = CreatePreingresoUseCase(self.repository, self.retry_policy)

            self.log_api_message("Enviando solicitud de crear el preingreso...")

            # Ejecutar caso de uso (operación asíncrona)
            result = await use_case.execute(
                CreatePreingresoInput(
                    datos_pdf=datos_pdf,
                    archivo_adjunto=archivo_adjunto
                )
            )

            return result

        # ========== EJECUTAR ASÍNCRONAMENTE ==========
        run_async_with_callback(
            procesar(),
            on_success=on_success,
            on_error=on_error
        )

    def extraer_datos_boleta_pdf(self, pdf_content):
        """Extrae datos de un PDF de boleta de reparación (con soporte OCR para Oracle Reports)"""
        try:
            # Usar la función optimizada de case1.py que detecta automáticamente
            # si es un PDF de Oracle Reports y aplica OCR si es necesario
            text = _extract_text_from_pdf(pdf_content, self.logger)

            if not text or not text.strip():
                self.log_api_message("No se pudo extraer texto del PDF", level="ERROR")
                return None

            # Extraer datos usando regex (ya optimizado para OCR)
            return extract_repair_data(text, self.logger)

        except Exception as ex:
            self.log_api_message(f"Error extrayendo datos del PDF: {ex}", level="EXCEPTION")
            return None

    def abrir_formulario_preingreso(self, resultado_api: dict[str, Any] | None):
        """Abre un formulario para completar y enviar el preingreso"""
        # Crear ventana modal
        modal = tk.Toplevel(self.root)
        modal.title("Crear Preingreso - Resultado")
        modal.geometry("900x600")
        modal.transient(self.root)
        modal.grab_set()

        # Centrar ventana
        modal.update_idletasks()
        width = modal.winfo_width()
        height = modal.winfo_height()
        x = (modal.winfo_screenwidth() // 2) - (width // 2)
        y = (modal.winfo_screenheight() // 2) - (height // 2)
        modal.geometry(f"{width}x{height}+{x}+{y}")

        # Frame principal con scroll
        main_frame = ttk.Frame(modal, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda ev: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Título
        ttk.Label(
            scrollable_frame,
            text="Preingreso creado",
            font=("Arial", 11, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky="w")

        row = 0

        # Mostrar datos extraídos
        if resultado_api is None or not isinstance(resultado_api, dict):
            self.log_api_message(f"❌ La API no devolvió la clave 'data'", level="ERROR")
            print("Error: La API no devolvió la clave 'data'.")
            print(resultado_api)
            modal.destroy()
            return

        for label, valor in resultado_api.items():
            ttk.Label(
                scrollable_frame,
                text=f"{label.replace('_', ' ').title()}:"
            ).grid(row=row, column=0, sticky="w", padx=5, pady=2)
            ttk.Label(
                scrollable_frame,
                text=formatear_valor(valor),
                foreground="blue"
            ).grid(row=row, column=1, sticky="w", padx=5, pady=2)

            row += 1

        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1


def main():
    """Función principal"""
    try:
        # Crear ventana principal
        root = tk.Tk()

        # Cargar configuración
        settings = Settings()

        # Configurar sistema de logging
        setup_logging(
            log_level=settings.LOG_LEVEL,
            log_dir=settings.LOG_DIR,
            use_json=False
        )

        # Inicializar interfaz gráfica
        app = IntegratedGUI(root, settings)

        # Iniciar loop de eventos
        root.mainloop()

    except KeyboardInterrupt:
        print("\n⚠️  Aplicación interrumpida por el usuario (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
