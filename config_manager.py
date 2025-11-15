# Archivo: config_manager.py
# Ubicación: raíz del proyecto
# Descripción: Gestiona la configuración y almacenamiento en JSON

import json
import os
import sys


class ConfigManager:
    def __init__(self, config_file="config.json"):
        """Inicializa el gestor de configuración"""
        # Determinar la ruta base según si es ejecutable o desarrollo
        if getattr(sys, 'frozen', False):
            # Si es ejecutable con PyInstaller
            # config.json debe estar al lado del .exe (editable por usuario)
            self.base_dir = os.path.dirname(sys.executable)
        else:
            # Si es desarrollo, usar directorio del script
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        # Ruta completa al archivo de configuración
        self.config_file = os.path.join(self.base_dir, config_file)

        # Si estamos en PyInstaller y el config no existe al lado del .exe, copiarlo desde el bundle
        if getattr(sys, 'frozen', False) and not os.path.exists(self.config_file):
            self._copy_config_from_bundle(config_file)

    def _copy_config_from_bundle(self, config_file):
        """Copia el config.json desde el bundle de PyInstaller al directorio del ejecutable"""
        try:
            bundled_config = os.path.join(sys._MEIPASS, config_file)
            if os.path.exists(bundled_config):
                import shutil
                shutil.copy2(bundled_config, self.config_file)
                print(f"✅ Config.json copiado desde bundle a: {self.config_file}")
            else:
                print(f"⚠️ Config.json no encontrado en bundle: {bundled_config}")
                # Crear un config vacío por defecto
                self.reset_config()
        except Exception as e:
            print(f"❌ Error al copiar config desde bundle: {e}")
            import traceback
            traceback.print_exc()

    @staticmethod
    def get_bundled_resource_path(resource_name):
        """
        Obtiene la ruta a un recurso empaquetado con PyInstaller.
        Para archivos que están dentro del bundle (ej: config_categorias.json)
        """
        if getattr(sys, 'frozen', False):
            # Si es ejecutable, usar el directorio temporal de PyInstaller
            base_path = sys._MEIPASS
        else:
            # Si es desarrollo, usar directorio del script
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, resource_name)

    def load_config(self):
        """Carga la configuración desde el archivo JSON"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as file:
                    config_data = json.load(file)

                    # Log solo la primera vez o si hay debug habilitado
                    frozen = getattr(sys, 'frozen', False)
                    if frozen:
                        print(f"[DEBUG ConfigManager] Sistema frozen: True")
                        print(f"[DEBUG ConfigManager] ✅ Config cargado desde: {self.config_file}")
                        if 'search_params' in config_data:
                            print(f"[DEBUG ConfigManager] ✅ search_params: {config_data['search_params']}")
                        else:
                            print(f"[DEBUG ConfigManager] ⚠️ 'search_params' NO encontrado en config.json")

                    return config_data
            else:
                print(f"[DEBUG ConfigManager] ⚠️ Archivo de configuración no encontrado: {self.config_file}")
                print(f"[DEBUG ConfigManager]    Buscando en: {self.base_dir}")
                print(f"[DEBUG ConfigManager]    Archivos en directorio: {os.listdir(self.base_dir) if os.path.exists(self.base_dir) else 'directorio no existe'}")
                return {}
        except Exception as e:
            print(f"[DEBUG ConfigManager] ❌ Error al cargar la configuración: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}

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