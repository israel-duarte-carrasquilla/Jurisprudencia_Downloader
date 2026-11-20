from backend.scrapers.corte_constitucional import CorteConstitucionalScraper
from backend.scrapers.corte_suprema import CorteSupremaScraper
from backend.scrapers.consejo_estado import ConsejoEstadoScraper
from backend.scrapers.secretaria_senado import SecretariaSenadoScraper
from backend.scrapers.superintendencias import SuperintendenciasScraper
from backend.scrapers.laudos_arbitrales import LaudosArbitralesScraper
from backend.scrapers.tribunales_departamentales import TribunalesDepartamentalesScraper
from backend.scrapers.icdp import ICDPScraper

SCRAPERS = {
    "Corte Constitucional": CorteConstitucionalScraper,
    "Corte Suprema de Justicia": CorteSupremaScraper,
    "Consejo de Estado": ConsejoEstadoScraper,
    "Secretaría del Senado": SecretariaSenadoScraper,
    "Secretaria del Senado": SecretariaSenadoScraper,
    "Superintendencias": SuperintendenciasScraper,
    "Laudos Arbitrales": LaudosArbitralesScraper,
    "Tribunales Departamentales": TribunalesDepartamentalesScraper,
    "Instituto Colombiano de Derecho Procesal (ICDP)": ICDPScraper,
    "ICDP": ICDPScraper,
    "Conceptos ICDP": ICDPScraper,
}

def get_scraper(corte_name: str):
    scraper_cls = SCRAPERS.get(corte_name)
    if not scraper_cls:
        raise ValueError(f"No existe scraper registrado para: {corte_name}")
    return scraper_cls()
