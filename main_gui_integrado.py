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
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont
import threading
import time
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw

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
        self.distribuidores_button = None
        self.preingreso_button = None
        self.marca_button = None
        self.garantias_button = None
        self.servitotal_button = None
        self.categoria_entry = None
        self.dispositivo_button = None
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

        # Variables para la pestaña de Análisis
        self.analisis_frame = None
        self.analisis_pdf_label = None
        self.analisis_upload_button = None
        self.analisis_canvas = None
        self.analisis_image_label = None
        self.analisis_tree = None
        self.analisis_text_widget = None
        self.analisis_toggle_var = None
        self.current_pdf_data = None
        self.current_ocr_results = None
        self.current_extracted_fields = None
        self.current_image = None
        self.current_photo = None

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

        # Pestaña 3: Análisis OCR
        self.analisis_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analisis_frame, text="Análisis")

        # Configurar diseño de dos columnas para la pestaña Análisis
        self.analisis_frame.columnconfigure(0, weight=1)
        self.analisis_frame.columnconfigure(1, weight=2)
        self.analisis_frame.rowconfigure(0, weight=1)

        self.setup_analisis_left_panel()
        self.setup_analisis_right_panel()

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
            text="Usuarios a Notificar",
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

        # Botón para editar categorías
        self.categorias_button = ttk.Button(
            self.bottom_left_panel,
            text="Editar Categorias",
            command=self.open_categorias_modal
        )
        self.categorias_button.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # Botón para editar proveedores
        self.proveedores_button = ttk.Button(
            self.bottom_left_panel,
            text="Proveedores",
            command=self.open_proveedores_modal
        )
        self.proveedores_button.grid(row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # Botón para configurar mapeos de códigos Servitotal
        self.servitotal_button = ttk.Button(
            self.bottom_left_panel,
            text="Servitotal",
            command=self.open_servitotal_modal
        )
        self.servitotal_button.grid(row=6, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # Botón para gestionar dominios de correo
        self.dominios_button = ttk.Button(
            self.bottom_left_panel,
            text="Dominio",
            command=self.open_dominios_modal
        )
        self.dominios_button.grid(row=7, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

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

        # Botón de preingreso personalizado
        self.preingreso_personalizado_button = ttk.Button(
            preingreso_frame,
            text="✏️ Preingreso Personalizado",
            command=self.abrir_preingreso_personalizado
        )
        self.preingreso_personalizado_button.pack(fill=tk.X, pady=(5, 0))

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
        self.recursos_button.pack(fill=tk.X, pady=(0, 5))

        # Botón consultar distribuidores
        self.distribuidores_button = ttk.Button(
            marca_frame,
            text="Distribuidores",
            command=self.consultar_distribuidores
        )
        self.distribuidores_button.pack(fill=tk.X, pady=(0, 5))

        # Botón consultar garantías
        self.garantias_button = ttk.Button(
            marca_frame,
            text="Garantías",
            command=self.consultar_garantias
        )
        self.garantias_button.pack(fill=tk.X, pady=(0, 10))

        # Campo y botón para consultar dispositivo por categoría
        ttk.Label(marca_frame, text="Categoría Dispositivo ID:").pack(anchor="w", pady=(0, 5))

        self.categoria_entry = ttk.Entry(marca_frame, width=30)
        self.categoria_entry.pack(fill=tk.X, pady=(0, 5))

        # Botón consultar dispositivo
        self.dispositivo_button = ttk.Button(
            marca_frame,
            text="Consultar Dispositivo",
            command=self.consultar_dispositivo
        )
        self.dispositivo_button.pack(fill=tk.X)

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

    def setup_analisis_left_panel(self):
        """Configura el panel izquierdo de la pestaña Análisis con visor de PDF"""
        left_panel = ttk.LabelFrame(self.analisis_frame, text="Visor de PDF")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Botón para subir PDF
        self.analisis_upload_button = ttk.Button(
            left_panel,
            text="📤 Subir PDF",
            command=self.upload_pdf_for_analysis
        )
        self.analisis_upload_button.pack(pady=10, padx=10, fill=tk.X)

        # Frame para la imagen del PDF
        image_frame = ttk.Frame(left_panel)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Canvas para mostrar la imagen con scroll
        self.analisis_canvas = tk.Canvas(image_frame, bg="white")
        self.analisis_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbars para el canvas
        v_scrollbar = ttk.Scrollbar(image_frame, orient=tk.VERTICAL, command=self.analisis_canvas.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar = ttk.Scrollbar(left_panel, orient=tk.HORIZONTAL, command=self.analisis_canvas.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.analisis_canvas.config(
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )

        # Label para mostrar la imagen en el canvas
        self.analisis_image_label = tk.Label(self.analisis_canvas, bg="white")
        self.analisis_canvas.create_window(0, 0, window=self.analisis_image_label, anchor="nw")

    def setup_analisis_right_panel(self):
        """Configura el panel derecho de la pestaña Análisis con tabla de resultados"""
        right_panel = ttk.LabelFrame(self.analisis_frame, text="Análisis OCR")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Frame para el toggle y controles
        controls_frame = ttk.Frame(right_panel)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(controls_frame, text="Mostrar:").pack(side=tk.LEFT, padx=(0, 5))

        # Variable para el toggle
        self.analisis_toggle_var = tk.StringVar(value="campos")

        # Radiobuttons para toggle
        ttk.Radiobutton(
            controls_frame,
            text="Solo Campos Extraídos",
            variable=self.analisis_toggle_var,
            value="campos",
            command=self.update_analisis_table
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            controls_frame,
            text="Todas las Detecciones",
            variable=self.analisis_toggle_var,
            value="todo",
            command=self.update_analisis_table
        ).pack(side=tk.LEFT, padx=5)

        # Frame para la tabla
        table_frame = ttk.Frame(right_panel)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Crear Treeview para mostrar resultados
        columns = ("campo", "valor", "confianza")
        self.analisis_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15
        )

        # Configurar columnas
        self.analisis_tree.heading("campo", text="Campo")
        self.analisis_tree.heading("valor", text="Valor")
        self.analisis_tree.heading("confianza", text="Confianza")

        self.analisis_tree.column("campo", width=150)
        self.analisis_tree.column("valor", width=200)
        self.analisis_tree.column("confianza", width=80)

        # Scrollbar para la tabla
        tree_scrollbar = ttk.Scrollbar(table_frame, command=self.analisis_tree.yview)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.analisis_tree.config(yscrollcommand=tree_scrollbar.set)
        self.analisis_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind evento de click
        self.analisis_tree.bind("<Double-Button-1>", self.on_tree_double_click)

        # Frame para texto completo
        text_frame = ttk.LabelFrame(right_panel, text="Texto Completo Extraído")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.analisis_text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            height=8,
            font=("Courier", 9)
        )
        self.analisis_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        text_scrollbar = ttk.Scrollbar(text_frame, command=self.analisis_text_widget.yview)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.analisis_text_widget.config(yscrollcommand=text_scrollbar.set)

    def upload_pdf_for_analysis(self):
        """Abre diálogo para subir PDF y lo procesa con OCR"""
        file_path = filedialog.askopenfilename(
            title="Seleccionar PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            # Leer el archivo PDF
            with open(file_path, 'rb') as f:
                pdf_data = f.read()

            self.current_pdf_data = pdf_data

            # Mostrar mensaje de procesamiento
            messagebox.showinfo("Procesando", "Procesando PDF con OCR. Esto puede tomar unos momentos...")

            # Procesar PDF con OCR en un thread para no bloquear la GUI
            threading.Thread(
                target=self._process_pdf_analysis,
                args=(pdf_data,),
                daemon=True
            ).start()

        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar PDF:\n{e}")
            self.logger.error(f"Error al cargar PDF: {e}")

    def _process_pdf_analysis(self, pdf_data):
        """Procesa el PDF con OCR (en thread separado)"""
        try:
            # Llamar a la función modificada que retorna coordenadas
            ocr_results, full_text = self._extract_text_from_pdf_with_coords(pdf_data)

            # Extraer campos del texto
            extracted_fields = extract_repair_data(full_text, self.logger)

            # Convertir PDF a imagen para visualización
            pdf_image = self._pdf_to_image(pdf_data)

            # Actualizar GUI en el hilo principal
            self.root.after(0, self._display_analysis_results, ocr_results, full_text, extracted_fields, pdf_image)

        except Exception as e:
            self.root.after(0, messagebox.showerror, "Error", f"Error procesando PDF:\n{e}")
            self.logger.error(f"Error procesando PDF: {e}")

    def _display_analysis_results(self, ocr_results, full_text, extracted_fields, pdf_image):
        """Muestra los resultados del análisis en la GUI"""
        try:
            # Guardar resultados
            self.current_ocr_results = ocr_results
            self.current_extracted_fields = extracted_fields
            self.current_image = pdf_image

            # Mostrar imagen del PDF
            self._display_pdf_image(pdf_image)

            # Mostrar texto completo
            self.analisis_text_widget.config(state=tk.NORMAL)
            self.analisis_text_widget.delete(1.0, tk.END)
            self.analisis_text_widget.insert(1.0, full_text)
            self.analisis_text_widget.config(state=tk.DISABLED)

            # Actualizar tabla
            self.update_analisis_table()

            messagebox.showinfo("Éxito", "PDF procesado correctamente")

        except Exception as e:
            messagebox.showerror("Error", f"Error mostrando resultados:\n{e}")
            self.logger.error(f"Error mostrando resultados: {e}")

    def _display_pdf_image(self, image):
        """Muestra la imagen del PDF en el canvas"""
        try:
            # Redimensionar imagen si es muy grande
            max_width = 600
            max_height = 800

            width, height = image.size
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convertir a PhotoImage
            self.current_photo = ImageTk.PhotoImage(image)

            # Mostrar en el label
            self.analisis_image_label.config(image=self.current_photo)

            # Actualizar región de scroll
            self.analisis_canvas.config(scrollregion=self.analisis_canvas.bbox("all"))

        except Exception as e:
            self.logger.error(f"Error mostrando imagen: {e}")

    def update_analisis_table(self):
        """Actualiza la tabla de análisis según el toggle seleccionado"""
        if not self.current_ocr_results:
            return

        # Limpiar tabla
        for item in self.analisis_tree.get_children():
            self.analisis_tree.delete(item)

        mode = self.analisis_toggle_var.get()

        if mode == "campos":
            # Mostrar solo campos extraídos
            if self.current_extracted_fields:
                for campo, valor in self.current_extracted_fields.items():
                    if valor and str(valor).strip():
                        # Buscar confianza en OCR results
                        confidence = self._find_confidence_for_text(str(valor))
                        self.analisis_tree.insert(
                            "",
                            tk.END,
                            values=(campo, valor, f"{confidence:.2%}" if confidence else "N/A"),
                            tags=(campo,)
                        )
        else:
            # Mostrar todas las detecciones
            for i, detection in enumerate(self.current_ocr_results):
                bbox, text, confidence = detection
                self.analisis_tree.insert(
                    "",
                    tk.END,
                    values=(f"Detección {i+1}", text, f"{confidence:.2%}"),
                    tags=(str(i),)
                )

    def _find_confidence_for_text(self, text):
        """Busca la confianza para un texto en los resultados OCR"""
        if not self.current_ocr_results:
            return None

        text_normalized = text.lower().strip()

        for detection in self.current_ocr_results:
            bbox, ocr_text, confidence = detection
            if ocr_text.lower().strip() in text_normalized or text_normalized in ocr_text.lower().strip():
                return confidence

        return None

    def on_tree_double_click(self, event):
        """Maneja el doble click en la tabla para resaltar área en la imagen"""
        selection = self.analisis_tree.selection()
        if not selection:
            return

        item = self.analisis_tree.item(selection[0])
        values = item['values']
        tags = item['tags']

        if not tags:
            return

        # Obtener el índice o campo
        tag = tags[0]

        # Resaltar en la imagen
        if self.analisis_toggle_var.get() == "todo":
            # Es una detección directa
            try:
                idx = int(tag)
                if idx < len(self.current_ocr_results):
                    detection = self.current_ocr_results[idx]
                    self._highlight_bbox(detection[0])
            except:
                pass
        else:
            # Es un campo extraído, buscar en OCR
            valor = str(values[1])
            self._highlight_text(valor)

    def _highlight_bbox(self, bbox):
        """Resalta un bounding box en la imagen"""
        if not self.current_image:
            return

        try:
            # Crear copia de la imagen
            img = self.current_image.copy()
            draw = ImageDraw.Draw(img)

            # Dibujar rectángulo
            # bbox es [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            points = [(int(p[0]), int(p[1])) for p in bbox]
            draw.polygon(points, outline="red", width=3)

            # Actualizar imagen
            self._display_pdf_image(img)

        except Exception as e:
            self.logger.error(f"Error resaltando bbox: {e}")

    def _highlight_text(self, text):
        """Busca y resalta un texto en la imagen"""
        if not self.current_ocr_results:
            return

        text_normalized = text.lower().strip()

        for detection in self.current_ocr_results:
            bbox, ocr_text, confidence = detection
            if ocr_text.lower().strip() in text_normalized or text_normalized in ocr_text.lower().strip():
                self._highlight_bbox(bbox)
                break

    def _extract_text_from_pdf_with_coords(self, pdf_data):
        """
        Extrae texto del PDF usando OCR con EasyOCR y retorna coordenadas
        Retorna: (ocr_results, full_text)
        - ocr_results: lista de (bbox, text, confidence)
        - full_text: texto completo concatenado
        """
        try:
            import io
            import numpy as np
            from PIL import Image
            import easyocr
            import fitz  # PyMuPDF

            self.logger.info("🤖 Iniciando extracción de texto con OCR (EasyOCR)...")

            # Detectar si hay GPU disponible e inicializar EasyOCR
            try:
                import torch
                gpu_available = torch.cuda.is_available()
                if gpu_available:
                    self.logger.info("🎮 GPU detectado - Inicializando EasyOCR con aceleración GPU...")
                    reader = easyocr.Reader(['es', 'en'], gpu=True)
                else:
                    self.logger.info("💻 GPU no disponible - Inicializando EasyOCR con CPU")
                    reader = easyocr.Reader(['es', 'en'], gpu=False)
            except ImportError:
                self.logger.warning("⚠️ PyTorch no instalado - usando CPU para OCR")
                reader = easyocr.Reader(['es', 'en'], gpu=False)
            except Exception as e:
                self.logger.warning(f"⚠️ Error al detectar GPU: {e} - fallback a CPU")
                reader = easyocr.Reader(['es', 'en'], gpu=False)

            # Abrir PDF con PyMuPDF
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            total_pages = len(pdf_document)
            self.logger.info(f"📄 Documento tiene {total_pages} página(s)")

            all_results = []
            text = ""

            for page_num in range(total_pages):
                self.logger.info(f"🔍 Procesando página {page_num + 1}/{total_pages}...")

                page = pdf_document[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))  # 300 DPI

                # Convertir a numpy array
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)

                # Extraer texto con EasyOCR (detail=1 para obtener coordenadas)
                results = reader.readtext(img_array, detail=1)

                # results es una lista de [bbox, text, confidence]
                for result in results:
                    all_results.append(result)
                    text += result[1] + "\n"

            pdf_document.close()

            self.logger.info(f"✅ OCR completado - {len(all_results)} detecciones, {len(text)} caracteres")

            return all_results, text

        except Exception as e:
            self.logger.exception(f"Error en OCR con coordenadas: {e}")
            return [], ""

    def _pdf_to_image(self, pdf_data):
        """Convierte la primera página del PDF a imagen PIL"""
        try:
            import fitz
            import numpy as np

            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            page = pdf_document[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))

            # Convertir a PIL Image
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            img = Image.fromarray(img_array)

            pdf_document.close()

            return img

        except Exception as e:
            self.logger.error(f"Error convirtiendo PDF a imagen: {e}")
            return None

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
            text="Ejemplo: @fruno.com o múltiples: @fruno.com, @unicomer.com",
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
        """Abre una ventana modal para configurar correos a notificar"""
        config = self.config_manager.load_config()
        cc_users_list = config.get('cc_users', [])

        modal = tk.Toplevel(self.root)
        modal.title("Configurar Usuarios a Notificar")
        modal.geometry("500x450")
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

        # Frame superior: Agregar correo
        add_frame = ttk.Frame(cc_frame)
        add_frame.pack(fill=tk.X, padx=5, pady=(0, 10))

        add_label = ttk.Label(add_frame, text="Agregar Correo:", font=("Segoe UI", 9, "bold"))
        add_label.pack(anchor="w", pady=(0, 5))

        input_frame = ttk.Frame(add_frame)
        input_frame.pack(fill=tk.X)

        email_entry = ttk.Entry(input_frame)
        email_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        def add_email():
            email = email_entry.get().strip()
            if email:
                # Validar que no esté duplicado
                if email not in email_listbox.get(0, tk.END):
                    email_listbox.insert(tk.END, email)
                    email_entry.delete(0, tk.END)
                else:
                    self.log_api_message("⚠️ El correo ya está en la lista.", level="WARNING")
            else:
                self.log_api_message("⚠️ Por favor ingrese un correo válido.", level="WARNING")

        add_button = ttk.Button(input_frame, text="Agregar", command=add_email)
        add_button.pack(side=tk.LEFT)

        # Permitir agregar con Enter
        email_entry.bind('<Return>', lambda e: add_email())

        # Frame central: Lista de usuarios configurados
        list_frame = ttk.Frame(cc_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 10))

        list_label = ttk.Label(list_frame, text="Usuarios Configurados:", font=("Segoe UI", 9, "bold"))
        list_label.pack(anchor="w", pady=(0, 5))

        # Listbox con scrollbar
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        email_listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, selectmode=tk.EXTENDED)
        email_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=email_listbox.yview)

        # Cargar correos existentes
        for email in cc_users_list:
            email_listbox.insert(tk.END, email)

        # Frame de botones de acción
        action_button_frame = ttk.Frame(cc_frame)
        action_button_frame.pack(fill=tk.X, pady=(0, 10))

        def delete_selected():
            selected_indices = email_listbox.curselection()
            if selected_indices:
                # Eliminar desde el final para no afectar los índices
                for index in reversed(selected_indices):
                    email_listbox.delete(index)
            else:
                self.log_api_message("⚠️ Por favor seleccione al menos un correo para eliminar.", level="WARNING")

        def clear_all():
            if email_listbox.size() > 0:
                email_listbox.delete(0, tk.END)
            else:
                self.log_api_message("⚠️ La lista ya está vacía.", level="WARNING")

        delete_button = ttk.Button(action_button_frame, text="Eliminar Seleccionado", command=delete_selected)
        delete_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        clear_button = ttk.Button(action_button_frame, text="Limpiar Todo", command=clear_all)
        clear_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # Frame de botones principales
        button_frame = ttk.Frame(cc_frame)
        button_frame.pack(fill=tk.X)

        def save_cc_users():
            emails_list = list(email_listbox.get(0, tk.END))

            current_config = self.config_manager.load_config()
            current_config['cc_users'] = emails_list

            if self.config_manager.save_config(current_config):
                self.log_api_message("✅ Lista de usuarios a notificar guardada correctamente.", level="INFO")
                modal.destroy()
            else:
                self.log_api_message("❌ Error al guardar la lista de usuarios a notificar.", level="ERROR")

        cancel_button = ttk.Button(button_frame, text="Cancelar", command=modal.destroy)
        cancel_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        save_button = ttk.Button(button_frame, text="Guardar", command=save_cc_users)
        save_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    def open_dominios_modal(self):
        """Abre una ventana modal para configurar dominios de correo"""
        from config_manager import get_dominios_config, save_dominios_config

        # Cargar dominios actuales
        config_data = get_dominios_config()
        dominios_list = config_data.get('dominios', [])

        modal = tk.Toplevel(self.root)
        modal.title("Configurar Dominios de Correo")
        modal.geometry("500x450")
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

        dominios_frame = ttk.Frame(modal, padding="10")
        dominios_frame.pack(fill=tk.BOTH, expand=True)

        # Frame superior: Agregar dominio
        add_frame = ttk.Frame(dominios_frame)
        add_frame.pack(fill=tk.X, padx=5, pady=(0, 10))

        add_label = ttk.Label(add_frame, text="Agregar Dominio:", font=("Segoe UI", 9, "bold"))
        add_label.pack(anchor="w", pady=(0, 5))

        info_label = ttk.Label(add_frame, text="Ingrese el dominio sin @ (ejemplo: gmail.com, fruno.com)",
                               font=("Segoe UI", 8), foreground="gray")
        info_label.pack(anchor="w", pady=(0, 5))

        input_frame = ttk.Frame(add_frame)
        input_frame.pack(fill=tk.X)

        dominio_entry = ttk.Entry(input_frame)
        dominio_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        def add_dominio():
            dominio = dominio_entry.get().strip()
            if dominio:
                # Validar formato básico (no vacío y sin @)
                if '@' in dominio:
                    self.log_api_message("⚠️ El dominio no debe incluir el símbolo @", level="WARNING")
                    return

                # Validar que no esté duplicado
                if dominio not in dominio_listbox.get(0, tk.END):
                    dominio_listbox.insert(tk.END, dominio)
                    dominio_entry.delete(0, tk.END)
                else:
                    self.log_api_message("⚠️ El dominio ya está en la lista.", level="WARNING")
            else:
                self.log_api_message("⚠️ Por favor ingrese un dominio válido.", level="WARNING")

        add_button = ttk.Button(input_frame, text="Agregar", command=add_dominio)
        add_button.pack(side=tk.LEFT)

        # Permitir agregar con Enter
        dominio_entry.bind('<Return>', lambda e: add_dominio())

        # Frame central: Lista de dominios configurados
        list_frame = ttk.Frame(dominios_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 10))

        list_label = ttk.Label(list_frame, text="Dominios Configurados:", font=("Segoe UI", 9, "bold"))
        list_label.pack(anchor="w", pady=(0, 5))

        # Listbox con scrollbar
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        dominio_listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, selectmode=tk.EXTENDED)
        dominio_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=dominio_listbox.yview)

        # Cargar dominios existentes
        for dominio in dominios_list:
            dominio_listbox.insert(tk.END, dominio)

        # Frame de botones de acción
        action_button_frame = ttk.Frame(dominios_frame)
        action_button_frame.pack(fill=tk.X, pady=(0, 10))

        def delete_selected():
            selected_indices = dominio_listbox.curselection()
            if selected_indices:
                # Eliminar desde el final para no afectar los índices
                for index in reversed(selected_indices):
                    dominio_listbox.delete(index)
            else:
                self.log_api_message("⚠️ Por favor seleccione al menos un dominio para eliminar.", level="WARNING")

        def clear_all():
            if dominio_listbox.size() > 0:
                dominio_listbox.delete(0, tk.END)
            else:
                self.log_api_message("⚠️ La lista ya está vacía.", level="WARNING")

        delete_button = ttk.Button(action_button_frame, text="Eliminar Seleccionado", command=delete_selected)
        delete_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        clear_button = ttk.Button(action_button_frame, text="Limpiar Todo", command=clear_all)
        clear_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # Frame de botones principales
        button_frame = ttk.Frame(dominios_frame)
        button_frame.pack(fill=tk.X)

        def save_dominios():
            dominios_list = list(dominio_listbox.get(0, tk.END))

            config_data = {
                'dominios': dominios_list
            }

            if save_dominios_config(config_data):
                self.log_api_message("✅ Lista de dominios guardada correctamente.", level="INFO")
                modal.destroy()
            else:
                self.log_api_message("❌ Error al guardar la lista de dominios.", level="ERROR")

        cancel_button = ttk.Button(button_frame, text="Cancelar", command=modal.destroy)
        cancel_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        save_button = ttk.Button(button_frame, text="Guardar", command=save_dominios)
        save_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    def open_categorias_modal(self):
        """Abre una ventana modal para configurar las categorías y sus palabras clave"""
        import json
        import os
        from config_manager import ConfigManager

        # Usar ConfigManager para manejar el archivo de categorías
        categorias_manager = ConfigManager()

        # Cargar configuración de categorías (crea el archivo si no existe)
        config_data = categorias_manager.load_categorias_config()
        categorias_guardadas = config_data.get('categorias', {})

        # Categorías hardcodeadas (solo categoria_id, sin tipo_dispositivo_id)
        categorias_hardcoded = {
            "Móviles": {"id": 1, "palabras_clave": []},
            "Hogar": {"id": 3, "palabras_clave": []},
            "Cómputo": {"id": 4, "palabras_clave": []},
            "Desconocido": {"id": 5, "palabras_clave": []},
            "Accesorios": {"id": 6, "palabras_clave": []},
            "Transporte": {"id": 7, "palabras_clave": []},
            "Seguridad": {"id": 8, "palabras_clave": []},
            "Entretenimiento": {"id": 10, "palabras_clave": []},
            "Telecomunicaciones": {"id": 11, "palabras_clave": []},
            "No encontrado": {"id": 12, "palabras_clave": []}
        }

        # Tipos de dispositivo hardcodeados para el dropdown
        tipos_dispositivo = {
            "Celulares y Tablets": 1,
            "Monitores": 2,
            "Cocinas": 3,
            "Refrigeradoras": 4,
            "Licuadoras": 6,
            "Desconocido": 7,
            "Audífonos": 8,
            "Relojes": 9,
            "Cubo": 11,
            "Proyector": 13,
            "Parlante": 15,
            "Mouse": 16,
            "Scooter": 17,
            "Robot de Limpieza": 18,
            "Pantallas": 19,
            "Impresora": 20,
            "Laptop": 21,
            "Cámaras de seguridad": 23,
            "Router": 24,
            "Drones": 25,
            "Baterías": 26,
            "Gaming": 27,
            "Teclado": 28,
            "Estuches": 29,
            "Audio/video": 32,
            "Internet Satelital": 33,
            "Tarjeta de memoria externa": 34,
            "No encontrado": 36
        }

        # Función helper para obtener nombre de tipo de dispositivo por ID
        def get_tipo_dispositivo_nombre(tipo_id):
            """Retorna el nombre del tipo de dispositivo dado su ID"""
            for nombre, id_valor in tipos_dispositivo.items():
                if id_valor == tipo_id:
                    return nombre
            return "Desconocido"

        # Importar palabras clave de las categorías guardadas
        for nombre_cat, datos_cat in categorias_guardadas.items():
            if nombre_cat in categorias_hardcoded:
                palabras_guardadas = datos_cat.get('palabras_clave', [])
                # Mantener el formato completo con tipo_dispositivo_id
                palabras_completas = []
                for palabra_data in palabras_guardadas:
                    if isinstance(palabra_data, str):
                        # Si es string simple, convertir a formato completo con tipo_dispositivo_id por defecto
                        palabras_completas.append({"palabra": palabra_data, "tipo_dispositivo_id": 7})
                    elif isinstance(palabra_data, dict):
                        # Si ya tiene el formato correcto, mantenerlo
                        palabras_completas.append(palabra_data)
                categorias_hardcoded[nombre_cat]['palabras_clave'] = palabras_completas

        # Usar las categorías hardcodeadas
        categorias_dict = categorias_hardcoded

        # Crear ventana modal
        modal = tk.Toplevel(self.root)
        modal.title("Configurar Categorías")
        modal.geometry("800x500")
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

        # Frame principal con dos paneles
        main_frame = ttk.Frame(modal, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Panel izquierdo: Lista de categorías
        left_frame = ttk.LabelFrame(main_frame, text="Categorías", padding="10")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Listbox para categorías
        categorias_listbox = tk.Listbox(left_frame, height=15, width=25)
        categorias_listbox.pack(fill=tk.BOTH, expand=True)

        # Scroll para listbox de categorías
        scrollbar_cat = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=categorias_listbox.yview)
        scrollbar_cat.pack(side=tk.RIGHT, fill=tk.Y)
        categorias_listbox.config(yscrollcommand=scrollbar_cat.set)

        # Panel derecho: Palabras clave de la categoría seleccionada
        right_frame = ttk.LabelFrame(main_frame, text="Palabras Clave", padding="10")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # Label con información de la categoría seleccionada
        info_label = ttk.Label(right_frame, text="Selecciona una categoría", font=("Arial", 10, "bold"))
        info_label.pack(pady=(0, 10))

        # Listbox para palabras clave
        palabras_listbox = tk.Listbox(right_frame, height=12, width=40)
        palabras_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Scroll para listbox de palabras
        scrollbar_pal = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=palabras_listbox.yview)
        scrollbar_pal.pack(side=tk.RIGHT, fill=tk.Y)
        palabras_listbox.config(yscrollcommand=scrollbar_pal.set)

        # Frame para botones de palabras clave
        palabras_buttons_frame = ttk.Frame(right_frame)
        palabras_buttons_frame.pack(fill=tk.X)

        # Variables para tracking
        categoria_seleccionada = [None]  # Usar lista para mutabilidad en closures

        def cargar_categorias():
            """Carga la lista de categorías en el listbox"""
            categorias_listbox.delete(0, tk.END)
            for nombre_cat in categorias_dict.keys():
                categoria_id = categorias_dict[nombre_cat].get('id', '?')
                categorias_listbox.insert(tk.END, f"{nombre_cat} (ID: {categoria_id})")

        def on_categoria_select(event):
            """Maneja la selección de una categoría"""
            selection = categorias_listbox.curselection()
            if not selection:
                return

            idx = selection[0]
            categoria_texto = categorias_listbox.get(idx)
            # Extraer el nombre de la categoría (antes del " (ID:")
            nombre_categoria = categoria_texto.split(" (ID:")[0]
            categoria_seleccionada[0] = nombre_categoria

            # Actualizar label de información
            categoria_id = categorias_dict[nombre_categoria].get('id', '?')
            info_label.config(text=f"Categoría: {nombre_categoria} (ID: {categoria_id})")

            # Cargar palabras clave de esta categoría
            palabras_listbox.delete(0, tk.END)
            palabras_clave = categorias_dict[nombre_categoria].get('palabras_clave', [])

            # Mostrar palabras clave con tipo de dispositivo
            for palabra_data in palabras_clave:
                if isinstance(palabra_data, dict):
                    palabra = palabra_data.get('palabra', '')
                    tipo_id = palabra_data.get('tipo_dispositivo_id', 7)
                    tipo_nombre = get_tipo_dispositivo_nombre(tipo_id)
                    palabras_listbox.insert(tk.END, f"{palabra} - {tipo_nombre}")
                else:
                    # Backward compatibility para strings simples
                    palabras_listbox.insert(tk.END, f"{palabra_data} - Desconocido")

        def agregar_palabra():
            """Agrega una nueva palabra clave a la categoría seleccionada"""
            if not categoria_seleccionada[0]:
                messagebox.showwarning("Advertencia", "Selecciona primero una categoría")
                return

            # Crear ventana para ingresar la palabra
            palabra_modal = tk.Toplevel(modal)
            palabra_modal.title("Agregar Palabra Clave")
            palabra_modal.geometry("450x200")
            palabra_modal.transient(modal)
            palabra_modal.grab_set()

            # Centrar ventana
            palabra_modal.update_idletasks()
            pw = palabra_modal.winfo_width()
            ph = palabra_modal.winfo_height()
            px = (palabra_modal.winfo_screenwidth() // 2) - (pw // 2)
            py = (palabra_modal.winfo_screenheight() // 2) - (ph // 2)
            palabra_modal.geometry(f"{pw}x{ph}+{px}+{py}")

            # Frame
            frame = ttk.Frame(palabra_modal, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            # Entrada de palabra clave
            ttk.Label(frame, text="Nueva palabra clave:").grid(row=0, column=0, sticky="w", pady=(0, 15))
            entrada = ttk.Entry(frame, width=30)
            entrada.grid(row=0, column=1, pady=(0, 15), padx=(10, 0), sticky="ew")
            entrada.focus_set()

            # Dropdown de tipo de dispositivo
            ttk.Label(frame, text="Tipo de dispositivo:").grid(row=1, column=0, sticky="w", pady=(0, 15))
            tipos_nombres = sorted(tipos_dispositivo.keys())
            tipo_combo = ttk.Combobox(frame, values=tipos_nombres, state="readonly", width=28)
            tipo_combo.grid(row=1, column=1, pady=(0, 15), padx=(10, 0), sticky="ew")
            tipo_combo.set("Desconocido")  # Valor por defecto

            def guardar_palabra():
                palabra = entrada.get().strip().upper()  # Convertir a mayúsculas
                if not palabra:
                    messagebox.showwarning("Advertencia", "La palabra clave no puede estar vacía")
                    return

                tipo_nombre = tipo_combo.get()
                tipo_id = tipos_dispositivo.get(tipo_nombre, 7)

                # Agregar a la categoría con formato completo
                palabra_completa = {
                    "palabra": palabra,
                    "tipo_dispositivo_id": tipo_id
                }
                categorias_dict[categoria_seleccionada[0]]['palabras_clave'].append(palabra_completa)

                # Actualizar listbox
                palabras_listbox.insert(tk.END, f"{palabra} - {tipo_nombre}")
                palabra_modal.destroy()

            button_frame = ttk.Frame(frame)
            button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))

            ttk.Button(button_frame, text="Guardar", command=guardar_palabra).pack(side=tk.LEFT, expand=True, padx=5)
            ttk.Button(button_frame, text="Cancelar", command=palabra_modal.destroy).pack(side=tk.LEFT, expand=True,
                                                                                          padx=5)

            frame.columnconfigure(1, weight=1)

            # Permitir Enter para guardar
            entrada.bind('<Return>', lambda e: guardar_palabra())

        def eliminar_palabra():
            """Elimina la palabra clave seleccionada"""
            if not categoria_seleccionada[0]:
                messagebox.showwarning("Advertencia", "Selecciona primero una categoría")
                return

            selection = palabras_listbox.curselection()
            if not selection:
                messagebox.showwarning("Advertencia", "Selecciona una palabra clave para eliminar")
                return

            idx = selection[0]
            palabra_display = palabras_listbox.get(idx)

            # Confirmar eliminación
            if messagebox.askyesno("Confirmar", f"¿Eliminar la palabra clave '{palabra_display}'?"):
                # Eliminar de la lista en memoria usando el índice directamente
                palabras_clave = categorias_dict[categoria_seleccionada[0]]['palabras_clave']

                # Eliminar por índice ya que el índice del listbox coincide con el índice del array
                if idx < len(palabras_clave):
                    palabras_clave.pop(idx)

                palabras_listbox.delete(idx)

        def editar_palabra():
            """Edita la palabra clave seleccionada"""
            if not categoria_seleccionada[0]:
                messagebox.showwarning("Advertencia", "Selecciona primero una categoría")
                return

            selection = palabras_listbox.curselection()
            if not selection:
                messagebox.showwarning("Advertencia", "Selecciona una palabra clave para editar")
                return

            idx = selection[0]
            palabra_display = palabras_listbox.get(idx)

            # Obtener los datos actuales de la palabra
            palabras_clave = categorias_dict[categoria_seleccionada[0]]['palabras_clave']
            palabra_data = palabras_clave[idx]

            # Extraer valores actuales
            if isinstance(palabra_data, dict):
                palabra_actual = palabra_data.get('palabra', '')
                tipo_id_actual = palabra_data.get('tipo_dispositivo_id', 7)
            else:
                palabra_actual = palabra_data
                tipo_id_actual = 7

            # Crear ventana para editar
            editar_modal = tk.Toplevel(modal)
            editar_modal.title("Editar Palabra Clave")
            editar_modal.geometry("450x200")
            editar_modal.transient(modal)
            editar_modal.grab_set()

            # Centrar ventana
            editar_modal.update_idletasks()
            ew = editar_modal.winfo_width()
            eh = editar_modal.winfo_height()
            ex = (editar_modal.winfo_screenwidth() // 2) - (ew // 2)
            ey = (editar_modal.winfo_screenheight() // 2) - (eh // 2)
            editar_modal.geometry(f"{ew}x{eh}+{ex}+{ey}")

            # Frame
            frame = ttk.Frame(editar_modal, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            # Entrada para editar la palabra
            ttk.Label(frame, text="Editar palabra clave:").grid(row=0, column=0, sticky="w", pady=(0, 15))
            entrada = ttk.Entry(frame, width=30)
            entrada.insert(0, palabra_actual)
            entrada.grid(row=0, column=1, pady=(0, 15), padx=(10, 0), sticky="ew")
            entrada.focus_set()
            entrada.select_range(0, tk.END)

            # Dropdown de tipo de dispositivo
            ttk.Label(frame, text="Tipo de dispositivo:").grid(row=1, column=0, sticky="w", pady=(0, 15))
            tipos_nombres = sorted(tipos_dispositivo.keys())
            tipo_combo = ttk.Combobox(frame, values=tipos_nombres, state="readonly", width=28)
            tipo_combo.grid(row=1, column=1, pady=(0, 15), padx=(10, 0), sticky="ew")

            # Seleccionar el tipo actual
            tipo_nombre_actual = get_tipo_dispositivo_nombre(tipo_id_actual)
            tipo_combo.set(tipo_nombre_actual)

            def guardar_edicion():
                nueva_palabra = entrada.get().strip().upper()  # Convertir a mayúsculas
                if not nueva_palabra:
                    messagebox.showwarning("Advertencia", "La palabra clave no puede estar vacía")
                    return

                tipo_nombre = tipo_combo.get()
                tipo_id = tipos_dispositivo.get(tipo_nombre, 7)

                # Actualizar en la lista
                palabra_completa = {
                    "palabra": nueva_palabra,
                    "tipo_dispositivo_id": tipo_id
                }
                palabras_clave[idx] = palabra_completa

                # Actualizar listbox
                palabras_listbox.delete(idx)
                palabras_listbox.insert(idx, f"{nueva_palabra} - {tipo_nombre}")
                palabras_listbox.selection_set(idx)

                messagebox.showinfo("Éxito", f"✅ Palabra clave actualizada correctamente")
                editar_modal.destroy()

            button_frame = ttk.Frame(frame)
            button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))

            ttk.Button(button_frame, text="Guardar", command=guardar_edicion).pack(side=tk.LEFT, expand=True, padx=5)
            ttk.Button(button_frame, text="Cancelar", command=editar_modal.destroy).pack(side=tk.LEFT, expand=True,
                                                                                         padx=5)

            frame.columnconfigure(1, weight=1)

            # Permitir Enter para guardar
            entrada.bind('<Return>', lambda e: guardar_edicion())

        # Botones para gestionar palabras clave
        ttk.Button(palabras_buttons_frame, text="➕ Agregar", command=agregar_palabra).pack(side=tk.LEFT, expand=True,
                                                                                           padx=2)
        ttk.Button(palabras_buttons_frame, text="✏️ Editar", command=editar_palabra).pack(side=tk.LEFT, expand=True,
                                                                                          padx=2)
        ttk.Button(palabras_buttons_frame, text="🗑️ Eliminar", command=eliminar_palabra).pack(side=tk.LEFT, expand=True,
                                                                                              padx=2)

        # Bind de selección de categoría
        categorias_listbox.bind('<<ListboxSelect>>', on_categoria_select)

        # Frame para botones principales (guardar/cancelar)
        main_button_frame = ttk.Frame(main_frame)
        main_button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        def guardar_configuracion():
            """Guarda la configuración de categorías en el archivo JSON"""
            try:
                # Crear el JSON completo con las categorías hardcodeadas
                config_data = {
                    "categorias": categorias_dict
                }

                # Guardar usando ConfigManager
                if categorias_manager.save_categorias_config(config_data):
                    messagebox.showinfo("Éxito", "✅ Configuración de categorías guardada correctamente")
                    self.log_api_message("✅ Configuración de categorías actualizada", level="INFO")
                    modal.destroy()
                else:
                    messagebox.showerror("Error", "Error al guardar la configuración")

            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar la configuración:\n{e}")

        ttk.Button(main_button_frame, text="💾 Guardar", command=guardar_configuracion).pack(side=tk.LEFT, expand=True,
                                                                                            padx=5)
        ttk.Button(main_button_frame, text="❌ Cancelar", command=modal.destroy).pack(side=tk.LEFT, expand=True, padx=5)

        # Configurar grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=1)

        # Cargar categorías iniciales
        cargar_categorias()

    def open_proveedores_modal(self):
        """Abre una ventana modal para configurar los proveedores y sus palabras clave"""
        import json
        import os
        from config_manager import get_proveedores_config, save_proveedores_config

        # Cargar configuración de proveedores
        config_data = get_proveedores_config()
        proveedores_dict = config_data.get('proveedores', {})

        # Crear ventana modal
        modal = tk.Toplevel(self.root)
        modal.title("Configurar Proveedores")
        modal.geometry("800x500")
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

        # Frame principal con dos paneles
        main_frame = ttk.Frame(modal, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Panel izquierdo: Lista de proveedores
        left_frame = ttk.LabelFrame(main_frame, text="Proveedores", padding="10")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Listbox para proveedores
        proveedores_listbox = tk.Listbox(left_frame, height=15, width=25)
        proveedores_listbox.pack(fill=tk.BOTH, expand=True)

        # Scroll para listbox de proveedores
        scrollbar_prov = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=proveedores_listbox.yview)
        scrollbar_prov.pack(side=tk.RIGHT, fill=tk.Y)
        proveedores_listbox.config(yscrollcommand=scrollbar_prov.set)

        # Panel derecho: Palabras clave del proveedor seleccionado
        right_frame = ttk.LabelFrame(main_frame, text="Palabras Clave", padding="10")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # Label con información del proveedor seleccionado
        info_label = ttk.Label(right_frame, text="Selecciona un proveedor", font=("Arial", 10, "bold"))
        info_label.pack(pady=(0, 10))

        # Listbox para palabras clave
        palabras_listbox = tk.Listbox(right_frame, height=12, width=40)
        palabras_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Scroll para listbox de palabras
        scrollbar_pal = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=palabras_listbox.yview)
        scrollbar_pal.pack(side=tk.RIGHT, fill=tk.Y)
        palabras_listbox.config(yscrollcommand=scrollbar_pal.set)

        # Frame para botones de palabras clave
        palabras_buttons_frame = ttk.Frame(right_frame)
        palabras_buttons_frame.pack(fill=tk.X)

        # Variable para tracking del proveedor seleccionado
        proveedor_seleccionado = [None]  # Usar lista para mutabilidad en closures

        def cargar_proveedores():
            """Carga la lista de proveedores en el listbox"""
            proveedores_listbox.delete(0, tk.END)
            for nombre_prov in sorted(proveedores_dict.keys()):
                proveedores_listbox.insert(tk.END, nombre_prov)

        def on_proveedor_select(event):
            """Maneja la selección de un proveedor"""
            selection = proveedores_listbox.curselection()
            if not selection:
                return

            idx = selection[0]
            nombre_proveedor = proveedores_listbox.get(idx)
            proveedor_seleccionado[0] = nombre_proveedor

            # Actualizar label de información
            proveedor_id = proveedores_dict[nombre_proveedor].get('id', '?')
            info_label.config(text=f"Proveedor: {nombre_proveedor}\nID: {proveedor_id}")

            # Cargar palabras clave de este proveedor
            palabras_listbox.delete(0, tk.END)
            palabras_clave = proveedores_dict[nombre_proveedor].get('palabras_clave', [])

            # Mostrar palabras clave
            for palabra in palabras_clave:
                palabras_listbox.insert(tk.END, palabra)

        def agregar_palabra():
            """Agrega una nueva palabra clave al proveedor seleccionado"""
            if not proveedor_seleccionado[0]:
                messagebox.showwarning("Advertencia", "Selecciona primero un proveedor")
                return

            # Crear ventana para ingresar la palabra
            palabra_modal = tk.Toplevel(modal)
            palabra_modal.title("Agregar Palabra Clave")
            palabra_modal.geometry("400x150")
            palabra_modal.transient(modal)
            palabra_modal.grab_set()

            # Centrar ventana
            palabra_modal.update_idletasks()
            pw = palabra_modal.winfo_width()
            ph = palabra_modal.winfo_height()
            px = (palabra_modal.winfo_screenwidth() // 2) - (pw // 2)
            py = (palabra_modal.winfo_screenheight() // 2) - (ph // 2)
            palabra_modal.geometry(f"{pw}x{ph}+{px}+{py}")

            # Frame
            frame = ttk.Frame(palabra_modal, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            # Entrada de palabra clave
            ttk.Label(frame, text="Nueva palabra clave:").grid(row=0, column=0, sticky="w", pady=(0, 15))
            entrada = ttk.Entry(frame, width=30)
            entrada.grid(row=0, column=1, pady=(0, 15), padx=(10, 0), sticky="ew")
            entrada.focus_set()

            def guardar_palabra():
                palabra = entrada.get().strip().upper()  # Convertir a mayúsculas
                if not palabra:
                    messagebox.showwarning("Advertencia", "La palabra clave no puede estar vacía")
                    return

                # Verificar que no exista ya
                palabras_actuales = proveedores_dict[proveedor_seleccionado[0]]['palabras_clave']
                if palabra in palabras_actuales:
                    messagebox.showwarning("Advertencia", "Esta palabra clave ya existe")
                    return

                # Agregar al proveedor
                proveedores_dict[proveedor_seleccionado[0]]['palabras_clave'].append(palabra)

                # Actualizar listbox
                palabras_listbox.insert(tk.END, palabra)
                palabra_modal.destroy()

            button_frame = ttk.Frame(frame)
            button_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))

            ttk.Button(button_frame, text="Guardar", command=guardar_palabra).pack(side=tk.LEFT, expand=True, padx=5)
            ttk.Button(button_frame, text="Cancelar", command=palabra_modal.destroy).pack(side=tk.LEFT, expand=True, padx=5)

            frame.columnconfigure(1, weight=1)

            # Permitir Enter para guardar
            entrada.bind('<Return>', lambda e: guardar_palabra())

        def eliminar_palabra():
            """Elimina la palabra clave seleccionada"""
            if not proveedor_seleccionado[0]:
                messagebox.showwarning("Advertencia", "Selecciona primero un proveedor")
                return

            selection = palabras_listbox.curselection()
            if not selection:
                messagebox.showwarning("Advertencia", "Selecciona una palabra clave para eliminar")
                return

            idx = selection[0]
            palabra = palabras_listbox.get(idx)

            # Confirmar eliminación
            if messagebox.askyesno("Confirmar", f"¿Eliminar la palabra clave '{palabra}'?"):
                # Eliminar de la lista en memoria
                palabras_clave = proveedores_dict[proveedor_seleccionado[0]]['palabras_clave']
                if idx < len(palabras_clave):
                    palabras_clave.pop(idx)
                palabras_listbox.delete(idx)

        def editar_palabra():
            """Edita la palabra clave seleccionada"""
            if not proveedor_seleccionado[0]:
                messagebox.showwarning("Advertencia", "Selecciona primero un proveedor")
                return

            selection = palabras_listbox.curselection()
            if not selection:
                messagebox.showwarning("Advertencia", "Selecciona una palabra clave para editar")
                return

            idx = selection[0]
            palabra_actual = palabras_listbox.get(idx)

            # Crear ventana para editar
            editar_modal = tk.Toplevel(modal)
            editar_modal.title("Editar Palabra Clave")
            editar_modal.geometry("400x150")
            editar_modal.transient(modal)
            editar_modal.grab_set()

            # Centrar ventana
            editar_modal.update_idletasks()
            ew = editar_modal.winfo_width()
            eh = editar_modal.winfo_height()
            ex = (editar_modal.winfo_screenwidth() // 2) - (ew // 2)
            ey = (editar_modal.winfo_screenheight() // 2) - (eh // 2)
            editar_modal.geometry(f"{ew}x{eh}+{ex}+{ey}")

            # Frame
            frame = ttk.Frame(editar_modal, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            # Entrada para editar la palabra
            ttk.Label(frame, text="Editar palabra clave:").grid(row=0, column=0, sticky="w", pady=(0, 15))
            entrada = ttk.Entry(frame, width=30)
            entrada.insert(0, palabra_actual)
            entrada.grid(row=0, column=1, pady=(0, 15), padx=(10, 0), sticky="ew")
            entrada.focus_set()
            entrada.select_range(0, tk.END)

            def guardar_edicion():
                nueva_palabra = entrada.get().strip().upper()  # Convertir a mayúsculas
                if not nueva_palabra:
                    messagebox.showwarning("Advertencia", "La palabra clave no puede estar vacía")
                    return

                # Actualizar en la lista
                palabras_clave = proveedores_dict[proveedor_seleccionado[0]]['palabras_clave']
                palabras_clave[idx] = nueva_palabra

                # Actualizar listbox
                palabras_listbox.delete(idx)
                palabras_listbox.insert(idx, nueva_palabra)
                palabras_listbox.selection_set(idx)

                messagebox.showinfo("Éxito", f"✅ Palabra clave actualizada correctamente")
                editar_modal.destroy()

            button_frame = ttk.Frame(frame)
            button_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))

            ttk.Button(button_frame, text="Guardar", command=guardar_edicion).pack(side=tk.LEFT, expand=True, padx=5)
            ttk.Button(button_frame, text="Cancelar", command=editar_modal.destroy).pack(side=tk.LEFT, expand=True, padx=5)

            frame.columnconfigure(1, weight=1)

            # Permitir Enter para guardar
            entrada.bind('<Return>', lambda e: guardar_edicion())

        # Botones para gestionar palabras clave
        ttk.Button(palabras_buttons_frame, text="➕ Agregar", command=agregar_palabra).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(palabras_buttons_frame, text="✏️ Editar", command=editar_palabra).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(palabras_buttons_frame, text="🗑️ Eliminar", command=eliminar_palabra).pack(side=tk.LEFT, expand=True, padx=2)

        # Bind de selección de proveedor
        proveedores_listbox.bind('<<ListboxSelect>>', on_proveedor_select)

        # Frame para botones principales (guardar/cancelar)
        main_button_frame = ttk.Frame(main_frame)
        main_button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        def guardar_configuracion():
            """Guarda la configuración de proveedores en el archivo JSON"""
            try:
                # Crear el JSON completo con los proveedores
                config_data = {
                    "proveedores": proveedores_dict
                }

                # Guardar usando la función global
                if save_proveedores_config(config_data):
                    messagebox.showinfo("Éxito", "✅ Configuración de proveedores guardada correctamente")
                    self.log_api_message("✅ Configuración de proveedores actualizada", level="INFO")
                    modal.destroy()
                else:
                    messagebox.showerror("Error", "Error al guardar la configuración")

            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar la configuración:\n{e}")

        ttk.Button(main_button_frame, text="💾 Guardar", command=guardar_configuracion).pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Button(main_button_frame, text="❌ Cancelar", command=modal.destroy).pack(side=tk.LEFT, expand=True, padx=5)

        # Configurar grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=1)

        # Cargar proveedores iniciales
        cargar_proveedores()

    def open_servitotal_modal(self):
        """Abre una ventana modal para configurar los mapeos de códigos Servitotal"""
        from config_manager import get_servitotal_config, save_servitotal_config

        # Cargar configuración de servitotal
        config_data = get_servitotal_config()
        mapeos_list = config_data.get('mapeos', [])

        # Crear ventana modal
        modal = tk.Toplevel(self.root)
        modal.title("Configurar Servitotal - Mapeo de Códigos")
        modal.geometry("700x500")
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

        # Frame principal
        main_frame = ttk.Frame(modal, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título y descripción
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            title_frame,
            text="Mapeo de Códigos Servitotal",
            font=("Arial", 12, "bold")
        ).pack()

        ttk.Label(
            title_frame,
            text="Configure códigos que serán reemplazados cuando se detecte 'servitotal' en el correo",
            font=("Arial", 9)
        ).pack()

        # Frame para la lista de mapeos
        list_frame = ttk.LabelFrame(main_frame, text="Mapeos Configurados", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Treeview para mostrar los mapeos
        columns = ('codigo_buscar', 'codigo_enviar')
        mapeos_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)

        mapeos_tree.heading('codigo_buscar', text='Código a Buscar')
        mapeos_tree.heading('codigo_enviar', text='Código a Enviar')

        mapeos_tree.column('codigo_buscar', width=150, anchor='center')
        mapeos_tree.column('codigo_enviar', width=150, anchor='center')

        mapeos_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar para el treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=mapeos_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        mapeos_tree.config(yscrollcommand=scrollbar.set)

        def cargar_mapeos():
            """Carga los mapeos en el treeview"""
            mapeos_tree.delete(*mapeos_tree.get_children())
            for mapeo in mapeos_list:
                codigo_buscar = mapeo.get('codigo_buscar', '')
                codigo_enviar = mapeo.get('codigo_enviar', '')
                mapeos_tree.insert('', tk.END, values=(codigo_buscar, codigo_enviar))

        def agregar_mapeo():
            """Agrega un nuevo mapeo de código"""
            # Crear ventana para ingresar el mapeo
            mapeo_modal = tk.Toplevel(modal)
            mapeo_modal.title("Agregar Mapeo")
            mapeo_modal.geometry("450x200")
            mapeo_modal.transient(modal)
            mapeo_modal.grab_set()

            # Centrar ventana
            mapeo_modal.update_idletasks()
            mw = mapeo_modal.winfo_width()
            mh = mapeo_modal.winfo_height()
            mx = (mapeo_modal.winfo_screenwidth() // 2) - (mw // 2)
            my = (mapeo_modal.winfo_screenheight() // 2) - (mh // 2)
            mapeo_modal.geometry(f"{mw}x{mh}+{mx}+{my}")

            # Frame
            frame = ttk.Frame(mapeo_modal, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            # Entrada de código a buscar
            ttk.Label(frame, text="Código a buscar:").grid(row=0, column=0, sticky="w", pady=(0, 15))
            entrada_buscar = ttk.Entry(frame, width=30)
            entrada_buscar.grid(row=0, column=1, pady=(0, 15), padx=(10, 0), sticky="ew")
            entrada_buscar.focus_set()

            # Entrada de código a enviar
            ttk.Label(frame, text="Código a enviar:").grid(row=1, column=0, sticky="w", pady=(0, 15))
            entrada_enviar = ttk.Entry(frame, width=30)
            entrada_enviar.grid(row=1, column=1, pady=(0, 15), padx=(10, 0), sticky="ew")

            def guardar_mapeo():
                codigo_buscar = entrada_buscar.get().strip()
                codigo_enviar = entrada_enviar.get().strip()

                if not codigo_buscar or not codigo_enviar:
                    messagebox.showwarning("Advertencia", "Ambos códigos son requeridos")
                    return

                # Verificar que no exista ya el mismo código_buscar
                for mapeo in mapeos_list:
                    if mapeo.get('codigo_buscar') == codigo_buscar:
                        messagebox.showwarning("Advertencia", f"Ya existe un mapeo para el código '{codigo_buscar}'")
                        return

                # Agregar a la lista
                nuevo_mapeo = {
                    "codigo_buscar": codigo_buscar,
                    "codigo_enviar": codigo_enviar
                }
                mapeos_list.append(nuevo_mapeo)

                # Actualizar treeview
                cargar_mapeos()
                mapeo_modal.destroy()
                messagebox.showinfo("Éxito", "✅ Mapeo agregado correctamente")

            button_frame = ttk.Frame(frame)
            button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))

            ttk.Button(button_frame, text="Guardar", command=guardar_mapeo).pack(side=tk.LEFT, expand=True, padx=5)
            ttk.Button(button_frame, text="Cancelar", command=mapeo_modal.destroy).pack(side=tk.LEFT, expand=True, padx=5)

            frame.columnconfigure(1, weight=1)

            # Permitir Enter para guardar
            entrada_enviar.bind('<Return>', lambda e: guardar_mapeo())

        def editar_mapeo():
            """Edita el mapeo seleccionado"""
            selection = mapeos_tree.selection()
            if not selection:
                messagebox.showwarning("Advertencia", "Selecciona un mapeo para editar")
                return

            item = selection[0]
            values = mapeos_tree.item(item, 'values')
            codigo_buscar_actual = values[0]
            codigo_enviar_actual = values[1]

            # Encontrar el índice del mapeo en la lista
            idx = None
            for i, mapeo in enumerate(mapeos_list):
                if mapeo.get('codigo_buscar') == codigo_buscar_actual:
                    idx = i
                    break

            if idx is None:
                messagebox.showerror("Error", "No se pudo encontrar el mapeo")
                return

            # Crear ventana para editar
            editar_modal = tk.Toplevel(modal)
            editar_modal.title("Editar Mapeo")
            editar_modal.geometry("450x200")
            editar_modal.transient(modal)
            editar_modal.grab_set()

            # Centrar ventana
            editar_modal.update_idletasks()
            ew = editar_modal.winfo_width()
            eh = editar_modal.winfo_height()
            ex = (editar_modal.winfo_screenwidth() // 2) - (ew // 2)
            ey = (editar_modal.winfo_screenheight() // 2) - (eh // 2)
            editar_modal.geometry(f"{ew}x{eh}+{ex}+{ey}")

            # Frame
            frame = ttk.Frame(editar_modal, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            # Entrada de código a buscar
            ttk.Label(frame, text="Código a buscar:").grid(row=0, column=0, sticky="w", pady=(0, 15))
            entrada_buscar = ttk.Entry(frame, width=30)
            entrada_buscar.insert(0, codigo_buscar_actual)
            entrada_buscar.grid(row=0, column=1, pady=(0, 15), padx=(10, 0), sticky="ew")
            entrada_buscar.focus_set()

            # Entrada de código a enviar
            ttk.Label(frame, text="Código a enviar:").grid(row=1, column=0, sticky="w", pady=(0, 15))
            entrada_enviar = ttk.Entry(frame, width=30)
            entrada_enviar.insert(0, codigo_enviar_actual)
            entrada_enviar.grid(row=1, column=1, pady=(0, 15), padx=(10, 0), sticky="ew")

            def guardar_edicion():
                codigo_buscar = entrada_buscar.get().strip()
                codigo_enviar = entrada_enviar.get().strip()

                if not codigo_buscar or not codigo_enviar:
                    messagebox.showwarning("Advertencia", "Ambos códigos son requeridos")
                    return

                # Verificar que no exista ya el mismo codigo_buscar (excepto el actual)
                for i, mapeo in enumerate(mapeos_list):
                    if i != idx and mapeo.get('codigo_buscar') == codigo_buscar:
                        messagebox.showwarning("Advertencia", f"Ya existe un mapeo para el código '{codigo_buscar}'")
                        return

                # Actualizar en la lista
                mapeos_list[idx] = {
                    "codigo_buscar": codigo_buscar,
                    "codigo_enviar": codigo_enviar
                }

                # Actualizar treeview
                cargar_mapeos()
                editar_modal.destroy()
                messagebox.showinfo("Éxito", "✅ Mapeo actualizado correctamente")

            button_frame = ttk.Frame(frame)
            button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))

            ttk.Button(button_frame, text="Guardar", command=guardar_edicion).pack(side=tk.LEFT, expand=True, padx=5)
            ttk.Button(button_frame, text="Cancelar", command=editar_modal.destroy).pack(side=tk.LEFT, expand=True, padx=5)

            frame.columnconfigure(1, weight=1)

            # Permitir Enter para guardar
            entrada_enviar.bind('<Return>', lambda e: guardar_edicion())

        def eliminar_mapeo():
            """Elimina el mapeo seleccionado"""
            selection = mapeos_tree.selection()
            if not selection:
                messagebox.showwarning("Advertencia", "Selecciona un mapeo para eliminar")
                return

            item = selection[0]
            values = mapeos_tree.item(item, 'values')
            codigo_buscar = values[0]

            # Confirmar eliminación
            if messagebox.askyesno("Confirmar", f"¿Eliminar el mapeo '{codigo_buscar}' → '{values[1]}'?"):
                # Eliminar de la lista
                for i, mapeo in enumerate(mapeos_list):
                    if mapeo.get('codigo_buscar') == codigo_buscar:
                        mapeos_list.pop(i)
                        break

                # Actualizar treeview
                cargar_mapeos()
                messagebox.showinfo("Éxito", "✅ Mapeo eliminado correctamente")

        # Frame para botones de acciones
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(actions_frame, text="➕ Agregar", command=agregar_mapeo).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(actions_frame, text="✏️ Editar", command=editar_mapeo).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(actions_frame, text="🗑️ Eliminar", command=eliminar_mapeo).pack(side=tk.LEFT, expand=True, padx=2)

        # Frame para botones principales (guardar/cancelar)
        main_button_frame = ttk.Frame(main_frame)
        main_button_frame.pack(fill=tk.X)

        def guardar_configuracion():
            """Guarda la configuración de servitotal en el archivo JSON"""
            try:
                config_data = {
                    "mapeos": mapeos_list
                }

                if save_servitotal_config(config_data):
                    messagebox.showinfo("Éxito", "✅ Configuración de Servitotal guardada correctamente")
                    self.log_api_message("✅ Configuración de Servitotal actualizada", level="INFO")
                    modal.destroy()
                else:
                    messagebox.showerror("Error", "Error al guardar la configuración")

            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar la configuración:\n{e}")

        ttk.Button(main_button_frame, text="💾 Guardar", command=guardar_configuracion).pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Button(main_button_frame, text="❌ Cancelar", command=modal.destroy).pack(side=tk.LEFT, expand=True, padx=5)

        # Cargar mapeos iniciales
        cargar_mapeos()

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
            palabra_clave = search_params.get('caso1', '').strip()
            titular_correo = search_params.get('titular_correo', '').strip()

            # Validar que haya al menos palabra clave O dominio configurado
            if not palabra_clave and not titular_correo:
                self.log_api_message("❌ Error: Configure al menos una palabra clave o un dominio", level="ERROR")
                messagebox.showwarning("Advertencia",
                                       "Configure al menos una palabra clave o un dominio en Parámetros de Búsqueda")
                return

            self.monitoring = True
            self.monitor_button.config(text="Detener Monitoreo")
            self.status_label.config(text="Estado: Monitoreando", foreground="green")

            self.monitor_thread = threading.Thread(target=self.monitor_emails, daemon=True)
            self.monitor_thread.start()

            # Log informativo sobre la configuración activa
            config_info = []
            if palabra_clave:
                config_info.append(f"palabra clave: '{palabra_clave}'")
            if titular_correo:
                config_info.append(f"dominios: {titular_correo}")

            self.log_api_message(f"✅ Monitoreo iniciado con {' y '.join(config_info)}", level="INFO")
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

                # Obtener dominios permitidos
                allowed_domains = search_params.get('titular_correo', '').strip()

                search_titles = []
                if search_params.get('caso1', '').strip():
                    search_titles.append(search_params['caso1'].strip())

                if search_titles or allowed_domains:
                    self.log_api_message(f"Revisando correos... ({datetime.now().strftime('%H:%M:%S')})")

                    self.email_manager.check_and_process_emails(
                        config['provider'],
                        config['email'],
                        config['password'],
                        search_titles,
                        self.logger,
                        cc_list,
                        allowed_domains  # Pasar dominios permitidos
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

    def consultar_distribuidores(self):
        """Consulta distribuidores desde recursos iniciales"""
        self.log_api_message("=" * 60)
        self.log_api_message("🏢 Consultando Distribuidores")
        self.log_api_message("=" * 60)

        # Deshabilitar botón
        self.distribuidores_button.config(state=tk.DISABLED, text="Consultando...")

        async def consultar():
            """Operación asíncrona"""
            self.log_api_message("🔄 Iniciando consulta de distribuidores...")
            endpoint = "/v1/preingreso/recursos_iniciales"
            self.log_api_message(f"📡 Endpoint: {endpoint}")
            self.log_api_message(f"🌐 URL completa: {self.settings.API_BASE_URL}{endpoint}")
            self.log_api_message("")

            # Llamar al repositorio
            response = await self.repository.listar_recursos_iniciales()
            return response

        def on_success(response):
            """Callback de éxito"""
            self.log_api_message(f"📥 Status Code: {response.status_code}")
            self.log_api_message("")

            if response.status_code == 200:
                self.log_api_message("✅ Respuesta exitosa - Distribuidores")
                try:
                    import json
                    # Extraer solo los distribuidores del response (el campo es "distribuidor" en singular)
                    distribuidores = response.body.get("data", {}).get("distribuidor", [])

                    if distribuidores:
                        distribuidores_data = {"distribuidor": distribuidores}
                        formatted_json = json.dumps(distribuidores_data, indent=2, ensure_ascii=False)
                        self.log_api_message("📄 Lista de Distribuidores:")
                        self.log_api_message(formatted_json)
                        self.log_api_message(f"\n📊 Total de distribuidores: {len(distribuidores)}")
                    else:
                        self.log_api_message("⚠️ No se encontraron distribuidores en la respuesta")

                except Exception as e:
                    self.log_api_message(f"❌ Error procesando respuesta: {str(e)}", "ERROR")
                    self.log_api_message("📄 Respuesta completa:")
                    self.log_api_message(response.raw_content)
            else:
                self.log_api_message(f"⚠️ Error: {response.status_code}")
                self.log_api_message(response.body if response.body else "(vacío)")

            self.log_api_message("=" * 60)
            self.distribuidores_button.config(state=tk.NORMAL, text="Distribuidores")

        def on_error(error):
            """Callback de error"""
            self.log_api_message(f"❌ Error: {str(error)}", "ERROR")
            self.log_api_message("=" * 60)
            self.distribuidores_button.config(state=tk.NORMAL, text="Distribuidores")

        # Ejecutar operación async
        run_async_with_callback(
            consultar(),
            on_success=on_success,
            on_error=on_error
        )

    def consultar_garantias(self):
        """Consulta garantías para todos los tipos de preingreso"""
        self.log_api_message("=" * 60)
        self.log_api_message("🛡️ Consultando Garantías para Todos los Tipos de Preingreso")
        self.log_api_message("=" * 60)

        # Deshabilitar botón
        self.garantias_button.config(state=tk.DISABLED, text="Consultando...")

        # Tipos de preingreso a consultar: Normal (7), DOA/STOCK (8), DAP (9), No/CSR (92)
        tipos_preingreso = {
            "7": "Normal",
            "8": "DOA/STOCK",
            "9": "DAP",
            "92": "No/CSR"
        }

        async def consultar():
            """Operación asíncrona - consulta múltiples tipos"""
            import asyncio

            self.log_api_message("🔄 Iniciando consulta de garantías para todos los tipos...")
            self.log_api_message(f"📋 Tipos a consultar: {', '.join([f'{k} ({v})' for k, v in tipos_preingreso.items()])}")
            self.log_api_message("")

            # Realizar consultas para todos los tipos
            resultados = {}
            for tipo_id, tipo_nombre in tipos_preingreso.items():
                try:
                    self.log_api_message(f"📡 Consultando tipo {tipo_id} ({tipo_nombre})...")
                    endpoint = f"/v1/preingreso/garantia/{tipo_id}"
                    self.log_api_message(f"   URL: {self.settings.API_BASE_URL}{endpoint}")

                    response = await self.repository.listar_garantias(tipo_id)
                    resultados[tipo_id] = {
                        "nombre": tipo_nombre,
                        "response": response
                    }

                except Exception as e:
                    self.log_api_message(f"   ⚠️ Error en tipo {tipo_id}: {str(e)}", "ERROR")
                    resultados[tipo_id] = {
                        "nombre": tipo_nombre,
                        "error": str(e)
                    }

            self.log_api_message("")
            return resultados

        def on_success(resultados):
            """Callback de éxito"""
            self.log_api_message("=" * 60)
            self.log_api_message("📊 RESULTADOS DE CONSULTA DE GARANTÍAS")
            self.log_api_message("=" * 60)

            import json

            for tipo_id, data in resultados.items():
                tipo_nombre = data.get("nombre", "Desconocido")
                self.log_api_message("")
                self.log_api_message(f"▶ Tipo de Preingreso: {tipo_id} - {tipo_nombre}")
                self.log_api_message("-" * 60)

                if "error" in data:
                    self.log_api_message(f"   ❌ Error: {data['error']}", "ERROR")
                    continue

                response = data.get("response")
                if response:
                    self.log_api_message(f"   📥 Status Code: {response.status_code}")

                    if response.status_code == 200:
                        self.log_api_message("   ✅ Respuesta exitosa")
                        try:
                            # Intentar formatear como JSON
                            response_data = response.body
                            formatted_json = json.dumps(response_data, indent=2, ensure_ascii=False)
                            self.log_api_message("   📄 Garantías disponibles:")
                            # Indentar cada línea del JSON
                            for line in formatted_json.split('\n'):
                                self.log_api_message(f"   {line}")
                        except:
                            self.log_api_message("   📄 Respuesta (texto plano):")
                            self.log_api_message(f"   {response.raw_content}")
                    else:
                        self.log_api_message(f"   ⚠️ Error: {response.status_code}")
                        self.log_api_message(f"   {response.body if response.body else '(vacío)'}")
                else:
                    self.log_api_message("   ⚠️ No se recibió respuesta")

            self.log_api_message("")
            self.log_api_message("=" * 60)
            self.log_api_message("✅ Consulta de garantías completada")
            self.log_api_message("=" * 60)

            # Rehabilitar botón
            self.garantias_button.config(state=tk.NORMAL, text="Garantías")

        def on_error(error):
            """Callback de error"""
            self.log_api_message(f"❌ Error general: {str(error)}", "ERROR")
            self.log_api_message("=" * 60)

            # Rehabilitar botón
            self.garantias_button.config(state=tk.NORMAL, text="Garantías")

        # Ejecutar operación async
        run_async_with_callback(
            consultar(),
            on_success=on_success,
            on_error=on_error
        )

    def consultar_dispositivo(self):
        """Consulta tipos de dispositivo por categoría"""
        # Obtener el ID de categoría del campo de entrada
        categoria_id = self.categoria_entry.get().strip()

        if not categoria_id:
            self.log_api_message("❌ Error: Debe ingresar un ID de categoría", "ERROR")
            messagebox.showwarning("Advertencia", "Ingrese un ID de categoría de dispositivo")
            return

        self.log_api_message("=" * 60)
        self.log_api_message("📱 Consultando Tipos de Dispositivo")
        self.log_api_message("=" * 60)
        self.log_api_message(f"🔍 Categoría ID: {categoria_id}")

        # Deshabilitar botón
        self.dispositivo_button.config(state=tk.DISABLED, text="Consultando...")

        async def consultar():
            """Operación asíncrona"""
            self.log_api_message("🔄 Iniciando consulta...")
            endpoint = f"/v1/unidad/categoria/{categoria_id}/tipo_dispositivo"
            self.log_api_message(f"📡 Endpoint: {endpoint}")
            self.log_api_message(f"🌐 URL completa: {self.settings.API_BASE_URL}{endpoint}")
            self.log_api_message("")

            # Llamar al repositorio
            response = await self.repository.listar_tipos_dispositivo(categoria_id)
            return response

        def on_success(response):
            """Callback de éxito"""
            self.log_api_message(f"📥 Status Code: {response.status_code}")
            self.log_api_message("")

            if response.status_code == 200:
                self.log_api_message("✅ Respuesta exitosa")
                try:
                    import json
                    formatted_json = json.dumps(response.body, indent=2, ensure_ascii=False)
                    self.log_api_message("📄 Tipos de Dispositivo:")
                    self.log_api_message(formatted_json)
                except:
                    self.log_api_message("📄 Respuesta (texto plano):")
                    self.log_api_message(str(response.raw_content))
            else:
                self.log_api_message(f"⚠️ Error: {response.status_code}", "ERROR")
                self.log_api_message(f"📄 Respuesta: {response.body if response.body else '(vacío)'}")

            self.log_api_message("")
            self.log_api_message("=" * 60)

            # Rehabilitar botón
            self.dispositivo_button.config(state=tk.NORMAL, text="Consultar Dispositivo")

        def on_error(error):
            """Callback de error"""
            self.log_api_message(f"❌ Error: {str(error)}", "ERROR")
            self.log_api_message("=" * 60)

            # Rehabilitar botón
            self.dispositivo_button.config(state=tk.NORMAL, text="Consultar Dispositivo")

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

    def abrir_preingreso_personalizado(self):
        """Abre un popup para crear un preingreso con datos personalizados"""
        from tkinter import filedialog

        self.log_api_message("=" * 60)
        self.log_api_message("Abriendo Preingreso Personalizado")
        self.log_api_message("=" * 60)

        # Variable para almacenar la ruta del PDF seleccionado
        pdf_path = tk.StringVar(value="")

        # Crear ventana modal
        modal = tk.Toplevel(self.root)
        modal.title("Preingreso Personalizado")
        modal.geometry("600x750")
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

        # Frame principal con scroll
        main_frame = ttk.Frame(modal, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título
        title_label = ttk.Label(
            main_frame,
            text="Ingrese los datos del preingreso",
            font=("Segoe UI", 11, "bold")
        )
        title_label.pack(pady=(0, 15))

        # Frame para selección de PDF
        pdf_frame = ttk.LabelFrame(main_frame, text="Archivo PDF Base", padding="10")
        pdf_frame.pack(fill=tk.X, pady=(0, 15))

        # Label para mostrar el archivo seleccionado
        pdf_label = ttk.Label(
            pdf_frame,
            text="Ningún archivo seleccionado",
            foreground="gray"
        )
        pdf_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # Función para seleccionar PDF
        def seleccionar_pdf():
            archivo = filedialog.askopenfilename(
                title="Seleccionar PDF Base",
                filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")],
                initialdir=os.path.expanduser("~")
            )
            if archivo:
                pdf_path.set(archivo)
                pdf_label.config(
                    text=os.path.basename(archivo),
                    foreground="blue"
                )
                self.log_api_message(f"📄 PDF seleccionado: {os.path.basename(archivo)}")

        # Botón para seleccionar PDF
        select_pdf_button = ttk.Button(
            pdf_frame,
            text="📁 Seleccionar PDF",
            command=seleccionar_pdf
        )
        select_pdf_button.pack(side=tk.RIGHT)

        # Nota informativa
        info_label = ttk.Label(
            main_frame,
            text="Los datos marcados reemplazarán a los del PDF.\nLos no marcados se tomarán del PDF.",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        info_label.pack(pady=(0, 10))

        # Frame para los campos
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.BOTH, expand=True)

        # Diccionario para almacenar campos y checkboxes
        campos = {}

        # Campo: numero_boleta
        campo_frame = ttk.Frame(fields_frame)
        campo_frame.pack(fill=tk.X, pady=5)

        # Checkbox para activar/desactivar
        var_check = tk.BooleanVar(value=False)
        check = ttk.Checkbutton(campo_frame, variable=var_check, width=2)
        check.pack(side=tk.LEFT, padx=(0, 5))

        # Label
        label = ttk.Label(campo_frame, text="Número de Boleta:", width=20)
        label.pack(side=tk.LEFT, padx=(0, 5))

        # Entry
        entry = ttk.Entry(campo_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Almacenar referencia
        campos['numero_boleta'] = {
            'entry': entry,
            'check': var_check,
            'label': 'Número de Boleta'
        }

        # Campo: cliente_nombre
        campo_frame = ttk.Frame(fields_frame)
        campo_frame.pack(fill=tk.X, pady=5)

        # Checkbox para activar/desactivar
        var_check = tk.BooleanVar(value=False)
        check = ttk.Checkbutton(campo_frame, variable=var_check, width=2)
        check.pack(side=tk.LEFT, padx=(0, 5))

        # Label
        label = ttk.Label(campo_frame, text="Nombre de Cliente:", width=20)
        label.pack(side=tk.LEFT, padx=(0, 5))

        # Entry
        entry = ttk.Entry(campo_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Almacenar referencia
        campos['cliente_nombre'] = {
            'entry': entry,
            'check': var_check,
            'label': 'Nombre de Cliente'
        }

        # Campo: tipo_garantia (Dropdown)
        campo_frame = ttk.Frame(fields_frame)
        campo_frame.pack(fill=tk.X, pady=5)

        # Checkbox para activar/desactivar
        var_check = tk.BooleanVar(value=False)
        check = ttk.Checkbutton(campo_frame, variable=var_check, width=2)
        check.pack(side=tk.LEFT, padx=(0, 5))

        # Label
        label = ttk.Label(campo_frame, text="Tipo de Garantía:", width=20)
        label.pack(side=tk.LEFT, padx=(0, 5))

        # Combobox (Dropdown) con los tipos de garantía
        tipos_garantia = ["Normal", "DOA", "STOCK", "DAP", "Sin", "C.S.R."]
        combo = ttk.Combobox(campo_frame, values=tipos_garantia, state="readonly")
        combo.set("Normal")  # Valor por defecto
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Almacenar referencia
        campos['garantia_nombre'] = {
            'entry': combo,  # Usamos 'entry' para mantener consistencia con la lógica existente
            'check': var_check,
            'label': 'Tipo de Garantía'
        }

        # Campo: nombre_contacto
        campo_frame = ttk.Frame(fields_frame)
        campo_frame.pack(fill=tk.X, pady=5)

        # Checkbox para activar/desactivar
        var_check = tk.BooleanVar(value=False)
        check = ttk.Checkbutton(campo_frame, variable=var_check, width=2)
        check.pack(side=tk.LEFT, padx=(0, 5))

        # Label
        label = ttk.Label(campo_frame, text="Nombre de Contacto:", width=20)
        label.pack(side=tk.LEFT, padx=(0, 5))

        # Entry
        entry = ttk.Entry(campo_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Almacenar referencia
        campos['nombre_contacto'] = {
            'entry': entry,
            'check': var_check,
            'label': 'Nombre de Contacto'
        }

        # Campo: nombre_cliente
        campo_frame = ttk.Frame(fields_frame)
        campo_frame.pack(fill=tk.X, pady=5)

        # Checkbox para activar/desactivar
        var_check = tk.BooleanVar(value=False)
        check = ttk.Checkbutton(campo_frame, variable=var_check, width=2)
        check.pack(side=tk.LEFT, padx=(0, 5))

        # Label
        label = ttk.Label(campo_frame, text="Nombre Cliente:", width=20)
        label.pack(side=tk.LEFT, padx=(0, 5))

        # Entry
        entry = ttk.Entry(campo_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Almacenar referencia
        campos['nombre_cliente'] = {
            'entry': entry,
            'check': var_check,
            'label': 'Nombre Cliente'
        }

        # Campo: telefono_cliente
        campo_frame = ttk.Frame(fields_frame)
        campo_frame.pack(fill=tk.X, pady=5)

        # Checkbox para activar/desactivar
        var_check = tk.BooleanVar(value=False)
        check = ttk.Checkbutton(campo_frame, variable=var_check, width=2)
        check.pack(side=tk.LEFT, padx=(0, 5))

        # Label
        label = ttk.Label(campo_frame, text="Teléfono del Cliente:", width=20)
        label.pack(side=tk.LEFT, padx=(0, 5))

        # Entry
        entry = ttk.Entry(campo_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Almacenar referencia
        campos['telefono_cliente'] = {
            'entry': entry,
            'check': var_check,
            'label': 'Teléfono del Cliente'
        }

        # Campo: correo_propietario
        campo_frame = ttk.Frame(fields_frame)
        campo_frame.pack(fill=tk.X, pady=5)

        # Checkbox para activar/desactivar
        var_check = tk.BooleanVar(value=False)
        check = ttk.Checkbutton(campo_frame, variable=var_check, width=2)
        check.pack(side=tk.LEFT, padx=(0, 5))

        # Label
        label = ttk.Label(campo_frame, text="Correo del Propietario:", width=20)
        label.pack(side=tk.LEFT, padx=(0, 5))

        # Entry
        entry = ttk.Entry(campo_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Almacenar referencia
        campos['cliente_correo'] = {
            'entry': entry,
            'check': var_check,
            'label': 'Correo del Propietario'
        }

        # Función para enviar el preingreso
        def enviar_preingreso():
            self.log_api_message("🚀 Enviando preingreso personalizado...")

            # Verificar que haya PDF o datos personalizados
            archivo_pdf = pdf_path.get()

            # Recolectar datos activos
            datos_recolectados = {}
            for campo_nombre, campo_data in campos.items():
                if campo_data['check'].get():  # Si está activado
                    valor = campo_data['entry'].get().strip()
                    if valor:
                        datos_recolectados[campo_nombre] = valor
                        self.log_api_message(f"  ✓ {campo_data['label']}: {valor}")

            # Validar que haya al menos un PDF o datos personalizados
            if not archivo_pdf and not datos_recolectados:
                self.log_api_message("❌ Debe seleccionar un PDF o ingresar datos personalizados", level="ERROR")
                from tkinter import messagebox
                messagebox.showerror(
                    "Error",
                    "Debe seleccionar un archivo PDF o ingresar al menos un dato personalizado"
                )
                return

            # Cerrar modal
            modal.destroy()

            # Procesar el preingreso
            self._procesar_preingreso_personalizado(datos_recolectados, archivo_pdf)

        # Frame de botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))

        # Botón Enviar
        send_button = ttk.Button(
            button_frame,
            text="✉️ Enviar Preingreso",
            command=enviar_preingreso
        )
        send_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Botón Cancelar
        cancel_button = ttk.Button(
            button_frame,
            text="Cancelar",
            command=modal.destroy
        )
        cancel_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

    def _procesar_preingreso_personalizado(self, datos_recolectados, archivo_pdf=None):
        """Procesa y envía el preingreso personalizado

        Args:
            datos_recolectados: Diccionario con los datos personalizados activos
            archivo_pdf: Ruta del archivo PDF base (opcional)
        """
        self.log_api_message("📤 Procesando preingreso personalizado...")

        # Callbacks
        def on_success(result: CreatePreingresoOutput):
            """Callback cuando el procesamiento es exitoso"""
            if result.success:
                self.log_api_message("✅ Preingreso personalizado creado exitosamente!")
                self.log_api_message(f"   Boleta usada: {result.boleta_usada}")
                self.log_api_message(f"   Preingreso ID: {result.preingreso_id}")
                self.log_api_message(f"   Preingreso Guía: {result.consultar_guia}")
                self.log_api_message(f"   Tipo preingreso: {result.tipo_preingreso_nombre}")
                self.log_api_message(f"   Garantía: {result.garantia_nombre}")
                self.log_api_message(f"   Preingreso link: {result.consultar_reparacion}")
                self.log_api_message(f"   Status: {result.response.status_code}")
                self.log_api_message(f"   Tiempo: {result.response.response_time_ms:.0f}ms")

                # Enviar correos a usuarios notificados
                self._enviar_correos_preingreso_personalizado(result, datos_recolectados)

            else:
                error_msg = f"Error creando preingreso personalizado: {result.message}"
                self.log_api_message(f"❌ {error_msg}", level="ERROR")
                if result.errors:
                    for error in result.errors:
                        self.log_api_message(f"   - {error}", level="ERROR")

        def on_error(exception: Exception):
            """Callback cuando hay un error"""
            error_msg = f"Error procesando preingreso personalizado: {str(exception)}"
            self.log_api_message(f"❌ {error_msg}", level="ERROR")
            import traceback
            self.log_api_message(traceback.format_exc(), level="ERROR")

        # Función asíncrona para procesar
        async def procesar():
            # Inicializar datos del PDF con valores por defecto
            datos_extraidos_pdf = {}
            archivo_adjunto = None

            # Si hay un archivo PDF, extraer sus datos
            if archivo_pdf:
                self.log_api_message(f"📄 Extrayendo datos del PDF: {os.path.basename(archivo_pdf)}")

                # Crear referencia al archivo
                archivo_adjunto = ArchivoAdjunto(
                    nombre_archivo=os.path.basename(archivo_pdf),
                    ruta_archivo=archivo_pdf,
                    tipo_mime="application/pdf"
                )

                # Leer el archivo PDF
                pdf_content = await archivo_adjunto.leer_contenido()
                self.log_api_message(f"📊 Tamaño del archivo: {len(pdf_content):,} bytes")

                # Extraer texto del PDF
                self.log_api_message("🔍 Extrayendo datos del PDF...")
                datos_extraidos_pdf = self.extraer_datos_boleta_pdf(pdf_content)

                if not datos_extraidos_pdf:
                    raise ValueError("No se pudieron extraer datos del PDF")

                self.log_api_message("✅ Datos del PDF extraídos correctamente")

            # Combinar datos: usar personalizados si están activos, sino usar los del PDF
            # Si un dato personalizado está activo, reemplaza al del PDF
            self.log_api_message("🔄 Combinando datos personalizados con datos del PDF...")

            # Función auxiliar para obtener el valor correcto
            def get_valor(campo_personalizado, campo_pdf, valor_defecto=''):
                """Obtiene el valor: prioriza personalizado, luego PDF, luego defecto"""
                # Si hay dato personalizado, usar ese
                if campo_personalizado in datos_recolectados:
                    return datos_recolectados[campo_personalizado]
                # Si hay dato del PDF, usar ese
                if datos_extraidos_pdf and campo_pdf in datos_extraidos_pdf:
                    return strip_if_string(datos_extraidos_pdf.get(campo_pdf, valor_defecto))
                # Sino, valor por defecto
                return valor_defecto

            # Crear objeto DatosExtraidosPDF combinando datos personalizados y del PDF
            datos_pdf = DatosExtraidosPDF(
                numero_boleta=get_valor('numero_boleta', 'numero_boleta'),
                referencia=get_valor('referencia', 'referencia'),
                nombre_sucursal=get_valor('nombre_sucursal', 'sucursal'),
                numero_transaccion=get_valor('numero_transaccion', 'numero_transaccion'),
                cliente_nombre=get_valor('nombre_cliente', 'nombre_cliente') or get_valor('cliente_nombre', 'nombre_cliente'),
                cliente_contacto=get_valor('nombre_contacto', 'nombre_contacto') or get_valor('cliente_contacto', 'nombre_contacto'),
                cliente_telefono=get_valor('telefono_cliente', 'telefono_cliente') or get_valor('cliente_telefono', 'telefono_cliente'),
                cliente_correo=get_valor('cliente_correo', 'correo_cliente'),
                serie=get_valor('serie', 'serie'),
                garantia_nombre=get_valor('garantia_nombre', 'tipo_garantia'),
                fecha_compra=get_valor('fecha_compra', 'fecha_compra', None),
                factura=get_valor('factura', 'numero_factura', None),
                cliente_cedula=get_valor('cliente_cedula', 'cedula_cliente', None),
                cliente_direccion=get_valor('cliente_direccion', 'direccion_cliente', None),
                cliente_telefono2=get_valor('cliente_telefono2', 'telefono_adicional', None),
                fecha_transaccion=get_valor('fecha_transaccion', 'fecha', None),
                transaccion_gestionada_por=get_valor('transaccion_gestionada_por', 'gestionada_por', None),
                telefono_sucursal=get_valor('telefono_sucursal', 'telefono_sucursal', None),
                producto_codigo=get_valor('producto_codigo', 'codigo_producto', None),
                producto_descripcion=get_valor('producto_descripcion', 'descripcion_producto', None),
                marca_nombre=get_valor('marca_nombre', 'marca', None),
                modelo_nombre=get_valor('modelo_nombre', 'modelo', None),
                garantia_fecha=get_valor('garantia_fecha', 'fecha_garantia', None),
                danos=get_valor('danos', 'danos', None),
                observaciones=get_valor('observaciones', 'observaciones', None),
                hecho_por=get_valor('hecho_por', 'hecho_por', None)
            )

            # Mostrar resumen de datos a usar
            self.log_api_message("📋 Datos finales a enviar:")
            self.log_api_message(f"   Número de Boleta: {datos_pdf.numero_boleta}")
            self.log_api_message(f"   Referencia: {datos_pdf.referencia}")
            self.log_api_message(f"   Sucursal: {datos_pdf.nombre_sucursal}")

            # Crear caso de uso
            use_case = CreatePreingresoUseCase(self.repository, self.retry_policy)

            self.log_api_message("Enviando solicitud de crear el preingreso personalizado...")

            # Ejecutar caso de uso
            result = await use_case.execute(
                CreatePreingresoInput(
                    datos_pdf=datos_pdf,
                    archivo_adjunto=archivo_adjunto
                )
            )

            return result

        # Ejecutar asíncronamente
        run_async_with_callback(
            procesar(),
            on_success=on_success,
            on_error=on_error
        )

    def _enviar_correos_preingreso_personalizado(self, result: CreatePreingresoOutput, datos_recolectados):
        """Envía correos de notificación para preingreso personalizado"""
        self.log_api_message("📧 Enviando correos de notificación...")

        # Obtener lista de usuarios a notificar
        config = self.config_manager.load_config()
        cc_users = config.get('cc_users', [])

        if not cc_users:
            self.log_api_message("⚠️ No hay usuarios configurados para notificar", level="WARNING")
            return

        self.log_api_message(f"📮 Enviando a {len(cc_users)} destinatarios...")

        # Obtener configuración de correo usando el método correcto del ConfigManager
        email_config = self.config_manager.get_email_config()
        provider = email_config.get('provider', 'gmail')
        email_addr = email_config.get('email', '')
        password = email_config.get('password', '')

        if not email_addr or not password:
            self.log_api_message("❌ No hay configuración de correo", level="ERROR")
            return

        # Crear asunto y cuerpo del correo
        asunto = f"Notificación: Preingreso Personalizado - Boleta {result.preingreso_id}"

        cuerpo = f"""
Estimado/a Usuario,

Se ha creado un nuevo preingreso personalizado en el sistema.

📄 Detalles de la solicitud:
   Boleta Fruno: {result.preingreso_id}
   Guía Fruno: {result.consultar_guia}
   Tipo de preingreso: {result.tipo_preingreso_nombre}
   Garantía: {result.garantia_nombre}

📊 Datos personalizados enviados:
"""
        # Agregar datos personalizados al cuerpo
        for campo, valor in datos_recolectados.items():
            cuerpo += f"   - {campo}: {valor}\n"

        cuerpo += f"""
🔗 Consulta del estado:
   👉 {result.consultar_reparacion}

El preingreso se ha creado correctamente en nuestro sistema.

---
Este es un correo automático del sistema de preingresos.
"""

        # Enviar correos individuales
        from email_manager import EmailManager
        email_manager = EmailManager()

        for destinatario in cc_users:
            try:
                resultado = email_manager.send_email(
                    provider=provider,
                    email_addr=email_addr,
                    password=password,
                    to=destinatario,
                    subject=asunto,
                    body=cuerpo,
                    cc_list=None,
                    attachments=None,
                    logger=self.logger
                )

                if resultado:
                    self.log_api_message(f"✅ Correo enviado a: {destinatario}")
                else:
                    self.log_api_message(f"❌ Error enviando a: {destinatario}", level="ERROR")

            except Exception as e:
                self.log_api_message(f"❌ Error enviando correo a {destinatario}: {str(e)}", level="ERROR")

        self.log_api_message("📬 Envío de correos completado")

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

        for label, valor in resultado_api["data"].items():
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