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


class AuthenticatorAdapter:
    pass