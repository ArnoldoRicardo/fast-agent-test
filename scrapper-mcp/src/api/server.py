"""
Servidor FastAPI para proporcionar acceso a los datos financieros.
"""

import asyncio
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional

from ..utils.config import get_config
from ..utils.logging import get_logger
from ..collectors.crypto import CryptoCollector
from ..database.connection import get_db, init_db

# Configuración
config = get_config()
logger = get_logger("api.server")

# Crear la aplicación FastAPI
app = FastAPI(
    title="Financial Data API",
    description="API para acceder a datos financieros recopilados",
    version="0.1.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, limitar a orígenes específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Colectores
crypto_collector = CryptoCollector()

@app.on_event("startup")
async def startup_event():
    """Eventos de inicio del servidor."""
    logger.info("Iniciando servidor API...")
    
    # Inicializar la base de datos
    init_db()
    logger.info("Base de datos inicializada")


@app.get("/")
async def root():
    """Endpoint raíz."""
    return {
        "message": "Financial Data API",
        "version": "0.1.0",
        "endpoints": [
            "/crypto",
            "/stocks",
            "/macro",
            "/fixed-income"
        ]
    }


@app.get("/crypto")
async def get_crypto(symbols: Optional[List[str]] = Query(None)):
    """
    Obtener datos de criptomonedas.
    
    Args:
        symbols: Lista opcional de símbolos (ej. BTC, ETH).
                Si no se proporciona, se devuelven todos los disponibles.
                
    Returns:
        Dict: Datos de criptomonedas por símbolo.
    """
    try:
        # Obtener los últimos precios
        prices = await crypto_collector.get_latest_prices()
        
        # Filtrar por símbolos si se proporcionaron
        if symbols:
            filtered_prices = {s: p for s, p in prices.items() if s.upper() in [sym.upper() for sym in symbols]}
            return filtered_prices
        
        return prices
    except Exception as e:
        logger.error(f"Error al obtener datos de criptomonedas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.get("/crypto/collect")
async def collect_crypto():
    """
    Forzar la recolección de datos de criptomonedas.
    
    Returns:
        Dict: Resultado de la operación.
    """
    try:
        result = await crypto_collector.run()
        if result:
            return {"status": "success", "message": "Datos de criptomonedas recolectados correctamente"}
        else:
            return {"status": "error", "message": "Error al recolectar datos de criptomonedas"}
    except Exception as e:
        logger.error(f"Error al forzar recolección de criptomonedas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# Placeholder para endpoints futuros
@app.get("/stocks")
async def get_stocks():
    """Placeholder para datos de acciones."""
    return {"message": "Endpoint de acciones en desarrollo"}


@app.get("/macro")
async def get_macro():
    """Placeholder para datos macroeconómicos."""
    return {"message": "Endpoint de datos macroeconómicos en desarrollo"}


@app.get("/fixed-income")
async def get_fixed_income():
    """Placeholder para datos de renta fija."""
    return {"message": "Endpoint de datos de renta fija en desarrollo"}


def start():
    """Inicia el servidor FastAPI usando uvicorn."""
    import uvicorn
    uvicorn.run(
        "src.api.server:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.debug,
        workers=config.api.workers
    )
