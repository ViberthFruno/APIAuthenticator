#!/usr/bin/env python3
"""
main_gui_integrado.py - Interfaz gráfica integrada: API iFR Pro + Bot de Correo
Combina autenticación API con procesamiento automático de correos
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
import threading
import logging
import time
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

# Importar módulos necesarios
try:
    from api_client import APIClient
    from file_handler import FileHandler
    from settings import Settings
    from config_manager import ConfigManager
    from email_manager import EmailManager
    from case_handler import CaseHandler
    from logger import Logger
except ImportError as e:
    print(f"Error importando módulos: {e}")
    print("Asegúrese de que todos los archivos necesarios estén en el directorio")
    sys.exit(1)


class IntegratedGUI:
    """Interfaz gráfica integrada para API y Correo"""

    def __init__(self, root):
        self.root = root
        self.root.title("API iFR Pro + Bot de Correo - Sistema Integrado")
        self.root.geometry("900x600")
        self.root.configure(bg="#f0f0f0")

        # Configurar fuente predeterminada
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Arial", size=10)
        self.root.option_add("*Font", default_font)

        # Variables de control
        self.monitoring = False
        self.monitor_thread = None

        # Inicializar componentes
        self.settings = Settings()
        self.config_manager = ConfigManager()
        self.logger = Logger()
        self.setup_logging()

        # Inicializar clientes
        self.initialize_clients()

        # Crear interfaz
        self.setup_main_frame()
        self.setup_top_panel()
        self.setup_bottom_left_panel()
        self.setup_bottom_right_panel()
        self.initialize_components()

        # Mensaje de bienvenida
        self.logger.log("=" * 60)
        self.logger.log("Sistema Integrado: API iFR Pro + Bot de Correo")
        self.logger.log("=" * 60)

    def setup_logging(self):
        """Configura el sistema de logging"""
        os.makedirs(self.settings.LOG_DIR, exist_ok=True)
        logging.basicConfig(
            level=getattr(logging, self.settings.LOG_LEVEL),
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
            handlers=[
                logging.FileHandler(
                    os.path.join(self.settings.LOG_DIR, 'integrated_gui.log'),
                    mode='a',
                    encoding='utf-8'
                )
            ]
        )

    def initialize_clients(self):
        """Inicializa los clientes de API y correo"""
        try:
            # Cliente API
            self.api_client = APIClient(
                cuenta_api=self.settings.API_CUENTA,
                llave_api=self.settings.API_LLAVE,
                codigo_servicio=self.settings.API_CODIGO_SERVICIO,
                pais=self.settings.API_PAIS,
                base_url=self.settings.API_BASE_URL,
                timeout=self.settings.API_TIMEOUT,
                verify=self.settings.ENABLE_SSL_VERIFY
            )
            logging.info("Cliente API inicializado correctamente")

            # Gestor de correo
            self.email_manager = EmailManager()

            # Manejador de casos
            self.case_handler = CaseHandler()
            logging.info(f"Casos cargados: {self.case_handler.get_available_cases()}")

        except Exception as e:
            logging.error(f"Error inicializando clientes: {e}")
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

        self.logger.set_text_widget(self.log_text)

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
            self.logger.log("Configuración cargada correctamente.")

    # ===== MÉTODOS DE CONFIGURACIÃ“N =====

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
                self.logger.log("Error: Todos los campos son obligatorios", level="ERROR")
                return

            self.logger.log("Probando conexión SMTP e IMAP...")
            smtp_result = self.email_manager.test_smtp_connection(provider, email, password)
            imap_result = self.email_manager.test_imap_connection(provider, email, password)

            if smtp_result and imap_result:
                self.logger.log(f"✅ Conexión exitosa a {provider} (SMTP e IMAP)", level="INFO")
                self.email_status.config(text="Email: Conectado", foreground="green")
            else:
                if not smtp_result:
                    self.logger.log(f"❌ Error en la conexión SMTP a {provider}", level="ERROR")
                if not imap_result:
                    self.logger.log(f"❌ Error en la conexión IMAP a {provider}", level="ERROR")
                self.email_status.config(text="Email: Error", foreground="red")

        def save_config_modal():
            current_config = self.config_manager.load_config()
            current_config.update({
                'provider': provider_var.get(),
                'email': email_var.get(),
                'password': password_var.get()
            })

            if not all([current_config['provider'], current_config['email'], current_config['password']]):
                self.logger.log("Error: Todos los campos son obligatorios para guardar", level="ERROR")
                return

            if self.config_manager.save_config(current_config):
                self.logger.log("✅ Configuración guardada correctamente", level="INFO")
                modal.destroy()
            else:
                self.logger.log("❌ Error al guardar la configuración", level="ERROR")

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
        modal.geometry("400x150")
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

        button_frame = ttk.Frame(params_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=20)

        def save_search_params():
            current_config = self.config_manager.load_config()

            current_config['search_params'] = {
                'caso1': caso1_var.get().strip()
            }

            if self.config_manager.save_config(current_config):
                self.logger.log("✅ Parámetros de búsqueda guardados correctamente", level="INFO")
                modal.destroy()
            else:
                self.logger.log("❌ Error al guardar parámetros de búsqueda", level="ERROR")

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
                self.logger.log("✅ Lista de usuarios CC guardada correctamente.", level="INFO")
                modal.destroy()
            else:
                self.logger.log("❌ Error al guardar la lista de usuarios CC.", level="ERROR")

        save_button = ttk.Button(button_frame, text="Guardar", command=save_cc_users)
        save_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        cancel_button = ttk.Button(button_frame, text="Cancelar", command=modal.destroy)
        cancel_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    # ===== MÉTODOS DE ACCIÃ“N =====

    def test_api_connection(self):
        """Prueba la conexión con la API"""

        def test():
            self.logger.log("Probando conexión API...")
            try:
                if self.api_client.health_check():
                    self.logger.log("✅ Conexión API exitosa", level="INFO")
                    self.api_status.config(text="API: Conectado", foreground="green")
                    messagebox.showinfo("Éxito", "Conexión API exitosa")
                else:
                    self.logger.log("❌ Fallo en conexión API", level="ERROR")
                    self.api_status.config(text="API: Error", foreground="red")
                    messagebox.showerror("Error", "Fallo en conexión API")
            except Exception as e:
                self.logger.log(f"❌ Error en conexión API: {e}", level="ERROR")
                self.api_status.config(text="API: Error", foreground="red")
                messagebox.showerror("Error", f"Error en conexión API:\n{e}")

        threading.Thread(target=test, daemon=True).start()

    def toggle_monitoring(self):
        """Inicia o detiene el monitoreo de emails"""
        if not self.monitoring:
            config = self.config_manager.load_config()
            if not all([config.get('provider'), config.get('email'), config.get('password')]):
                self.logger.log("❌ Error: Configure primero los datos de correo", level="ERROR")
                messagebox.showwarning("Advertencia", "Configure primero el correo")
                return

            search_params = config.get('search_params', {})
            if not search_params.get('caso1', '').strip():
                self.logger.log("❌ Error: Configure primero los parámetros de búsqueda", level="ERROR")
                messagebox.showwarning("Advertencia", "Configure los parámetros de búsqueda")
                return

            self.monitoring = True
            self.monitor_button.config(text="Detener Monitoreo")
            self.status_label.config(text="Estado: Monitoreando", foreground="green")

            self.monitor_thread = threading.Thread(target=self.monitor_emails, daemon=True)
            self.monitor_thread.start()

            self.logger.log("✅ Monitoreo de emails iniciado", level="INFO")
        else:
            self.monitoring = False
            self.monitor_button.config(text="Iniciar Monitoreo")
            self.status_label.config(text="Estado: Detenido", foreground="red")
            self.logger.log("Monitoreo de emails detenido", level="INFO")

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
                    self.logger.log(f"Revisando correos... ({datetime.now().strftime('%H:%M:%S')})")

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
                self.logger.log(f"❌ Error en el monitoreo: {str(e)}", level="ERROR")
                time.sleep(60)

    def buscar_preingreso(self):
        """Busca información de pre-ingreso usando el número de boleta, orden de servicio o guía"""
        numero_boleta = self.boleta_entry.get().strip()

        if not numero_boleta:
            self.log_api_message("❌ Error: Debe ingresar un número de boleta", "ERROR")
            messagebox.showwarning("Advertencia", "Ingrese un número de boleta")
            return

        # Deshabilitar botón mientras se procesa
        self.search_button.config(state=tk.DISABLED)
        self.search_button.config(text="Buscando...")

        # Ejecutar en hilo separado para no bloquear la UI
        def search():
            try:
                self.log_api_message("=" * 60)
                self.log_api_message(f"Buscando Pre-Ingreso: {numero_boleta}")
                self.log_api_message(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.log_api_message("-" * 60)

                # Construir endpoint (sin agregar "0" extra)
                endpoint = f"/v1/reparacion/{numero_boleta}/consultar"

                self.log_api_message(f"📡 Endpoint: {endpoint}")
                self.log_api_message(f"🌐 URL completa: {self.settings.API_BASE_URL}{endpoint}")
                self.log_api_message("")

                # Realizar petición GET
                response = self.api_client.get(endpoint)

                # Log de respuesta
                self.log_api_message(f"📥 Status Code: {response.status_code}")
                self.log_api_message("")

                if response.status_code == 200:
                    self.log_api_message("✅ Respuesta exitosa")
                    self.log_api_message("-" * 60)

                    try:
                        # Intentar parsear JSON
                        data = response.json()
                        import json
                        formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
                        self.log_api_message("📄 Datos recibidos:")
                        self.log_api_message("")
                        self.log_api_message(formatted_json)
                    except Exception as e:
                        # Si no es JSON, mostrar texto plano
                        self.log_api_message("📄 Respuesta (texto plano):")
                        self.log_api_message("")
                        self.log_api_message(response.text)
                else:
                    self.log_api_message(f"⚠️ Error en la respuesta: {response.status_code}")
                    self.log_api_message("")
                    self.log_api_message("📄 Contenido:")
                    self.log_api_message(response.text if response.text else "(vacío)")

                self.log_api_message("")
                self.log_api_message("=" * 60)

            except Exception as e:
                self.log_api_message(f"❌ Error al realizar la petición: {str(e)}", "ERROR")
                self.log_api_message("")
                import traceback
                self.log_api_message("📋 Detalles del error:")
                self.log_api_message(traceback.format_exc())
                self.log_api_message("=" * 60)

            finally:
                # Rehabilitar botón
                self.search_button.config(state=tk.NORMAL)
                self.search_button.config(text="Buscar")

        threading.Thread(target=search, daemon=True).start()

    def log_api_message(self, message, level="INFO"):
        """Escribe un mensaje en el log de API"""
        # Habilitar edición temporal
        self.api_log_text.config(state=tk.NORMAL)

        # Insertar mensaje con timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")

        if level == "ERROR":
            tag = "error"
            self.api_log_text.tag_config(tag, foreground="red")
        elif level == "WARNING":
            tag = "warning"
            self.api_log_text.tag_config(tag, foreground="orange")
        else:
            tag = "info"
            self.api_log_text.tag_config(tag, foreground="black")

        # Agregar mensaje
        if message.startswith("=") or message.startswith("-"):
            # Líneas separadoras sin timestamp
            self.api_log_text.insert(tk.END, f"{message}\n", tag)
        else:
            self.api_log_text.insert(tk.END, f"{message}\n", tag)

        # Scroll al final
        self.api_log_text.see(tk.END)

        # Deshabilitar edición
        self.api_log_text.config(state=tk.DISABLED)

    def quit_app(self):
        """Cierra la aplicación de forma segura"""
        if self.monitoring:
            if messagebox.askyesno(
                    "Confirmar",
                    "El monitoreo está activo. ¿Desea detenerlo y salir?"
            ):
                self.monitoring = False
                time.sleep(1)
                self.root.quit()
        else:
            self.root.quit()

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

        # Procesar PDF en un hilo separado
        def procesar():
            try:
                # Leer el archivo PDF
                with open(archivo_pdf, 'rb') as f:
                    pdf_content = f.read()

                self.log_api_message(f"📊 Tamaño del archivo: {len(pdf_content):,} bytes")

                # Extraer texto del PDF
                self.log_api_message("🔍 Extrayendo datos del PDF...")
                datos_extraidos = self.extraer_datos_boleta_pdf(pdf_content)

                if not datos_extraidos:
                    self.log_api_message("❌ No se pudieron extraer datos del PDF", "ERROR")
                    messagebox.showerror("Error", "No se pudieron extraer datos del PDF")
                    return

                # Mostrar datos extraídos
                self.log_api_message("✅ Datos extraídos exitosamente:")
                self.log_api_message(f"   • Cliente: {datos_extraidos.get('nombre_cliente', 'N/A')}")
                self.log_api_message(f"   • Teléfono: {datos_extraidos.get('telefono_cliente', 'N/A')}")
                self.log_api_message(f"   • Correo: {datos_extraidos.get('correo_cliente', 'N/A')}")
                self.log_api_message(f"   • Producto: {datos_extraidos.get('descripcion_producto', 'N/A')}")
                self.log_api_message(f"   • Marca: {datos_extraidos.get('marca', 'N/A')}")
                self.log_api_message(f"   • Modelo: {datos_extraidos.get('modelo', 'N/A')}")

                # Abrir formulario de preingreso
                self.root.after(0, lambda: self.abrir_formulario_preingreso(datos_extraidos, archivo_pdf))

            except Exception as e:
                self.log_api_message(f"❌ Error al procesar PDF: {str(e)}", "ERROR")
                import traceback
                self.log_api_message(traceback.format_exc())
                messagebox.showerror("Error", f"Error al procesar PDF:\n{str(e)}")

        threading.Thread(target=procesar, daemon=True).start()

    def extraer_datos_boleta_pdf(self, pdf_content):
        """Extrae datos de un PDF de boleta de reparación"""
        try:
            import io
            import re
            try:
                import pdfplumber
            except ImportError:
                self.logger.log("Instalando pdfplumber...", level="WARNING")
                import subprocess
                subprocess.check_call(['pip', 'install', 'pdfplumber', '--break-system-packages'])
                import pdfplumber

            # Extraer texto del PDF
            pdf_file = io.BytesIO(pdf_content)
            text = ""
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            if not text.strip():
                return None

            # Extraer datos usando regex
            datos = {}

            # Número de transacción
            match = re.search(r'No\.Transaccion:\s*(\S+)', text)
            if match:
                datos['numero_transaccion'] = match.group(1).strip()

            # Número de boleta
            match = re.search(r'No\.\s*Boleta:\s*(\S+)', text)
            if match:
                datos['numero_boleta'] = match.group(1).strip()

            # Fecha
            match = re.search(r'Fecha:\s*(\d{2}/\d{2}/\d{4})', text)
            if match:
                fecha_str = match.group(1).strip()
                # Convertir de DD/MM/YYYY a YYYY-MM-DD
                partes = fecha_str.split('/')
                datos['fecha'] = f"{partes[2]}-{partes[1]}-{partes[0]}"

            # Cliente
            match = re.search(r'C L I E N T E:\s*(.+?)\s+Tel:', text)
            if match:
                datos['nombre_cliente'] = match.group(1).strip()

            # Teléfono del cliente
            match = re.search(r'C L I E N T E:.*?Tel:\s*(\d+)', text)
            if match:
                datos['telefono_cliente'] = match.group(1).strip()

            # Correo electrónico
            match = re.search(r'Correo:\s*([\w\.\-]+@[\w\.\-]+\.\w+)', text)
            if match:
                datos['correo_cliente'] = match.group(1).strip()

            # Dirección
            match = re.search(r'Direcc:\s*(.+?)(?=\n.*?No\. Factura|\nNo\. Factura)', text, re.DOTALL)
            if match:
                direccion = match.group(1).strip()
                direccion = ' '.join(direccion.split())
                datos['direccion_cliente'] = direccion

            # Código del producto
            match = re.search(r'Código:\s*(\d+)', text)
            if match:
                datos['codigo_producto'] = match.group(1).strip()

            # Descripción del producto
            match = re.search(r'Código:\s*\d+\s+([A-Z\s]+?)\s+Serie:', text)
            if match:
                datos['descripcion_producto'] = match.group(1).strip()

            # Serie
            match = re.search(r'Serie:\s*(\S+)', text)
            if match:
                datos['serie'] = match.group(1).strip()

            # Marca
            match = re.search(r'Marca:\s*(\S+)', text)
            if match:
                datos['marca'] = match.group(1).strip()

            # Modelo
            match = re.search(r'Modelo:\s*(.+?)(?=\n|$)', text)
            if match:
                datos['modelo'] = match.group(1).strip()

            # Número de factura
            match = re.search(r'No\.\s*Factura:\s*(\S+)', text)
            if match:
                datos['numero_factura'] = match.group(1).strip()

            # Fecha de compra
            match = re.search(r'Fecha de Compra:\s*(\d{2}/\d{2}/\d{4})', text)
            if match:
                fecha_str = match.group(1).strip()
                partes = fecha_str.split('/')
                datos['fecha_compra'] = f"{partes[2]}-{partes[1]}-{partes[0]}"

            # Daños
            match = re.search(r'D A Ñ O S:\s*(.+?)(?=\n={5,}|\n-{5,}|$)', text, re.DOTALL)
            if match:
                danos = match.group(1).strip()
                danos = ' '.join(danos.split())
                datos['danos'] = danos

            # Sucursal
            match = re.search(r'(\d{3}\s+[\w\-]+)', text)
            if match:
                datos['sucursal'] = match.group(1).strip()

            return datos

        except Exception as e:
            self.logger.log(f"Error extrayendo datos del PDF: {e}", level="ERROR")
            return None

    def abrir_formulario_preingreso(self, datos_extraidos, pdf_path):
        """Abre un formulario para completar y enviar el preingreso"""
        # Crear ventana modal
        modal = tk.Toplevel(self.root)
        modal.title("Crear Preingreso - Completar Datos")
        modal.geometry("700x600")
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
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Título
        ttk.Label(
            scrollable_frame,
            text="Complete los datos faltantes para crear el preingreso",
            font=("Arial", 11, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky="w")

        row = 1

        # Variables para almacenar los datos del formulario
        form_vars = {}

        # DATOS EXTRAÍDOS (solo lectura)
        ttk.Label(scrollable_frame, text="DATOS EXTRAÍDOS DEL PDF", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 5)
        )
        row += 1

        # Mostrar datos extraídos
        datos_mostrar = [
            ("Número de Boleta", datos_extraidos.get('numero_boleta', 'N/A')),
            ("Cliente", datos_extraidos.get('nombre_cliente', 'N/A')),
            ("Teléfono", datos_extraidos.get('telefono_cliente', 'N/A')),
            ("Correo", datos_extraidos.get('correo_cliente', 'N/A')),
            ("Producto", datos_extraidos.get('descripcion_producto', 'N/A')),
            ("Marca", datos_extraidos.get('marca', 'N/A')),
            ("Modelo", datos_extraidos.get('modelo', 'N/A')),
            ("Serie", datos_extraidos.get('serie', 'N/A')),
            ("Daños", datos_extraidos.get('danos', 'N/A')),
        ]

        for label, valor in datos_mostrar:
            ttk.Label(scrollable_frame, text=f"{label}:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
            ttk.Label(scrollable_frame, text=valor, foreground="blue").grid(row=row, column=1, sticky="w", padx=5,
                                                                            pady=2)
            row += 1

        # DATOS FALTANTES (editables)
        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1

        ttk.Label(scrollable_frame, text="COMPLETAR DATOS FALTANTES", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(5, 10)
        )
        row += 1

        # Código de sucursal
        ttk.Label(scrollable_frame, text="*Código Sucursal:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
        form_vars['codigo_sucursal'] = tk.StringVar(value="")
        ttk.Entry(scrollable_frame, textvariable=form_vars['codigo_sucursal'], width=40).grid(
            row=row, column=1, sticky="w", padx=5, pady=5
        )
        row += 1

        # Nota explicativa
        ttk.Label(
            scrollable_frame,
            text="⚠️ Por ahora, esta es una versión simplificada para pruebas.\n"
                 "Complete el código de sucursal para continuar.",
            foreground="orange",
            wraplength=600
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=10)
        row += 1

        # Botones
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)

        def enviar_preingreso():
            codigo_sucursal = form_vars['codigo_sucursal'].get().strip()

            if not codigo_sucursal:
                messagebox.showwarning("Advertencia", "Debe ingresar el código de sucursal")
                return

            self.log_api_message("=" * 60)
            self.log_api_message("Enviando Preingreso a la API...")
            self.log_api_message("=" * 60)
            self.log_api_message(f"Código Sucursal: {codigo_sucursal}")
            self.log_api_message(f"Archivo PDF: {os.path.basename(pdf_path)}")

            # Por ahora solo mostrar mensaje de éxito
            messagebox.showinfo(
                "Información",
                "Función en desarrollo.\n\n"
                "Los datos han sido extraídos correctamente.\n"
            )

            self.log_api_message("✅ Datos preparados para envío (función en desarrollo)")
            self.log_api_message("=" * 60)

            modal.destroy()

        ttk.Button(button_frame, text="✅ Enviar Preingreso", command=enviar_preingreso).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Cancelar", command=modal.destroy).pack(side=tk.LEFT, padx=5)


def main():
    """Función principal"""
    root = tk.Tk()
    app = IntegratedGUI(root)

    # Centrar ventana
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    # Configurar cierre seguro
    root.protocol("WM_DELETE_WINDOW", app.quit_app)

    root.mainloop()


if __name__ == "__main__":
    main()