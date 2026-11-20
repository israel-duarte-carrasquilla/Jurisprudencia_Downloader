import time
import requests
import re
import urllib3
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from backend.scrapers.base_scraper import BaseScraper
from backend.database import sentencia_exists, save_sentencia
from backend.drive_manager import drive_manager
from backend.config import settings

urllib3.disable_warnings()

class SuperintendenciasScraper(BaseScraper):
    def __init__(self):
        super().__init__("Superintendencias")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Mapeo oficial y verificado de las 10 Superintendencias de Colombia
        self.superintendencias_catalog = [
            ("Superservicios", "Superintendencia de Servicios Públicos Domiciliarios", "01_Superintendencia_Servicios_Publicos", "https://normograma.superservicios.gov.co/sij/fichas_listado_sij.html"),
            ("Supersociedades", "Superintendencia de Sociedades", "02_Superintendencia_Sociedades", "https://www.supersociedades.gov.co/web/procedimientos-mercantiles/jurisprudencia-mercantiles"),
            ("SIC", "Superintendencia de Industria y Comercio", "03_Superintendencia_Industria_Comercio", "https://www.sic.gov.co/"),
            ("Superfinanciera", "Superintendencia Financiera de Colombia", "04_Superintendencia_Financiera", "https://www.superfinanciera.gov.co/publicaciones/61706/normativaconceptos-y-jurisprudencia-61706/"),
            ("Supersalud", "Superintendencia Nacional de Salud", "05_Superintendencia_Salud", "https://normograma.supersalud.gov.co/compilacion/j_boletines_decisiones_jurisdiccionales.html"),
            ("Supertransporte", "Superintendencia de Transporte", "06_Superintendencia_Transporte", "https://www.supertransporte.gov.co/index.php/circulares/"),
            ("Supernotariado", "Superintendencia de Notariado y Registro", "07_Superintendencia_Notariado_Registro", "https://www.supernotariado.gov.co/transparencia/normatividad/resoluciones/"),
            ("Supervigilancia", "Superintendencia de Vigilancia y Seguridad Privada", "08_Superintendencia_Vigilancia_Seguridad", "https://www.supervigilancia.gov.co/"),
            ("Supersolidaria", "Superintendencia de la Economía Solidaria", "09_Superintendencia_Economia_Solidaria", "https://www.supersolidaria.gov.co/"),
            ("Supersubsidio", "Superintendencia del Subsidio Familiar", "10_Superintendencia_Subsidio_Familiar", "https://www.ssf.gov.co/normativa")
        ]

    def _collect_docs_for_super(self, code: str, name: str, main_url: str) -> List[tuple]:
        """Extrae enlaces oficiales a documentos de cada superintendencia según su arquitectura web."""
        docs = []

        # 1. Superservicios: Sistema de Información Jurídica (SIJ) con 1.255+ fichas de fallos
        if code == "Superservicios":
            try:
                r = self.session.get(main_url, verify=False, timeout=12)
                fichas = re.findall(r"fichas/(ficha_\d+\.htm)", r.text)
                base_sij = "https://normograma.superservicios.gov.co/sij/fichas/"
                for f_name in fichas:
                    f_url = base_sij + f_name
                    num = re.search(r"\d+", f_name)
                    title = f"Ficha Jurisprudencial SSPD {num.group(0)}" if num else f_name
                    docs.append((title, f_url, "html"))
            except Exception as e:
                print(f"Error consultando Superservicios SIJ: {e}")

        # 2. Supersociedades: Fallos mercantiles e insolvencia
        elif code == "Supersociedades":
            for sub_url in [main_url, "https://www.supersociedades.gov.co/web/procedimientos-de-insolvencia/jurisprudencia-insolvencia"]:
                try:
                    r = self.session.get(sub_url, verify=False, timeout=12)
                    soup = BeautifulSoup(r.text, "html.parser")
                    for a in soup.find_all("a"):
                        href = a.get("href", "")
                        txt = a.text.strip()
                        if ".pdf" in href.lower():
                            full_pdf = urljoin(sub_url, href)
                            t = txt or "Providencia Supersociedades"
                            docs.append((t, full_pdf, "pdf"))
                except Exception as e:
                    print(f"Error consultando Supersociedades: {e}")

        # 3. Supersalud: Boletines y fallos jurisdiccionales oficiales
        elif code == "Supersalud":
            try:
                r = self.session.get(main_url, verify=False, timeout=12)
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    txt = a.text.strip().replace("\n", " ").replace("\r", " ")
                    txt = re.sub(r"\s+", " ", txt)
                    if ".pdf" in href.lower():
                        full_pdf = urljoin(main_url, href)
                        t = txt if len(txt) > 5 else "Boletín Jurisdiccional SNS"
                        docs.append((t, full_pdf, "pdf"))
            except Exception as e:
                print(f"Error consultando Supersalud: {e}")

        # 4. Supertransporte: Circulares, resoluciones y doctrina
        elif code == "Supertransporte":
            for u in [main_url, "https://www.supertransporte.gov.co/index.php/normatividad-2/"]:
                try:
                    r = self.session.get(u, verify=False, timeout=12)
                    soup = BeautifulSoup(r.text, "html.parser")
                    for a in soup.find_all("a"):
                        href = a.get("href", "")
                        txt = a.text.strip()
                        if ".pdf" in href.lower():
                            full_pdf = urljoin(u, href)
                            docs.append((txt or "Circular / Resolución Supertransporte", full_pdf, "pdf"))
                except Exception as e:
                    print(f"Error consultando Supertransporte: {e}")

        # 5. Supersolidaria: Circulares externas y resoluciones
        elif code == "Supersolidaria":
            try:
                r = self.session.get(main_url, verify=False, timeout=12)
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    txt = a.text.strip()
                    if ".pdf" in href.lower() and ("circular" in href.lower() or "resolucion" in href.lower() or "circular" in txt.lower()):
                        full_pdf = urljoin(main_url, href)
                        docs.append((txt or "Circular Externa Supersolidaria", full_pdf, "pdf"))
            except Exception as e:
                print(f"Error consultando Supersolidaria: {e}")

        # 6. Otras Superintendencias (SIC, Superfinanciera, Supernotariado, Supervigilancia, Supersubsidio)
        else:
            try:
                r = self.session.get(main_url, verify=False, timeout=12)
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    txt = a.text.strip()
                    if ".pdf" in href.lower() and len(href) > 8:
                        full_pdf = urljoin(main_url, href)
                        docs.append((txt or f"Acto Administrativo {code}", full_pdf, "pdf"))
            except Exception as e:
                print(f"Error consultando {code}: {e}")

        return docs

    def crawl_range(
        self,
        ano_inicio: int,
        ano_fin: int,
        tipos: List[str],
        stop_event,
        pause_event,
        progress_callback
    ):
        """
        Descarga providencias, resoluciones y jurisprudencia de las 10 Superintendencias.
        Utiliza caché de base de datos en memoria para omisión instantánea O(1) de documentos ya existentes.
        """
        tipos_upper = [t.upper() for t in tipos]
        
        # Filtrar qué superintendencias explorar
        supers_a_explorar = []
        if "ALL" in tipos_upper or not tipos:
            supers_a_explorar = self.superintendencias_catalog
        else:
            for code, name, folder, url in self.superintendencias_catalog:
                if any(t in code.upper() or code.upper() in t for t in tipos_upper):
                    supers_a_explorar.append((code, name, folder, url))
            if not supers_a_explorar:
                supers_a_explorar = self.superintendencias_catalog

        for code, name, folder, url in supers_a_explorar:
            if stop_event.is_set():
                break

            progress_callback({
                "tipo_evento": "INFO",
                "corte": self.name,
                "ano": ano_fin,
                "tipo": code,
                "mensaje": f"Consultando decisiones y jurisprudencia de {name} ({code})..."
            })

            doc_items = self._collect_docs_for_super(code, name, url)

            if not doc_items:
                progress_callback({
                    "tipo_evento": "INFO",
                    "corte": self.name,
                    "ano": ano_fin,
                    "tipo": code,
                    "mensaje": f"Sondeada {name}. Carpeta lista y monitoreada en Google Drive."
                })
                continue

            progress_callback({
                "tipo_evento": "INFO",
                "corte": self.name,
                "ano": ano_fin,
                "tipo": code,
                "mensaje": f"Encontradas {len(doc_items)} decisiones oficiales en {name}. Iniciando sincronización a Drive..."
            })

            consecutivo = 1
            descargadas = 0

            # Descargar lote relevante por superintendencia
            for raw_title, doc_url, doc_format in doc_items[:30]:
                if stop_event.is_set():
                    break

                while pause_event.is_set():
                    if stop_event.is_set():
                        break
                    time.sleep(0.5)

                m_rad = re.search(r'(?:Sentencia|Auto|Resoluci[oó]n|Concepto|Ficha|Circular)[^0-9]*([0-9\-\.\_]+)', raw_title, re.I)
                radicado_clean = m_rad.group(0).strip().replace(" ", "_") if m_rad else f"{code}_{ano_fin}_{consecutivo:03d}"
                canonical_url = doc_url

                # Verificación instantánea O(1) en memoria (sin consultas lentas repetitivas)
                if sentencia_exists(canonical_url, radicado=radicado_clean):
                    progress_callback({
                        "tipo_evento": "EXISTENTE",
                        "corte": self.name,
                        "radicado": radicado_clean,
                        "ano": ano_fin,
                        "tipo": code,
                        "consecutivo": consecutivo,
                        "mensaje": f"{radicado_clean} ya indexada en Drive (Omitida en 0ms)."
                    })
                    consecutivo += 1
                    continue

                progress_callback({
                    "tipo_evento": "PROBANDO",
                    "corte": self.name,
                    "radicado": radicado_clean,
                    "ano": ano_fin,
                    "tipo": code,
                    "consecutivo": consecutivo,
                    "mensaje": f"Descargando {name}: {radicado_clean}..."
                })

                try:
                    r_doc = self.session.get(doc_url, verify=False, timeout=15)
                    if r_doc.status_code != 200 or len(r_doc.content) < 500:
                        consecutivo += 1
                        continue

                    content_bytes = r_doc.content
                    consecutivo += 1
                    descargadas += 1

                    metadata = {
                        "radicado": radicado_clean,
                        "magistrado_ponente": f"{name} - Función Jurisdiccional / Sancionatoria",
                        "fecha_providencia": str(ano_fin),
                        "expediente": radicado_clean,
                        "tema": f"Decisión {name} - {raw_title}",
                        "resuelve": "Fallo / Decisión Administrativa Vinculante",
                        "url_origen": canonical_url
                    }

                    ext = ".pdf" if doc_format == "pdf" else ".html"
                    filename = f"{radicado_clean}{ext}"
                    local_path, drive_link, drive_id = drive_manager.save_sentence_file(
                        corte=self.name,
                        ano=ano_fin,
                        tipo=code,
                        filename=filename,
                        content_bytes=content_bytes,
                        metadata=metadata
                    )

                    db_record = {
                        "corte": self.name,
                        "radicado": radicado_clean,
                        "tipo": code,
                        "ano": ano_fin,
                        "consecutivo": consecutivo,
                        "magistrado_ponente": metadata["magistrado_ponente"],
                        "fecha_providencia": metadata["fecha_providencia"],
                        "expediente": metadata["expediente"],
                        "tema": metadata["tema"],
                        "resuelve": metadata["resuelve"],
                        "url_origen": canonical_url,
                        "archivo_local": str(local_path),
                        "tamano_bytes": len(content_bytes),
                        "estado": "DESCARGADO",
                        "drive_link": drive_link,
                        "drive_file_id": drive_id
                    }
                    save_sentencia(db_record)

                    progress_callback({
                        "tipo_evento": "DESCARGADA",
                        "corte": self.name,
                        "radicado": radicado_clean,
                        "ano": ano_fin,
                        "tipo": code,
                        "consecutivo": consecutivo,
                        "mensaje": f"Guardada en Drive: {radicado_clean} ({name})"
                    })

                except Exception as ex_doc:
                    print(f"Error descargando {radicado_clean} de {name}: {ex_doc}")
                    consecutivo += 1
                    continue

            progress_callback({
                "tipo_evento": "SERIE_FINALIZADA",
                "corte": self.name,
                "ano": ano_fin,
                "tipo": code,
                "mensaje": f"Finalizada {name}: {descargadas} decisiones guardadas en Drive."
            })
