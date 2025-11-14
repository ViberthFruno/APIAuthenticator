# Archivo: base_case.py
# Ubicación: raíz del proyecto
# Descripción: Clase base reutilizable para los casos de respuesta automática

from config_manager import ConfigManager


class BaseCase:
    """Implementa comportamiento común para los casos"""

    def __init__(self, name, description, config_key, response_message):
        self._name = name
        self._description = description
        self._config_key = config_key
        self._response_message = response_message

    def get_name(self):
        """Retorna el nombre del caso"""
        return self._name

    def get_description(self):
        """Retorna la descripción del caso"""
        return self._description

    def get_search_keywords(self):
        """Obtiene las palabras clave de búsqueda desde la configuración"""
        try:
            config = ConfigManager().load_config()
            search_param = config.get('search_params', {}).get(self._config_key)

            # Formato nuevo: {"keywords": [...], "senders": [...]}
            if isinstance(search_param, dict):
                keywords = search_param.get('keywords', [])
                return keywords if isinstance(keywords, list) else [keywords]

            # Formato antiguo (retrocompatible): "Gollo"
            elif isinstance(search_param, str):
                keyword = search_param.strip()
                return [keyword] if keyword else []

            return []
        except Exception as e:
            print(f"Error al cargar palabras clave para {self._config_key}: {e}")
            return []

    def get_search_senders(self):
        """Obtiene los dominios/correos permitidos desde la configuración"""
        try:
            config = ConfigManager().load_config()
            search_param = config.get('search_params', {}).get(self._config_key)

            # Solo el formato nuevo soporta senders
            if isinstance(search_param, dict):
                senders = search_param.get('senders', [])
                return senders if isinstance(senders, list) else [senders]

            return []
        except Exception as e:
            print(f"Error al cargar senders para {self._config_key}: {e}")
            return []

    def get_response_message(self):
        """Retorna el mensaje de respuesta"""
        return self._response_message

    def set_response_message(self, message):
        """Establece el mensaje de respuesta"""
        self._response_message = message

    def process_email(self, email_data, logger):
        """
        Procesa un email y genera una respuesta.
        Los casos específicos pueden hacer override de este método.
        """
        try:
            sender = email_data.get('sender', '')
            subject = email_data.get('subject', '')

            logger.info(f"Procesando {self._config_key} para email de {sender}")

            response = {
                'recipient': sender,
                'subject': f"Re: {subject}",
                'body': self._response_message
            }

            logger.info(f"Respuesta generada para {self._config_key}")
            return response

        except Exception as e:
            logger.exception(f"Error al procesar email en {self._config_key}: {str(e)}")
            return None