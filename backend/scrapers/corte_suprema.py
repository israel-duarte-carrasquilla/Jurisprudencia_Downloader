import time
import requests
import re
from typing import List, Dict, Any, Optional
from backend.scrapers.base_scraper import BaseScraper
from backend.database import sentencia_exists, save_sentencia
from backend.drive_manager import drive_manager
from backend.config import settings

class CorteSupremaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Corte Suprema de Justicia")
        self.api_url = "https://consultaprovidenciasbk.cortesuprema.gov.co/api"
        self.download_url = "https://consultaprovidenciasbk.cortesuprema.gov.co/downloadFile"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Origin": "https://consultaprovidencias.cortesuprema.gov.co",
            "Referer": "https://consultaprovidencias.cortesuprema.gov.co/"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _normalize_sala(self, tipo: str) -> str:
        """Mapea el tipo de providencia / sala a los identificadores del backend de la Corte Suprema."""
        tipo_l = tipo.lower()
        if "descongestion" in tipo_l:
            return "Laboral"
        elif "laboral" in tipo_l or tipo_l in ["sl", "al", "l"]:
            return "Laboral"
        elif "primera" in tipo_l or "aforado" in tipo_l:
            return "Penal"
        elif "instruccion" in tipo_l:
            return "Penal"
        elif "penal" in tipo_l or tipo_l in ["sp", "ap", "p"]:
            return "Penal"
        elif "tutela" in tipo_l or tipo_l in ["stc", "stp", "stl", "t"]:
            return "Tutelas"
        else:
            return "Civil"

    def _fetch_providencias_page(self, sala: str, ano: int, start: int = 0) -> List[Dict[str, Any]]:
        """Consulta un lote de providencias vía la API GraphQL de la Corte Suprema."""
        query = f"""
        {{
          getSearchResult(searchQuery: {{
            query: "*"
            typeOfQuery: "{sala}"
            start: {start}
            isExact: false
            magistrate: ""
            year: "{ano}"
            autoSentencia: ""
            order: "Más reciente primero"
            roomTutelas: ""
            addedQueries: []
          }}) {{
            searchResults {{
              title
              doctor
              ano
              fechaCreacion
              id
              autoSentencia
              onlinePath
              aplicationName
            }}
            numOfResults
          }}
        }}
        """
        try:
            resp = self.session.post(self.api_url, json={"query": query}, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", {}).get("getSearchResult", {}).get("searchResults", [])
        except Exception as e:
            print(f"Error consultando API Corte Suprema ({sala}-{ano}): {e}")
        return []

    def _download_file_bytes(self, online_path: str) -> Optional[tuple[bytes, str]]:
        """Descarga el archivo (priorizando PDF, y si no .docx)."""
        # 1. Probar ruta PDF
        pdf_path = re.sub(r'\.(?:docx?|doc)$', '.pdf', online_path, flags=re.IGNORECASE)
        try:
            r = self.session.post(self.download_url, json={"path": pdf_path}, timeout=15)
            if r.status_code == 200 and len(r.content) > 1000:
                return r.content, ".pdf"
        except Exception:
            pass

        # 2. Probar ruta original si falló el PDF
        try:
            r = self.session.post(self.download_url, json={"path": online_path}, timeout=15)
            if r.status_code == 200 and len(r.content) > 1000:
                ext = ".docx" if online_path.lower().endswith(".docx") else ".doc"
                return r.content, ext
        except Exception:
            pass

        return None

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
        Descarga providencias de la Corte Suprema de Justicia para los años y salas indicadas.
        """
        salas_a_explorar = set()
        for t in tipos:
            salas_a_explorar.add(self._normalize_sala(t))
        if not salas_a_explorar:
            salas_a_explorar = {"Civil", "Laboral", "Penal"}

        for ano in range(ano_fin, ano_inicio - 1, -1):
            if stop_event.is_set():
                break

            for sala in sorted(salas_a_explorar):
                if stop_event.is_set():
                    break

                progress_callback({
                    "tipo_evento": "INFO",
                    "corte": self.name,
                    "ano": ano,
                    "tipo": sala,
                    "mensaje": f"Consultando providencias de Sala {sala} para el año {ano} en Corte Suprema..."
                })

                page_size = 10
                max_items_per_sala = 30 # Lote ágil por año
                consecutivo = 1
                items_descargados_sala = 0

                for start in range(0, max_items_per_sala, page_size):
                    if stop_event.is_set():
                        break

                    while pause_event.is_set():
                        if stop_event.is_set():
                            break
                        time.sleep(0.5)

                    results = self._fetch_providencias_page(sala, ano, start=start)
                    if not results:
                        break

                    for item in results:
                        if stop_event.is_set():
                            break

                        while pause_event.is_set():
                            if stop_event.is_set():
                                break
                            time.sleep(0.5)

                        raw_title = item.get("title", f"Providencia_{consecutivo}_{ano}")
                        radicado = re.sub(r'\.(?:docx?|pdf)$', '', raw_title, flags=re.IGNORECASE)
                        canonical_url = f"https://consultaprovidencias.cortesuprema.gov.co/doc/{ano}/{radicado}"

                        if sentencia_exists(canonical_url, radicado=radicado):
                            progress_callback({
                                "tipo_evento": "EXISTENTE",
                                "corte": self.name,
                                "radicado": radicado,
                                "ano": ano,
                                "tipo": sala,
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
                            "tipo": sala,
                            "consecutivo": consecutivo,
                            "mensaje": f"Descargando {radicado} de Sala {sala}..."
                        })

                        online_path = item.get("onlinePath", "")
                        download_res = self._download_file_bytes(online_path) if online_path else None

                        if not download_res:
                            consecutivo += 1
                            continue

                        content_bytes, ext = download_res
                        consecutivo += 1
                        items_descargados_sala += 1

                        metadata = {
                            "radicado": radicado,
                            "magistrado_ponente": item.get("doctor", "No especificado"),
                            "fecha_providencia": item.get("fechaCreacion", str(ano))[:10],
                            "expediente": raw_title,
                            "tema": f"Providencia de Casación {item.get('autoSentencia', 'Decisión')} - {sala}",
                            "resuelve": item.get("autoSentencia", "Fallo de Casación"),
                            "url_origen": canonical_url
                        }

                        filename = f"{radicado}{ext}"
                        local_path, drive_link, drive_id = drive_manager.save_sentence_file(
                            corte=self.name,
                            ano=ano,
                            tipo=sala,
                            filename=filename,
                            content_bytes=content_bytes,
                            metadata=metadata
                        )

                        db_record = {
                            "corte": self.name,
                            "radicado": radicado,
                            "tipo": sala,
                            "ano": ano,
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
                            "ano": ano,
                            "tipo": sala,
                            "consecutivo": consecutivo,
                            "tamano_bytes": len(content_bytes),
                            "magistrado": metadata["magistrado_ponente"],
                            "drive_link": drive_link,
                            "archivo_local": local_path,
                            "mensaje": f"Descargada {radicado} de Sala {sala} ({len(content_bytes)//1024} KB) en Google Drive."
                        })

                        time.sleep(settings.request_delay_seconds)

                progress_callback({
                    "tipo_evento": "SERIE_FINALIZADA",
                    "corte": self.name,
                    "ano": ano,
                    "tipo": sala,
                    "mensaje": f"Finalizada descarga de Sala {sala} ({ano}): {items_descargados_sala} providencias procesadas."
                })
