import logging
import sys
from app.config import settings

def configurar_logging() -> logging.Logger:
    """
    Configura y unifica el sistema de logs de la aplicación.
    Establece el formato de consola profesional y el nivel definido en los settings.
    
    Returns:
        Un logger configurado con el nombre 'bot_gastos'.
    """
    nivel = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Formato profesional: Timestamp | Level | Name | Message
    formateador = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    manejador_consola = logging.StreamHandler(sys.stdout)
    manejador_consola.setFormatter(formateador)
    
    logger_raiz = logging.getLogger()
    
    # Limpiamos manejadores por defecto para no duplicar logs
    if logger_raiz.hasHandlers():
        logger_raiz.handlers.clear()
        
    logger_raiz.addHandler(manejador_consola)
    logger_raiz.setLevel(nivel)
    
    # Obtenemos el logger específico de nuestra aplicación
    logger = logging.getLogger("bot_gastos")
    logger.setLevel(nivel)
    
    logger.info("Sistema de logging inicializado en nivel: %s", settings.LOG_LEVEL.upper())
    return logger

# Logger preconfigurado listo para importar
logger = configurar_logging()
