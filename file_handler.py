import os
import io
import hashlib
import mimetypes
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from PIL import Image
import base64

logger = logging.getLogger(__name__)


class FileHandler:
    """Manejador de archivos con validación y procesamiento"""

    # Tamaños máximos por tipo de archivo (en bytes)
    MAX_SIZES = {
        'image': 10 * 1024 * 1024,  # 10MB para imágenes
        'pdf': 50 * 1024 * 1024,     # 50MB para PDFs
        'document': 20 * 1024 * 1024, # 20MB para documentos
        'default': 10 * 1024 * 1024   # 10MB por defecto
    }

    # Extensiones permitidas por categoría
    ALLOWED_EXTENSIONS = {
        'image': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'],
        'pdf': ['.pdf'],
        'document': ['.doc', '.docx', '.xls', '.xlsx', '.odt', '.txt'],
        'archive': ['.zip', '.tar', '.gz', '.rar', '.7z']
    }

    # MIME types
    MIME_TYPES = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.zip': 'application/zip',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip',
        '.rar': 'application/x-rar-compressed',
        '.7z': 'application/x-7z-compressed'
    }

    @classmethod
    def validate_file(cls, file_path: str,
                     allowed_extensions: List[str] = None,
                     max_size: int = None) -> Tuple[bool, str]:
        """
        Valida un archivo

        Args:
            file_path: Ruta del archivo
            allowed_extensions: Extensiones permitidas
            max_size: Tamaño máximo en bytes

        Returns:
            Tupla (es_válido, mensaje)
        """
        # Verificar que existe
        if not os.path.exists(file_path):
            return False, f"Archivo no encontrado: {file_path}"

        # Verificar que es archivo
        if not os.path.isfile(file_path):
            return False, f"No es un archivo: {file_path}"

        # Verificar extensión
        extension = Path(file_path).suffix.lower()

        if allowed_extensions:
            if extension not in allowed_extensions:
                return False, f"Extensión no permitida: {extension}"

        # Verificar tamaño
        file_size = os.path.getsize(file_path)

        if max_size:
            if file_size > max_size:
                return False, f"Archivo muy grande: {file_size:,} bytes (máximo: {max_size:,})"

        return True, "OK"

    @classmethod
    def get_mime_type(cls, file_path: str) -> str:
        """
        Obtiene el MIME type de un archivo

        Args:
            file_path: Ruta del archivo

        Returns:
            MIME type del archivo
        """
        extension = Path(file_path).suffix.lower()

        # Primero intentar con nuestro diccionario
        if extension in cls.MIME_TYPES:
            return cls.MIME_TYPES[extension]

        # Si no, usar mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)

        return mime_type or 'application/octet-stream'

    @classmethod
    def read_file_safely(cls, file_path: str,
                        max_size: int = None) -> Optional[bytes]:
        """
        Lee un archivo de forma segura

        Args:
            file_path: Ruta del archivo
            max_size: Tamaño máximo a leer

        Returns:
            Contenido del archivo en bytes o None si hay error
        """
        try:
            if max_size:
                file_size = os.path.getsize(file_path)
                if file_size > max_size:
                    logger.error(f"Archivo muy grande: {file_path} ({file_size:,} bytes)")
                    return None

            with open(file_path, 'rb') as f:
                return f.read()
        except IOError as e:
            logger.error(f"Error leyendo archivo {file_path}: {e}")
            return None

    @classmethod
    def calculate_hash(cls, file_path: str,
                      algorithm: str = 'sha256') -> Optional[str]:
        """
        Calcula el hash de un archivo

        Args:
            file_path: Ruta del archivo
            algorithm: Algoritmo de hash (sha256, sha384, md5)

        Returns:
            Hash del archivo en hexadecimal
        """
        try:
            hash_func = getattr(hashlib, algorithm)()

            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_func.update(chunk)

            return hash_func.hexdigest()
        except (IOError, AttributeError) as e:
            logger.error(f"Error calculando hash de {file_path}: {e}")
            return None

    @classmethod
    def prepare_files_for_upload(cls, file_paths: List[str],
                                field_name: str = "archivos",
                                validate: bool = True,
                                allowed_extensions: List[str] = None,
                                max_size: int = None) -> List[Tuple]:
        """
        Prepara múltiples archivos para upload

        Args:
            file_paths: Lista de rutas de archivos
            field_name: Nombre del campo para los archivos
            validate: Si validar los archivos
            allowed_extensions: Extensiones permitidas
            max_size: Tamaño máximo por archivo

        Returns:
            Lista de tuplas listas para requests.post(files=...)
        """
        files = []

        for file_path in file_paths:
            # Validar si es necesario
            if validate:
                is_valid, message = cls.validate_file(
                    file_path, allowed_extensions, max_size
                )

                if not is_valid:
                    logger.warning(f"Archivo inválido: {message}")
                    continue

            # Leer archivo
            content = cls.read_file_safely(file_path, max_size)
            if content is None:
                continue

            # Preparar para upload
            filename = os.path.basename(file_path)
            mime_type = cls.get_mime_type(file_path)

            files.append((field_name, (filename, content, mime_type)))

            logger.debug(f"Archivo preparado: {filename} ({mime_type}) - {len(content):,} bytes")

        return files

    @classmethod
    def create_test_image(cls, width: int = 100, height: int = 100,
                         color: str = 'red', format: str = 'PNG') -> bytes:
        """
        Crea una imagen de prueba

        Args:
            width: Ancho de la imagen
            height: Alto de la imagen
            color: Color de la imagen
            format: Formato de salida (PNG, JPEG, etc.)

        Returns:
            Imagen en bytes
        """
        try:
            img = Image.new('RGB', (width, height), color=color)
            buffer = io.BytesIO()
            img.save(buffer, format=format)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Error creando imagen de prueba: {e}")
            return b''

    @classmethod
    def create_test_pdf(cls, content: str = "Test PDF") -> bytes:
        """
        Crea un PDF básico de prueba

        Args:
            content: Contenido del PDF

        Returns:
            PDF en bytes
        """
        # PDF básico sin dependencias externas
        pdf_content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length {len(content) + 30} >>
stream
BT
/F1 12 Tf
100 700 Td
({content}) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
365
%%EOF"""
        return pdf_content.encode('latin-1')

    @classmethod
    def create_test_files(cls, directory: str = "./test_files",
                         count: Dict[str, int] = None) -> List[str]:
        """
        Crea archivos de prueba

        Args:
            directory: Directorio donde crear los archivos
            count: Diccionario con cantidad de archivos por tipo
                  Ej: {'png': 2, 'jpg': 1, 'pdf': 1}

        Returns:
            Lista de rutas de archivos creados
        """
        # Cantidades por defecto
        if count is None:
            count = {'png': 2, 'jpg': 1, 'jpeg': 1, 'pdf': 1}

        # Crear directorio
        Path(directory).mkdir(parents=True, exist_ok=True)

        created_files = []

        try:
            # Crear imágenes PNG
            for i in range(count.get('png', 0)):
                file_path = os.path.join(directory, f'imagen_{i+1}.png')
                img_data = cls.create_test_image(
                    100 + i*50, 100 + i*50,
                    ['red', 'blue', 'green'][i % 3]
                )
                with open(file_path, 'wb') as f:
                    f.write(img_data)
                created_files.append(file_path)
                logger.info(f"Creado: {file_path}")

            # Crear imágenes JPG
            for i in range(count.get('jpg', 0)):
                file_path = os.path.join(directory, f'foto_{i+1}.jpg')
                img_data = cls.create_test_image(
                    200, 200, 'yellow', 'JPEG'
                )
                with open(file_path, 'wb') as f:
                    f.write(img_data)
                created_files.append(file_path)
                logger.info(f"Creado: {file_path}")

            # Crear imágenes JPEG
            for i in range(count.get('jpeg', 0)):
                file_path = os.path.join(directory, f'picture_{i+1}.jpeg')
                img_data = cls.create_test_image(
                    250, 250, 'cyan', 'JPEG'
                )
                with open(file_path, 'wb') as f:
                    f.write(img_data)
                created_files.append(file_path)
                logger.info(f"Creado: {file_path}")

            # Crear PDFs
            for i in range(count.get('pdf', 0)):
                file_path = os.path.join(directory, f'documento_{i+1}.pdf')
                pdf_data = cls.create_test_pdf(f"Documento de prueba {i+1}")
                with open(file_path, 'wb') as f:
                    f.write(pdf_data)
                created_files.append(file_path)
                logger.info(f"Creado: {file_path}")

        except Exception as e:
            logger.error(f"Error creando archivos de prueba: {e}")

        return created_files

    @classmethod
    def cleanup_directory(cls, directory: str,
                         extensions: List[str] = None) -> int:
        """
        Limpia archivos de un directorio

        Args:
            directory: Directorio a limpiar
            extensions: Extensiones a eliminar (None = todas)

        Returns:
            Número de archivos eliminados
        """
        if not os.path.exists(directory):
            return 0

        deleted_count = 0

        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)

            if os.path.isfile(file_path):
                if extensions:
                    extension = Path(file_path).suffix.lower()
                    if extension not in extensions:
                        continue

                try:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.debug(f"Eliminado: {file_path}")
                except OSError as e:
                    logger.error(f"Error eliminando {file_path}: {e}")

        return deleted_count

    @classmethod
    def encode_file_base64(cls, file_path: str) -> Optional[str]:
        """
        Codifica un archivo en base64

        Args:
            file_path: Ruta del archivo

        Returns:
            String en base64 o None si hay error
        """
        content = cls.read_file_safely(file_path)
        if content:
            return base64.b64encode(content).decode('utf-8')
        return None

    @classmethod
    def save_uploaded_file(cls, file_content: bytes,
                          filename: str,
                          directory: str = "./uploads") -> Optional[str]:
        """
        Guarda un archivo subido

        Args:
            file_content: Contenido del archivo
            filename: Nombre del archivo
            directory: Directorio de destino

        Returns:
            Ruta del archivo guardado o None si hay error
        """
        try:
            # Crear directorio si no existe
            Path(directory).mkdir(parents=True, exist_ok=True)

            # Generar nombre único si es necesario
            file_path = os.path.join(directory, filename)
            if os.path.exists(file_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{timestamp}{ext}"
                file_path = os.path.join(directory, filename)

            # Guardar archivo
            with open(file_path, 'wb') as f:
                f.write(file_content)

            logger.info(f"Archivo guardado: {file_path}")
            return file_path

        except IOError as e:
            logger.error(f"Error guardando archivo: {e}")
            return None
