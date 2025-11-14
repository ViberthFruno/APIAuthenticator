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
            print(f"[DEBUG {self._config_key}] Obteniendo palabras clave...")
            config = ConfigManager().load_config()
            print(f"[DEBUG {self._config_key}] Config keys: {list(config.keys())}")

            search_params = config.get('search_params', {})
            print(f"[DEBUG {self._config_key}] search_params: {search_params}")

            keyword = search_params.get(self._config_key, '').strip()
            print(f"[DEBUG {self._config_key}] Keyword para '{self._config_key}': '{keyword}'")

            result = [keyword] if keyword else []
            print(f"[DEBUG {self._config_key}] Retornando keywords: {result}")
            return result
        except Exception as e:
            print(f"[DEBUG {self._config_key}] ❌ Error al cargar palabras clave: {e}")
            import traceback
            traceback.print_exc()
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