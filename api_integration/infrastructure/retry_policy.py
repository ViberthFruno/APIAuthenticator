# retry_policy.py.
# Implementa estrategia de backoff exponencial para reintentos.

from typing import Optional
class RetryPolicy:

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 10.0, backoff_factor: float = 2.0):
        """
        Inicializa la política de reintentos.

        Args:
            max_retries: Número máximo de reintentos
            base_delay: Delay base en segundos
            max_delay: Delay máximo en segundos
            backoff_factor: Factor de multiplicación para backoff exponencial
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

        # Status codes que deberían reintentar
        self.retryable_status_codes = {
            408,  # Request Timeout
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504  # Gateway Timeout
        }

    def should_retry(self, status_code: Optional[int]) -> bool:
        """
        Determina si se debe reintentar basándose en el status code.

        Args:
            status_code: Código de estado HTTP

        Returns:
            True si se debe reintentar, False en caso contrario
        """
        if status_code is None:
            return True  # Reintentar si no hay respuesta

        return status_code in self.retryable_status_codes

    def get_delay(self, attempt: int) -> float:
        """
        Calcula el delay antes del siguiente reintento usando backoff exponencial.

        Args:
            attempt: Número del intento actual

        Returns:
            Delay en segundos
        """
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)


class ExponentialRetryPolicy:
    pass