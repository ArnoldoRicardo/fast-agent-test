"""
Colector base que define la interfaz común para todos los colectores de datos financieros.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict

from ..utils.logging import get_logger
from ..database.connection import get_db


class BaseCollector(ABC):
    """Clase base abstracta para colectores de datos financieros."""

    def __init__(self, name: str):
        """
        Inicializa el colector base.

        Args:
            name: Nombre del colector para identificación y logging.
        """
        self.name = name
        self.logger = get_logger(f"collector.{name}")

    @abstractmethod
    async def collect(self) -> Dict[str, Any]:
        """
        Método principal para recolectar datos.
        Debe ser implementado por las clases derivadas.

        Returns:
            Dict[str, Any]: Datos recolectados.
        """
        pass

    @abstractmethod
    async def store(self, data: Dict[str, Any]) -> bool:
        """
        Almacena los datos recolectados en la base de datos.
        Debe ser implementado por las clases derivadas.

        Args:
            data: Datos a almacenar.

        Returns:
            bool: True si se almacenaron correctamente, False en caso contrario.
        """
        pass

    async def run(self) -> bool:
        """
        Ejecuta el proceso completo de recolección y almacenamiento.

        Returns:
            bool: True si se completó correctamente, False en caso contrario.
        """
        try:
            self.logger.info(f"Iniciando recolección de datos para {self.name}")
            start_time = datetime.now()

            # Recolectar datos
            data = await self.collect()

            # Almacenar datos
            result = await self.store(data)

            elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Recolección completada para {self.name} en {elapsed:.2f} segundos")

            return result
        except Exception as e:
            self.logger.error(f"Error durante la recolección para {self.name}: {str(e)}")
            return False

    def get_session(self):
        """
        Obtiene una sesión de base de datos.

        Returns:
            Generator: Generador de sesión de base de datos.
        """
        return get_db()
