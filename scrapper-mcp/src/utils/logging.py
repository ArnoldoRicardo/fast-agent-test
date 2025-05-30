"""
Configuración de logging para el scrapper-mcp.
"""

import sys
from loguru import logger
from .config import get_config

config = get_config()

# Configurar logger
logger.remove()  # Eliminar el handler por defecto

# Agregar handler para la consola
logger.add(
    sys.stderr,
    level=config.log.level,
    format=config.log.format
)

# Agregar handler para archivo si está configurado
if config.log.file:
    logger.add(
        config.log.file,
        level=config.log.level,
        format=config.log.format,
        rotation="10 MB",  # Rotar cuando el archivo alcance 10MB
        retention="1 week"  # Mantener logs por 1 semana
    )

def get_logger(name: str):
    """Obtener un logger con un nombre específico."""
    return logger.bind(name=name)
