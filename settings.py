"""
Configuración del servicio de autenticación API
"""

import os
import json
from typing import Dict, Any
from pathlib import Path


class Settings:
    """Maneja la configuración del servicio"""

    def __init__(self):
        """Inicializa la configuración con valores por defecto o de entorno"""

        # API Configuration
        self.API_BASE_URL = os.getenv('API_BASE_URL', '')
        self.API_CUENTA = os.getenv('API_CUENTA', '')
        self.API_LLAVE = os.getenv('API_LLAVE', '')
        self.API_CODIGO_SERVICIO = os.getenv('API_CODIGO_SERVICIO', '')
        self.API_PAIS = os.getenv('API_PAIS', 'CR')
        self.API_TIMEOUT = int(os.getenv('API_TIMEOUT', '90'))

        # Application Settings
        # self.API_ENV = os.getenv('API_ENV', 'production')
        # self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        # self.DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

        self.API_ENV = os.getenv('API_ENV', 'development')
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
        self.DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'

        # File Settings / Si no existe la variable de entorno entonces utiliza
        # una Carpeta dentro del proyecto actual ("storage").
        log_dir = os.path.join(os.getcwd(), "storage")
        # os.makedirs(log_dir, exist_ok=True)

        self.UPLOAD_DIR = os.getenv('UPLOAD_DIR', log_dir)
        self.TEMP_DIR = os.getenv('TEMP_DIR', log_dir)
        self.LOG_DIR = os.getenv('LOG_DIR', os.path.join(log_dir, "logs"))
        self.DATA_DIR = os.getenv('DATA_DIR', log_dir)

        # File Restrictions
        self.MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '5242880'))  # 5MB default
        self.ALLOWED_EXTENSIONS = os.getenv('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,pdf,gif')
        self.MAX_FILES_PER_REQUEST = int(os.getenv('MAX_FILES_PER_REQUEST', '6'))

        # Security
        self.ENABLE_SSL_VERIFY = os.getenv('ENABLE_SSL_VERIFY', 'true').lower() == 'true'
        self.MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
        self.RATE_LIMIT_CALLS = int(os.getenv('RATE_LIMIT_CALLS', '200'))
        self.REQUEST_RETRY_COUNT = int(os.getenv('REQUEST_RETRY_COUNT', '3'))
        self.REQUEST_RETRY_DELAY = int(os.getenv('REQUEST_RETRY_DELAY', '1'))

        # Performance
        self.BATCH_SIZE = int(os.getenv('BATCH_SIZE', '5'))
        self.PARALLEL_UPLOADS = os.getenv('PARALLEL_UPLOADS', 'false').lower() == 'true'
        self.CONNECTION_POOL_SIZE = int(os.getenv('CONNECTION_POOL_SIZE', '10'))

        # Create directories if they don't exist
        # self._create_directories()

    def _create_directories(self):
        """Crea los directorios necesarios si no existen"""
        directories = [
            self.UPLOAD_DIR,
            self.TEMP_DIR,
            self.LOG_DIR,
            self.DATA_DIR
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def load_from_file(self, config_file: str):
        """
        Carga configuración desde un archivo JSON

        Args:
            config_file: Ruta al archivo de configuración
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {config_file}")

        with open(config_file, 'r') as f:
            config = json.load(f)

        # Actualizar valores
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def save_to_file(self, config_file: str):
        """
        Guarda la configuración actual en un archivo JSON

        Args:
            config_file: Ruta al archivo de configuración
        """
        config = {}

        for key in dir(self):
            if not key.startswith('_') and not callable(getattr(self, key)):
                config[key] = getattr(self, key)

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def validate(self) -> bool:
        """
        Valida la configuración actual

        Returns:
            True si la configuración es válida
        """
        errors = []

        # Validar credenciales requeridas
        if not self.API_CUENTA:
            errors.append("API_CUENTA no está configurado")

        if not self.API_LLAVE:
            errors.append("API_LLAVE no está configurado")

        if not self.API_CODIGO_SERVICIO:
            errors.append("API_CODIGO_SERVICIO no está configurado")

        # Validar URLs
        if not self.API_BASE_URL:
            errors.append("API_BASE_URL no está configurado")
        elif not (self.API_BASE_URL.startswith('http://') or
                  self.API_BASE_URL.startswith('https://')):
            errors.append("API_BASE_URL debe empezar con http:// o https://")

        # Validar valores numéricos
        if self.API_TIMEOUT <= 0:
            errors.append("API_TIMEOUT debe ser mayor a 0")

        if self.MAX_FILE_SIZE <= 0:
            errors.append("MAX_FILE_SIZE debe ser mayor a 0")

        if self.MAX_FILES_PER_REQUEST <= 0:
            errors.append("MAX_FILES_PER_REQUEST debe ser mayor a 0")

        if errors:
            for error in errors:
                print(f"❌ Error de configuración: {error}")
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la configuración a diccionario

        Returns:
            Diccionario con la configuración
        """
        config = {}

        for key in dir(self):
            if not key.startswith('_') and not callable(getattr(self, key)):
                config[key] = getattr(self, key)

        return config

    def __str__(self) -> str:
        """Representación en string de la configuración"""
        config = self.to_dict()

        # Ocultar información sensible
        if 'API_LLAVE' in config:
            config['API_LLAVE'] = config['API_LLAVE'][:10] + '...' if len(config['API_LLAVE']) > 10 else '***'

        return json.dumps(config, indent=2)

    def get_allowed_extensions_list(self) -> list:
        """
        Obtiene la lista de extensiones permitidas

        Returns:
            Lista de extensiones con punto (ej: ['.png', '.jpg'])
        """
        extensions = self.ALLOWED_EXTENSIONS.split(',')
        return [f".{ext.strip()}" for ext in extensions if ext.strip()]

    def is_development(self) -> bool:
        """
        Verifica si está en modo desarrollo

        Returns:
            True si está en modo desarrollo
        """
        return self.API_ENV.lower() in ['development', 'dev', 'local']

    def is_production(self) -> bool:
        """
        Verifica si está en modo producción

        Returns:
            True si está en modo producción
        """
        return self.API_ENV.lower() in ['production', 'prod']

    def update_from_dict(self, config: Dict[str, Any]):
        """
        Actualiza la configuración desde un diccionario

        Args:
            config: Diccionario con configuración
        """
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)
