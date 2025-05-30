"""
Configuración de la conexión a la base de datos SQLite.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from ..utils.config import get_config
from ..utils.logging import get_logger

logger = get_logger("database")
config = get_config()

# Crear engine SQLAlchemy
engine = create_engine(
    config.database.url,
    echo=config.database.echo
)

# Crear una sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos
Base = declarative_base()

def get_db():
    """
    Función para obtener una sesión de base de datos.
    Se debe usar como un context manager para asegurar que se cierre correctamente.
    
    Ejemplo:
    ```
    with get_db() as db:
        # Operaciones con la base de datos
    ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Inicializa la base de datos creando todas las tablas definidas.
    """
    from . import models  # Importación para registrar modelos
    
    logger.info("Inicializando base de datos...")
    Base.metadata.create_all(bind=engine)
    logger.info("Base de datos inicializada correctamente")
