#!/usr/bin/env python
"""
Script para ejecutar el colector de datos de Binance.
Recopila datos OHLCV para los pares de criptomonedas configurados.
"""

from src.database.connection import init_db
from src.collectors.binance import BinanceCollector
import sys
import asyncio
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("binance_collector")

# Añadir el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent  # Ajustado para que apunte al directorio raíz desde scripts/
sys.path.insert(0, str(ROOT_DIR))

# Importar el colector y la base de datos


async def main():
    """
    Función principal para ejecutar el colector de Binance.
    """
    # Inicializar la base de datos
    init_db()

    # Crear instancia del colector
    collector = BinanceCollector()

    try:
        # Ejecutar colector
        logger.info("Iniciando colector de Binance...")
        result = await collector.collect()
        logger.info(f"Colector de Binance completado. Resultados: {result}")

        # Almacenar los datos recolectados
        if result:
            logger.info("Almacenando datos en la base de datos...")
            stored = await collector.store(result)
            if stored:
                logger.info("Datos almacenados correctamente")
            else:
                logger.warning("No se pudieron almacenar los datos")
    except Exception as e:
        logger.error(f"Error al ejecutar el colector de Binance: {str(e)}")
        raise

if __name__ == "__main__":
    # Ejecutar el colector
    asyncio.run(main())
