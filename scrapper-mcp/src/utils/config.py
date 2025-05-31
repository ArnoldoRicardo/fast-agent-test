"""
Configuración para el scrapper-mcp.
Carga variables de entorno y proporciona configuraciones predeterminadas.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# Determinar la ruta base del proyecto
BASE_DIR = Path(__file__).parent.parent.parent

# Cargar variables de entorno desde .env si existe
load_dotenv(BASE_DIR / ".env")


class DatabaseConfig(BaseModel):
    """Configuración de la base de datos."""
    url: str = f"sqlite:///{BASE_DIR}/data/financial_data.db"
    echo: bool = False


class ScraperConfig(BaseModel):
    """Configuración de los scrapers."""
    # Configuración para criptomonedas
    crypto_symbols: List[str] = ["BTC", "ETH", "BNB", "SOL", "XRP"]
    crypto_update_minutes: int = 15
    crypto_api_key: Optional[str] = os.getenv("COINGECKO_API_KEY")

    # Configuración para acciones y ETFs
    stock_symbols: List[str] = ["SPY", "QQQ", "DIA", "AAPL", "MSFT", "GOOGL", "AMZN"]
    etf_symbols: List[str] = ["SPY", "QQQ", "VTI", "IWM", "EFA"]
    stock_update_minutes: int = 60
    yfinance_api_key: Optional[str] = os.getenv("YFINANCE_API_KEY")

    # Configuración para datos macroeconómicos
    macro_update_hours: int = 24
    fred_api_key: Optional[str] = os.getenv("FRED_API_KEY")

    # Configuración para tasa fija
    fixed_income_update_hours: int = 24


class APIConfig(BaseModel):
    """Configuración para la API."""
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = True
    workers: int = 1


class MCPConfig(BaseModel):
    """Configuración para el servidor MCP."""
    host: str = "127.0.0.1"
    port: int = 8001


class LogConfig(BaseModel):
    """Configuración para logging."""
    level: str = os.getenv("LOG_LEVEL", "INFO")
    format: str = "{time} | {level} | {message}"
    file: Optional[str] = BASE_DIR / "data" / "scrapper.log"


class Config(BaseModel):
    """Configuración principal."""
    database: DatabaseConfig = DatabaseConfig()
    scraper: ScraperConfig = ScraperConfig()
    api: APIConfig = APIConfig()
    mcp: MCPConfig = MCPConfig()
    log: LogConfig = LogConfig()


# Crear una instancia de configuración con valores predeterminados
config = Config()


def get_config() -> Config:
    """Obtener la configuración actual."""
    return config
