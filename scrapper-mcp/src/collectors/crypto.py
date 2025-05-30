"""
Colector para datos de criptomonedas utilizando la API de CoinGecko.
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests
import requests_cache

from ..utils.config import get_config
from ..database.connection import get_db
from ..database.models import CryptoCurrency, CryptoPrice
from .base_collector import BaseCollector


class CryptoCollector(BaseCollector):
    """Colector de datos de criptomonedas."""
    
    def __init__(self):
        """Inicializa el colector de criptomonedas."""
        super().__init__("crypto")
        self.config = get_config()
        self.api_key = self.config.scraper.crypto_api_key
        self.base_url = "https://api.coingecko.com/api/v3"
        self.coins_url = f"{self.base_url}/coins/markets"
        
        # Mapeo de símbolos a IDs de CoinGecko
        self.symbol_to_id = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "BNB": "binancecoin",
            "SOL": "solana",
            "XRP": "ripple"
        }
        
        # Control de tasa para respetar los límites de la API
        # CoinGecko permite 30 llamadas por minuto (2 segundos por llamada)
        self.last_request_time = 0
        self.min_request_interval = 2  # segundos entre solicitudes
        self.monthly_limit = 10000     # límite mensual de llamadas
        self.monthly_calls = 0         # contador de llamadas mensuales
        
        # Configurar caché para requests
        # Expira después de 10 minutos para datos de cripto que cambian rápidamente
        requests_cache.install_cache(
            cache_name=f"{self.config.database.url.replace('sqlite:///', '')}_crypto",
            backend='sqlite',
            expire_after=600
        )
        
    async def collect(self) -> Dict[str, Any]:
        """
        Recolecta datos de criptomonedas desde CoinGecko.
        
        Returns:
            Dict[str, Any]: Datos de criptomonedas.
        """
        self.logger.info("Recolectando datos de criptomonedas...")
        
        try:
            # Obtener los símbolos configurados
            symbols = self.config.scraper.crypto_symbols
            self.logger.info(f"Obteniendo datos para: {', '.join(symbols)}")
            
            # Convertir símbolos a IDs de CoinGecko
            coin_ids = []
            for symbol in symbols:
                if symbol.upper() in self.symbol_to_id:
                    coin_ids.append(self.symbol_to_id[symbol.upper()])
                else:
                    # Si no hay mapeo, usar el símbolo en minúsculas como fallback
                    self.logger.warning(f"No se encontró mapeo para {symbol}, usando el símbolo en minúsculas")
                    coin_ids.append(symbol.lower())
            
            # Parámetros para la API
            params = {
                "vs_currency": "usd",
                "ids": ",".join(coin_ids),
                "order": "market_cap_desc",
                "per_page": len(symbols),
                "page": 1,
                "sparkline": False,
                "price_change_percentage": "24h"
            }
            
            # Preparar headers con API key si está disponible
            headers = {}
            if self.api_key:
                headers["x-cg-api-key"] = self.api_key
            
            # Respetar el límite de tasa antes de hacer la solicitud
            await self._respect_rate_limit()
            
            # Realizar la solicitud HTTP
            self.logger.info(f"URL: {self.coins_url}")
            self.logger.info(f"Params: {params}")
            self.logger.info(f"Headers: {headers}")
            response = requests.get(self.coins_url, params=params, headers=headers)
            
            # Imprimir información de la respuesta
            self.logger.info(f"Status Code: {response.status_code}")
            self.logger.info(f"Response Headers: {response.headers}")
            
            # Si hay un error, imprimir el contenido de la respuesta
            if response.status_code >= 400:
                self.logger.error(f"Error response: {response.text}")
                
            response.raise_for_status()  # Lanzar excepción si hay error HTTP
            
            coins_data = response.json()
            self.logger.info(f"Se obtuvieron datos para {len(coins_data)} criptomonedas")
            
            # Formatear los datos para su almacenamiento
            result = {
                "timestamp": datetime.utcnow(),
                "coins": coins_data
            }
            
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error al obtener datos de criptomonedas: {str(e)}")
            # En caso de error, devolver un diccionario vacío
            return {"timestamp": datetime.utcnow(), "coins": []}
    
    async def store(self, data: Dict[str, Any]) -> bool:
        """
        Almacena los datos de criptomonedas en la base de datos.
        
        Args:
            data: Datos a almacenar.
            
        Returns:
            bool: True si se almacenaron correctamente, False en caso contrario.
        """
        if not data or "coins" not in data or not data["coins"]:
            self.logger.warning("No hay datos para almacenar")
            return False
        
        try:
            # Usar el generador de sesión
            db_gen = self.get_session()
            db = next(db_gen)
            
            timestamp = data["timestamp"]
            count = 0
            
            for coin in data["coins"]:
                # Buscar o crear la criptomoneda
                crypto = db.query(CryptoCurrency).filter_by(symbol=coin["symbol"].upper()).first()
                
                if not crypto:
                    crypto = CryptoCurrency(
                        symbol=coin["symbol"].upper(),
                        name=coin["name"],
                        slug=coin["id"],
                        last_updated=timestamp
                    )
                    db.add(crypto)
                    db.flush()  # Para obtener el ID
                else:
                    crypto.last_updated = timestamp
                
                # Crear el registro de precio
                price = CryptoPrice(
                    cryptocurrency_id=crypto.id,
                    timestamp=timestamp,
                    price_usd=coin["current_price"],
                    market_cap_usd=coin.get("market_cap"),
                    volume_24h_usd=coin.get("total_volume"),
                    percent_change_24h=coin.get("price_change_percentage_24h")
                )
                db.add(price)
                count += 1
            
            # Commit los cambios
            db.commit()
            self.logger.info(f"Almacenados {count} registros de precios de criptomonedas")
            return True
        
        except Exception as e:
            self.logger.error(f"Error al almacenar datos de criptomonedas: {str(e)}")
            if 'db' in locals():
                db.rollback()
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    async def _respect_rate_limit(self):
        """
        Espera un tiempo fijo entre solicitudes para respetar los límites de tasa de la API.
        """
        # Esperar un tiempo fijo entre solicitudes (2 segundos)
        await asyncio.sleep(2)
        
        # Actualizar el tiempo de la última solicitud
        self.last_request_time = time.time()
    
    async def collect_historical(self, symbol: str, from_timestamp: int, to_timestamp: int) -> Dict[str, Any]:
        """
        Recolecta datos históricos de una criptomoneda específica.
        
        Args:
            symbol: Símbolo de la criptomoneda.
            from_timestamp: Timestamp de inicio (en milisegundos).
            to_timestamp: Timestamp de fin (en milisegundos).
            
        Returns:
            Dict[str, Any]: Datos históricos de la criptomoneda.
        """
        self.logger.info(f"Recolectando datos históricos para {symbol}...")
        
        try:
            # Obtener el ID correcto de CoinGecko
            if symbol.upper() in self.symbol_to_id:
                coin_id = self.symbol_to_id[symbol.upper()]
            else:
                # Si no hay mapeo, usar el símbolo en minúsculas como fallback
                self.logger.warning(f"No se encontró mapeo para {symbol}, usando el símbolo en minúsculas")
                coin_id = symbol.lower()
            
            # Construir URL
            url = f"{self.base_url}/coins/{coin_id}/market_chart/range"
            params = {
                "vs_currency": "usd",
                "from": from_timestamp // 1000,  # CoinGecko usa segundos, no milisegundos
                "to": to_timestamp // 1000
            }
            
            # Preparar headers con API key si está disponible
            headers = {}
            if self.api_key:
                headers["x-cg-api-key"] = self.api_key
            
            # Respetar el límite de tasa antes de hacer la solicitud
            await self._respect_rate_limit()
            
            # Realizar la solicitud HTTP
            self.logger.info(f"URL: {url}")
            self.logger.info(f"Params: {params}")
            self.logger.info(f"Headers: {headers}")
            response = requests.get(url, params=params, headers=headers)
            
            # Imprimir información de la respuesta
            self.logger.info(f"Status Code: {response.status_code}")
            
            # Si hay un error, imprimir el contenido de la respuesta
            if response.status_code >= 400:
                self.logger.error(f"Error response: {response.text}")
                
            response.raise_for_status()  # Lanzar excepción si hay error HTTP
            
            # Procesar la respuesta
            data = response.json()
            
            if 'prices' not in data:
                self.logger.warning(f"No se encontraron datos de precios para {symbol}")
                return {}
            
            # Obtener precios, market_cap y volumen
            prices = data.get('prices', [])
            market_caps = data.get('market_caps', [])
            volumes = data.get('total_volumes', [])
            
            # Asegurarse de que todos los arrays tengan la misma longitud
            min_length = min(len(prices), len(market_caps), len(volumes))
            
            result = {
                "symbol": symbol,
                "data": []
            }
            
            for i in range(min_length):
                timestamp = prices[i][0]  # El timestamp está en milisegundos
                price = prices[i][1]
                market_cap = market_caps[i][1] if i < len(market_caps) else None
                volume = volumes[i][1] if i < len(volumes) else None
                
                result["data"].append({
                    "timestamp": timestamp,
                    "price": price,
                    "market_cap": market_cap,
                    "volume": volume
                })
            
            self.logger.info(f"Se obtuvieron {len(result['data'])} puntos de datos históricos para {symbol}")
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error al obtener datos históricos para {symbol}: {str(e)}")
            return {}
    
    async def get_latest_prices(self) -> Dict[str, Any]:
        """
        Obtiene los precios más recientes de criptomonedas.
        
        Returns:
            Dict[str, Any]: Precios recientes por símbolo.
        """
        try:
            db_gen = self.get_session()
            db = next(db_gen)
            
            result = {}
            
            for symbol in self.config.scraper.crypto_symbols:
                # Obtener la criptomoneda y su precio más reciente
                crypto = db.query(CryptoCurrency).filter_by(symbol=symbol.upper()).first()
                
                if crypto:
                    # Obtener el precio más reciente
                    latest_price = (
                        db.query(CryptoPrice)
                        .filter_by(cryptocurrency_id=crypto.id)
                        .order_by(CryptoPrice.timestamp.desc())
                        .first()
                    )
                    
                    if latest_price:
                        result[symbol] = {
                            "name": crypto.name,
                            "symbol": crypto.symbol,
                            "price_usd": latest_price.price_usd,
                            "market_cap_usd": latest_price.market_cap_usd,
                            "volume_24h_usd": latest_price.volume_24h_usd,
                            "percent_change_24h": latest_price.percent_change_24h,
                            "timestamp": latest_price.timestamp.isoformat()
                        }
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error al obtener precios recientes: {str(e)}")
            return {}
        finally:
            if 'db' in locals():
                db.close()
