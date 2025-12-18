# Archivo: base_case.py
# Ubicación: raíz del proyecto.
# Descripción: Clase base para todos los casos de procesamiento de correo.

from config_manager import ConfigManager


class BaseCase:
    """Clase base para todos los casos de procesamiento de emails"""

    def __init__(self, name, description, config_key, response_message):
        """
        Inicializa un caso base

        Args:
            name: Nombre del caso
            description: Descripción del caso
            config_key: Clave para buscar configuración en config.json
            response_message: Mensaje de respuesta por defecto
        """
        self._name = name
        self._description = description
        self._config_key = config_key
        self._response_message = response_message
        self._config_manager = ConfigManager()

    def get_name(self):
        """Retorna el nombre del caso"""
        return self._name

    def get_description(self):
        """Retorna la descripción del caso"""
        return self._description

    def get_search_keywords(self):
        """
        Retorna las palabras clave de búsqueda desde config.json
        Lee la configuración guardada en search_params[config_key]
        """
        try:
            search_params = self._config_manager.get_search_params()
            keyword = search_params.get(self._config_key, '')

            if keyword and keyword.strip():
                # Retornar como lista con un solo elemento
                return [keyword.strip()]
            else:
                # Retornar lista vacía si no hay keyword configurado
                return []
        except Exception as e:
            print(f"Error al obtener keywords para {self._config_key}: {e}")
            return []

    def process_email(self, email_data, logger):
        """
        Procesa un email (debe ser implementado por las subclases)

        Args:
            email_data: Diccionario con datos del email
            logger: Logger para mensajes

        Returns:
            Diccionario con respuesta o None si falla
        """
        raise NotImplementedError("Las subclases deben implementar process_email()")