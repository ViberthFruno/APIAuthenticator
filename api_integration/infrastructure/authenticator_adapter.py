"""
API Integration Context - Infrastructure: API Authenticator Adapter
Adaptador para el APIAuthenticator existente para que implemente IApiAuthenticator
"""
from typing import Dict

from api_integration.domain.entities import (
    ApiRequest,
    ApiCredentials
)
from api_integration.ports.interfaces import IApiAuthenticator
from logger import get_logger

logger = get_logger(__name__)


class ApiAuthenticatorAdapter(IApiAuthenticator):
    """
    Adaptador para el APIAuthenticator existente
    
    Envuelve la implementación existente para cumplir con la interfaz IApiAuthenticator
    y hacerla compatible con la nueva arquitectura
    """

    def __init__(self):
        """Inicializa el adaptador"""
        self.logger = logger.bind(component="ApiAuthenticatorAdapter")
        # El authenticator se creará por petición con las credenciales específicas

    def generate_auth_headers(
            self,
            request: ApiRequest,
            credentials: ApiCredentials
    ) -> Dict[str, str]:
        """
        Genera headers de autenticación usando el APIAuthenticator existente
        
        Args:
            request: Petición a autenticar
            credentials: Credenciales de la API
            
        Returns:
            Diccionario con headers de autenticación
        """
        self.logger.debug(
            "Generating auth headers",
            request_id=request.request_id,
            method=request.endpoint.method.value,
            cuenta=credentials.cuenta
        )

        try:
            from api_integration.infrastructure.api_authenticator import APIAuthenticator

            # Crear authenticator con las credenciales
            authenticator = APIAuthenticator(
                cuenta_api=credentials.cuenta,
                llave_api=credentials.llave,
                codigo_servicio=credentials.codigo_servicio,
                pais=credentials.pais
            )

            # Generar autenticación usando el método existente
            auth_headers = authenticator.generar_autorizacion(
                method=request.endpoint.method.value,
                url=request.endpoint.full_url,
                headers=request.headers.copy(),
                body=request.body,
                query_params=request.query_params
            )

            self.logger.debug(
                "Auth headers generated",
                request_id=request.request_id,
                headers=list(auth_headers.keys())
            )

            return auth_headers

        except ImportError:
            self.logger.error(
                "Failed to import APIAuthenticator"
            )
            raise

        except Exception as e:
            self.logger.error(
                "Error generating auth headers",
                request_id=request.request_id,
                error=str(e)
            )
            raise

    def validate_credentials(self, credentials: ApiCredentials) -> bool:
        """
        Valida que las credenciales sean correctas
        
        Args:
            credentials: Credenciales a validar
            
        Returns:
            True si son válidas
        """
        try:
            # Validaciones básicas
            if not credentials.cuenta:
                self.logger.warning("Cuenta vacía")
                return False

            if not credentials.llave:
                self.logger.warning("Llave vacía")
                return False

            if not credentials.codigo_servicio:
                self.logger.warning("Código de servicio vacío")
                return False

            if len(credentials.pais) != 2:
                self.logger.warning(
                    "País inválido",
                    pais=credentials.pais
                )
                return False

            self.logger.info(
                "Credentials validated",
                cuenta=credentials.cuenta,
                pais=credentials.pais
            )

            return True

        except Exception as e:
            self.logger.error(
                "Error validating credentials",
                error=str(e)
            )
            return False


# Factory para crear el adaptador
def create_api_authenticator() -> ApiAuthenticatorAdapter:
    """
    Factory para crear el ApiAuthenticatorAdapter
    
    Returns:
        ApiAuthenticatorAdapter configurado
    """
    return ApiAuthenticatorAdapter()


# Ejemplo de uso completo del stack de API Integration
def example_usage():
    """
    Ejemplo de cómo usar todos los componentes juntos
    """
    import asyncio
    from http_client import create_api_client
    from api_ifrpro_repository import create_ifrpro_repository
    from api_integration.application.use_cases import CreatePreingresoUseCase, CreatePreingresoInput
    from api_integration.domain.entities import (
        ApiCredentials, PreingresoData
    )

    async def main():
        # 1. Configurar credenciales
        credentials = ApiCredentials(
            cuenta="CD2D",
            llave="ifr-pruebas-F7EC2E",
            codigo_servicio="cd85e",
            pais="CR"
        )

        # 2. Crear authenticator
        authenticator = create_api_authenticator()

        # 3. Crear cliente HTTP con políticas
        api_client, retry_policy, rate_limiter = create_api_client(
            authenticator=authenticator,
            base_url="https://pruebas.api.ifrpro.nargallo.com",
            timeout=30,
            verify_ssl=True,
            max_attempts=3,
            rate_limit_calls=100
        )

        # 4. Crear repositorio
        repository = create_ifrpro_repository(
            api_client=api_client,
            authenticator=authenticator,
            credentials=credentials,
            base_url="https://pruebas.api.ifrpro.nargallo.com",
            rate_limiter=rate_limiter
        )

        # 5. Crear caso de uso
        use_case = CreatePreingresoUseCase(
            api_ifrpro_repository=repository,
            retry_policy=retry_policy
        )

        # 6. Crear preingreso de ejemplo
        preingreso_data = PreingresoData(
            numero_boleta="B-12345",
            numero_transaccion="T-67890",
            fecha="2025-01-15",
            nombre_cliente="Juan Pérez",
            cedula_cliente="1-2345-6789",
            telefono_cliente="88888888",
            correo_cliente="juan@example.com",
            direccion_cliente="San José, Costa Rica",
            codigo_producto="PROD001",
            descripcion_producto="Televisor Samsung",
            marca="Samsung",
            modelo="UN55",
            serie="SN12345",
            numero_factura="F-001",
            fecha_compra="2024-12-01",
            distribuidor="Gollo",
            danos="Pantalla no enciende",
            observaciones="Cliente reporta problema desde hace 2 días",
            codigo_sucursal="001",
            pdf_filename="boleta_B-12345.pdf",
            pdf_content=b"PDF content here..."  # En realidad sería el PDF real
        )

        # 7. Ejecutar caso de uso
        result = await use_case.execute(
            CreatePreingresoInput(
                preingreso_data=preingreso_data,
                retry_on_failure=True,
                validate_before_send=True
            )
        )

        # 8. Procesar resultado
        if result.success:
            print(f"✅ Preingreso creado exitosamente!")
            print(f"   ID: {result.preingreso_id}")
            print(f"   Status Code: {result.response.status_code}")
            print(f"   Tiempo: {result.response.response_time_ms:.0f}ms")
        else:
            print(f"❌ Error creando preingreso:")
            print(f"   Mensaje: {result.error_message}")
            if result.validation_errors:
                print(f"   Errores de validación:")
                for error in result.validation_errors:
                    print(f"      - {error}")

        # 9. Cerrar cliente
        await api_client.close()

    # Ejecutar
    asyncio.run(main())


if __name__ == "__main__":
    # Ejemplo de uso
    example_usage()
