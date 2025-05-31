"""
Servidor MCP para datos financieros utilizando el SDK oficial de MCP.
"""

import logging
from typing import List

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send
import contextlib
from collections.abc import AsyncIterator

from ..collectors.crypto import CryptoCollector
from ..collectors.binance import BinanceCollector
from ..utils.logging import get_logger

# Inicializar logger
logger = get_logger("mcp.server")

# Colectores
crypto_collector = CryptoCollector()
binance_collector = BinanceCollector()


def create_mcp_app(port: int = 8080, json_response: bool = False):
    """
    Crea una aplicación MCP utilizando el SDK oficial.

    Args:
        port: Puerto en el que escuchar.
        json_response: Si se deben devolver respuestas JSON en lugar de streams SSE.

    Returns:
        La aplicación Starlette.
    """
    # Crear la aplicación MCP
    app = Server("finance-mcp-server")

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[types.TextContent]:
        """
        Maneja las llamadas a herramientas.

        Args:
            name: Nombre de la herramienta.
            arguments: Argumentos para la herramienta.

        Returns:
            Lista de contenido de texto.
        """
        ctx = app.request_context
        logger.info(f"Llamada a herramienta: {name} con argumentos: {arguments}")

        try:
            result = None

            # Ejecutar la herramienta correspondiente
            if name == "get_crypto_prices":
                symbols = arguments.get("symbols", [])
                if not symbols:
                    return [types.TextContent(
                        type="text",
                        text="Debe proporcionar al menos un símbolo de criptomoneda"
                    )]

                # Obtener precios actuales
                prices = await crypto_collector.get_latest_prices()

                # Filtrar por símbolos solicitados
                if symbols:
                    prices = {k: v for k, v in prices.items() if k.upper() in [s.upper() for s in symbols]}

                result = prices

            elif name == "get_crypto_historical":
                symbol = arguments.get("symbol")
                days = arguments.get("days", 7)

                if not symbol:
                    return [types.TextContent(
                        type="text",
                        text="Debe proporcionar un símbolo de criptomoneda"
                    )]

                # Calcular timestamps para el rango de días
                import time
                from datetime import datetime, timedelta

                to_date = datetime.now()
                from_date = to_date - timedelta(days=days)

                from_timestamp = int(from_date.timestamp() * 1000)
                to_timestamp = int(to_date.timestamp() * 1000)

                # Obtener datos históricos
                historical_data = await crypto_collector.collect_historical(symbol, from_timestamp, to_timestamp)
                result = historical_data

            elif name == "get_crypto_details":
                symbol = arguments.get("symbol")

                if not symbol:
                    return [types.TextContent(
                        type="text",
                        text="Debe proporcionar un símbolo de criptomoneda"
                    )]

                # Obtener el ID correcto de CoinGecko
                coin_id = None
                if symbol.upper() in crypto_collector.symbol_to_id:
                    coin_id = crypto_collector.symbol_to_id[symbol.upper()]
                else:
                    # Si no hay mapeo, usar el símbolo en minúsculas como fallback
                    coin_id = symbol.lower()

                # Construir URL para detalles de la criptomoneda
                url = f"{crypto_collector.base_url}/coins/{coin_id}"

                # Preparar headers con API key si está disponible
                headers = {}
                if crypto_collector.api_key:
                    headers["x-cg-api-key"] = crypto_collector.api_key

                # Respetar el límite de tasa antes de hacer la solicitud
                await crypto_collector._respect_rate_limit()

                # Realizar la solicitud HTTP
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            details = await response.json()

                            # Extraer información relevante
                            result = {
                                "id": details.get("id"),
                                "symbol": details.get("symbol"),
                                "name": details.get("name"),
                                "description": details.get("description", {}).get("en", ""),
                                "market_data": {
                                    "current_price": details.get("market_data", {}).get("current_price", {}),
                                    "market_cap": details.get("market_data", {}).get("market_cap", {}),
                                    "total_volume": details.get("market_data", {}).get("total_volume", {})
                                },
                                "links": details.get("links", {})
                            }
                        else:
                            return [types.TextContent(
                                type="text",
                                text=f"Error al obtener detalles: {await response.text()}"
                            )]
                            
            elif name == "get_ohlcv_data":
                symbol = arguments.get("symbol")
                timeframe = arguments.get("timeframe", "1d")
                limit = arguments.get("limit", 30)
                
                if not symbol:
                    return [types.TextContent(
                        type="text",
                        text="Debe proporcionar un símbolo de criptomoneda"
                    )]
                
                # Obtener datos OHLCV
                ohlcv_data = await binance_collector.get_ohlcv_data(symbol, timeframe, limit)
                result = ohlcv_data
                
            elif name == "calculate_indicators":
                symbol = arguments.get("symbol")
                timeframe = arguments.get("timeframe", "1d")
                indicators = arguments.get("indicators", ["sma", "ema", "rsi"])
                limit = arguments.get("limit", 30)
                
                if not symbol:
                    return [types.TextContent(
                        type="text",
                        text="Debe proporcionar un símbolo de criptomoneda"
                    )]
                
                # Obtener datos OHLCV
                ohlcv_data = await binance_collector.get_ohlcv_data(symbol, timeframe, limit)
                
                # Calcular indicadores usando implementaciones manuales (sin pandas-ta)
                import pandas as pd
                import numpy as np
                
                # Convertir a DataFrame
                df = pd.DataFrame(ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
                close_prices = df["close"].values.tolist()  # Convertir a lista para evitar problemas de tipo
                
                # Calcular indicadores solicitados
                result = {"ohlcv": ohlcv_data, "indicators": {}}
                
                for indicator in indicators:
                    if indicator.lower() == "sma":
                        # Media móvil simple (20 períodos)
                        window_size = 20
                        sma = []
                        for i in range(len(close_prices)):
                            if i < window_size - 1:
                                sma.append(0.0)  # No hay suficientes datos para calcular SMA
                            else:
                                sma.append(float(sum(close_prices[i-window_size+1:i+1]) / window_size))
                        result["indicators"]["sma_20"] = sma
                    
                    elif indicator.lower() == "ema":
                        # Media móvil exponencial (20 períodos)
                        window_size = 20
                        multiplier = 2.0 / (window_size + 1.0)
                        ema = [0.0] * window_size  # Primeros valores son 0
                        
                        # Inicializar con SMA
                        if len(close_prices) >= window_size:
                            ema[window_size-1] = float(sum(close_prices[:window_size]) / window_size)
                            
                            # Calcular EMA
                            for i in range(window_size, len(close_prices)):
                                ema.append(float(close_prices[i] * multiplier + ema[i-1] * (1.0 - multiplier)))
                        
                        result["indicators"]["ema_20"] = ema
                    
                    elif indicator.lower() == "rsi":
                        # Índice de fuerza relativa (14 períodos)
                        window_size = 14
                        rsi = [0.0] * window_size  # Primeros valores son 0
                        
                        if len(close_prices) >= window_size + 1:
                            # Calcular cambios
                            changes = [float(close_prices[i] - close_prices[i-1]) for i in range(1, len(close_prices))]
                            
                            # Calcular ganancias y pérdidas
                            gains = [max(0.0, change) for change in changes]
                            losses = [max(0.0, -change) for change in changes]
                            
                            # Inicializar con promedios
                            avg_gain = float(sum(gains[:window_size]) / window_size)
                            avg_loss = float(sum(losses[:window_size]) / window_size)
                            
                            # Calcular RSI
                            for i in range(window_size, len(changes)):
                                avg_gain = float((avg_gain * (window_size - 1) + gains[i]) / window_size)
                                avg_loss = float((avg_loss * (window_size - 1) + losses[i]) / window_size)
                                
                                if avg_loss == 0:
                                    rsi.append(100.0)
                                else:
                                    rs = float(avg_gain / avg_loss)
                                    rsi.append(float(100.0 - (100.0 / (1.0 + rs))))
                        
                        result["indicators"]["rsi_14"] = rsi
                    
                    elif indicator.lower() == "macd":
                        # MACD simplificado
                        fast_period = 12
                        slow_period = 26
                        signal_period = 9
                        
                        # Calcular EMAs para fast y slow
                        # Fast EMA
                        fast_multiplier = 2.0 / (fast_period + 1.0)
                        fast_ema = [0.0] * fast_period
                        if len(close_prices) >= fast_period:
                            # Inicializar con SMA
                            fast_ema[fast_period-1] = float(sum(close_prices[:fast_period]) / fast_period)
                            # Calcular resto de EMAs
                            for i in range(fast_period, len(close_prices)):
                                fast_ema.append(float(close_prices[i] * fast_multiplier + 
                                                     fast_ema[-1] * (1.0 - fast_multiplier)))
                        
                        # Slow EMA
                        slow_multiplier = 2.0 / (slow_period + 1.0)
                        slow_ema = [0.0] * slow_period
                        if len(close_prices) >= slow_period:
                            # Inicializar con SMA
                            slow_ema[slow_period-1] = float(sum(close_prices[:slow_period]) / slow_period)
                            # Calcular resto de EMAs
                            for i in range(slow_period, len(close_prices)):
                                slow_ema.append(float(close_prices[i] * slow_multiplier + 
                                                     slow_ema[-1] * (1.0 - slow_multiplier)))
                        
                        # Calcular línea MACD (fast_ema - slow_ema)
                        macd_line = []
                        # Asegurarnos de que ambas listas tengan la misma longitud para restar
                        min_len = min(len(fast_ema), len(slow_ema))
                        for i in range(min_len):
                            # Ajustar índices para alinear correctamente
                            fast_idx = i + (len(fast_ema) - min_len)
                            slow_idx = i + (len(slow_ema) - min_len)
                            macd_line.append(float(fast_ema[fast_idx] - slow_ema[slow_idx]))
                        
                        # Calcular línea de señal (EMA de 9 períodos del MACD)
                        signal_multiplier = 2.0 / (signal_period + 1.0)
                        signal_line = [0.0] * signal_period
                        if len(macd_line) >= signal_period:
                            # Inicializar con SMA
                            signal_line[signal_period-1] = float(sum(macd_line[:signal_period]) / signal_period)
                            # Calcular resto de señal
                            for i in range(signal_period, len(macd_line)):
                                signal_line.append(float(macd_line[i] * signal_multiplier + 
                                                       signal_line[-1] * (1.0 - signal_multiplier)))
                        
                        # Calcular histograma (MACD - Señal)
                        histogram = []
                        # Asegurarnos de que ambas listas tengan la misma longitud para restar
                        min_len = min(len(macd_line), len(signal_line))
                        for i in range(min_len):
                            # Ajustar índices para alinear correctamente
                            macd_idx = i + (len(macd_line) - min_len)
                            signal_idx = i + (len(signal_line) - min_len)
                            histogram.append(float(macd_line[macd_idx] - signal_line[signal_idx]))
                        
                        result["indicators"]["macd"] = {
                            "macd": macd_line,
                            "signal": signal_line,
                            "histogram": histogram
                        }
                    
                    elif indicator.lower() == "bbands":
                        # Bandas de Bollinger simplificadas
                        window_size = 20
                        num_std = 2.0
                        
                        # Inicializar bandas
                        upper_band = []
                        middle_band = []
                        lower_band = []
                        
                        # Calcular bandas
                        for i in range(len(close_prices)):
                            if i < window_size - 1:
                                # No hay suficientes datos para calcular
                                upper_band.append(0.0)
                                middle_band.append(0.0)
                                lower_band.append(0.0)
                            else:
                                # Tomar ventana de precios
                                window = close_prices[i-window_size+1:i+1]
                                # Calcular media
                                mean = float(sum(window) / window_size)
                                # Calcular desviación estándar
                                variance = sum([(x - mean) ** 2 for x in window]) / window_size
                                std = float(variance ** 0.5)  # Raíz cuadrada para obtener desviación estándar
                                
                                # Calcular bandas
                                middle_band.append(float(mean))
                                upper_band.append(float(mean + num_std * std))
                                lower_band.append(float(mean - num_std * std))
                        
                        result["indicators"]["bbands"] = {
                            "upper": upper_band,
                            "middle": middle_band,
                            "lower": lower_band
                        }
                    

            else:
                return [types.TextContent(
                    type="text",
                    text=f"Herramienta '{name}' no implementada"
                )]

            # Devolver el resultado como texto JSON
            import json
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error al ejecutar herramienta {name}: {str(e)}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    @app.list_tools()
    async def list_tools() -> List[types.Tool]:
        """
        Lista las herramientas disponibles.

        Returns:
            Lista de herramientas.
        """
        return [
            types.Tool(
                name="get_crypto_prices",
                description="Obtiene los precios actuales de criptomonedas",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbols": {
                            "type": "array",
                            "description": "Lista de símbolos de criptomonedas (ej. BTC, ETH)",
                            "items": {
                                "type": "string"
                            }
                        }
                    }
                }
            ),
            types.Tool(
                name="get_ohlcv_data",
                description="Obtiene datos OHLCV (Open, High, Low, Close, Volume) de Binance",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Símbolo de la criptomoneda (ej. BTCUSDT, ETHUSDT)"
                        },
                        "timeframe": {
                            "type": "string",
                            "description": "Marco temporal (ej. 1m, 5m, 15m, 30m, 1h, 4h, 1d)",
                            "default": "1d"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Número de velas a obtener",
                            "default": 30
                        }
                    },
                    "required": ["symbol"]
                }
            ),
            types.Tool(
                name="calculate_indicators",
                description="Calcula indicadores técnicos a partir de datos OHLCV",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Símbolo de la criptomoneda (ej. BTCUSDT, ETHUSDT)"
                        },
                        "timeframe": {
                            "type": "string",
                            "description": "Marco temporal (ej. 1m, 5m, 15m, 30m, 1h, 4h, 1d)",
                            "default": "1d"
                        },
                        "indicators": {
                            "type": "array",
                            "description": "Lista de indicadores a calcular (sma, ema, rsi, macd, bbands)",
                            "items": {
                                "type": "string"
                            },
                            "default": ["sma", "ema", "rsi"]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Número de velas a obtener",
                            "default": 30
                        }
                    },
                    "required": ["symbol"]
                }
            ),
            types.Tool(
                name="get_crypto_historical",
                description="Obtiene datos históricos de criptomonedas para un período específico",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Símbolo de la criptomoneda (ej. BTC, ETH)"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Número de días hacia atrás para obtener datos"
                        }
                    },
                    "required": ["symbol"]
                }
            ),
            types.Tool(
                name="get_crypto_details",
                description="Obtiene información detallada sobre una criptomoneda",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Símbolo de la criptomoneda (ej. BTC, ETH)"
                        }
                    },
                    "required": ["symbol"]
                }
            )
        ]

    # Crear el administrador de sesiones
    session_manager = StreamableHTTPSessionManager(
        app=app,
        event_store=None,
        json_response=json_response,
        stateless=True,
    )

    async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
        """Manejador de solicitudes HTTP."""
        await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Administrador de ciclo de vida para el administrador de sesiones."""
        async with session_manager.run():
            logger.info(f"Servidor MCP iniciado en http://127.0.0.1:{port}/mcp")
            try:
                yield
            finally:
                logger.info("Servidor MCP cerrándose...")

    # Crear la aplicación ASGI
    starlette_app = Starlette(
        debug=True,
        routes=[
            Mount("/mcp", app=handle_streamable_http),
        ],
        lifespan=lifespan,
    )

    return starlette_app


def start_server(port: int = 8080):
    """
    Inicia el servidor MCP.

    Args:
        port: Puerto en el que escuchar.
    """
    import uvicorn

    app = create_mcp_app(port=port)
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    start_server()
