import os
import uuid
import logging
from pathlib import Path
from typing import List, Tuple
import requests
from requests.exceptions import RequestException

from api_authenticator import APIAuthenticator

logger = logging.getLogger(__name__)


class APIClient:
    """Cliente de API con autenticación HMAC-SHA384 integrada"""
    
    def __init__(self, cuenta_api: str = None, llave_api: str = None, 
                 codigo_servicio: str = None, pais: str = None, 
                 base_url: str = None, timeout: int = 30, verify: bool = True):
        """
        Inicializa el cliente de API
        
        Args:
            cuenta_api: ID de la cuenta API
            llave_api: Llave secreta de la API
            codigo_servicio: Código del servicio
            pais: Código del país (default: "CR")
            base_url: URL base de la API
            timeout: Timeout para las peticiones en segundos
        """
        # Obtener valores de variables de entorno si no se proporcionan
        self.cuenta_api = cuenta_api or os.environ.get('API_CUENTA', 'CD2D')
        self.llave_api = llave_api or os.environ.get('API_LLAVE', 'ifr-pruebas-F7EC2E')
        self.codigo_servicio = codigo_servicio or os.environ.get('API_CODIGO_SERVICIO', 'cd85e')
        self.pais = pais or os.environ.get('API_PAIS', 'CR')
        self.base_url = base_url or os.environ.get('API_BASE_URL', 'https://api.ejemplo.com')
        self.timeout = timeout
        self.verify = verify
        
        # Inicializar autenticador
        self.auth = APIAuthenticator(
            self.cuenta_api, 
            self.llave_api, 
            self.codigo_servicio, 
            self.pais
        )

        # Crear sesión de requests para reutilizar conexiones
        self.session = requests.Session()
        
        logger.info(f"Cliente API inicializado para {self.base_url}")
    
    def _prepare_request(self, method: str, endpoint: str, 
                        headers: dict = None, body: dict = None, 
                        query_params: dict = None) -> Tuple[str, dict]:
        """
        Prepara la petición con autenticación
        
        Args:
            method: Método HTTP
            endpoint: Endpoint de la API
            headers: Headers adicionales
            body: Body de la petición
            query_params: Parámetros de query
            
        Returns:
            Tupla con (url completa, headers con autenticación)
        """
        url = f"{self.base_url}{endpoint}"
        headers = headers or {}
        
        # Agregar headers por defecto
        if "Accept" not in headers:
            headers["Accept"] = "application/json"
        
        # Generar headers de autorización
        auth_headers = self.auth.generar_autorizacion(
            method=method,
            url=url,
            headers=headers,
            body=body,
            query_params=query_params
        )
        
        # Combinar headers
        headers.update(auth_headers)
        
        return url, headers
    
    def get(self, endpoint: str, params: dict = None, 
            headers: dict = None) -> requests.Response:
        """Realiza una petición GET"""
        url, headers = self._prepare_request("GET", endpoint, headers, None, params)
        
        logger.debug(f"GET {url}")
        try:
            response = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
            #logger.info(f"Headers enviados: {headers}")
            logger.info(f"GET {endpoint}: {response.status_code}")
            return response
        except RequestException as e:
            logger.error(f"Error en GET {endpoint}: {e}")
            raise
    
    def post(self, endpoint: str, data: dict = None, 
             headers: dict = None) -> requests.Response:
        """Realiza una petición POST"""
        url, headers = self._prepare_request("POST", endpoint, headers, data, None)
        
        logger.debug(f"POST {url}")
        try:
            response = self.session.post(url, headers=headers, data=data, timeout=self.timeout)
            logger.info(f"POST {endpoint}: {response.status_code}")
            return response
        except RequestException as e:
            logger.error(f"Error en POST {endpoint}: {e}")
            raise
    
    def put(self, endpoint: str, data: dict = None, 
            headers: dict = None) -> requests.Response:
        """Realiza una petición PUT"""
        url, headers = self._prepare_request("PUT", endpoint, headers, data, None)
        
        logger.debug(f"PUT {url}")
        try:
            response = self.session.put(url, headers=headers, data=data, timeout=self.timeout)
            logger.info(f"PUT {endpoint}: {response.status_code}")
            return response
        except RequestException as e:
            logger.error(f"Error en PUT {endpoint}: {e}")
            raise
    
    def delete(self, endpoint: str, headers: dict = None) -> requests.Response:
        """Realiza una petición DELETE"""
        url, headers = self._prepare_request("DELETE", endpoint, headers, None, None)
        
        logger.debug(f"DELETE {url}")
        try:
            response = self.session.delete(url, headers=headers, timeout=self.timeout)
            logger.info(f"DELETE {endpoint}: {response.status_code}")
            return response
        except RequestException as e:
            logger.error(f"Error en DELETE {endpoint}: {e}")
            raise
    
    def post_with_files(self, endpoint: str, data: dict, 
                       files: List[Tuple]) -> requests.Response:
        """
        Realiza POST con archivos (multipart/form-data)
        
        Args:
            endpoint: Endpoint de la API
            data: Diccionario con los campos del formulario (sin archivos)
            files: Lista de tuplas con los archivos
                   Formato: [('campo', ('nombre.ext', contenido, 'mime/type')), ...]
                   
        Returns:
            Response de la petición
        """
        url = f"{self.base_url}{endpoint}"
        
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

        logger.debug(f"POST con archivos {url}: {len(files)} archivos")
        
        try:
            response = self.session.post(
                url,
                headers=final_headers,
                data=data,
                files=files,
                timeout=self.timeout
            )
            logger.info(f"POST con archivos {endpoint}: {response.status_code}")
            return response
        except RequestException as e:
            logger.error(f"Error en POST con archivos {endpoint}: {e}")
            raise
    
    def upload_files(self, endpoint: str, data: dict, 
                    file_paths: List[str], 
                    field_name: str = "archivos") -> requests.Response:
        """
        Helper para subir archivos desde rutas en disco
        
        Args:
            endpoint: Endpoint de la API
            data: Datos del formulario (sin archivos)
            file_paths: Lista de rutas de archivos
            field_name: Nombre del campo para los archivos
            
        Returns:
            Response de la petición
        """
        files = []
        
        # Mime types comunes
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.zip': 'application/zip'
        }
        
        for file_path in file_paths:
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                extension = Path(file_path).suffix.lower()
                mime_type = mime_types.get(extension, 'application/octet-stream')
                
                try:
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                        files.append((field_name, (filename, file_content, mime_type)))
                    
                    file_size = len(file_content)
                    logger.debug(f"Archivo preparado: {filename} ({mime_type}) - {file_size:,} bytes")
                except IOError as e:
                    logger.error(f"Error leyendo archivo {file_path}: {e}")
            else:
                logger.warning(f"Archivo no encontrado: {file_path}")
        
        if not files:
            raise ValueError("No se encontraron archivos válidos para subir")
        
        logger.info(f"Subiendo {len(files)} archivos a {endpoint}")
        return self.post_with_files(endpoint, data, files)
    
    def batch_upload(self, endpoint: str, data: dict,
                    directory: str, extensions: List[str] = None,
                    field_name: str = "archivos",
                    max_files: int = None) -> requests.Response:
        """
        Sube todos los archivos de un directorio
        
        Args:
            endpoint: Endpoint de la API
            data: Datos del formulario
            directory: Directorio con los archivos
            extensions: Extensiones permitidas (None = todas)
            field_name: Nombre del campo para los archivos
            max_files: Número máximo de archivos a subir
            
        Returns:
            Response de la petición
        """
        if not os.path.exists(directory):
            raise ValueError(f"Directorio no encontrado: {directory}")
        
        # Extensiones por defecto
        if extensions is None:
            extensions = ['.png', '.jpg', '.jpeg', '.pdf', '.gif']
        
        # Recolectar archivos
        file_paths = []
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            
            if os.path.isfile(file_path):
                extension = Path(file_path).suffix.lower()
                
                if extension in extensions:
                    file_paths.append(file_path)
                    
                    if max_files and len(file_paths) >= max_files:
                        break
        
        if not file_paths:
            raise ValueError(f"No se encontraron archivos válidos en {directory}")
        
        logger.info(f"Encontrados {len(file_paths)} archivos en {directory}")
        
        return self.upload_files(endpoint, data, file_paths, field_name)
    
    def health_check(self) -> bool:
        """
        Verifica la conectividad con la API
        
        Returns:
            True si la API responde, False en caso contrario
        """
        try:
            response = self.get("/", headers={"Accept": "application/json"})
           # logger.info(f"Headers: {response.headers}")
           # logger.info(f"Response: {response.content.decode('utf-8')}")
            return response.status_code in [200, 204]
        except:
            return False
    
    def close(self):
        """Cierra la sesión de requests"""
        self.session.close()
        logger.info("Sesión del cliente API cerrada")
    
    def __enter__(self):
        """Permite usar el cliente con context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la sesión al salir del context manager"""
        self.close()
