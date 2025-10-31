import os
import requests
from pathlib import Path
from api_authenticator import APIAuthenticator

class MultipartFormDataClient:
    """
    Cliente especializado para manejar peticiones con archivos
    """
    
    def __init__(self, cuenta_api: str, llave_api: str, 
                 codigo_servicio: str, pais: str = "CR"):
        self.auth = APIAuthenticator(cuenta_api, llave_api, codigo_servicio, pais)
    
    def post_with_files(self, url: str, data: dict, files: list):
        """
        Realiza POST con archivos
        
        Args:
            url: URL completa del endpoint
            data: Diccionario con los campos del formulario (sin archivos)
            files: Lista de tuplas con los archivos
                   Formato: [('campo', ('nombre.ext', contenido, 'mime/type')), ...]
        """
        import uuid
        
        # Generar boundary para la firma
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex[:16]}"
        
        # Headers para autorización
        headers_for_auth = {
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }
        
        # Generar autorización (sin archivos en el body)
        auth_headers = self.auth.generar_autorizacion(
            method="POST",
            url=url,
            headers=headers_for_auth,
            body=data,  # Solo datos, sin archivos
            query_params=None
        )
        
        # Headers finales (sin Content-Type)
        final_headers = {
            "Accept": "application/json",
            "Authorization": auth_headers["Authorization"],
            "X-IfrPro-Ahora": auth_headers["X-IfrPro-Ahora"],
            "Host": auth_headers["Host"]
        }
        
        # Realizar petición
        return requests.post(
            url,
            headers=final_headers,
            data=data,
            files=files
        )
    
    def upload_files_from_paths(self, url: str, data: dict, file_paths: list, 
                                field_name: str = "archivos"):
        """
        Helper para subir archivos desde rutas en disco
        
        Args:
            url: URL del endpoint
            data: Datos del formulario
            file_paths: Lista de rutas de archivos
            field_name: Nombre del campo para los archivos
        """
        files = []
        
        for file_path in file_paths:
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                extension = Path(file_path).suffix.lower()
                
                # Mime types comunes
                mime_types = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.pdf': 'application/pdf'
                }
                
                mime_type = mime_types.get(extension, 'application/octet-stream')
                
                with open(file_path, 'rb') as f:
                    files.append((field_name, (filename, f.read(), mime_type)))
                
                print(f"✓ Preparado: {filename} ({mime_type})")
            else:
                print(f"✗ No encontrado: {file_path}")
        
        if files:
            return self.post_with_files(url, data, files)
        else:
            raise ValueError("No se encontraron archivos válidos para subir")

