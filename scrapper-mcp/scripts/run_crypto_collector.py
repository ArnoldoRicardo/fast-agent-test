"""
Script para probar manualmente la ingesta de datos de criptomonedas.
Permite recopilar datos actuales o históricos en un marco de tiempo específico.
"""

import asyncio
import argparse
import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta

# Asegurar que el directorio raíz esté en el path
ROOT_DIR = Path(__file__).parent.parent  # Ajustado para que apunte al directorio raíz desde scripts/
sys.path.insert(0, str(ROOT_DIR))

from src.collectors.crypto import CryptoCollector
from src.database.connection import init_db, get_db
from src.database.models import CryptoCurrency, CryptoPrice
from src.utils.logging import get_logger
from src.utils.config import get_config

# Inicializar logger y configuración
logger = get_logger("crypto_collector")
config = get_config()


async def collect_current_data():
    """Recopila los datos actuales de criptomonedas."""
    logger.info("Creando colector de criptomonedas...")
    collector = CryptoCollector()

    logger.info("Iniciando recolección de datos actuales...")
    result = await collector.run()

    if result:
        logger.info("Recolección completada exitosamente")

        # Obtener y mostrar los datos recolectados
        logger.info("Obteniendo datos recolectados...")
        prices = await collector.get_latest_prices()

        logger.info(f"Se obtuvieron datos para {len(prices)} criptomonedas")

        # Mostrar los datos
        for symbol, data in prices.items():
            logger.info(f"{symbol}: ${data['price_usd']:.2f} (Cambio 24h: {data.get('percent_change_24h', 0):.2f}%)")
        return True
    else:
        logger.error("La recolección falló")
        return False


async def collect_historical_data(days=30, interval="daily"):
    """
    Recopila datos históricos de criptomonedas para un período específico.

    Args:
        days: Número de días hacia atrás para recopilar datos.
        interval: Intervalo de tiempo ('daily', 'hourly').
    """
    logger.info(f"Iniciando recolección de datos históricos para los últimos {days} días con intervalo {interval}...")

    # Crear colector
    collector = CryptoCollector()

    # Obtener los símbolos configurados
    symbols = config.scraper.crypto_symbols
    logger.info(f"Recopilando datos históricos para: {', '.join(symbols)}")

    # Obtener la fecha de fin (fecha actual)
    end_date = datetime.utcnow()
    
    # Verificar si se especificó un máximo de días por intervalo
    max_days_per_interval = min(days, 90)  # Máximo 90 días por intervalo (límite de CoinGecko)
    
    # Calcular cuántos intervalos necesitamos
    total_intervals = (days + max_days_per_interval - 1) // max_days_per_interval
    
    logger.info(f"Recolectando datos históricos en {total_intervals} intervalos de máximo {max_days_per_interval} días cada uno")

    # Inicializar contador de éxitos
    success_count = 0
    total_records_stored = 0

    # Procesar cada símbolo
    for symbol in symbols:
        symbol_success = True
        symbol_records = 0
        
        # Procesar cada intervalo para este símbolo
        for interval_idx in range(total_intervals):
            # Calcular fechas de inicio y fin para este intervalo
            interval_end = end_date - timedelta(days=interval_idx * max_days_per_interval)
            interval_start = interval_end - timedelta(days=max_days_per_interval)
            
            # Convertir a timestamps (milisegundos)
            from_timestamp = int(interval_start.timestamp() * 1000)
            to_timestamp = int(interval_end.timestamp() * 1000)
            
            interval_start_str = interval_start.strftime('%Y-%m-%d')
            interval_end_str = interval_end.strftime('%Y-%m-%d')
            
            logger.info(f"Intervalo {interval_idx+1}/{total_intervals} para {symbol}: {interval_start_str} a {interval_end_str}")
            
            try:
                # Usar el colector para obtener datos históricos para este intervalo
                result = await collector.collect_historical(symbol, from_timestamp, to_timestamp)
                
                if not result or "data" not in result or not result["data"]:
                    logger.warning(f"No se encontraron datos históricos para {symbol} en el intervalo {interval_idx+1}")
                    continue
                
                data_points = result["data"]
                logger.info(f"Se obtuvieron {len(data_points)} puntos de datos para {symbol} en el intervalo {interval_idx+1}")
                
                if data_points:
                    first_date = datetime.fromtimestamp(data_points[0]["timestamp"] / 1000).strftime('%Y-%m-%d')
                    last_date = datetime.fromtimestamp(data_points[-1]["timestamp"] / 1000).strftime('%Y-%m-%d')
                    logger.info(f"Rango de fechas: {first_date} a {last_date}")
                    logger.info(f"Precio inicial: ${data_points[0]['price']:.2f}, Precio final: ${data_points[-1]['price']:.2f}")
                    
                    # Obtener la sesión de la base de datos
                    db_gen = get_db()
                    db = next(db_gen)
                    
                    try:
                        # Buscar o crear la criptomoneda
                        crypto = db.query(CryptoCurrency).filter_by(symbol=symbol.upper()).first()
                        
                        if not crypto:
                            # Si no existe, crear un nuevo registro
                            crypto = CryptoCurrency(
                                symbol=symbol.upper(),
                                name=symbol.upper(),  # En una implementación real, obtendríamos el nombre completo
                                slug=symbol.lower(),
                                last_updated=datetime.utcnow()
                            )
                            db.add(crypto)
                            db.flush()
                        
                        # Almacenar cada punto de datos
                        stored_count = 0
                        for point in data_points:
                            # Convertir timestamp de milisegundos a datetime
                            timestamp = datetime.fromtimestamp(point["timestamp"] / 1000)
                            
                            # Verificar si ya existe un precio para este timestamp
                            existing_price = (
                                db.query(CryptoPrice)
                                .filter_by(cryptocurrency_id=crypto.id, timestamp=timestamp)
                                .first()
                            )
                            
                            if not existing_price:
                                # Crear nuevo registro de precio
                                price_record = CryptoPrice(
                                    cryptocurrency_id=crypto.id,
                                    timestamp=timestamp,
                                    price_usd=point["price"],
                                    market_cap_usd=point.get("market_cap"),
                                    volume_24h_usd=point.get("volume"),
                                    percent_change_24h=None  # No tenemos este dato en el histórico
                                )
                                db.add(price_record)
                                stored_count += 1
                        
                        # Commit los cambios
                        db.commit()
                        logger.info(f"Almacenados {stored_count} registros históricos para {symbol} en el intervalo {interval_idx+1}")
                        symbol_records += stored_count
                        
                    except Exception as e:
                        db.rollback()
                        logger.error(f"Error al almacenar datos históricos para {symbol} en el intervalo {interval_idx+1}: {str(e)}")
                        symbol_success = False
                    finally:
                        db.close()
                
                # Esperar un poco para no sobrecargar la API
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error al obtener datos históricos para {symbol} en el intervalo {interval_idx+1}: {str(e)}")
                symbol_success = False
        
        # Actualizar contadores
        if symbol_success:
            success_count += 1
        total_records_stored += symbol_records
        logger.info(f"Total de registros almacenados para {symbol}: {symbol_records}")

    logger.info(f"Recolección histórica completada. Éxito para {success_count}/{len(symbols)} criptomonedas")
    logger.info(f"Total de registros históricos almacenados: {total_records_stored}")
    return success_count > 0


async def run_crypto_collector(historical=False, days=30, interval="daily"):
    """Ejecuta la recolección de datos de criptomonedas.

    Args:
        historical: Si es True, recopila datos históricos.
        days: Número de días hacia atrás para recopilar datos históricos.
        interval: Intervalo de tiempo para datos históricos ('daily', 'hourly').
    """
    logger.info("Inicializando base de datos...")
    init_db()

    if historical:
        return await collect_historical_data(days, interval)
    else:
        return await collect_current_data()


if __name__ == "__main__":
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="Recolector de datos de criptomonedas")
    parser.add_argument(
        "--historical", "-hist", action="store_true",
        help="Recopilar datos históricos en lugar de datos actuales"
    )
    parser.add_argument(
        "--days", "-d", type=int, default=30,
        help="Número de días hacia atrás para recopilar datos históricos (por defecto: 30)"
    )
    parser.add_argument(
        "--interval", "-i", choices=["daily", "hourly"], default="daily",
        help="Intervalo de tiempo para datos históricos (por defecto: daily)"
    )

    args = parser.parse_args()

    # Ejecutar el recolector
    asyncio.run(run_crypto_collector(
        historical=args.historical,
        days=args.days,
        interval=args.interval
    ))
