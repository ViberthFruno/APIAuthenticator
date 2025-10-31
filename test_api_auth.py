#!/usr/bin/env python3
"""
Pruebas unitarias para el autenticador de API
"""

import unittest
import hashlib
from api_authenticator import APIAuthenticator


class TestAPIAuthenticator(unittest.TestCase):
    """Pruebas para la clase APIAuthenticator"""
    
    def setUp(self):
        """Configuración inicial para las pruebas"""
        self.auth = APIAuthenticator(
            cuenta_api="CD2D",
            llave_api="ifr-pruebas-F7EC2E",
            codigo_servicio="cd85e",
            pais="CR"
        )
    
    def test_get_uri_canonico(self):
        """Prueba la generación del URI canónico"""
        
        # Caso 1: Path simple
        result = self.auth._get_uri_canonico("/api/v1/test")
        self.assertEqual(result, "/api/v1/test")
        
        # Caso 2: Path vacío
        result = self.auth._get_uri_canonico("/")
        self.assertEqual(result, "/")
        
        # Caso 3: Path con caracteres especiales
        result = self.auth._get_uri_canonico("/api/test space")
        self.assertEqual(result, "/api/test%20space")
        
        # Caso 4: Path con barras codificadas
        result = self.auth._get_uri_canonico("/api/path/to/resource")
        self.assertEqual(result, "/api/path/to/resource")
    
    def test_get_cadena_de_consulta_canonica(self):
        """Prueba la generación de la cadena de consulta canónica"""
        
        # Caso 1: Query params simples
        query = {"param1": "value1", "param2": "value2"}
        result = self.auth._get_cadena_de_consulta_canonica(query)
        self.assertEqual(result, "param1=value1&param2=value2")
        
        # Caso 2: Query params con valores especiales
        query = {"param": "value with spaces", "empty": ""}
        result = self.auth._get_cadena_de_consulta_canonica(query)
        self.assertEqual(result, "empty=&param=value%20with%20spaces")
        
        # Caso 3: Query params con lista
        query = {"param": ["b", "a", "c"]}
        result = self.auth._get_cadena_de_consulta_canonica(query)
        self.assertEqual(result, "param=a&param=b&param=c")
        
        # Caso 4: Sin query params
        result = self.auth._get_cadena_de_consulta_canonica(None)
        self.assertEqual(result, "")
    
    def test_get_encabezados_para_firmar(self):
        """Prueba la generación de encabezados canónicos"""
        
        headers = {
            "Host": "api.ejemplo.com",
            "Content-Type": "application/json",
            "X-IfrPro-Custom": "value",
            "Accept": "application/json"  # No debe incluirse
        }
        
        result = self.auth._get_encabezados_para_firmar(headers, "\n")
        
        # Verificar que contiene los headers correctos
        self.assertIn("content-type:application/json", result)
        self.assertIn("host:api.ejemplo.com", result)
        self.assertIn("x-ifrpro-custom:value", result)
        
        # Verificar que NO contiene Accept
        self.assertNotIn("accept", result)
        
        # Verificar los encabezados firmados al final
        self.assertIn("content-type;host;x-ifrpro-custom", result)
    
    def test_get_carga_util_get(self):
        """Prueba la carga útil para método GET"""
        
        result = self.auth._get_carga_util(None, "GET")
        # Hash SHA384 de string vacío
        expected = "38b060a751ac96384cd9327eb1b1e36a21fdb71114be07434c0cc7bf63f6e1da274edebfe76f65fbd51ad2f14898b95b"
        self.assertEqual(result, expected)
    
    def test_get_carga_util_post(self):
        """Prueba la carga útil para método POST con body"""
        
        # Caso 1: Body como diccionario
        body = {"campo1": "valor1", "campo2": "valor2"}
        result = self.auth._get_carga_util(body, "POST")
        
        # Verificar que es un hash SHA384 válido (96 caracteres hex)
        self.assertEqual(len(result), 96)
        
        # Verificar el hash del JSON ordenado
        expected_json = '{"campo1":"valor1","campo2":"valor2"}'
        expected_hash = hashlib.sha384(expected_json.encode()).hexdigest()
        self.assertEqual(result, expected_hash)
        
        # Caso 2: Body vacío
        result = self.auth._get_carga_util({}, "POST")
        expected = "38b060a751ac96384cd9327eb1b1e36a21fdb71114be07434c0cc7bf63f6e1da274edebfe76f65fbd51ad2f14898b95b"
        self.assertEqual(result, expected)
        
        # Caso 3: Body como lista (formato Postman)
        body_list = [
            {"key": "campo1", "value": "valor1", "type": "text"},
            {"key": "campo2", "value": "valor2", "type": "text"},
            {"key": "archivo", "value": "path/to/file", "type": "file"},  # Debe excluirse
            {"key": "campo3", "value": "valor3", "disabled": True}  # Debe excluirse
        ]
        result = self.auth._get_carga_util(body_list, "POST")
        
        # Solo debe incluir campo1 y campo2
        expected_json = '{"campo1":"valor1","campo2":"valor2"}'
        expected_hash = hashlib.sha384(expected_json.encode()).hexdigest()
        self.assertEqual(result, expected_hash)
    
    def test_get_llave_secreta_de_la_firma(self):
        """Prueba la generación de la llave secreta"""
        
        result = self.auth._get_llave_secreta_de_la_firma(
            "2024-01-15",
            "CR",
            "cd85e",
            "ifr-pruebas-F7EC2E"
        )
        
        # Verificar que es bytes
        self.assertIsInstance(result, bytes)
        
        # Verificar longitud (SHA384 produce 48 bytes)
        self.assertEqual(len(result), 48)
    
    def test_crear_solicitud_canonica(self):
        """Prueba la creación de la solicitud canónica completa"""
        
        method = "POST"
        url = "https://api.ejemplo.com/v1/recurso"
        headers = {
            "Host": "api.ejemplo.com",
            "Content-Type": "application/json",
            "X-IfrPro-Fecha": "2024-01-15T10:30:00Z"
        }
        body = {"test": "value"}
        query_params = {"param": "value"}
        
        result = self.auth._crear_solicitud_canonica(
            method, url, headers, body, query_params
        )
        
        # Verificar que contiene las partes esperadas
        lines = result.split("\n")
        
        # Primera línea: método
        self.assertEqual(lines[0], "POST")
        
        # Segunda línea: URI canónico
        self.assertEqual(lines[1], "/v1/recurso")
        
        # Tercera línea: query string
        self.assertEqual(lines[2], "param=value")
        
        # Verificar que contiene los headers
        self.assertIn("content-type:application/json", result)
        self.assertIn("host:api.ejemplo.com", result)
    
    def test_generar_autorizacion(self):
        """Prueba la generación completa de autorización"""
        
        method = "GET"
        url = "https://api.ejemplo.com/v1/test"
        headers = {"Accept": "application/json"}
        
        result = self.auth.generar_autorizacion(
            method=method,
            url=url,
            headers=headers,
            body=None,
            query_params={"test": "value"}
        )
        
        # Verificar que contiene los headers necesarios
        self.assertIn("Authorization", result)
        self.assertIn("X-IfrPro-Fecha", result)
        self.assertIn("Host", result)
        
        # Verificar formato de Authorization
        self.assertTrue(result["Authorization"].startswith("Basic "))
        
        # Verificar formato de fecha RFC3339
        fecha = result["X-IfrPro-Fecha"]
        self.assertRegex(fecha, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
        
        # Verificar Host
        self.assertEqual(result["Host"], "api.ejemplo.com")
    
    def test_content_type_detection(self):
        """Prueba la detección del Content-Type"""
        
        # Caso 1: GET sin Content-Type
        result = self.auth._get_content_type("GET", {})
        self.assertEqual(result, "")
        
        # Caso 2: POST sin Content-Type (default)
        result = self.auth._get_content_type("POST", {})
        self.assertEqual(result, "application/x-www-form-urlencoded")
        
        # Caso 3: POST con Content-Type especificado
        result = self.auth._get_content_type("POST", {"Content-Type": "application/json"})
        self.assertEqual(result, "application/json")
    
    def test_ordenamiento_consistente(self):
        """Prueba que el ordenamiento sea consistente con el código original"""
        
        # Probar con datos desordenados
        body = {
            "zebra": "valor",
            "apple": "fruta",
            "mango": "tropical",
            "banana": "amarilla"
        }
        
        result = self.auth._get_carga_util(body, "POST")
        
        # El JSON debe estar ordenado alfabéticamente
        expected_json = '{"apple":"fruta","banana":"amarilla","mango":"tropical","zebra":"valor"}'
        expected_hash = hashlib.sha384(expected_json.encode()).hexdigest()
        self.assertEqual(result, expected_hash)
    
    def test_valores_especiales_en_body(self):
        """Prueba el manejo de valores especiales en el body"""
        
        body = {
            "cero_numero": 0,
            "cero_string": "0",
            "vacio": "",
            "none": None,
            "numero": 123,
            "flotante": 45.67,
            "booleano": True
        }
        
        result = self.auth._get_carga_util(body, "POST")
        
        # Todos los valores deben convertirse a string
        expected_json = '{"booleano":"True","cero_numero":"0","cero_string":"0","flotante":"45.67","none":"None","numero":"123","vacio":""}'
        expected_hash = hashlib.sha384(expected_json.encode()).hexdigest()
        self.assertEqual(result, expected_hash)


class TestIntegracion(unittest.TestCase):
    """Pruebas de integración end-to-end"""
    
    def test_firma_completa_get(self):
        """Prueba la firma completa para una petición GET"""
        
        auth = APIAuthenticator(
            cuenta_api="TEST_ACCOUNT",
            llave_api="test-key-123456",
            codigo_servicio="test01",
            pais="US"
        )
        
        # Simular una petición GET real
        method = "GET"
        url = "https://api.test.com/v1/users"
        headers = {
            "Accept": "application/json",
            "User-Agent": "TestClient/1.0"
        }
        query_params = {
            "page": "1",
            "limit": "10",
            "sort": "name"
        }
        
        result = auth.generar_autorizacion(
            method=method,
            url=url,
            headers=headers,
            body=None,
            query_params=query_params
        )
        
        # Verificar estructura de autorización
        self.assertIn("Authorization", result)
        self.assertTrue(result["Authorization"].startswith("Basic "))
        
        # Decodificar y verificar formato
        import base64
        auth_decoded = base64.b64decode(
            result["Authorization"].replace("Basic ", "")
        ).decode()
        
        parts = auth_decoded.split(":")
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0], "TEST_ACCOUNT")
        
        # La contraseña debe ser base64 válida
        try:
            base64.b64decode(parts[1])
        except:
            self.fail("La contraseña no es base64 válida")
    
    def test_firma_completa_post(self):
        """Prueba la firma completa para una petición POST"""
        
        auth = APIAuthenticator(
            cuenta_api="TEST_ACCOUNT",
            llave_api="test-key-123456",
            codigo_servicio="test01",
            pais="US"
        )
        
        # Simular una petición POST real
        method = "POST"
        url = "https://api.test.com/v1/orders"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        body = {
            "customer_id": "CUST123",
            "items": [
                {"product": "PROD001", "quantity": 2},
                {"product": "PROD002", "quantity": 1}
            ],
            "total": 150.50
        }
        
        result = auth.generar_autorizacion(
            method=method,
            url=url,
            headers=headers,
            body=body,
            query_params=None
        )
        
        # Verificar que todos los headers necesarios están presentes
        required_headers = ["Authorization", "X-IfrPro-Fecha", "Host", "Content-Type"]
        for header in required_headers:
            self.assertIn(header, result)
        
        # Verificar Content-Type
        self.assertEqual(result["Content-Type"], "application/json")
        
        # Verificar Host
        self.assertEqual(result["Host"], "api.test.com")


if __name__ == "__main__":
    unittest.main(verbosity=2)
