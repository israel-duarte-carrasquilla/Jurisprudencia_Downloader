import time
import requests
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from backend.scrapers.base_scraper import BaseScraper
from backend.database import sentencia_exists, save_sentencia
from backend.drive_manager import drive_manager
from backend.config import settings

class ICDPScraper(BaseScraper):
    def __init__(self):
        super().__init__("Instituto Colombiano de Derecho Procesal (ICDP)")
        self.base_url = "https://icdp.org.co"
        self.intervenciones_url = "https://icdp.org.co/intervenciones-ante-la-corte/"
        self.blog_url = "https://icdp.org.co/blog/"
        self.compendio_url = "https://icdp.org.co/compendio-jurisprudencial/"
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _download_gdrive_file(self, url: str) -> Optional[bytes]:
        """Descarga un archivo alojado en Google Drive mediante su ID."""
        m = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
        if not m:
            m = re.search(r'id=([a-zA-Z0-9_-]+)', url)
        if not m:
            return None
        file_id = m.group(1)
        download_url = f"https://docs.google.com/uc?export=download"
        try:
            r = self.session.get(download_url, params={"id": file_id}, timeout=30, stream=True)
            for k, v in r.cookies.items():
                if k.startswith("download_warning"):
                    r = self.session.get(download_url, params={"id": file_id, "confirm": v}, timeout=30, stream=True)
                    break
            if r.status_code == 200 and len(r.content) > 500:
                return r.content
        except Exception as e:
            self.logger.warning(f"Error descargando desde Google Drive ({file_id}): {e}")
        return None

    def _get_year_pages(self) -> Dict[int, str]:
        """Obtiene el mapa de años y URLs de intervenciones ante la Corte."""
        mapping = {}
        try:
            r = self.session.get(self.intervenciones_url, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    m = re.search(r"intervenciones-(\d{4})", href)
                    if m:
                        yr = int(m.group(1))
                        mapping[yr] = href
        except Exception as e:
            self.logger.error(f"Error extrayendo páginas anuales de intervenciones ICDP: {e}")
        return mapping

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
        Descarga conceptos técnicos, intervenciones constitucionales y doctrina del ICDP.
        """
        tipos_upper = [t.upper() for t in tipos]
        consecutivo = 1
        descargados_total = 0

        incluir_intervenciones = ("ALL" in tipos_upper or not tipos or any("INTERV" in t or "CONST" in t for t in tipos_upper))
        incluir_doctrina = ("ALL" in tipos_upper or not tipos or any("DOCTRINA" in t or "VOCES" in t or "BLOG" in t for t in tipos_upper))
        incluir_compendios = ("ALL" in tipos_upper or not tipos or any("COMPEND" in t or "OBSERV" in t for t in tipos_upper))

        progress_callback({
            "tipo_evento": "INFO",
            "mensaje": f"Iniciando descarga de Conceptos y Doctrina del ICDP ({ano_inicio} - {ano_fin})...",
            "corte": "Instituto Colombiano de Derecho Procesal (ICDP)"
        })

        # ==============================================================
        # 1. INTERVENCIONES Y CONCEPTOS ANTE LA CORTE CONSTITUCIONAL
        # ==============================================================
        if incluir_intervenciones:
            year_map = self._get_year_pages()
            anos_objetivo = [y for y in range(ano_inicio, ano_fin + 1) if y in year_map]
            
            for ano in sorted(anos_objetivo, reverse=True):
                if stop_event.is_set():
                    break

                page_url = year_map[ano]
                progress_callback({
                    "tipo_evento": "INFO",
                    "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                    "ano": ano,
                    "tipo": "Intervenciones",
                    "mensaje": f"Explorando Intervenciones y Conceptos Constitucionales del ICDP para el año {ano}..."
                })

                try:
                    r_yr = self.session.get(page_url, timeout=15)
                    if r_yr.status_code != 200:
                        continue
                    
                    soup_yr = BeautifulSoup(r_yr.text, "html.parser")
                    # Buscar todos los enlaces a archivos (Google Drive o PDF directo)
                    enlaces_archivos = []
                    for a in soup_yr.find_all("a", href=True):
                        href = a["href"].strip()
                        if "drive.google.com" in href or href.lower().endswith(".pdf"):
                            title = a.get_text(strip=True)
                            parent = a.find_parent(["p", "div", "td", "li", "article"])
                            ctx = parent.get_text(" ", strip=True) if parent else title
                            enlaces_archivos.append({
                                "url": href,
                                "title": title or ctx[:60],
                                "context": ctx
                            })

                    for item in enlaces_archivos:
                        if stop_event.is_set():
                            break
                        while pause_event.is_set():
                            time.sleep(0.5)

                        doc_url = item["url"]
                        raw_title = item["title"] or f"Concepto_ICDP_{ano}_{consecutivo}"
                        context_desc = item["context"]

                        # Extraer radicado/expediente
                        rad_match = re.search(r'(D[-0-9\.]+|LAT[-0-9\.]+|T[-0-9\.]+|EXP[-0-9\.]+)', raw_title + " " + context_desc, re.IGNORECASE)
                        radicado = rad_match.group(1).replace(".", "").strip() if rad_match else f"ICDP-{ano}-{consecutivo:03d}"
                        
                        # Limpiar nombre para archivo
                        safe_rad = re.sub(r'[^\w\-]', '_', radicado)
                        filename = f"Concepto_ICDP_{safe_rad}_{ano}.pdf"

                        # Verificación en Base de Datos e In-Memory Cache O(1)
                        if sentencia_exists(doc_url, radicado):
                            progress_callback({
                                "tipo_evento": "DUPLICADO",
                                "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                                "ano": ano,
                                "tipo": "Intervenciones",
                                "radicado": radicado,
                                "consecutivo": consecutivo,
                                "mensaje": f"[CACHE O(1)] Concepto ICDP {radicado} ya existe en Google Drive."
                            })
                            consecutivo += 1
                            continue

                        # Descargar contenido
                        content_bytes = None
                        if "drive.google.com" in doc_url:
                            content_bytes = self._download_gdrive_file(doc_url)
                        else:
                            try:
                                r_doc = self.session.get(doc_url, timeout=20)
                                if r_doc.status_code == 200:
                                    content_bytes = r_doc.content
                            except Exception as e_dl:
                                self.logger.warning(f"Error descargando {doc_url}: {e_dl}")

                        if not content_bytes:
                            progress_callback({
                                "tipo_evento": "ERROR",
                                "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                                "ano": ano,
                                "tipo": "Intervenciones",
                                "radicado": radicado,
                                "consecutivo": consecutivo,
                                "mensaje": f"No se pudo descargar el archivo de {radicado} ({doc_url})"
                            })
                            consecutivo += 1
                            continue

                        # Metadatos analíticos enriquecidos
                        metadata = {
                            "radicado": radicado,
                            "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                            "sala_especializada": "Intervenciones y Conceptos Constitucionales ICDP",
                            "ano": ano,
                            "tipo": "Intervenciones",
                            "magistrado_ponente": "Comisión de Expertos y Miembros ICDP",
                            "fecha_providencia": f"{ano}-01-01",
                            "expediente": radicado,
                            "tema": context_desc[:400] if context_desc else "Concepto técnico-jurídico e intervención procesal emitida por el ICDP ante la Corte Constitucional.",
                            "url_origen": doc_url,
                            "consecutivo": consecutivo
                        }

                        # Guardado en Google Drive en 4 formatos sincronizados (.pdf, .pdf copia, .md, .json)
                        file_path_str, pdf_path, md_path = drive_manager.save_sentence_file(
                            corte="Instituto Colombiano de Derecho Procesal (ICDP)",
                            ano=ano,
                            tipo="Intervenciones",
                            filename=filename,
                            content_bytes=content_bytes,
                            metadata=metadata
                        )

                        # Indexación en SQLite
                        save_sentencia({
                            "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                            "radicado": radicado,
                            "tipo": "Intervenciones",
                            "ano": ano,
                            "consecutivo": consecutivo,
                            "magistrado_ponente": metadata["magistrado_ponente"],
                            "fecha_providencia": metadata["fecha_providencia"],
                            "expediente": metadata["expediente"],
                            "tema": metadata["tema"],
                            "resuelve": "Concepto Técnico y Solicitud Doctrinal del ICDP",
                            "url_origen": doc_url,
                            "archivo_local": file_path_str,
                            "tamano_bytes": len(content_bytes),
                            "estado": "DESCARGADO",
                            "drive_link": None,
                            "drive_file_id": None
                        })

                        descargados_total += 1
                        progress_callback({
                            "tipo_evento": "DESCARGA",
                            "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                            "ano": ano,
                            "tipo": "Intervenciones",
                            "radicado": radicado,
                            "consecutivo": consecutivo,
                            "tamano_bytes": len(content_bytes),
                            "mensaje": f"Descargado e indexado: {radicado} en 01_Intervenciones_y_Conceptos_Constitucionales/{ano} ({len(content_bytes) // 1024} KB)"
                        })
                        consecutivo += 1
                        time.sleep(settings.request_delay_seconds)

                except Exception as e_ano:
                    self.logger.error(f"Error procesando año {ano} de intervenciones ICDP: {e_ano}")

        # ==============================================================
        # 2. DOCTRINA Y CONCEPTOS PROCESALES (BLOG VOCES PROCESALES)
        # ==============================================================
        if incluir_doctrina and not stop_event.is_set():
            progress_callback({
                "tipo_evento": "INFO",
                "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                "ano": ano_fin,
                "tipo": "Doctrina",
                "mensaje": "Explorando Conceptos Doctrinales y Artículos de Voces Procesales del ICDP..."
            })

            # Recorrer las primeras páginas del blog del ICDP
            for page_num in range(1, 6):
                if stop_event.is_set():
                    break
                blog_page_url = f"{self.blog_url}page/{page_num}/" if page_num > 1 else self.blog_url
                try:
                    r_blog = self.session.get(blog_page_url, timeout=15)
                    if r_blog.status_code != 200:
                        break
                    
                    soup_blog = BeautifulSoup(r_blog.text, "html.parser")
                    articulos = []
                    for art in soup_blog.find_all("article"):
                        title_el = art.find(["h2", "h3"])
                        link_el = art.find("a", href=True)
                        time_el = art.find(["time", "span"])
                        if title_el and link_el:
                            articulos.append({
                                "title": title_el.get_text(strip=True),
                                "url": link_el["href"],
                                "date": time_el.get_text(strip=True) if time_el else ""
                            })

                    for art in articulos:
                        if stop_event.is_set():
                            break
                        while pause_event.is_set():
                            time.sleep(0.5)

                        art_url = art["url"]
                        art_title = art["title"]
                        
                        # Extraer año de la fecha o de la URL
                        ano_art = ano_fin
                        m_ano = re.search(r'/(\d{4})/', art_url)
                        if m_ano:
                            ano_art = int(m_ano.group(1))
                        
                        if not (ano_inicio <= ano_art <= ano_fin):
                            continue

                        # Radicado sintetizado
                        safe_title = re.sub(r'[^\w\-]', '_', art_title)[:50]
                        radicado = f"DOCTRINA-ICDP-{safe_title}"

                        if sentencia_exists(art_url, radicado):
                            progress_callback({
                                "tipo_evento": "DUPLICADO",
                                "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                                "ano": ano_art,
                                "tipo": "Doctrina",
                                "radicado": radicado,
                                "consecutivo": consecutivo,
                                "mensaje": f"[CACHE O(1)] Artículo doctrinal {art_title[:40]} ya existe."
                            })
                            consecutivo += 1
                            continue

                        # Descargar artículo completo
                        r_art = self.session.get(art_url, timeout=15)
                        if r_art.status_code != 200:
                            continue

                        soup_post = BeautifulSoup(r_art.text, "html.parser")
                        content_el = soup_post.find(["div", "article"], class_=lambda c: c and any(w in c for w in ["entry-content", "post-content", "article-content"]))
                        if not content_el:
                            continue

                        html_bytes = f"<html><head><meta charset='utf-8'><title>{art_title}</title></head><body><h1>{art_title}</h1><div>{str(content_el)}</div></body></html>".encode("utf-8")
                        filename = f"Doctrina_ICDP_{safe_title}.html"

                        metadata = {
                            "radicado": radicado,
                            "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                            "sala_especializada": "Conceptos Doctrinales y Voces Procesales ICDP",
                            "ano": ano_art,
                            "tipo": "Doctrina",
                            "magistrado_ponente": "Miembro Investigador ICDP",
                            "fecha_providencia": f"{ano_art}-01-01",
                            "expediente": art_title,
                            "tema": f"Artículo Doctrinal y Concepto Procesal: {art_title}",
                            "url_origen": art_url,
                            "consecutivo": consecutivo
                        }

                        file_path_str, pdf_path, md_path = drive_manager.save_sentence_file(
                            corte="Instituto Colombiano de Derecho Procesal (ICDP)",
                            ano=ano_art,
                            tipo="Doctrina",
                            filename=filename,
                            content_bytes=html_bytes,
                            metadata=metadata
                        )

                        save_sentencia({
                            "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                            "radicado": radicado,
                            "tipo": "Doctrina",
                            "ano": ano_art,
                            "consecutivo": consecutivo,
                            "magistrado_ponente": metadata["magistrado_ponente"],
                            "fecha_providencia": metadata["fecha_providencia"],
                            "expediente": metadata["expediente"],
                            "tema": metadata["tema"],
                            "resuelve": "Análisis y Criterio Doctrinal Especializado",
                            "url_origen": art_url,
                            "archivo_local": file_path_str,
                            "tamano_bytes": len(html_bytes),
                            "estado": "DESCARGADO",
                            "drive_link": None,
                            "drive_file_id": None
                        })

                        descargados_total += 1
                        progress_callback({
                            "tipo_evento": "DESCARGA",
                            "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                            "ano": ano_art,
                            "tipo": "Doctrina",
                            "radicado": radicado,
                            "consecutivo": consecutivo,
                            "tamano_bytes": len(html_bytes),
                            "mensaje": f"Descargado e indexado: {art_title[:50]} en 02_Doctrina_y_Conceptos_Voces_Procesales/{ano_art}"
                        })
                        consecutivo += 1
                        time.sleep(settings.request_delay_seconds)

                except Exception as e_blog:
                    self.logger.warning(f"Error procesando página {page_num} de blog ICDP: {e_blog}")

        # ==============================================================
        # 3. COMPENDIOS Y OBSERVATORIO JURÍDICO
        # ==============================================================
        if incluir_compendios and not stop_event.is_set():
            progress_callback({
                "tipo_evento": "INFO",
                "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                "ano": ano_fin,
                "tipo": "Compendios",
                "mensaje": "Explorando Compendios Jurisprudenciales oficiales del ICDP..."
            })

            try:
                r_comp = self.session.get(self.compendio_url, timeout=15)
                if r_comp.status_code == 200:
                    soup_comp = BeautifulSoup(r_comp.text, "html.parser")
                    comp_links = [a for a in soup_comp.find_all("a", href=True) if "drive.google.com" in a["href"] or a["href"].lower().endswith(".pdf")]
                    for a_link in comp_links:
                        if stop_event.is_set():
                            break
                        c_url = a_link["href"].strip()
                        c_text = a_link.get_text(strip=True) or "Compendio Jurisprudencial ICDP"
                        
                        m_ano = re.search(r'20\d{2}', c_text)
                        ano_c = int(m_ano.group(0)) if m_ano else ano_fin

                        radicado = f"COMPENDIO-ICDP-{ano_c}"
                        if sentencia_exists(c_url, radicado):
                            progress_callback({
                                "tipo_evento": "DUPLICADO",
                                "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                                "ano": ano_c,
                                "tipo": "Compendios",
                                "radicado": radicado,
                                "consecutivo": consecutivo,
                                "mensaje": f"[CACHE O(1)] {c_text} ya existe en Google Drive."
                            })
                            consecutivo += 1
                            continue

                        bytes_comp = self._download_gdrive_file(c_url) if "drive.google.com" in c_url else None
                        if not bytes_comp:
                            try:
                                r_c = self.session.get(c_url, timeout=30)
                                if r_c.status_code == 200:
                                    bytes_comp = r_c.content
                            except Exception:
                                pass

                        if bytes_comp:
                            filename = f"Compendio_Jurisprudencial_ICDP_{ano_c}.pdf"
                            meta_c = {
                                "radicado": radicado,
                                "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                                "sala_especializada": "Compendios y Observatorio Jurídico ICDP",
                                "ano": ano_c,
                                "tipo": "Compendios",
                                "magistrado_ponente": "Observatorio Jurídico ICDP",
                                "fecha_providencia": f"{ano_c}-12-31",
                                "expediente": c_text,
                                "tema": f"Compendio oficial de jurisprudencia y doctrina procesal {ano_c} - ICDP",
                                "url_origen": c_url,
                                "consecutivo": consecutivo
                            }

                            file_path_str, pdf_path, md_path = drive_manager.save_sentence_file(
                                corte="Instituto Colombiano de Derecho Procesal (ICDP)",
                                ano=ano_c,
                                tipo="Compendios",
                                filename=filename,
                                content_bytes=bytes_comp,
                                metadata=meta_c
                            )

                            save_sentencia({
                                "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                                "radicado": radicado,
                                "tipo": "Compendios",
                                "ano": ano_c,
                                "consecutivo": consecutivo,
                                "magistrado_ponente": meta_c["magistrado_ponente"],
                                "fecha_providencia": meta_c["fecha_providencia"],
                                "expediente": meta_c["expediente"],
                                "tema": meta_c["tema"],
                                "resuelve": "Compendio Doctrinal y Jurisprudencial",
                                "url_origen": c_url,
                                "archivo_local": file_path_str,
                                "tamano_bytes": len(bytes_comp),
                                "estado": "DESCARGADO",
                                "drive_link": None,
                                "drive_file_id": None
                            })

                            descargados_total += 1
                            progress_callback({
                                "tipo_evento": "DESCARGA",
                                "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
                                "ano": ano_c,
                                "tipo": "Compendios",
                                "radicado": radicado,
                                "consecutivo": consecutivo,
                                "tamano_bytes": len(bytes_comp),
                                "mensaje": f"Descargado: {c_text} en 03_Compendios_y_Observatorio_Juridico/{ano_c} ({len(bytes_comp) // 1024} KB)"
                            })
                            consecutivo += 1

            except Exception as e_comp:
                self.logger.warning(f"Error procesando compendios ICDP: {e_comp}")

        progress_callback({
            "tipo_evento": "INFO",
            "corte": "Instituto Colombiano de Derecho Procesal (ICDP)",
            "mensaje": f"Finalizado rastreo de ICDP. Total conceptos y documentos procesados: {descargados_total}"
        })
