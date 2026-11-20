import time
import requests
import re
from typing import List, Dict, Any, Optional
from backend.scrapers.base_scraper import BaseScraper
from backend.database import sentencia_exists, save_sentencia
from backend.drive_manager import drive_manager
from backend.config import settings

class LaudosArbitralesScraper(BaseScraper):
    def __init__(self):
        super().__init__("Laudos Arbitrales")
        self.api_url = "https://bibliotecadigital.ccb.org.co/server/api/discover/search/objects"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://bibliotecadigital.ccb.org.co"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Repositorios arbitrales por Cámara de Comercio
        self.centros_arbitraje = [
            ("Bogota", "Cámara de Comercio de Bogotá (Centro de Arbitraje y Conciliación)", "CAC_Bogota"),
            ("Barranquilla", "Cámara de Comercio de Barranquilla (Centro de Conciliación y Arbitraje)", "CAC_Barranquilla"),
            ("Medellin", "Cámara de Comercio de Medellín para Antioquia (Centro de Arbitraje)", "CAC_Medellin"),
            ("Cali", "Cámara de Comercio de Cali (Centro de Conciliación y Arbitraje)", "CAC_Cali")
        ]

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
        Descarga laudos arbitrales oficiales de Bogotá, Barranquilla y Medellín.
        """
        tipos_upper = [t.upper() for t in tipos]
        centros_a_explorar = []
        if "ALL" in tipos_upper or not tipos:
            centros_a_explorar = self.centros_arbitraje
        else:
            for code, name, folder in self.centros_arbitraje:
                if any(t in code.upper() or code.upper() in t for t in tipos_upper):
                    centros_a_explorar.append((code, name, folder))
            if not centros_a_explorar:
                centros_a_explorar = self.centros_arbitraje

        consecutivo = 1
        descargados_total = 0

        for code, name, folder in centros_a_explorar:
            if stop_event.is_set():
                break

            progress_callback({
                "tipo_evento": "INFO",
                "corte": self.name,
                "ano": ano_fin,
                "tipo": folder,
                "mensaje": f"Consultando laudos arbitrales en {name}..."
            })

            # 1. Búsqueda en API DSpace de Arbitraje
            queries = [f"laudo arbitral {code}", f"tribunal arbitral {code}", "laudo arbitral"]
            for q in queries:
                if stop_event.is_set():
                    break

                params = {"query": q, "size": 10}
                try:
                    r = self.session.get(self.api_url, params=params, timeout=15)
                    if r.status_code != 200:
                        continue
                    data = r.json()
                    objects = data.get("_embedded", {}).get("searchResult", {}).get("_embedded", {}).get("objects", [])
                except Exception:
                    continue

                for obj in objects:
                    if stop_event.is_set():
                        break

                    while pause_event.is_set():
                        if stop_event.is_set():
                            break
                        time.sleep(0.5)

                    item = obj.get("_embedded", {}).get("indexableObject", {})
                    item_id = item.get("id")
                    item_name = item.get("name", f"Laudo Arbitral {code}")
                    handle = item.get("handle", "")

                    try:
                        b_resp = self.session.get(f"https://bibliotecadigital.ccb.org.co/server/api/core/items/{item_id}/bundles", timeout=12)
                        if b_resp.status_code != 200:
                            continue
                        bundles = b_resp.json().get("_embedded", {}).get("bundles", [])
                    except Exception:
                        continue

                    pdf_download_url = None
                    for b in bundles:
                        if b.get("name") == "ORIGINAL":
                            bs_url = b.get("_links", {}).get("bitstreams", {}).get("href")
                            try:
                                bs_data = self.session.get(bs_url, timeout=12).json()
                                for bs in bs_data.get("_embedded", {}).get("bitstreams", []):
                                    fname = bs.get("name", "")
                                    if fname.lower().endswith(".pdf"):
                                        pdf_download_url = bs.get("_links", {}).get("content", {}).get("href")
                                        break
                            except Exception:
                                pass
                        if pdf_download_url:
                            break

                    if not pdf_download_url:
                        continue

                    clean_rad = re.sub(r"[^\w\s-]", "", item_name).strip().replace(" ", "_")
                    if len(clean_rad) > 60:
                        clean_rad = clean_rad[:60]
                    radicado = f"Laudo_{code}_{clean_rad}"
                    canonical_url = f"https://bibliotecadigital.ccb.org.co/handle/{handle}" if handle else pdf_download_url

                    if sentencia_exists(canonical_url, radicado=radicado):
                        progress_callback({
                            "tipo_evento": "EXISTENTE",
                            "corte": self.name,
                            "radicado": radicado,
                            "ano": ano_fin,
                            "tipo": folder,
                            "consecutivo": consecutivo,
                            "mensaje": f"{radicado} ya registrado en Drive."
                        })
                        consecutivo += 1
                        continue

                    progress_callback({
                        "tipo_evento": "PROBANDO",
                        "corte": self.name,
                        "radicado": radicado,
                        "ano": ano_fin,
                        "tipo": folder,
                        "consecutivo": consecutivo,
                        "mensaje": f"Descargando Laudo Arbitral de {code}: {item_name[:50]}..."
                    })

                    try:
                        r_pdf = self.session.get(pdf_download_url, timeout=25)
                        if r_pdf.status_code != 200 or len(r_pdf.content) < 1000:
                            consecutivo += 1
                            continue

                        content_bytes = r_pdf.content
                        consecutivo += 1
                        descargados_total += 1

                        metadata = {
                            "radicado": radicado,
                            "magistrado_ponente": f"Tribunal de Arbitramento - {name}",
                            "fecha_providencia": str(ano_fin),
                            "expediente": handle or f"Laudo-{code}-{consecutivo:03d}",
                            "tema": item_name[:250],
                            "resuelve": "Laudo Arbitral en Derecho - Decisión Definitiva y Vinculante",
                            "url_origen": canonical_url
                        }

                        filename = f"{radicado}.pdf"
                        local_path, drive_link, drive_id = drive_manager.save_sentence_file(
                            corte=self.name,
                            ano=ano_fin,
                            tipo=folder,
                            filename=filename,
                            content_bytes=content_bytes,
                            metadata=metadata
                        )

                        db_record = {
                            "corte": self.name,
                            "radicado": radicado,
                            "tipo": folder,
                            "ano": ano_fin,
                            "consecutivo": consecutivo,
                            "magistrado_ponente": metadata["magistrado_ponente"],
                            "fecha_providencia": metadata["fecha_providencia"],
                            "expediente": metadata["expediente"],
                            "tema": metadata["tema"],
                            "resuelve": metadata["resuelve"],
                            "url_origen": canonical_url,
                            "archivo_local": local_path,
                            "tamano_bytes": len(content_bytes),
                            "estado": "SUBIDO_DRIVE",
                            "drive_link": drive_link,
                            "drive_file_id": drive_id
                        }
                        save_sentencia(db_record)

                        progress_callback({
                            "tipo_evento": "DESCARGADA",
                            "corte": self.name,
                            "radicado": radicado,
                            "ano": ano_fin,
                            "tipo": folder,
                            "consecutivo": consecutivo,
                            "tamano_bytes": len(content_bytes),
                            "magistrado": f"Tribunal Arbitral ({code})",
                            "drive_link": drive_link,
                            "archivo_local": local_path,
                            "mensaje": f"Descargado {radicado} ({len(content_bytes)//1024} KB) en Google Drive ({code})."
                        })

                        time.sleep(settings.request_delay_seconds)

                    except Exception as ex_laudo:
                        print(f"Error procesando laudo {radicado}: {ex_laudo}")
                        consecutivo += 1
                        continue

            progress_callback({
                "tipo_evento": "SERIE_FINALIZADA",
                "corte": self.name,
                "ano": ano_fin,
                "tipo": folder,
                "mensaje": f"Finalizada tanda de laudos en {name}."
            })
