import time
import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List, Tuple
from backend.scrapers.base_scraper import BaseScraper
from backend.database import sentencia_exists, save_sentencia
from backend.drive_manager import drive_manager
from backend.config import settings

class CorteConstitucionalScraper(BaseScraper):
    def __init__(self):
        super().__init__("Corte Constitucional")
        self.base_url = "https://www.corteconstitucional.gov.co/relatoria"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        })

    def extract_metadata(self, html_text: str, default_radicado: str, default_ano: int) -> Dict[str, Any]:
        """Extrae metadatos jurídicos clave del texto de la sentencia."""
        soup = BeautifulSoup(html_text, "html.parser")
        full_text = soup.get_text(separator="\n")
        
        # 1. Magistrado Ponente
        mp = ""
        mp_match = re.search(
            r'(?:Magistrad[oa]\s+Ponente|M\.?\s*P\.?)[:\s]+([^\n\r,;]{4,80})',
            full_text,
            re.IGNORECASE
        )
        if mp_match:
            mp = mp_match.group(1).strip()
            # Limpiar posibles saltos o basura
            mp = re.sub(r'\s+', ' ', mp)
            
        # 2. Fecha de providencia
        fecha = ""
        fecha_match = re.search(
            r'(\b\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+\d{4}\b)',
            full_text,
            re.IGNORECASE
        )
        if fecha_match:
            fecha = fecha_match.group(1).strip()
            
        # 3. Expediente
        expediente = ""
        exp_match = re.search(
            r'Expediente(?:s)?[:\s]+([^\n\r,;]{3,50})',
            full_text,
            re.IGNORECASE
        )
        if exp_match:
            expediente = exp_match.group(1).strip()

        # 4. Tema / Síntesis
        tema = ""
        tema_match = re.search(
            r'(?:TEMA|ASUNTO|SÍNTESIS|SINTESIS)[:\s]+([^\n\r]+(?:\n[^\n\r]+){1,3})',
            full_text,
            re.IGNORECASE
        )
        if tema_match:
            tema = tema_match.group(1).strip()
            tema = re.sub(r'\s+', ' ', tema)[:300]
        else:
            # Si no hay encabezado explícito, tomar los primeros párrafos significativos
            paragraphs = [p.strip() for p in full_text.split("\n") if len(p.strip()) > 60]
            if len(paragraphs) > 1:
                tema = paragraphs[1][:250] + "..."

        # 5. Resuelve (Fallo)
        resuelve = ""
        resuelve_match = re.search(
            r'(?:RESUELVE|DECIDE|DISPONE)[:\s]+([\s\S]{10,400})',
            full_text,
            re.IGNORECASE
        )
        if resuelve_match:
            resuelve = re.sub(r'\s+', ' ', resuelve_match.group(1).strip())[:350] + "..."

        return {
            "magistrado_ponente": mp or "No especificado",
            "fecha_providencia": fecha or f"{default_ano}",
            "expediente": expediente or "N/A",
            "tema": tema or f"Providencia {default_radicado}",
            "resuelve": resuelve or "Ver texto completo de la providencia"
        }

    def _try_download_sentence(
        self,
        ano: int,
        tipo: str,
        consecutivo: int
    ) -> Optional[Tuple[str, bytes, str]]:
        """
        Intenta descargar la providencia probando patrones comunes de nomenclatura en la relatoría.
        Filtra respuestas SPA o 404 simuladas (evita páginas de error Angular de 8.6 KB).
        Retorna (url_exitosa, contenido_bytes, extension) o None si no existe.
        """
        short_yr = str(ano)[-2:]
        num_str = f"{consecutivo:03d}"
        tipo_upper = tipo.upper()
        
        # Generar candidatos específicos según el tipo de providencia
        candidates = []
        if tipo_upper == "T":
            candidates.extend([
                f"{ano}/T-{num_str}-{short_yr}.htm",
                f"{ano}/t-{num_str}-{short_yr}.htm",
            ])
        elif tipo_upper == "C":
            candidates.extend([
                f"{ano}/C-{num_str}-{short_yr}.htm",
                f"{ano}/c-{num_str}-{short_yr}.htm",
            ])
        elif tipo_upper == "SU":
            candidates.extend([
                f"{ano}/SU{num_str}-{short_yr}.htm",
                f"{ano}/su{num_str}-{short_yr}.htm",
                f"{ano}/SU-{num_str}-{short_yr}.htm",
                f"{ano}/su-{num_str}-{short_yr}.htm",
                f"{ano}/su{consecutivo}-{short_yr}.htm",
            ])
        elif tipo_upper == "A":
            candidates.extend([
                f"autos/{ano}/A{num_str}-{short_yr}.htm",
                f"autos/{ano}/A-{num_str}-{short_yr}.htm",
                f"{ano}/A-{num_str}-{short_yr}.htm",
                f"{ano}/A{num_str}-{short_yr}.htm",
            ])
        else:
            candidates.extend([
                f"{ano}/{tipo}-{num_str}-{short_yr}.htm",
                f"{ano}/{tipo.lower()}-{num_str}-{short_yr}.htm"
            ])

        for path in candidates:
            url = f"{self.base_url}/{path}"
            try:
                # Timeout rápido para no congelar la exploración
                resp = self.session.get(url, timeout=2.5)
                if resp.status_code == 200:
                    content_len = len(resp.content)
                    # En la Corte, si no existe devuelve 200 con la SPA Angular vacía (8607 bytes aprox)
                    if content_len > 1200:
                        sample = resp.content[:2000].decode("latin-1", errors="ignore").lower()
                        # Verificar que NO sea la página de fallback SPA Angular
                        is_spa = "app-root" in sample or "data-beasties" in sample or content_len == 8607
                        if not is_spa:
                            ext = "." + path.split(".")[-1]
                            return url, resp.content, ext
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
        Recorre los años y tipos indicados descargando y enviando a Google Drive.
        """
        for ano in range(ano_fin, ano_inicio - 1, -1):
            if stop_event.is_set():
                break

            for tipo in tipos:
                if stop_event.is_set():
                    break

                consecutivo = 1
                consecutive_errors = 0
                max_consecutive_errors = settings.max_consecutive_errors

                while consecutive_errors < max_consecutive_errors:
                    # Comprobar pausa
                    while pause_event.is_set():
                        if stop_event.is_set():
                            break
                        time.sleep(0.5)

                    if stop_event.is_set():
                        break

                    short_yr = str(ano)[-2:]
                    radicado = f"{tipo}-{consecutivo:03d}-{short_yr}"
                    canonical_url = f"{self.base_url}/{ano}/{radicado}.htm"

                    # 1. Comprobar si ya la tenemos en base de datos local (O(1) memoria)
                    if sentencia_exists(canonical_url, radicado=radicado):
                        progress_callback({
                            "tipo_evento": "EXISTENTE",
                            "corte": self.name,
                            "radicado": radicado,
                            "ano": ano,
                            "tipo": tipo,
                            "consecutivo": consecutivo,
                            "mensaje": f"{radicado} ({ano}) ya registrada en Drive."
                        })
                        consecutivo += 1
                        consecutive_errors = 0
                        continue

                    # 2. Notificar a la interfaz que se está sondeando este radicado
                    progress_callback({
                        "tipo_evento": "PROBANDO",
                        "corte": self.name,
                        "radicado": radicado,
                        "ano": ano,
                        "tipo": tipo,
                        "consecutivo": consecutivo,
                        "fallos_consecutivos": consecutive_errors,
                        "max_fallos": max_consecutive_errors,
                        "mensaje": f"Consultando {radicado} en relatoría ({ano})..."
                    })

                    # 3. Intentar descarga de la relatoría
                    result = self._try_download_sentence(ano, tipo, consecutivo)
                    
                    if result is None:
                        consecutive_errors += 1
                        # Informar en el log cada 5 fallos, al inicio o cerca del límite
                        if consecutive_errors == 1 or consecutive_errors % 5 == 0 or consecutive_errors >= max_consecutive_errors:
                            progress_callback({
                                "tipo_evento": "NO_ENCONTRADA",
                                "corte": self.name,
                                "radicado": radicado,
                                "ano": ano,
                                "tipo": tipo,
                                "consecutivo": consecutivo,
                                "fallos_consecutivos": consecutive_errors,
                                "max_fallos": max_consecutive_errors,
                                "mensaje": f"{radicado} no disponible en relatoría ({consecutive_errors}/{max_consecutive_errors})."
                            })
                        consecutivo += 1
                        time.sleep(settings.request_delay_seconds)
                        continue

                    # Éxito: providencia auténtica encontrada
                    found_url, content_bytes, ext = result
                    consecutive_errors = 0

                    # 3. Extraer metadatos
                    try:
                        html_text = content_bytes.decode("latin-1", errors="ignore")
                    except Exception:
                        html_text = content_bytes.decode("utf-8", errors="ignore")
                        
                    metadata = self.extract_metadata(html_text, radicado, ano)

                    # 4. Guardar archivo en Google Drive (sincronizada o nube)
                    filename = f"{radicado}{ext}"
                    local_path, drive_link, drive_id = drive_manager.save_sentence_file(
                        corte=self.name,
                        ano=ano,
                        tipo=tipo,
                        filename=filename,
                        content_bytes=content_bytes,
                        metadata={
                            "radicado": radicado,
                            "corte": self.name,
                            "ano": ano,
                            "tipo": tipo,
                            "consecutivo": consecutivo,
                            "url_origen": found_url,
                            **metadata
                        }
                    )

                    # 5. Registrar en Base de Datos
                    db_record = {
                        "corte": self.name,
                        "radicado": radicado,
                        "tipo": tipo,
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
                        "estado": "SUBIDO_DRIVE" if drive_link else "DESCARGADO",
                        "drive_link": drive_link,
                        "drive_file_id": drive_id
                    }
                    save_sentencia(db_record)

                    # 6. Reportar a la UI
                    progress_callback({
                        "tipo_evento": "DESCARGADA",
                        "corte": self.name,
                        "radicado": radicado,
                        "ano": ano,
                        "tipo": tipo,
                        "consecutivo": consecutivo,
                        "tamano_bytes": len(content_bytes),
                        "magistrado": metadata["magistrado_ponente"],
                        "drive_link": drive_link,
                        "archivo_local": local_path,
                        "mensaje": f"Descargada {radicado} ({len(content_bytes)//1024} KB) y guardada en Google Drive."
                    })

                    consecutivo += 1
                    # Pausa reactiva que responde inmediatamente a stop_event
                    delay = settings.request_delay_seconds
                    steps = max(1, int(delay / 0.1))
                    for _ in range(steps):
                        if stop_event.is_set():
                            break
                        time.sleep(0.1)

                if not stop_event.is_set():
                    progress_callback({
                        "tipo_evento": "SERIE_FINALIZADA",
                        "corte": self.name,
                        "ano": ano,
                        "tipo": tipo,
                        "mensaje": f"Serie de providencias {tipo} ({ano}) completada. Evaluadas hasta el consecutivo {consecutivo-1}."
                    })

