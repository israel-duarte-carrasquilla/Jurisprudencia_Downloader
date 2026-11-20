from abc import ABC, abstractmethod
from typing import Dict, Any, Generator, Optional
import logging

class BaseScraper(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"scraper.{name}")

    @abstractmethod
    def crawl_range(
        self,
        ano_inicio: int,
        ano_fin: int,
        tipos: list,
        stop_event,
        pause_event,
        progress_callback
    ):
        """
        Ejecuta el rastreo para los rangos de años y tipos indicados.
        stop_event: threading.Event para cancelar
        pause_event: threading.Event para pausar
        progress_callback: función para reportar novedades
        """
        pass
