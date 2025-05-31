"""
Gestión de sesiones de base de datos para el proyecto.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .connection import get_connection_string

# Crear el motor de base de datos
engine = create_async_engine(
    get_connection_string(),
    echo=False,
    future=True,
)

# Crear el creador de sesiones
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Obtiene una sesión de base de datos asíncrona.

    Returns:
        AsyncGenerator[AsyncSession, None]: Sesión de base de datos.
    """
    session = async_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
