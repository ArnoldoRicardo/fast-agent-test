"""
Implementación del servidor MCP (Model Context Protocol) para datos financieros.
Permite a los agentes de Fast-Agent interactuar con los datos financieros.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional, Union

from ..utils.config import get_config
from ..utils.logging import get_logger
from ..collectors.crypto import CryptoCollector

# Inicializar logger y configuración
logger = get_logger("mcp.server")
config = get_config()

# Colectores
crypto_collector = CryptoCollector()

# Definir las herramientas MCP
TOOLS = [
    {
        "name": "get_crypto_prices",
        "description": "Obtiene los precios actuales de criptomonedas",
        "parameters": {
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
    },
    {
        "name": "get_stock_prices",
        "description": "Obtiene los precios actuales de acciones y ETFs",
        "parameters": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "description": "Lista de símbolos de acciones o ETFs (ej. AAPL, MSFT, SPY)",
                    "items": {
                        "type": "string"
                    }
                },
                "type": {
                    "type": "string",
                    "description": "Tipo de instrumento: 'stock' o 'etf'",
                    "enum": ["stock", "etf", "all"]
                }
            }
        }
    },
    {
        "name": "get_macro_indicators",
        "description": "Obtiene indicadores macroeconómicos",
        "parameters": {
            "type": "object",
            "properties": {
                "indicators": {
                    "type": "array",
                    "description": "Lista de indicadores (ej. inflation, interest_rate)",
                    "items": {
                        "type": "string"
                    }
                },
                "countries": {
                    "type": "array",
                    "description": "Lista de países o regiones (ej. US, EU)",
                    "items": {
                        "type": "string"
                    }
                }
            }
        }
    },
    {
        "name": "get_fixed_income_yields",
        "description": "Obtiene rendimientos de instrumentos de renta fija",
        "parameters": {
            "type": "object",
            "properties": {
                "instrument_types": {
                    "type": "array",
                    "description": "Tipos de instrumentos (ej. bond, certificate)",
                    "items": {
                        "type": "string"
                    }
                },
                "maturities": {
                    "type": "array",
                    "description": "Plazos de vencimiento (ej. 1M, 3M, 1Y, 10Y)",
                    "items": {
                        "type": "string"
                    }
                },
                "countries": {
                    "type": "array",
                    "description": "Países emisores (ej. US, EU)",
                    "items": {
                        "type": "string"
                    }
                }
            }
        }
    }
]

class MCPServer:
    """
    Implementación del servidor MCP para datos financieros.
    """
    
    def __init__(self):
        """Inicializa el servidor MCP."""
        self.logger = logger
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un mensaje MCP y ejecuta la herramienta solicitada.
        
        Args:
            message: Mensaje MCP con la solicitud.
            
        Returns:
            Dict[str, Any]: Respuesta MCP.
        """
        try:
            if not message or "tool" not in message:
                return self._error_response("Mensaje MCP inválido: falta el campo 'tool'")
            
            tool_name = message.get("tool")
            tool_params = message.get("parameters", {})
            
            # Validar que la herramienta existe
            if tool_name not in [tool["name"] for tool in TOOLS]:
                return self._error_response(f"Herramienta '{tool_name}' no encontrada")
            
            # Ejecutar la herramienta
            if tool_name == "get_crypto_prices":
                return await self._handle_get_crypto_prices(tool_params)
            elif tool_name == "get_stock_prices":
                return await self._handle_get_stock_prices(tool_params)
            elif tool_name == "get_macro_indicators":
                return await self._handle_get_macro_indicators(tool_params)
            elif tool_name == "get_fixed_income_yields":
                return await self._handle_get_fixed_income_yields(tool_params)
            else:
                return self._error_response(f"Implementación de herramienta '{tool_name}' no disponible")
                
        except Exception as e:
            self.logger.error(f"Error al procesar mensaje MCP: {str(e)}")
            return self._error_response(f"Error interno: {str(e)}")
    
    async def _handle_get_crypto_prices(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja la solicitud para obtener precios de criptomonedas.
        
        Args:
            params: Parámetros de la solicitud.
            
        Returns:
            Dict[str, Any]: Respuesta con los precios.
        """
        try:
            symbols = params.get("symbols", [])
            
            # Obtener precios
            prices = await crypto_collector.get_latest_prices()
            
            # Filtrar por símbolos si se proporcionaron
            if symbols:
                filtered_prices = {s: p for s, p in prices.items() if s.upper() in [sym.upper() for sym in symbols]}
                result = filtered_prices
            else:
                result = prices
            
            return {
                "result": result,
                "status": "success"
            }
        except Exception as e:
            self.logger.error(f"Error al obtener precios de criptomonedas: {str(e)}")
            return self._error_response(str(e))
    
    async def _handle_get_stock_prices(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja la solicitud para obtener precios de acciones y ETFs.
        
        Args:
            params: Parámetros de la solicitud.
            
        Returns:
            Dict[str, Any]: Respuesta con los precios.
        """
        # Placeholder - Implementar cuando se tenga el colector de acciones
        return {
            "result": {"message": "Funcionalidad en desarrollo"},
            "status": "success"
        }
    
    async def _handle_get_macro_indicators(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja la solicitud para obtener indicadores macroeconómicos.
        
        Args:
            params: Parámetros de la solicitud.
            
        Returns:
            Dict[str, Any]: Respuesta con los indicadores.
        """
        # Placeholder - Implementar cuando se tenga el colector de indicadores macro
        return {
            "result": {"message": "Funcionalidad en desarrollo"},
            "status": "success"
        }
    
    async def _handle_get_fixed_income_yields(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja la solicitud para obtener rendimientos de renta fija.
        
        Args:
            params: Parámetros de la solicitud.
            
        Returns:
            Dict[str, Any]: Respuesta con los rendimientos.
        """
        # Placeholder - Implementar cuando se tenga el colector de renta fija
        return {
            "result": {"message": "Funcionalidad en desarrollo"},
            "status": "success"
        }
    
    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Genera una respuesta de error MCP.
        
        Args:
            error_message: Mensaje de error.
            
        Returns:
            Dict[str, Any]: Respuesta de error.
        """
        return {
            "status": "error",
            "error": error_message
        }


async def handle_stdin_stdout():
    """
    Maneja la comunicación MCP a través de stdin/stdout.
    Este es el método estándar para que Fast-Agent se comunique con servidores MCP.
    """
    server = MCPServer()
    
    try:
        # Leer mensajes de stdin y responder a stdout
        while True:
            # Leer una línea de stdin
            line = sys.stdin.readline()
            if not line:
                break
                
            # Parsear el mensaje JSON
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                error_response = server._error_response("Mensaje JSON inválido")
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
                continue
            
            # Procesar el mensaje
            response = await server.process_message(message)
            
            # Enviar respuesta a stdout
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    
    except Exception as e:
        logger.error(f"Error en el servidor MCP: {str(e)}")
        sys.exit(1)


def start():
    """Inicia el servidor MCP."""
    logger.info("Iniciando servidor MCP para datos financieros...")
    asyncio.run(handle_stdin_stdout())
