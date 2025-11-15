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

    def get_search_keywords(self, logger=None):
        """Obtiene las palabras clave de búsqueda desde la configuración"""
        def log(msg, level='info'):
            """Helper para loggear tanto con logger como con print"""
            if logger:
                getattr(logger, level)(msg)
            else:
                print(msg)

        try:
            config_manager = ConfigManager()
            config = config_manager.load_config()

            if not config:
                log(f"⚠️ ADVERTENCIA: Configuración vacía para {self._config_key}", 'warning')
                return []

            search_params = config.get('search_params', {})
            if not search_params:
                log(f"⚠️ ADVERTENCIA: 'search_params' vacío en config.json para {self._config_key}", 'warning')
                return []

            keyword = search_params.get(self._config_key, '').strip()

            if keyword:
                log(f"✅ Palabra clave cargada para {self._config_key}: '{keyword}'", 'info')
                return [keyword]
            else:
                log(f"⚠️ ADVERTENCIA: No hay palabra clave configurada para {self._config_key} en config.json", 'warning')
                return []

        except Exception as e:
            log(f"❌ ERROR al cargar palabras clave para {self._config_key}: {e}", 'error')
            if logger:
                logger.exception(f"Traceback completo:")
            else:
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