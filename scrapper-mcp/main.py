"""
Punto de entrada principal para scrapper-mcp.
Permite iniciar el servidor API o el servidor MCP.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Asegurar que el directorio raíz esté en el path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from src.utils.logging import get_logger
from src.utils.config import get_config
from src.database.connection import init_db
from src.api.server import start as start_api
from src.mcp.server import start as start_mcp

# Inicializar logger
logger = get_logger("main")
config = get_config()

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Financial Data Scraper MCP")
    parser.add_argument(
        "--mode", 
        choices=["api", "mcp", "all"], 
        default="api",
        help="Modo de ejecución: 'api' para servidor REST, 'mcp' para servidor MCP, 'all' para ambos"
    )
    parser.add_argument(
        "--init-db", 
        action="store_true", 
        help="Inicializar la base de datos"
    )
    
    args = parser.parse_args()
    
    # Inicializar la base de datos si se solicita
    if args.init_db:
        logger.info("Inicializando la base de datos...")
        init_db()
        logger.info("Base de datos inicializada correctamente")
    
    # Iniciar el modo seleccionado
    if args.mode == "api":
        logger.info("Iniciando servidor API...")
        start_api()
    elif args.mode == "mcp":
        logger.info("Iniciando servidor MCP...")
        start_mcp()
    elif args.mode == "all":
        # No implementado aún - requeriría iniciar ambos en procesos separados
        logger.error("El modo 'all' no está implementado actualmente")
        logger.info("Por favor, inicie cada servidor por separado")
        sys.exit(1)

if __name__ == "__main__":
    main()
