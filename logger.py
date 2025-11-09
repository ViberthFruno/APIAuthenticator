# logger.py
"""
Sistema de Logging centralizado
Usa structlog para logs estructurados con contexto
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler
import structlog
from structlog.types import EventDict, Processor


class ContextLogger:
    """
    Logger centralizado con contexto estructurado
    Wrapper sobre structlog para consistencia en el proyecto
    """

    def __init__(self, name: str, context: Optional[dict] = None):
        """
        Inicializa el logger

        Args:
            name: Nombre del logger (ej: 'email.domain')
            context: Contexto inicial (ej: {'user_id': '123'})
        """
        self._name = name
        self._logger = structlog.get_logger(name)
        self._context = context or {}

        if self._context:
            self._logger = self._logger.bind(**self._context)

    def bind(self, **kwargs) -> 'ContextLogger':
        """
        Crea un nuevo logger con contexto adicional

        Args:
            **kwargs: Par clave-valor para el contexto

        Returns:
            Nuevo logger con contexto ampliado
        """
        new_context = {**self._context, **kwargs}
        return ContextLogger(self._name, new_context)

    def debug(self, event: str, **kwargs):
        """Log nivel DEBUG"""
        self._logger.debug(event, **kwargs)

    def info(self, event: str, **kwargs):
        """Log nivel INFO"""
        self._logger.info(event, **kwargs)

    def warning(self, event: str, **kwargs):
        """Log nivel WARNING"""
        self._logger.warning(event, **kwargs)

    def error(self, event: str, **kwargs):
        """Log nivel ERROR"""
        self._logger.error(event, **kwargs)

    def critical(self, event: str, **kwargs):
        """Log nivel CRITICAL"""
        self._logger.critical(event, **kwargs)

    def exception(self, event: str, exc_info=True, **kwargs):
        """Log de excepción con traceback"""
        self._logger.exception(event, exc_info=exc_info, **kwargs)


def add_app_context(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Processor personalizado para agregar contexto de aplicación

    Args:
        logger: Logger instance
        method_name: Nombre del método
        event_dict: Diccionario del evento

    Returns:
        EventDict con contexto adicional
    """
    # Agregar información adicional si está disponible
    # Por ejemplo, desde contexto de request, thread, etc.
    return event_dict


def setup_logging(
        log_level: str = "INFO",
        log_dir: Path = Path("./storage/logs"),
        use_json: bool = False,
        max_bytes: int = 10_485_760,  # 10MB
        backup_count: int = 5
) -> None:
    """
    Configura el sistema de logging

    Args:
        log_level: Nivel de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directorio para archivos de log
        use_json: Si True, usa formato JSON
        max_bytes: Tamaño máximo por archivo
        backup_count: Número de archivos de backup
    """
    # Crear directorio de logs
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Configurar logging estándar
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Handler para archivo con rotación
    file_handler = RotatingFileHandler(
        filename=log_path / "application.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        mode='a',
        encoding='utf-8'
    )
    file_handler.setLevel(numeric_level)

    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # Configurar formato
    if use_json:
        # Formato JSON para producción
        processors: list[Processor] = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            add_app_context,
            structlog.processors.JSONRenderer()
        ]
    else:
        # Formato legible para desarrollo
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            add_app_context,
            structlog.dev.ConsoleRenderer(colors=True)
        ]

    # Configurar structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    # Configurar logging estándar para capturar logs de librerías
    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
        handlers=[file_handler, console_handler]
    )

    # Silenciar logs verbosos de librerías
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str, **context) -> ContextLogger:
    """
    Factory para obtener un logger

    Args:
        name: Nombre del logger (usar __name__ del módulo)
        **context: Contexto inicial del logger

    Returns:
        ContextLogger configurado

    Example:
        >>> logger = get_logger(__name__, user_id="123", request_id="abc")
        >>> logger.info("Usuario autenticado", email="user@example.com")
    """
    return ContextLogger(name, context)


class LoggerMixin:
    """
    Mixin para agregar logging a clases

    Usage:
        class MyService(LoggerMixin):
            def __init__(self):
                super().__init__()
                self.logger.info("Service initialized")
    """

    @property
    def logger(self) -> ContextLogger:
        """Obtiene el logger de la clase"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(
                f"{self.__class__.__module__}.{self.__class__.__name__}"
            )
        return self._logger


# Performance Logging Decorator
def log_execution_time(func):
    """
    Decorador para loguear tiempo de ejecución

    Usage:
        @log_execution_time
        def expensive_operation():
            pass
    """
    import time
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            logger.info(
                "Function executed",
                function=func.__name__,
                execution_time_seconds=round(execution_time, 4),
                status="success"
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time

            logger.error(
                "Function failed",
                function=func.__name__,
                execution_time_seconds=round(execution_time, 4),
                status="error",
                error=str(e)
            )
            raise

    return wrapper
