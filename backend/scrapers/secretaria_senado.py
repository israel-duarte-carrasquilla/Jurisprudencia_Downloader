import time
import requests
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from backend.scrapers.base_scraper import BaseScraper
from backend.database import sentencia_exists, save_sentencia
from backend.drive_manager import drive_manager
from backend.config import settings

class SecretariaSenadoScraper(BaseScraper):
    def __init__(self):
        super().__init__("Secretaría del Senado")
        self.base_url = "http://www.secretariasenado.gov.co/senado/basedoc/"
        self.laws_chronological_url = "http://www.secretariasenado.gov.co/senado/basedoc/arbol/1183.html"
        self.codes_url = "http://www.secretariasenado.gov.co/senado/basedoc/arbol/7824.html"
        self.actos_url = "http://www.secretariasenado.gov.co/senado/basedoc/arbol/16355.html"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://www.secretariasenado.gov.co"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _get_year_mapping(self) -> Dict[int, str]:
        """Obtiene el mapa de años a URLs de páginas de leyes cronológicas."""
        year_map = {}
        try:
            r = self.session.get(self.laws_chronological_url, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a"):
                    txt = a.text.strip()
                    m = re.search(r"LEYES\s+(\d{4})", txt, re.I)
                    if m:
                        year = int(m.group(1))
                        href = a.get("href", "")
                        year_map[year] = urljoin(self.laws_chronological_url, href)
        except Exception as e:
            print(f"Error consultando índice de años de Secretaría del Senado: {e}")
        return year_map

    def _get_actos_mapping(self) -> Dict[int, str]:
        """Obtiene el mapa de años para Actos Legislativos."""
        actos_map = {}
        try:
            r = self.session.get(self.actos_url, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a"):
                    txt = a.text.strip()
                    if txt.isdigit() and len(txt) == 4:
                        year = int(txt)
                        href = a.get("href", "")
                        actos_map[year] = urljoin(self.actos_url, href)
        except Exception as e:
            print(f"Error consultando índice de Actos Legislativos: {e}")
        return actos_map

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
        Descarga normativa y leyes de la República de la Secretaría General del Senado.
        """
        tipos_upper = [t.upper() for t in tipos]
        descargar_leyes = "LEYES" in tipos_upper or "ALL" in tipos_upper or not tipos
        descargar_codigos = "CODIGOS" in tipos_upper or "ALL" in tipos_upper
        descargar_actos = "ACTOS" in tipos_upper or "ALL" in tipos_upper

        year_map = self._get_year_mapping() if descargar_leyes else {}

        # 1. DESCARGA DE LEYES POR AÑO
        if descargar_leyes:
            for ano in range(ano_fin, ano_inicio - 1, -1):
                if stop_event.is_set():
                    break

                page_url = year_map.get(ano)
                if not page_url:
                    continue

                progress_callback({
                    "tipo_evento": "INFO",
                    "corte": self.name,
                    "ano": ano,
                    "tipo": "Leyes",
                    "mensaje": f"Consultando catálogo de Leyes de la República del año {ano} en Secretaría del Senado..."
                })

                try:
                    r_ano = self.session.get(page_url, timeout=15)
                    soup_ano = BeautifulSoup(r_ano.text, "html.parser")
                except Exception as e:
                    progress_callback({
                        "tipo_evento": "ERROR",
                        "corte": self.name,
                        "ano": ano,
                        "tipo": "Leyes",
                        "mensaje": f"Error al consultar leyes de {ano}: {e}"
                    })
                    continue

                law_links = []
                for a in soup_ano.find_all("a"):
                    href = a.get("href", "")
                    if re.search(r"ley_\d+_\d+\.html", href, re.I):
                        law_links.append((a.text.strip(), urljoin(page_url, href)))

                if not law_links:
                    continue

                progress_callback({
                    "tipo_evento": "INFO",
                    "corte": self.name,
                    "ano": ano,
                    "tipo": "Leyes",
                    "mensaje": f"Encontradas {len(law_links)} leyes sancionadas en {ano}. Iniciando descarga..."
                })

                consecutivo = 1
                descargadas_ano = 0

                for raw_title, full_law_url in law_links:
                    if stop_event.is_set():
                        break

                    while pause_event.is_set():
                        if stop_event.is_set():
                            break
                        time.sleep(0.5)

                    m_ley = re.search(r"ley_(\d+)_(\d+)", full_law_url, re.I)
                    num_str = m_ley.group(1).lstrip("0") if m_ley else str(consecutivo)
                    radicado = f"Ley {num_str} de {ano}"

                    if sentencia_exists(full_law_url, radicado=radicado):
                        progress_callback({
                            "tipo_evento": "EXISTENTE",
                            "corte": self.name,
                            "radicado": radicado,
                            "ano": ano,
                            "tipo": "Leyes",
                            "consecutivo": consecutivo,
                            "mensaje": f"{radicado} ya registrada en Drive."
                        })
                        consecutivo += 1
                        continue

                    progress_callback({
                        "tipo_evento": "PROBANDO",
                        "corte": self.name,
                        "radicado": radicado,
                        "ano": ano,
                        "tipo": "Leyes",
                        "consecutivo": consecutivo,
                        "mensaje": f"Descargando {radicado} de Secretaría del Senado..."
                    })

                    try:
                        r_doc = self.session.get(full_law_url, timeout=15)
                        if r_doc.status_code != 200 or len(r_doc.content) < 500:
                            consecutivo += 1
                            continue

                        doc_text = r_doc.text
                        # Extraer Diario Oficial y Epígrafe
                        m_do = re.search(r"Diario\s+Oficial\s+No\.\s*[\d\.\,]+(?:\s+de\s+[^\n\r<]+)?", doc_text, re.I)
                        diario = m_do.group(0).strip() if m_do else f"Diario Oficial {ano}"

                        m_epigrafe = re.search(r"(?:Por\s+medio\s+de\s+la\s+cual|Por\s+la\s+cual)[^\.\n\r<]+(?:\.[^\.\n\r<]+)?", doc_text, re.I)
                        epigrafe = m_epigrafe.group(0).strip() if m_epigrafe else f"Norma oficial expedida por el Congreso de la República en {ano}"

                        metadata = {
                            "radicado": radicado,
                            "magistrado_ponente": "Congreso de la República de Colombia",
                            "fecha_providencia": str(ano),
                            "expediente": f"Ley-{num_str}-{ano}",
                            "tema": epigrafe[:250],
                            "resuelve": f"Promúlguese, publíquese y cúmplase ({diario})",
                            "url_origen": full_law_url
                        }

                        filename = f"Ley_{num_str}_{ano}.htm"
                        local_path, drive_link, drive_id = drive_manager.save_sentence_file(
                            corte=self.name,
                            ano=ano,
                            tipo="Leyes",
                            filename=filename,
                            content_bytes=r_doc.content,
                            metadata=metadata
                        )

                        db_record = {
                            "corte": self.name,
                            "radicado": radicado,
                            "tipo": "Leyes",
                            "ano": ano,
                            "consecutivo": consecutivo,
                            "magistrado_ponente": metadata["magistrado_ponente"],
                            "fecha_providencia": metadata["fecha_providencia"],
                            "expediente": metadata["expediente"],
                            "tema": metadata["tema"],
                            "resuelve": metadata["resuelve"],
                            "url_origen": full_law_url,
                            "archivo_local": local_path,
                            "tamano_bytes": len(r_doc.content),
                            "estado": "SUBIDO_DRIVE",
                            "drive_link": drive_link,
                            "drive_file_id": drive_id
                        }
                        save_sentencia(db_record)

                        consecutivo += 1
                        descargadas_ano += 1

                        progress_callback({
                            "tipo_evento": "DESCARGADA",
                            "corte": self.name,
                            "radicado": radicado,
                            "ano": ano,
                            "tipo": "Leyes",
                            "consecutivo": consecutivo,
                            "tamano_bytes": len(r_doc.content),
                            "magistrado": "Congreso de la República",
                            "drive_link": drive_link,
                            "archivo_local": local_path,
                            "mensaje": f"Descargada {radicado} ({len(r_doc.content)//1024} KB) en Google Drive."
                        })

                        time.sleep(settings.request_delay_seconds)

                    except Exception as ex_law:
                        print(f"Error procesando {radicado}: {ex_law}")
                        consecutivo += 1
                        continue

                progress_callback({
                    "tipo_evento": "SERIE_FINALIZADA",
                    "corte": self.name,
                    "ano": ano,
                    "tipo": "Leyes",
                    "mensaje": f"Finalizadas Leyes de la República ({ano}): {descargadas_ano} normas guardadas en Drive."
                })

        # 2. DESCARGA DE CÓDIGOS Y ESTATUTOS NACIONALES
        if descargar_codigos and not stop_event.is_set():
            progress_callback({
                "tipo_evento": "INFO",
                "corte": self.name,
                "ano": 0,
                "tipo": "Codigos",
                "mensaje": "Consultando Códigos y Estatutos Nacionales de Colombia en Secretaría del Senado..."
            })

            try:
                r_cod = self.session.get(self.codes_url, timeout=15)
                soup_cod = BeautifulSoup(r_cod.text, "html.parser")
                code_items = []
                for a in soup_cod.find_all("a"):
                    href = a.get("href", "")
                    if "codigo" in href or "ley" in href:
                        code_items.append((a.text.strip(), urljoin(self.codes_url, href)))
            except Exception as e:
                code_items = []

            for title_raw, code_url in code_items:
                if stop_event.is_set():
                    break

                while pause_event.is_set():
                    if stop_event.is_set():
                        break
                    time.sleep(0.5)

                slug = re.sub(r"[^\w\s-]", "", title_raw.split(" - ")[0]).strip().replace(" ", "_")
                canonical_url = code_url

                if sentencia_exists(canonical_url, radicado=slug):
                    continue

                progress_callback({
                    "tipo_evento": "PROBANDO",
                    "corte": self.name,
                    "radicado": slug,
                    "ano": 2024,
                    "tipo": "Codigos",
                    "consecutivo": 1,
                    "mensaje": f"Descargando {slug}..."
                })

                try:
                    r_code_doc = self.session.get(code_url, timeout=20)
                    if r_code_doc.status_code == 200 and len(r_code_doc.content) > 1000:
                        meta = {
                            "radicado": slug,
                            "magistrado_ponente": "República de Colombia",
                            "fecha_providencia": "Vigente Compilado",
                            "expediente": slug,
                            "tema": title_raw[:250],
                            "resuelve": "Texto oficial concordado y con vigencia constitucional",
                            "url_origen": canonical_url
                        }
                        filename = f"{slug}.htm"
                        local_path, drive_link, drive_id = drive_manager.save_sentence_file(
                            corte=self.name,
                            ano=0,
                            tipo="Codigos",
                            filename=filename,
                            content_bytes=r_code_doc.content,
                            metadata=meta
                        )
                        db_record = {
                            "corte": self.name,
                            "radicado": slug,
                            "tipo": "Codigos",
                            "ano": 0,
                            "consecutivo": 1,
                            "magistrado_ponente": "República de Colombia",
                            "fecha_providencia": "Vigente Compilado",
                            "expediente": slug,
                            "tema": meta["tema"],
                            "resuelve": meta["resuelve"],
                            "url_origen": canonical_url,
                            "archivo_local": local_path,
                            "tamano_bytes": len(r_code_doc.content),
                            "estado": "SUBIDO_DRIVE",
                            "drive_link": drive_link,
                            "drive_file_id": drive_id
                        }
                        save_sentencia(db_record)

                        progress_callback({
                            "tipo_evento": "DESCARGADA",
                            "corte": self.name,
                            "radicado": slug,
                            "ano": 0,
                            "tipo": "Codigos",
                            "consecutivo": 1,
                            "tamano_bytes": len(r_code_doc.content),
                            "magistrado": "República de Colombia",
                            "drive_link": drive_link,
                            "archivo_local": local_path,
                            "mensaje": f"Descargado {slug} ({len(r_code_doc.content)//1024} KB) en Google Drive."
                        })
                        time.sleep(settings.request_delay_seconds)
                except Exception as ex_code:
                    print(f"Error descargando código {slug}: {ex_code}")
                    continue
