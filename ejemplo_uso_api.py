import requests
from api_authenticator import APIAuthenticator


def ejemplo_peticion_get():
    """Ejemplo de petición GET con autenticación"""
    
    # Configuración
    auth = APIAuthenticator(
        cuenta_api="CD2D",
        llave_api="ifr-pruebas-F7EC2E",
        codigo_servicio="cd85e",
        pais="CR"
    )
    
    # URL y parámetros
    url = "https://api.ejemplo.com/v1/productos"
    query_params = {
        "categoria": "electronica",
        "limite": 10
    }
    
    # Headers básicos
    headers = {
        "Accept": "application/json"
    }
    
    # Generar headers de autorización
    auth_headers = auth.generar_autorizacion(
        method="GET",
        url=url,
        headers=headers,
        body=None,
        query_params=query_params
    )
    
    # Combinar headers
    headers.update(auth_headers)
    
    # Realizar la petición
    try:
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        
        print("Respuesta exitosa:")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.json()}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error en la petición: {e}")


def ejemplo_peticion_post():
    """Ejemplo de petición POST con autenticación"""
    
    # Configuración
    auth = APIAuthenticator(
        cuenta_api="CD2D",
        llave_api="ifr-pruebas-F7EC2E",
        codigo_servicio="cd85e",
        pais="CR"
    )
    
    # URL y datos
    url = "https://api.ejemplo.com/v1/pedidos"
    
    # Datos del body (form-data)
    body_data = {
        "cliente_id": "12345",
        "producto": "Laptop",
        "cantidad": 2,
        "precio": 1500.00
    }
    
    # Headers básicos
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # Generar headers de autorización
    auth_headers = auth.generar_autorizacion(
        method="POST",
        url=url,
        headers=headers,
        body=body_data,
        query_params=None
    )
    
    # Combinar headers
    headers.update(auth_headers)
    
    # Realizar la petición
    try:
        response = requests.post(url, headers=headers, data=body_data)
        response.raise_for_status()
        
        print("Respuesta exitosa:")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.json()}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error en la petición: {e}")


def ejemplo_peticion_multipart():
    """Ejemplo de petición POST con multipart/form-data"""
    
    # Configuración
    auth = APIAuthenticator(
        cuenta_api="CD2D",
        llave_api="ifr-pruebas-F7EC2E",
        codigo_servicio="cd85e",
        pais="CR"
    )
    
    url = "https://api.ejemplo.com/v1/documentos"
    
    # Datos del formulario (sin archivos para el cálculo de firma)
    body_data_for_signature = {
        "titulo": "Documento de prueba",
        "descripcion": "Este es un documento de prueba"
    }
    
    # Headers para multipart
    # Nota: No incluir Content-Type aquí, requests lo agregará automáticamente con el boundary
    headers = {
        "Accept": "application/json"
    }
    
    # Para la firma, necesitamos simular el Content-Type con boundary
    import uuid
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex[:16]}"
    headers_for_auth = headers.copy()
    headers_for_auth["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    
    # Generar headers de autorización
    auth_headers = auth.generar_autorizacion(
        method="POST",
        url=url,
        headers=headers_for_auth,
        body=body_data_for_signature,
        query_params=None
    )

    # Para la petición real, no incluir Content-Type (requests lo maneja)
    final_headers = {
        "Accept": "application/json",
        "Authorization": auth_headers["Authorization"],
        "X-IfrPro-Fecha": auth_headers["X-IfrPro-Fecha"],
        "Host": auth_headers["Host"]
    }
    
    # Preparar los datos incluyendo archivo
    files = {
        'archivo': ('documento.txt', 'Contenido del archivo de prueba', 'text/plain')
    }
    
    # Realizar la petición
    try:
        response = requests.post(
            url, 
            headers=final_headers, 
            data=body_data_for_signature,
            files=files
        )
        response.raise_for_status()
        
        print("Respuesta exitosa:")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.json()}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error en la petición: {e}")



def ejemplo_con_cliente():
    """Ejemplo usando la clase cliente"""
    
    # Crear cliente
    client = APIClient(
        cuenta_api="CD2D",
        llave_api="ifr-pruebas-F7EC2E",
        codigo_servicio="cd85e",
        pais="CR",
        base_url="https://api.ejemplo.com"
    )
    
    try:
        # GET request
        response = client.get("/v1/productos", params={"limite": 5})
        print(f"GET /productos: {response.status_code}")
        
        # POST request
        nuevo_producto = {
            "nombre": "Producto Test",
            "precio": 99.99,
            "stock": 100
        }
        response = client.post("/v1/productos", data=nuevo_producto)
        print(f"POST /productos: {response.status_code}")
        
        # PUT request
        actualizacion = {
            "precio": 89.99,
            "stock": 150
        }
        response = client.put("/v1/productos/123", data=actualizacion)
        print(f"PUT /productos/123: {response.status_code}")
        
        # DELETE request
        response = client.delete("/v1/productos/456")
        print(f"DELETE /productos/456: {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("=== Ejemplo de petición GET ===")
    ejemplo_peticion_get()
    
    print("\n=== Ejemplo de petición POST ===")
    ejemplo_peticion_post()
    
    print("\n=== Ejemplo de petición Multipart ===")
    ejemplo_peticion_multipart()
    
    print("\n=== Ejemplo con cliente integrado ===")
    ejemplo_con_cliente()
