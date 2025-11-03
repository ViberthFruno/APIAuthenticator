#!/usr/bin/env python3
"""
Autenticación para API iFR Pro
"""

import hashlib
import uuid
import hmac
import json
import base64
from datetime import datetime, timezone
from urllib.parse import quote
from typing import Dict, List, Optional, Union


class APIAuthenticator:
    """Clase para generar autenticación de API con firma HMAC-SHA384"""

    def __init__(self, cuenta_api: str, llave_api: str, codigo_servicio: str, pais: str = "CR"):
        """
        Inicializa el autenticador con las credenciales

        Args:
            cuenta_api: ID de la cuenta API (ej: "CD2D")
            llave_api: Llave secreta de la API (ej: 'ifr-pruebas-F7EC2E')
            codigo_servicio: Código del servicio (ej: 'cd85e')
            pais: Código del país (default: "CR")
        """
        self.cuenta_api = cuenta_api
        self.llave_api = llave_api
        self.codigo_servicio = codigo_servicio
        self.pais = pais

    def generar_autorizacion(self, method: str, url: str, headers: Dict[str, str],
                             body: Optional[Union[Dict, List]] = None,
                             query_params: Optional[Dict] = None) -> Dict[str, str]:
        """
        Genera los headers de autorización para la petición

        Args:
            method: Método HTTP (GET, POST, PUT, etc.)
            url: URL completa de la petición
            headers: Headers de la petición
            body: Body de la petición (dict para form-data/urlencoded)
            query_params: Parámetros de query string

        Returns:
            Dict con los headers necesarios para la autorización
        """

        # Hora en formato RFC 3339 - 6 dígitos (microsegundos):
        hora_rfc3339 = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        # Hora en formato RFC 3339 - 3 dígitos (milisegundos):
        # hora_rfc3339 = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        # Extraer host de la URL
        host = url.replace("https://", "").replace("http://", "").split("/")[0]

        # Determinar content-type
        content_type = self._get_content_type(headers)

        # Actualizar headers con valores necesarios
        headers_actualizados = headers.copy()
        headers_actualizados['Host'] = host
        headers_actualizados['Content-Type'] = content_type
        headers_actualizados['x-ifrpro-ahora'] = hora_rfc3339

        # Crear solicitud canónica
        solicitud_canonica = self._crear_solicitud_canonica(
            method, url, headers_actualizados, body, query_params
        )

        # Generar contraseña
        contrasena = self._get_contrasena(
            solicitud_canonica, self.llave_api, hora_rfc3339,
            self.pais, self.codigo_servicio
        )

        # Codificar autorización en base64
        auth_string = f"{self.cuenta_api}:{contrasena}"
        authorization = base64.b64encode(auth_string.encode()).decode()

        return {
            'Authorization': f'Basic {authorization}',
            'x-ifrpro-ahora': hora_rfc3339,
            'Host': host,
            'Content-Type': content_type
        }

    def _get_content_type(self, headers: Dict[str, str]) -> str:
        """Determina el content-type basado en el método y headers"""

        if 'Content-Type' in headers:
            return headers['Content-Type']

        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex[:16]}"
        return f"multipart/form-data; boundary={boundary}"

    def _crear_solicitud_canonica(self, method: str, url: str, headers: Dict[str, str],
                                  body: Optional[Union[Dict, List]] = None,
                                  query_params: Optional[Dict] = None) -> str:
        """
        Paso 1: Creación de una solicitud canónica
        """
        method = method.upper()
        solicitud_canonica = f"{method}\n"

        # Extraer path de la URL
        path = "/" + "/".join(url.split("/")[3:]) if len(url.split("/")) > 3 else "/"
        path = path.split("?")[0]  # Remover query string si existe

        # Paso 1.2: Uri canónico
        solicitud_canonica += self._get_uri_canonico(path) + "\n"

        # Paso 1.3: Cadena de consulta canónica (query string)
        solicitud_canonica += self._get_cadena_de_consulta_canonica(query_params) + "\n"

        # Paso 1.4 y 1.5: Encabezados canónicos y firmados
        solicitud_canonica += self._get_encabezados_para_firmar(headers, "\n") + "\n"

        # Paso 1.6: Carga útil codificada
        solicitud_canonica += self._get_carga_util(body, method)

        return solicitud_canonica

    def _get_uri_canonico(self, path: str) -> str:
        """
        Paso 1.2: Uri canónico
        Codifica el path según RFC 3986
        """
        if not path or path == '' or path == '/':
            return '/'

        # Remover barras iniciales
        path = path.lstrip('/')

        # Codificar URI
        doble_codificado = quote(path, safe='')

        # Reemplazar %2F por /
        return '/' + doble_codificado.replace('%2F', '/')

    def _get_cadena_de_consulta_canonica(self, query: Optional[Dict]) -> str:
        """
        Paso 1.3: Cadena de consulta canónica (query string)
        """
        if not query:
            return ''

        # Ordenar por clave
        query_sorted = dict(sorted(query.items()))

        qs_parts = []
        for key, value in query_sorted.items():
            if isinstance(value, list):
                # Si el valor es una lista, ordenar y procesar cada elemento
                value.sort()
                for item in value:
                    qs_parts.append(f"{quote(str(key))}={quote(str(item))}")
            else:
                if value == 0 or value == '0':
                    value = '0'
                elif not value:
                    value = ''
                qs_parts.append(f"{quote(str(key))}={quote(str(value))}")

        return '&'.join(qs_parts)

    def _get_encabezados_para_firmar(self, headers: Dict[str, str], separador: str) -> str:
        """
        Paso 1.4: Encabezados canónicos
        Paso 1.5: Encabezados firmados
        """
        if not headers:
            return ''

        headers_firma = {}

        for key, value in headers.items():
            # Convertir key a minúscula
            key_lower = key.lower()

            # Solo firmar headers específicos
            if key_lower not in ['host', 'content-type'] and not key_lower.startswith('x-ifrpro-'):
                continue

            # Convertir a string si no lo es
            if not isinstance(value, str):
                value = str(value)

            # Convertir espacios secuenciales en un solo espacio
            value = ' '.join(value.split())

            # Separar por comas si hay múltiples valores
            vals = [v.strip() for v in value.split(',')]

            # Ordenar valores
            vals.sort()

            # Unir valores con comas
            headers_firma[key_lower] = ','.join(vals)

        # Ordenar por clave
        headers_firma = dict(sorted(headers_firma.items()))

        # Paso 1.4: Encabezados canónicos
        canon_headers = [f"{key}:{value}" for key, value in headers_firma.items()]
        resultado = separador.join(canon_headers) + separador

        # Paso 1.5: Encabezados firmados
        resultado += ';'.join(headers_firma.keys())

        return resultado

    def _get_carga_util(self, body: Optional[Union[Dict, List]], method: str) -> str:
        """
        Paso 1.6: Carga útil codificada
        Retorna la suma de verificación (SHA384) del cuerpo de la solicitud
        """
        # Hash SHA384 de string vacío
        empty_hash = "38b060a751ac96384cd9327eb1b1e36a21fdb71114be07434c0cc7bf63f6e1da274edebfe76f65fbd51ad2f14898b95b"

        if method == "GET":
            return empty_hash

        if not body:
            return empty_hash

        # Si body es una lista (form-data de Postman), convertir a dict
        if isinstance(body, list):
            clean_body = {}
            for item in body:
                if isinstance(item, dict):
                    # Excluir archivos y campos deshabilitados
                    if item.get('type') == 'file' or item.get('disabled'):
                        continue
                    clean_body[item.get('key', '')] = str(item.get('value', ''))
        else:
            # Si ya es un dict, convertir valores a string
            clean_body = {k: str(v) for k, v in body.items()}

        if not clean_body:
            return empty_hash

        # Ordenar por clave
        clean_body = dict(sorted(clean_body.items()))

        # Convertir a JSON string
        body_str = json.dumps(clean_body, separators=(',', ':'), ensure_ascii=False)

        # Calcular SHA384
        return hashlib.sha384(body_str.encode()).hexdigest()

    def _get_llave_secreta_de_la_firma(self, short_date: str, region: str,
                                       service: str, llave_api: str) -> bytes:
        """
        Paso 4: Cálculo de la llave secreta de la firma
        """

        def hmac_sha384(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode(), hashlib.sha384).digest()

        # Empezar con "ifr" + llave_api
        date_key = hmac_sha384(f"ifr{llave_api}".encode(), short_date)

        # Aplicar HMAC sucesivamente
        date_region_key = hmac.new(date_key, region.encode(), hashlib.sha384).digest()
        date_region_service_key = hmac.new(date_region_key, service.encode(), hashlib.sha384).digest()

        # Llave secreta (SigningKey)
        return hmac.new(date_region_service_key, 'ifr_request'.encode(), hashlib.sha384).digest()

    def _get_contrasena(self, solicitud_canonica: str, llave_api: str,
                        fecha_hora_rfc3339: str, region: str, codigo_servicio: str) -> str:
        """
        Genera la contraseña final usando la solicitud canónica y la llave secreta
        """
        # Paso 2: Hash de la solicitud canónica
        hash_solicitud = hashlib.sha384(solicitud_canonica.encode()).hexdigest()

        fecha_corta = fecha_hora_rfc3339[:10]

        # Paso 3: Creación de una cadena para firmar
        cadena_para_firmar = (
            f"IFR-HMAC-SHA384\n"
            f"{fecha_hora_rfc3339}\n"
            f"{fecha_corta}/{region}/{codigo_servicio}/ifr_request\n"
            f"{hash_solicitud}"
        )

        # Paso 4: Cálculo de la llave secreta
        llave_secreta = self._get_llave_secreta_de_la_firma(
            fecha_corta, region, codigo_servicio, llave_api
        )

        # Paso 5: Obtener la contraseña
        firma = hmac.new(llave_secreta, cadena_para_firmar.encode(), hashlib.sha384).digest()

        return base64.b64encode(firma).decode()

