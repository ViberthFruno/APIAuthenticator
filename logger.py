# Archivo: logger.py
# Ubicación: raíz del proyecto
# Descripción: Sistema de registro para mostrar mensajes en la interfaz

import tkinter as tk
import datetime


class Logger:
    def __init__(self):
        """Inicializa el sistema de registro"""
        self.text_widget = None

    def set_text_widget(self, text_widget):
        """Establece el widget de texto donde se mostrarán los logs"""
        self.text_widget = text_widget

    def log(self, message, level="INFO"):
        """Registra un mensaje con un nivel específico"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{now}] [{level}] {message}\n"

        print(log_message, end="")

        if self.text_widget:
            tag = f"tag_{level.lower()}"
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, log_message, tag)

            if level == "ERROR":
                self.text_widget.tag_config(tag, foreground="red")
            elif level == "WARNING":
                self.text_widget.tag_config(tag, foreground="orange")
            elif level == "INFO":
                self.text_widget.tag_config(tag, foreground="blue")

            self.text_widget.see(tk.END)
            self.text_widget.config(state=tk.DISABLED)