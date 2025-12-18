# Archivo: config_manager.py
# Ubicación: raíz del proyecto.
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
            # Debug: Mostrar información del sistema
            is_frozen = getattr(sys, 'frozen', False)
            print(f"[DEBUG ConfigManager] Sistema frozen: {is_frozen}")
            print(f"[DEBUG ConfigManager] Base dir: {self.base_dir}")
            print(f"[DEBUG ConfigManager] Buscando config en: {self.config_file}")
            print(f"[DEBUG ConfigManager] ¿Existe el archivo? {os.path.exists(self.config_file)}")

            if os.path.exists(self.config_file):
                print(f"[DEBUG ConfigManager] ✓ Archivo encontrado, cargando...")
                with open(self.config_file, 'r', encoding='utf-8') as file:
                    config_data = json.load(file)
                    print(f"[DEBUG ConfigManager] ✓ Config cargada: {list(config_data.keys())}")
                    if 'search_params' in config_data:
                        print(f"[DEBUG ConfigManager] ✓ search_params: {config_data['search_params']}")
                    return config_data
            else:
                print(f"[DEBUG ConfigManager] ❌ Archivo NO encontrado")
                print(f"   ⚠️  Archivo de configuración no encontrado: {self.config_file}")
                print(f"   📁 Directorio actual: {os.getcwd()}")
                print(f"   📁 Archivos en base_dir:")
                try:
                    files_in_dir = os.listdir(self.base_dir)
                    for f in files_in_dir[:10]:  # Mostrar solo primeros 10
                        print(f"      - {f}")
                except Exception as list_err:
                    print(f"      Error al listar: {list_err}")
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

    def get_categorias_config_path(self):
        """Obtiene la ruta al archivo de configuración de categorías"""
        return os.path.join(self.base_dir, "config_categorias.json")

    def load_categorias_config(self):
        """Carga la configuración de categorías desde el archivo JSON"""
        categorias_file = self.get_categorias_config_path()

        # Categorías por defecto
        default_categorias = {
            "categorias": {
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
        }

        try:
            print(f"[DEBUG ConfigManager] Buscando config_categorias.json en: {categorias_file}")
            print(f"[DEBUG ConfigManager] ¿Existe el archivo? {os.path.exists(categorias_file)}")

            if os.path.exists(categorias_file):
                print(f"[DEBUG ConfigManager] ✓ Archivo encontrado, cargando...")
                with open(categorias_file, 'r', encoding='utf-8') as file:
                    config_data = json.load(file)
                    print(
                        f"[DEBUG ConfigManager] ✓ Categorías cargadas: {list(config_data.get('categorias', {}).keys())}")
                    return config_data
            else:
                print(f"[DEBUG ConfigManager] ❌ Archivo NO encontrado, creando con valores por defecto...")
                # Crear el archivo con valores por defecto
                self.save_categorias_config(default_categorias)
                print(f"[DEBUG ConfigManager] ✓ Archivo config_categorias.json creado en: {categorias_file}")
                return default_categorias

        except Exception as e:
            print(f"[DEBUG ConfigManager] ❌ Error al cargar categorías: {str(e)}")
            import traceback
            traceback.print_exc()
            # Si hay error, intentar crear el archivo con valores por defecto
            try:
                self.save_categorias_config(default_categorias)
                return default_categorias
            except:
                return default_categorias

    def save_categorias_config(self, config):
        """Guarda la configuración de categorías en el archivo JSON"""
        categorias_file = self.get_categorias_config_path()
        try:
            with open(categorias_file, 'w', encoding='utf-8') as file:
                json.dump(config, file, indent=2, ensure_ascii=False)
            print(f"[DEBUG ConfigManager] ✓ Categorías guardadas en: {categorias_file}")
            return True
        except Exception as e:
            print(f"[DEBUG ConfigManager] ❌ Error al guardar categorías: {str(e)}")
            return False


# ============================================================================
# FUNCIONES GLOBALES - Para usar desde cualquier módulo sin instancia
# ============================================================================

def get_categorias_config_path():
    """
    Función global para obtener la ruta correcta a config_categorias.json
    Compatible con PyInstaller y desarrollo.

    IMPORTANTE: Usar esta función en lugar de rutas hardcodeadas.

    Returns:
        str: Ruta absoluta al archivo config_categorias.json
    """
    if getattr(sys, 'frozen', False):
        # Si es ejecutable con PyInstaller
        # config_categorias.json debe estar al lado del .exe
        base_dir = os.path.dirname(sys.executable)
    else:
        # Si es desarrollo, usar directorio del script
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, 'config_categorias.json')


def get_categorias_config():
    """
    Función global para cargar la configuración de categorías.
    Compatible con PyInstaller y desarrollo.

    IMPORTANTE: Usar esta función en TODOS los módulos que necesiten
    leer config_categorias.json (especialmente en api_integration/).

    Returns:
        Dict: Configuración de categorías con estructura:
              {
                  "categorias": {
                      "Móviles": {"id": 1, "palabras_clave": [...]},
                      ...
                  }
              }
    """
    # Usar la instancia del ConfigManager para aprovechar toda su lógica
    manager = ConfigManager()
    return manager.load_categorias_config()


def save_categorias_config(config):
    """
    Función global para guardar la configuración de categorías.
    Compatible con PyInstaller y desarrollo.

    Args:
        config (Dict): Configuración de categorías a guardar

    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    manager = ConfigManager()
    return manager.save_categorias_config(config)


# ============================================================================
# FUNCIONES PARA CONFIGURACIÓN DE PROVEEDORES
# ============================================================================

def get_proveedores_config_path():
    """
    Función global para obtener la ruta correcta a config_proveedores.json
    Compatible con PyInstaller y desarrollo.

    Returns:
        str: Ruta absoluta al archivo config_proveedores.json
    """
    if getattr(sys, 'frozen', False):
        # Si es ejecutable con PyInstaller
        base_dir = os.path.dirname(sys.executable)
    else:
        # Si es desarrollo, usar directorio del script
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, 'config_proveedores.json')


def get_proveedores_config():
    """
    Función global para cargar la configuración de proveedores.
    Compatible con PyInstaller y desarrollo.

    Returns:
        Dict: Configuración de proveedores con estructura:
              {
                  "palabras_clave_campo": ["PROVEEDOR", "PROBEDOR", "PROVEDOR", ...],
                  "proveedores": {
                      "MobilePro": {
                          "id": "UUID",
                          "palabras_clave": ["MOBILEPRO", "MOBILE PRO", ...]
                      },
                      ...
                  }
              }
    """
    proveedores_file = get_proveedores_config_path()

    # Proveedores por defecto con sus UUIDs
    default_proveedores = {
        "palabras_clave_campo": [
            "PROVEEDOR",
            "PROBEDOR",
            "PROVEDOR",
            "PROBEEDOR",
            "PROVEHEDOR",
            "PROOVEDOR"
        ],
        "proveedores": {
            "MobilePro": {
                "id": "4d368873-4488-416f-9996-a95c416eaec2",
                "palabras_clave": ["MOBILEPRO", "MOBILE PRO"]
            },
            "Suplidora Movil": {
                "id": "af3e8a46-cd6a-4eae-a1d1-8b6c1a8111d7",
                "palabras_clave": ["SUPLIDORA MOVIL", "SUPLIDORA", "SUPLIDORAMOVIL"]
            },
            "Liberty": {
                "id": "560600c2-60d5-42a7-9478-e9d1fef48a97",
                "palabras_clave": ["LIBERTY"]
            },
            "CTC GRUP": {
                "id": "497c7e40-7e8a-45bd-962f-a79f5f5fe641",
                "palabras_clave": ["CTC GRUP", "CTCGRUP", "CTC-GRUP"]
            },
            "OSL": {
                "id": "88f9f5fd-4569-40dd-bc20-9a34097dcedd",
                "palabras_clave": ["OSL"]
            },
            "MAJICAL": {
                "id": "796b6e10-539d-479b-89d8-644c564308c6",
                "palabras_clave": ["MAJICAL", "MAGICAL"]
            },
            "INTCOMEX": {
                "id": "66e20464-0afa-4d7e-9e33-8cb7a358731f",
                "palabras_clave": ["INTCOMEX", "INT COMEX", "INTCOMEX"]
            },
            "Mobiltech": {
                "id": "b24941fa-955f-4a66-9326-da6aaf8b18d1",
                "palabras_clave": ["MOBILTECH", "MOBIL TECH", "MOVILTECH"]
            },
            "CTC GROUP": {
                "id": "235b222e-ad2d-4493-9e0d-24eae244f8f9",
                "palabras_clave": ["CTC GROUP", "CTCGROUP", "CTC-GROUP"]
            }
        }
    }

    try:
        print(f"[DEBUG ConfigManager] Buscando config_proveedores.json en: {proveedores_file}")
        print(f"[DEBUG ConfigManager] ¿Existe el archivo? {os.path.exists(proveedores_file)}")

        if os.path.exists(proveedores_file):
            print(f"[DEBUG ConfigManager] ✓ Archivo encontrado, cargando...")
            with open(proveedores_file, 'r', encoding='utf-8') as file:
                config_data = json.load(file)
                print(f"[DEBUG ConfigManager] ✓ Proveedores cargados: {list(config_data.get('proveedores', {}).keys())}")
                return config_data
        else:
            print(f"[DEBUG ConfigManager] ❌ Archivo NO encontrado, creando con valores por defecto...")
            # Crear el archivo con valores por defecto
            save_proveedores_config(default_proveedores)
            print(f"[DEBUG ConfigManager] ✓ Archivo config_proveedores.json creado en: {proveedores_file}")
            return default_proveedores

    except Exception as e:
        print(f"[DEBUG ConfigManager] ❌ Error al cargar proveedores: {str(e)}")
        import traceback
        traceback.print_exc()
        # Si hay error, intentar crear el archivo con valores por defecto
        try:
            save_proveedores_config(default_proveedores)
            return default_proveedores
        except:
            return default_proveedores


def save_proveedores_config(config):
    """
    Función global para guardar la configuración de proveedores.
    Compatible con PyInstaller y desarrollo.

    Args:
        config (Dict): Configuración de proveedores a guardar

    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    proveedores_file = get_proveedores_config_path()
    try:
        with open(proveedores_file, 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=2, ensure_ascii=False)
        print(f"[DEBUG ConfigManager] ✓ Proveedores guardados en: {proveedores_file}")
        return True
    except Exception as e:
        print(f"[DEBUG ConfigManager] ❌ Error al guardar proveedores: {str(e)}")
        return False


# ============================================================================
# FUNCIONES PARA CONFIGURACIÓN DE SERVITOTAL (MAPEO DE CÓDIGOS)
# ============================================================================

def get_servitotal_config_path():
    """
    Función global para obtener la ruta correcta a config_servitotal.json
    Compatible con PyInstaller y desarrollo.

    Returns:
        str: Ruta absoluta al archivo config_servitotal.json
    """
    if getattr(sys, 'frozen', False):
        # Si es ejecutable con PyInstaller
        base_dir = os.path.dirname(sys.executable)
    else:
        # Si es desarrollo, usar directorio del script
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, 'config_servitotal.json')


def get_servitotal_config():
    """
    Función global para cargar la configuración de mapeos de códigos servitotal.
    Compatible con PyInstaller y desarrollo.

    Returns:
        Dict: Configuración de mapeos servitotal con estructura:
              {
                  "mapeos": [
                      {"codigo_buscar": "00", "codigo_enviar": "123"},
                      {"codigo_buscar": "01", "codigo_enviar": "456"}
                  ]
              }
    """
    servitotal_file = get_servitotal_config_path()

    # Configuración por defecto
    default_servitotal = {
        "mapeos": []
    }

    try:
        print(f"[DEBUG ConfigManager] Buscando config_servitotal.json en: {servitotal_file}")
        print(f"[DEBUG ConfigManager] ¿Existe el archivo? {os.path.exists(servitotal_file)}")

        if os.path.exists(servitotal_file):
            print(f"[DEBUG ConfigManager] ✓ Archivo encontrado, cargando...")
            with open(servitotal_file, 'r', encoding='utf-8') as file:
                config_data = json.load(file)
                print(f"[DEBUG ConfigManager] ✓ Mapeos servitotal cargados: {len(config_data.get('mapeos', []))} mapeos")
                return config_data
        else:
            print(f"[DEBUG ConfigManager] ❌ Archivo NO encontrado, creando con valores por defecto...")
            # Crear el archivo con valores por defecto
            save_servitotal_config(default_servitotal)
            print(f"[DEBUG ConfigManager] ✓ Archivo config_servitotal.json creado en: {servitotal_file}")
            return default_servitotal

    except Exception as e:
        print(f"[DEBUG ConfigManager] ❌ Error al cargar servitotal: {str(e)}")
        import traceback
        traceback.print_exc()
        # Si hay error, intentar crear el archivo con valores por defecto
        try:
            save_servitotal_config(default_servitotal)
            return default_servitotal
        except:
            return default_servitotal


def save_servitotal_config(config):
    """
    Función global para guardar la configuración de mapeos servitotal.
    Compatible con PyInstaller y desarrollo.

    Args:
        config (Dict): Configuración de mapeos servitotal a guardar

    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    servitotal_file = get_servitotal_config_path()
    try:
        with open(servitotal_file, 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=2, ensure_ascii=False)
        print(f"[DEBUG ConfigManager] ✓ Mapeos servitotal guardados en: {servitotal_file}")
        return True
    except Exception as e:
        print(f"[DEBUG ConfigManager] ❌ Error al guardar servitotal: {str(e)}")
        return False