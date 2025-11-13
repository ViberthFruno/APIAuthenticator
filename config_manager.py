# Archivo: config_manager.py
# Ubicación: raíz del proyecto
# Descripción: Gestiona la configuración y almacenamiento en JSON

import json
import os


class ConfigManager:
    def __init__(self, config_file="config.json"):
        """Inicializa el gestor de configuración"""
        self.config_file = config_file
        # Asegurar que existe un archivo de configuración válido al inicializar
        self._ensure_valid_config()

    def _ensure_valid_config(self):
        """Asegura que existe un archivo de configuración válido"""
        try:
            # Si el archivo no existe o está vacío, crear uno limpio
            if not os.path.exists(self.config_file) or os.path.getsize(self.config_file) == 0:
                print(f"⚠️  Archivo de configuración no encontrado o vacío. Creando uno nuevo...")
                self._create_clean_config()
                return

            # Intentar cargar el archivo para verificar que es JSON válido
            with open(self.config_file, 'r', encoding='utf-8') as file:
                json.load(file)
        except json.JSONDecodeError as e:
            print(f"⚠️  Archivo de configuración corrupto: {str(e)}")
            print(f"   Creando nuevo archivo de configuración limpio...")
            self._create_clean_config()
        except Exception as e:
            print(f"⚠️  Error al verificar configuración: {str(e)}")
            print(f"   Creando nuevo archivo de configuración limpio...")
            self._create_clean_config()

    def _create_clean_config(self):
        """Crea un archivo de configuración limpio con valores por defecto"""
        default_config = {
            'provider': '',
            'email': '',
            'password': '',
            'search_params': {
                'caso1': '',
                'titular_correo': ''
            },
            'cc_users': []
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as file:
                json.dump(default_config, file, indent=4, ensure_ascii=False)
            print(f"✅ Archivo de configuración creado: {self.config_file}")
        except Exception as e:
            print(f"❌ Error al crear archivo de configuración: {str(e)}")

    def load_config(self):
        """Carga la configuración desde el archivo JSON"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as file:
                    config = json.load(file)
                    # Asegurar que tiene las claves necesarias
                    if 'search_params' not in config:
                        config['search_params'] = {}
                    if 'cc_users' not in config:
                        config['cc_users'] = []
                    return config
            else:
                # Si no existe, crear uno limpio y devolverlo
                self._create_clean_config()
                return self.load_config()
        except json.JSONDecodeError as e:
            print(f"Error: JSON corrupto - {str(e)}")
            print("Creando nuevo archivo de configuración...")
            self._create_clean_config()
            return self.load_config()
        except Exception as e:
            print(f"Error al cargar la configuración: {str(e)}")
            return {
                'provider': '',
                'email': '',
                'password': '',
                'search_params': {},
                'cc_users': []
            }

    def save_config(self, config):
        """Guarda la configuración en el archivo JSON"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as file:
                json.dump(config, file, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error al guardar la configuración: {str(e)}")
            return False

    def get_value(self, key, default=None):
        """Obtiene un valor específico de la configuración"""
        config = self.load_config()
        return config.get(key, default)

    def set_value(self, key, value):
        """Establece un valor específico en la configuración"""
        config = self.load_config()
        config[key] = value
        return self.save_config(config)

    def get_email_config(self):
        """Obtiene la configuración de correo electrónico"""
        config = self.load_config()
        return {
            'provider': config.get('provider', ''),
            'email': config.get('email', ''),
            'password': config.get('password', '')
        }

    def set_email_config(self, provider, email, password):
        """Establece la configuración de correo electrónico"""
        config = self.load_config()
        config['provider'] = provider
        config['email'] = email
        config['password'] = password
        return self.save_config(config)

    def get_search_params(self):
        """Obtiene todos los parámetros de búsqueda"""
        config = self.load_config()
        return config.get('search_params', {})

    def set_search_params(self, search_params):
        """Establece todos los parámetros de búsqueda"""
        config = self.load_config()
        config['search_params'] = search_params
        return self.save_config(config)

    def has_email_config(self):
        """Verifica si existe configuración completa de correo"""
        email_config = self.get_email_config()
        return all([email_config['provider'], email_config['email'], email_config['password']])

    def has_search_params(self):
        """Verifica si existen parámetros de búsqueda configurados"""
        search_params = self.get_search_params()
        return bool(search_params)

    def validate_config(self):
        """Valida la configuración completa"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        if not self.has_email_config():
            validation_result['valid'] = False
            validation_result['errors'].append("Configuración de correo incompleta")

        if not self.has_search_params():
            validation_result['warnings'].append("No hay parámetros de búsqueda configurados")

        try:
            config = self.load_config()
            if not isinstance(config, dict):
                validation_result['valid'] = False
                validation_result['errors'].append("Archivo de configuración corrupto")
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Error al validar configuración: {str(e)}")

        return validation_result

    def reset_config(self):
        """Resetea la configuración a valores por defecto"""
        default_config = {
            'provider': '',
            'email': '',
            'password': '',
            'search_params': {},
            'cc_users': []
        }
        return self.save_config(default_config)