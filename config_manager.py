# Archivo: config_manager.py
# Ubicación: raíz del proyecto
# Descripción: Gestiona la configuración y almacenamiento en JSON

import json
import os


class ConfigManager:
    def __init__(self, config_file="config.json"):
        """Inicializa el gestor de configuración"""
        self.config_file = config_file

    def load_config(self):
        """Carga la configuración desde el archivo JSON"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as file:
                    return json.load(file)
            else:
                return {}
        except Exception as e:
            print(f"Error al cargar la configuración: {str(e)}")
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
            'cc_users': [],
            'categorias_personalizadas': []
        }
        return self.save_config(default_config)

    # ===== MÉTODOS DE CATEGORÍAS PERSONALIZADAS =====

    def get_categorias_personalizadas(self):
        """Obtiene la lista de categorías personalizadas"""
        config = self.load_config()
        return config.get('categorias_personalizadas', [])

    def set_categorias_personalizadas(self, categorias):
        """
        Establece la lista completa de categorías personalizadas

        Args:
            categorias (list): Lista de diccionarios con estructura:
                [
                    {
                        "id": 1,
                        "nombre": "iPhone 15",
                        "tipo_dispositivo_id": 1,
                        "tipo_dispositivo_nombre": "Móviles"
                    },
                    ...
                ]
        """
        config = self.load_config()
        config['categorias_personalizadas'] = categorias
        return self.save_config(config)

    def agregar_categoria(self, nombre, tipo_dispositivo_id, tipo_dispositivo_nombre):
        """
        Agrega una nueva categoría personalizada

        Args:
            nombre (str): Nombre de la categoría
            tipo_dispositivo_id (int): ID del tipo de dispositivo
            tipo_dispositivo_nombre (str): Nombre del tipo de dispositivo

        Returns:
            bool: True si se guardó correctamente
        """
        categorias = self.get_categorias_personalizadas()

        # Obtener el siguiente ID disponible
        if categorias:
            nuevo_id = max(cat['id'] for cat in categorias) + 1
        else:
            nuevo_id = 1

        nueva_categoria = {
            'id': nuevo_id,
            'nombre': nombre,
            'tipo_dispositivo_id': tipo_dispositivo_id,
            'tipo_dispositivo_nombre': tipo_dispositivo_nombre
        }

        categorias.append(nueva_categoria)
        return self.set_categorias_personalizadas(categorias)

    def editar_categoria(self, categoria_id, nombre, tipo_dispositivo_id, tipo_dispositivo_nombre):
        """
        Edita una categoría existente

        Args:
            categoria_id (int): ID de la categoría a editar
            nombre (str): Nuevo nombre
            tipo_dispositivo_id (int): Nuevo ID del tipo de dispositivo
            tipo_dispositivo_nombre (str): Nuevo nombre del tipo de dispositivo

        Returns:
            bool: True si se editó correctamente
        """
        categorias = self.get_categorias_personalizadas()

        for cat in categorias:
            if cat['id'] == categoria_id:
                cat['nombre'] = nombre
                cat['tipo_dispositivo_id'] = tipo_dispositivo_id
                cat['tipo_dispositivo_nombre'] = tipo_dispositivo_nombre
                return self.set_categorias_personalizadas(categorias)

        return False

    def eliminar_categoria(self, categoria_id):
        """
        Elimina una categoría por su ID

        Args:
            categoria_id (int): ID de la categoría a eliminar

        Returns:
            bool: True si se eliminó correctamente
        """
        categorias = self.get_categorias_personalizadas()
        categorias = [cat for cat in categorias if cat['id'] != categoria_id]
        return self.set_categorias_personalizadas(categorias)

    def get_categoria_default(self):
        """
        Obtiene la categoría por defecto configurada

        Returns:
            dict: Categoría por defecto o None
        """
        config = self.load_config()
        return config.get('categoria_default', None)

    def set_categoria_default(self, categoria_id):
        """
        Establece la categoría por defecto

        Args:
            categoria_id (int): ID de la categoría a usar por defecto

        Returns:
            bool: True si se guardó correctamente
        """
        config = self.load_config()

        # Verificar que la categoría existe
        categorias = self.get_categorias_personalizadas()
        categoria = next((cat for cat in categorias if cat['id'] == categoria_id), None)

        if categoria:
            config['categoria_default'] = categoria
            return self.save_config(config)

        return False