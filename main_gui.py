#!/usr/bin/env python3
"""
main_gui.py - Interfaz gráfica refinada para el servicio de autenticación API iFR Pro
Diseño: limpio, gris neutro, botones simples y centrados
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import logging
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api_ifrpro'))
load_dotenv()

from api_ifrpro import APIClient
from config.settings import Settings


class TextHandler(logging.Handler):
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
    def __init__(self, root):
        self.root = root
        self.root.title("API iFR Pro - Servicio de Autenticación")
        self.root.geometry("900x550")
        self.root.configure(bg="#dfe1e4")

        self.setup_style()
        self.settings = Settings()
        self.setup_logging()
        self.initialize_client()
        self.create_widgets()

        self.log_info("=" * 50)
        self.log_info("API iFR Pro - Servicio de Autenticación Iniciado")
        self.log_info("=" * 50)
        self.show_service_info()

    def setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        bg_main = "#dfe1e4"
        bg_panel = "#c9cbcf"
        bg_log = "#2f3237"
        text_main = "#1f1f1f"
        btn_bg = "#4c4c4c"
        btn_hover = "#333333"

        style.configure(".", background=bg_main)
        style.configure("TFrame", background=bg_main)
        style.configure("TLabelframe", background=bg_panel, relief="solid", borderwidth=1)
        style.configure("TLabelframe.Label", background=bg_panel, foreground=text_main, font=("Segoe UI", 10, "bold"))
        style.configure("Title.TLabel", background=bg_main, foreground=text_main, font=("Segoe UI", 15, "bold"))
        style.configure("TButton", background=btn_bg, foreground="white", padding=8, font=("Segoe UI", 10), borderwidth=0)
        style.map("TButton", background=[("active", btn_hover)])

    def setup_logging(self):
        os.makedirs(self.settings.LOG_DIR, exist_ok=True)
        logging.basicConfig(
            level=getattr(logging, self.settings.LOG_LEVEL),
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
            handlers=[logging.FileHandler(os.path.join(self.settings.LOG_DIR, 'api_gui.log'), mode='a', encoding='utf-8')]
        )

    def initialize_client(self):
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
        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        # Encabezado
        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(header, text="API iFR Pro - Servicio de Autenticación", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="Limpiar Log", command=self.clear_log, width=12).pack(side=tk.RIGHT, padx=5)
        ttk.Button(header, text="Info", command=self.show_service_info, width=10).pack(side=tk.RIGHT, padx=5)
        self.status_label = ttk.Label(header, text="No conectado", background="#dfe1e4", font=("Segoe UI", 9))
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # Panel principal
        main_panel = ttk.LabelFrame(main, text="Panel Principal", padding=20)
        main_panel.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        main.rowconfigure(1, weight=2)

        # Panel inferior
        bottom = ttk.Frame(main)
        bottom.grid(row=2, column=0, sticky="nsew")
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=2)
        bottom.rowconfigure(0, weight=1)

        # Ajustes
        ajustes = ttk.LabelFrame(bottom, text="Ajustes", padding=20)
        ajustes.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ajustes.columnconfigure(0, weight=1)

        ttk.Button(ajustes, text="Probar conexión", command=self.test_authentication).grid(row=0, column=0, pady=(50, 10), sticky="ew")

        # Registro de actividad
        log_frame = ttk.LabelFrame(bottom, text="Registro de Actividad", padding=5)
        log_frame.grid(row=0, column=1, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Consolas", 9),
            bg="#2f3237", fg="#f1f1f1", insertbackground="white",
            height=12, borderwidth=0
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.configure(state='disabled')

        handler = TextHandler(self.log_text)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"))
        logging.getLogger().addHandler(handler)

        # Barra de progreso
        self.progress = ttk.Progressbar(main, mode='indeterminate')
        self.progress.grid(row=3, column=0, sticky="ew", pady=(10, 0))

    # --- Acciones ---
    def log_info(self, msg): logging.info(msg)
    def log_error(self, msg): logging.error(msg)
    def log_success(self, msg): logging.info(f"✅ {msg}")

    def start_progress(self): self.progress.start(10)
    def stop_progress(self): self.progress.stop()

    def run_in_thread(self, func, *args):
        def wrapper():
            try:
                self.start_progress()
                func(*args)
            except Exception as e:
                self.log_error(f"Error: {e}")
                messagebox.showerror("Error", str(e))
            finally:
                self.stop_progress()
        threading.Thread(target=wrapper, daemon=True).start()

    def show_service_info(self):
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
        def test():
            self.log_info("Probando autenticación...")
            try:
                if self.client.health_check():
                    self.log_success("Autenticación exitosa")
                    self.status_label.config(text="Conectado", foreground="green")
                    messagebox.showinfo("Éxito", "Autenticación exitosa")
                else:
                    self.log_error("Fallo en autenticación")
                    self.status_label.config(text="Error", foreground="red")
                    messagebox.showerror("Error", "Fallo en autenticación")
            except Exception as e:
                self.log_error(f"Error en autenticación: {e}")
                self.status_label.config(text="Error", foreground="red")
                messagebox.showerror("Error", f"Error en autenticación:\n{e}")
        self.run_in_thread(test)

    def clear_log(self):
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        self.log_info("=" * 50)
        self.log_info("Log limpiado")
        self.log_info("=" * 50)


def main():
    root = tk.Tk()
    app = APIAuthGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
