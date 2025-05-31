"""
Colector para datos de criptomonedas utilizando la API de Binance a través de ccxt.
"""

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import ccxt
import ccxt.async_support as ccxt_async
from dotenv import load_dotenv

from ..utils.config import get_config
from ..database.models import CryptoCurrency, CryptoPrice, OHLCV
from .base_collector import BaseCollector


class BinanceCollector(BaseCollector):
    """Colector de datos de criptomonedas desde Binance."""

    def __init__(self):
        """Inicializa el colector de Binance."""
        super().__init__("binance")
        self.config = get_config()
        
        # Cargar variables de entorno
        load_dotenv()
        
        # Configuración de la API de Binance
        self.api_key = os.getenv('BINANCE_API_KEY', '')
        self.api_secret = os.getenv('BINANCE_API_SECRET', '')
        
        # Inicializar cliente de Binance
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
            'apiKey': self.api_key,
            'secret': self.api_secret,
        })
        
        # Cliente asíncrono para operaciones no bloqueantes
        self.async_exchange = ccxt_async.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
            'apiKey': self.api_key,
            'secret': self.api_secret,
        })
        
        # Pares y timeframes a recolectar
        self.pairs = ['BTC/USDT', 'ETH/USDT']
        self.timeframes = ['1h', '4h', '1d']
        
        # Mínimo histórico a mantener
        self.min_rows = 200
        
        # Mapeo de símbolos a pares de Binance
        self.symbol_to_pair = {
            "BTC": "BTC/USDT",
            "ETH": "ETH/USDT",
        }
        
    async def get_ohlcv_data(self, symbol: str, timeframe: str = "1d", limit: int = 30) -> list:
        """Obtiene datos OHLCV para un par y timeframe específicos.
        
        Args:
            symbol: Par de criptomonedas (ej. BTCUSDT)
            timeframe: Marco temporal (ej. 1d, 4h, 1h)
            limit: Número de velas a obtener
            
        Returns:
            Lista de datos OHLCV [timestamp, open, high, low, close, volume]
        """
        try:
            # Formatear el símbolo si es necesario
            if "/" not in symbol:
                # Convertir BTCUSDT a BTC/USDT
                if "USDT" in symbol:
                    base = symbol.replace("USDT", "")
                    formatted_symbol = f"{base}/USDT"
                elif symbol in self.symbol_to_pair:
                    formatted_symbol = self.symbol_to_pair[symbol]
                else:
                    # Intentar inferir el formato
                    for quote in ["USDT", "BTC", "ETH"]:
                        if symbol.endswith(quote):
                            base = symbol[:-len(quote)]
                            formatted_symbol = f"{base}/{quote}"
                            break
                    else:
                        formatted_symbol = symbol
            else:
                formatted_symbol = symbol
                
            self.logger.info(f"Obteniendo datos OHLCV para {formatted_symbol} en timeframe {timeframe}")
            
            # Obtener datos OHLCV desde la base de datos
            db_gen = self.get_session()
            db = next(db_gen)
            
            query = db.query(OHLCV).filter(
                OHLCV.symbol == formatted_symbol,
                OHLCV.timeframe == timeframe
            ).order_by(OHLCV.timestamp.desc()).limit(limit)
            
            results = query.all()
            
            if results:
                # Convertir a formato de lista OHLCV [timestamp, open, high, low, close, volume]
                ohlcv_data = [
                    [
                        int(row.timestamp.replace(tzinfo=timezone.utc).timestamp() * 1000),
                        float(row.open),
                        float(row.high),
                        float(row.low),
                        float(row.close),
                        float(row.volume)
                    ] for row in reversed(results)  # Ordenar cronológicamente
                ]
                return ohlcv_data
            else:
                # Si no hay datos en la base de datos, obtenerlos directamente de Binance
                self.logger.info(f"No hay datos en la base de datos para {formatted_symbol} {timeframe}, obteniendo de Binance")
                ohlcv = self.exchange.fetch_ohlcv(formatted_symbol, timeframe, limit=limit)
                return ohlcv
                
        except Exception as e:
            self.logger.error(f"Error al obtener datos OHLCV para {symbol}: {str(e)}")
            return []

    async def collect(self) -> Dict[str, Any]:
        """
        Recolecta datos OHLCV desde Binance.

        Returns:
            Dict[str, Any]: Datos OHLCV por par y timeframe.
        """
        self.logger.info("Recolectando datos OHLCV desde Binance...")

        try:
            result = {
                "timestamp": datetime.now(timezone.utc),
                "data": {}
            }
            
            for pair in self.pairs:
                result["data"][pair] = {}
                
                for timeframe in self.timeframes:
                    self.logger.info(f"Obteniendo datos para {pair} en timeframe {timeframe}")
                    
                    # Buscar último timestamp en la base de datos
                    last_ohlcv = await self._get_last_ohlcv(pair, timeframe)
                    
                    if last_ohlcv:
                        last_ts = int(last_ohlcv.timestamp.replace(tzinfo=timezone.utc).timestamp() * 1000)
                        self.logger.info(f"Última vela guardada en BD: {last_ohlcv.timestamp}")
                    else:
                        self.logger.info(f"No hay histórico en la base de datos para {pair} {timeframe}, descargando desde 2020...")
                        last_ts = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
                    
                    # Obtener nuevos datos
                    ohlcv_data = await self._fetch_ohlcv_since(pair, timeframe, last_ts)
                    
                    if ohlcv_data:
                        result["data"][pair][timeframe] = ohlcv_data
                        self.logger.info(f"Se obtuvieron {len(ohlcv_data)} velas para {pair} {timeframe}")
                    else:
                        result["data"][pair][timeframe] = []
                        self.logger.warning(f"No se obtuvieron datos para {pair} {timeframe}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error al recolectar datos OHLCV: {str(e)}")
            return {"timestamp": datetime.now(timezone.utc), "data": {}}

    async def store(self, data: Dict[str, Any]) -> bool:
        """
        Almacena los datos OHLCV en la base de datos.

        Args:
            data: Datos a almacenar.

        Returns:
            bool: True si se almacenaron correctamente, False en caso contrario.
        """
        if not data or "data" not in data or not data["data"]:
            self.logger.warning("No hay datos para almacenar")
            return False

        try:
            # Usar el generador de sesión
            db_gen = self.get_session()
            db = next(db_gen)
            
            timestamp = data["timestamp"]
            total_count = 0
            
            for pair, timeframes_data in data["data"].items():
                # Extraer símbolo del par (BTC/USDT -> BTC)
                symbol = pair.split('/')[0]
                
                # Buscar o crear la criptomoneda
                crypto = db.query(CryptoCurrency).filter_by(symbol=symbol).first()
                
                if not crypto:
                    crypto = CryptoCurrency(
                        symbol=symbol,
                        name=symbol,  # Nombre provisional
                        slug=symbol.lower(),
                        last_updated=timestamp
                    )
                    db.add(crypto)
                    db.flush()  # Para obtener el ID
                else:
                    crypto.last_updated = timestamp
                
                for timeframe, ohlcv_list in timeframes_data.items():
                    count = 0
                    
                    # Obtener el rango de timestamps de los nuevos datos
                    if ohlcv_list:
                        min_new_ts = min(item["timestamp"] for item in ohlcv_list)
                        max_new_ts = max(item["timestamp"] for item in ohlcv_list)
                        min_new_dt = datetime.fromtimestamp(min_new_ts / 1000, tz=timezone.utc)
                        max_new_dt = datetime.fromtimestamp(max_new_ts / 1000, tz=timezone.utc)
                        
                        # Consultar timestamps existentes en el rango relevante
                        existing_timestamps = set(
                            ts[0].replace(tzinfo=timezone.utc) for ts in db.query(OHLCV.timestamp)
                            .filter(
                                OHLCV.symbol == pair,
                                OHLCV.timeframe == timeframe,
                                OHLCV.timestamp >= min_new_dt,
                                OHLCV.timestamp <= max_new_dt
                            ).all()
                        )
                        
                        # Crear lista de diccionarios para bulk_insert_mappings
                        new_ohlcv_dicts = []
                        for item in ohlcv_list:
                            ts_dt = datetime.fromtimestamp(item["timestamp"] / 1000, tz=timezone.utc)
                            if ts_dt not in existing_timestamps:
                                new_ohlcv_dicts.append({
                                    'timestamp': ts_dt,
                                    'open': item["open"],
                                    'high': item["high"],
                                    'low': item["low"],
                                    'close': item["close"],
                                    'volume': item["volume"],
                                    'symbol': pair,
                                    'timeframe': timeframe,
                                    'cryptocurrency_id': crypto.id
                                })
                        
                        if new_ohlcv_dicts:
                            db.bulk_insert_mappings(OHLCV, new_ohlcv_dicts)
                            count = len(new_ohlcv_dicts)
                            total_count += count
                    
                    self.logger.info(f"Almacenadas {count} velas nuevas para {pair} {timeframe}")
            
            # Commit los cambios
            db.commit()
            self.logger.info(f"Almacenados {total_count} registros OHLCV en total")
            return True
            
        except Exception as e:
            self.logger.error(f"Error al almacenar datos OHLCV: {str(e)}")
            if 'db' in locals():
                db.rollback()
            return False
        finally:
            if 'db' in locals():
                db.close()

    async def _fetch_ohlcv_since(self, pair: str, timeframe: str, since: int) -> List[Dict[str, Any]]:
        """
        Descarga velas desde 'since' hasta ahora.
        
        Args:
            pair: Par de trading (ej. BTC/USDT)
            timeframe: Intervalo de tiempo (ej. 1h, 4h, 1d)
            since: Timestamp en milisegundos desde donde comenzar
            
        Returns:
            List[Dict[str, Any]]: Lista de velas OHLCV
        """
        all_ohlcv = []
        limit = 500  # Máximo permitido por ccxt
        batch = 0
        
        try:
            while True:
                # Usar el cliente asíncrono
                ohlcv = await self.async_exchange.fetch_ohlcv(pair, timeframe=timeframe, since=since, limit=limit)
                
                if not ohlcv:
                    self.logger.info(f"Descargadas {len(all_ohlcv)} velas en total para {pair} {timeframe}. No hay más datos.")
                    break
                
                # Convertir a formato más amigable
                formatted_ohlcv = []
                for candle in ohlcv:
                    formatted_ohlcv.append({
                        "timestamp": candle[0],
                        "open": candle[1],
                        "high": candle[2],
                        "low": candle[3],
                        "close": candle[4],
                        "volume": candle[5]
                    })
                
                all_ohlcv.extend(formatted_ohlcv)
                batch += 1
                
                last_ts = ohlcv[-1][0] if ohlcv else since
                last_dt = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc)
                self.logger.info(f"Batch {batch}: +{len(ohlcv)} velas (total: {len(all_ohlcv)}) - Última vela: {last_dt}")
                
                if len(ohlcv) < limit:
                    break
                    
                since = ohlcv[-1][0] + 1  # Siguiente vela
                
                # Respetar límites de tasa
                await asyncio.sleep(0.5)
                
            return all_ohlcv
            
        except Exception as e:
            self.logger.error(f"Error al obtener datos OHLCV para {pair} {timeframe}: {str(e)}")
            return []
        finally:
            # Cerrar el cliente asíncrono al finalizar
            if hasattr(self, 'async_exchange') and self.async_exchange:
                await self.async_exchange.close()

    async def _get_last_ohlcv(self, symbol: str, timeframe: str) -> Optional[OHLCV]:
        """
        Obtiene el último registro OHLCV para un símbolo y timeframe.
        
        Args:
            symbol: Símbolo del par (ej. BTC/USDT)
            timeframe: Intervalo de tiempo (ej. 1h, 4h, 1d)
            
        Returns:
            Optional[OHLCV]: Último registro OHLCV o None si no existe
        """
        try:
            db_gen = self.get_session()
            db = next(db_gen)
            
            last_ohlcv = (
                db.query(OHLCV)
                .filter_by(symbol=symbol, timeframe=timeframe)
                .order_by(OHLCV.timestamp.desc())
                .first()
            )
            
            return last_ohlcv
            
        except Exception as e:
            self.logger.error(f"Error al obtener último OHLCV para {symbol} {timeframe}: {str(e)}")
            return None
        finally:
            if 'db' in locals():
                db.close()

    async def get_latest_ohlcv(self, symbol: str, timeframe: str = '1d', limit: int = 30) -> Dict[str, Any]:
        """
        Obtiene los datos OHLCV más recientes para un símbolo y timeframe.
        
        Args:
            symbol: Símbolo de la criptomoneda (ej. BTC)
            timeframe: Intervalo de tiempo (ej. 1h, 4h, 1d)
            limit: Número máximo de velas a devolver
            
        Returns:
            Dict[str, Any]: Datos OHLCV recientes
        """
        try:
            # Convertir símbolo a par de Binance
            pair = self.symbol_to_pair.get(symbol.upper())
            if not pair:
                self.logger.warning(f"No se encontró mapeo para {symbol}")
                return {"data": []}
                
            db_gen = self.get_session()
            db = next(db_gen)
            
            # Obtener los últimos registros OHLCV
            ohlcv_data = (
                db.query(OHLCV)
                .filter_by(symbol=pair, timeframe=timeframe)
                .order_by(OHLCV.timestamp.desc())
                .limit(limit)
                .all()
            )
            
            # Convertir a formato JSON
            result = []
            for ohlcv in reversed(ohlcv_data):  # Revertir para orden cronológico
                result.append({
                    "timestamp": int(ohlcv.timestamp.replace(tzinfo=timezone.utc).timestamp() * 1000),
                    "open": ohlcv.open,
                    "high": ohlcv.high,
                    "low": ohlcv.low,
                    "close": ohlcv.close,
                    "volume": ohlcv.volume
                })
                
            return {"data": result}
            
        except Exception as e:
            self.logger.error(f"Error al obtener OHLCV recientes para {symbol} {timeframe}: {str(e)}")
            return {"data": []}
        finally:
            if 'db' in locals():
                db.close()

    async def calculate_indicators(self, symbol: str, timeframe: str = '1d') -> Dict[str, Any]:
        """
        Calcula indicadores técnicos para un símbolo y timeframe.
        
        Args:
            symbol: Símbolo de la criptomoneda (ej. BTC)
            timeframe: Intervalo de tiempo (ej. 1h, 4h, 1d)
            
        Returns:
            Dict[str, Any]: Indicadores técnicos calculados
        """
        try:
            # Obtener datos OHLCV recientes
            ohlcv_data = await self.get_latest_ohlcv(symbol, timeframe, limit=50)
            
            if not ohlcv_data["data"]:
                return {"indicators": {}}
                
            # Extraer precios de cierre para cálculos
            closes = [candle["close"] for candle in ohlcv_data["data"]]
            
            # Calcular SMA de 7 y 25 períodos
            sma7 = self._calculate_sma(closes, 7)
            sma25 = self._calculate_sma(closes, 25)
            
            # Calcular RSI de 14 períodos
            rsi = self._calculate_rsi(closes, 14)
            
            # Calcular volatilidad (desviación estándar de los retornos)
            volatility = self._calculate_volatility(closes, 14)
            
            # Determinar tendencia basada en SMA
            current_price = closes[-1]
            trend = "lateral"
            if current_price > sma7 > sma25:
                trend = "alcista"
            elif current_price < sma7 < sma25:
                trend = "bajista"
                
            # Determinar nivel de volatilidad
            volatility_level = "media"
            if volatility > 0.03:  # 3% diario
                volatility_level = "alta"
            elif volatility < 0.01:  # 1% diario
                volatility_level = "baja"
                
            # Determinar soporte y resistencia (simplificado)
            highs = [candle["high"] for candle in ohlcv_data["data"]]
            lows = [candle["low"] for candle in ohlcv_data["data"]]
            
            resistance = max(highs[-20:])  # Máximo de los últimos 20 períodos
            support = min(lows[-20:])  # Mínimo de los últimos 20 períodos
            
            return {
                "indicators": {
                    "sma7": sma7,
                    "sma25": sma25,
                    "rsi": rsi,
                    "volatility": volatility,
                    "trend": trend,
                    "volatility_level": volatility_level,
                    "support": support,
                    "resistance": resistance,
                    "current_price": current_price,
                    "position_to_sma7": "por encima" if current_price > sma7 else "por debajo",
                    "position_to_sma25": "por encima" if current_price > sma25 else "por debajo"
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error al calcular indicadores para {symbol} {timeframe}: {str(e)}")
            return {"indicators": {}}

    def _calculate_sma(self, data: List[float], period: int) -> float:
        """Calcula la Media Móvil Simple."""
        if len(data) < period:
            return 0
        return sum(data[-period:]) / period

    def _calculate_rsi(self, data: List[float], period: int) -> float:
        """Calcula el Índice de Fuerza Relativa (RSI)."""
        if len(data) < period + 1:
            return 50  # Valor neutral si no hay suficientes datos
            
        # Calcular cambios diarios
        deltas = [data[i] - data[i-1] for i in range(1, len(data))]
        
        # Separar ganancias y pérdidas
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [abs(delta) if delta < 0 else 0 for delta in deltas]
        
        # Calcular promedio de ganancias y pérdidas
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        # Evitar división por cero
        if avg_loss == 0:
            return 100
            
        # Calcular RS y RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    def _calculate_volatility(self, data: List[float], period: int) -> float:
        """Calcula la volatilidad como desviación estándar de los retornos porcentuales."""
        if len(data) < period + 1:
            return 0
            
        # Calcular retornos porcentuales diarios
        returns = [(data[i] / data[i-1]) - 1 for i in range(1, len(data))]
        returns = returns[-period:]  # Usar solo los últimos 'period' retornos
        
        # Calcular desviación estándar
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        return std_dev
