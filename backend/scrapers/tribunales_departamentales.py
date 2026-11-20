import time
import requests
import re
import html
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from backend.scrapers.base_scraper import BaseScraper
from backend.database import sentencia_exists, save_sentencia
from backend.drive_manager import drive_manager
from backend.config import settings

class TribunalesDepartamentalesScraper(BaseScraper):
    def __init__(self):
        super().__init__("Tribunales Departamentales")
        self.base_url = "https://samai.consejodeestado.gov.co/TitulacionRelatoria/BuscadorProvidenciasTituladas.aspx"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://samai.consejodeestado.gov.co",
            "Referer": self.base_url
        }
        # Principales Tribunales Administrativos y Superiores Departamentales
        self.tribunales_catalog = [
            ("Atlantico", "Tribunal Administrativo y Superior del Atlántico (Barranquilla)", "Tribunal_Atlantico_Barranquilla", "08001"),
            ("Antioquia", "Tribunal Administrativo y Superior de Antioquia (Medellín)", "Tribunal_Antioquia_Medellin", "05001"),
            ("Cundinamarca", "Tribunal Administrativo de Cundinamarca y Bogotá", "Tribunal_Cundinamarca_Bogota", "2500023"),
            ("Valle", "Tribunal Administrativo y Superior del Valle del Cauca (Cali)", "Tribunal_Valle_Cali", "76001"),
            ("Santander", "Tribunal Administrativo y Superior de Santander (Bucaramanga)", "Tribunal_Santander_Bucaramanga", "68001"),
            ("Bolivar", "Tribunal Administrativo y Superior de Bolívar (Cartagena)", "Tribunal_Bolivar_Cartagena", "13001"),
            ("Magdalena", "Tribunal Administrativo del Magdalena (Santa Marta)", "Tribunal_Magdalena_SantaMarta", "47001"),
            ("Boyaca", "Tribunal Administrativo de Boyacá", "Tribunal_Boyaca_Tunja", "1500123"),
            ("Caldas", "Tribunal Administrativo de Caldas (Manizales)", "Tribunal_Caldas_Manizales", "1700123"),
            ("Meta", "Tribunal Administrativo del Meta (Villavicencio)", "Tribunal_Meta_Villavicencio", "5000123")
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
        Descarga providencias de Tribunales Departamentales y Distritos Judiciales.
        """
        session = requests.Session()
        session.headers.update(self.headers)
        tipos_upper = [t.upper() for t in tipos]

        tribunales_a_explorar = []
        if "ALL" in tipos_upper or not tipos:
            tribunales_a_explorar = self.tribunales_catalog
        else:
            for code, name, slug, dep_code in self.tribunales_catalog:
                if any(t in code.upper() or code.upper() in t for t in tipos_upper):
                    tribunales_a_explorar.append((code, name, slug, dep_code))
            if not tribunales_a_explorar:
                tribunales_a_explorar = self.tribunales_catalog

        for ano in range(ano_fin, ano_inicio - 1, -1):
            if stop_event.is_set():
                break

            for code, name, slug, dep_code in tribunales_a_explorar:
                if stop_event.is_set():
                    break

                progress_callback({
                    "tipo_evento": "INFO",
                    "corte": self.name,
                    "ano": ano,
                    "tipo": slug,
                    "mensaje": f"Consultando providencias judiciales de {name} ({ano})..."
                })

                try:
                    r1 = session.get(self.base_url, timeout=15)
                    soup1 = BeautifulSoup(r1.text, "html.parser")
                    form_data = {inp.get("name"): inp.get("value", "") for inp in soup1.find_all("input") if inp.get("name")}
                except Exception as e:
                    continue

                form_data["__EVENTTARGET"] = "ctl00$MainContent$BusquedaRapidaLinkButton"
                form_data["__EVENTARGUMENT"] = ""
                form_data["ctl00$MainContent$BusquedaRapidaTextBox"] = f"{code} {ano}"

                # Si es una corporación específica en el dropdown
                if dep_code.isdigit() and len(dep_code) >= 6:
                    form_data["ctl00$MainContent$CorporacionesTitulanDataList"] = dep_code

                try:
                    r2 = session.post(self.base_url, data=form_data, timeout=20)
                    soup2 = BeautifulSoup(r2.text, "html.parser")
                except Exception as e:
                    continue

                doc_buttons = soup2.find_all("a", id=re.compile(r"TitulacionesRepeater.*documentlink"))
                if not doc_buttons:
                    progress_callback({
                        "tipo_evento": "INFO",
                        "corte": self.name,
                        "ano": ano,
                        "tipo": slug,
                        "mensaje": f"No se registraron providencias disponibles para {name} en {ano}."
                    })
                    continue

                progress_callback({
                    "tipo_evento": "INFO",
                    "corte": self.name,
                    "ano": ano,
                    "tipo": slug,
                    "mensaje": f"Encontradas {len(doc_buttons)} providencias en {name} ({ano}). Iniciando descarga..."
                })

                current_inputs = {inp.get("name"): inp.get("value", "") for inp in soup2.find_all("input") if inp.get("name")}
                consecutivo = 1
                descargadas_tribunal = 0

                for btn in doc_buttons:
                    if stop_event.is_set():
                        break

                    while pause_event.is_set():
                        if stop_event.is_set():
                            break
                        time.sleep(0.5)

                    btn_id = btn.get("id", "")
                    name_target = btn_id.replace("_", "$")

                    row_el = btn.find_parent("div", class_="row")
                    if not row_el or "proceso" not in row_el.text.lower():
                        curr = btn
                        while curr and curr.parent:
                            curr = curr.parent
                            if "núm. del proceso" in curr.text.lower() or "sala de decisión" in curr.text.lower():
                                row_el = curr
                                break

                    card_text = row_el.text if row_el else ""

                    rad_match = re.search(r'N[uú]m\.\s*del\s*proceso[:\s]+(\d{23})', card_text, re.I)
                    if not rad_match:
                        rad_match = re.search(r'\b(\d{23})\b', card_text)

                    if rad_match:
                        radicado = rad_match.group(1)
                    else:
                        int_match = re.search(r'Interno[:\s]+([0-9\-]+)', card_text, re.I)
                        radicado = f"TRIB-{code[:3]}-{int_match.group(1).strip()}" if int_match else f"TRIB-{code[:3]}-{ano}-{consecutivo:03d}"

                    pon_match = re.search(r'Titular[:\s]+([^\n\r,;]{4,60})', card_text, re.I)
                    magistrado = pon_match.group(1).strip() if pon_match else "Magistrado de Tribunal"

                    clase_match = re.search(r'Clase\s+del\s+proceso[:\s]+([^\n\r]+)', card_text, re.I)
                    clase_proceso = clase_match.group(1).strip() if clase_match else "Segunda Instancia Departamental"

                    fec_match = re.search(r'Providencia\s+del[:\s]+([^\n\r]+)', card_text, re.I)
                    fecha_prov = fec_match.group(1).strip() if fec_match else str(ano)

                    canonical_url = f"https://samai.consejodeestado.gov.co/doc/tribunal/{radicado}"

                    if sentencia_exists(canonical_url, radicado=radicado):
                        progress_callback({
                            "tipo_evento": "EXISTENTE",
                            "corte": self.name,
                            "radicado": radicado,
                            "ano": ano,
                            "tipo": slug,
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
                        "tipo": slug,
                        "consecutivo": consecutivo,
                        "mensaje": f"Descargando fallo de {name}: {radicado}..."
                    })

                    current_inputs["__EVENTTARGET"] = name_target
                    current_inputs["__EVENTARGUMENT"] = ""

                    try:
                        r_doc = session.post(self.base_url, data=current_inputs, timeout=18)
                        soup_doc = BeautifulSoup(r_doc.text, "html.parser")
                        for inp in soup_doc.find_all("input"):
                            if inp.get("name"):
                                current_inputs[inp.get("name")] = inp.get("value", "")

                        unescaped_doc = html.unescape(r_doc.text)
                        vp_match = re.search(r'CargarVentana\([\'"]([^\'"]+VerProvidencia[^\'"]+)[\'"]\)', unescaped_doc, re.I)
                        if not vp_match:
                            vp_match = re.search(r'CargarVentana\((?:&#39;|\')([^\'\"]+VerProvidencia[^\'\"]+)(?:&#39;|\')\)', r_doc.text, re.I)

                        if not vp_match:
                            consecutivo += 1
                            continue

                        vp_url = html.unescape(vp_match.group(1))

                        r_vp = session.get(vp_url, timeout=15)
                        vp_content = html.unescape(r_vp.text)
                        blob_match = re.search(r'https://[a-zA-Z0-9_\-\.]+\.blob\.core\.windows\.net/[^\'\"\s\<\>]+', vp_content)
                        if not blob_match:
                            consecutivo += 1
                            continue

                        blob_url = blob_match.group(0)

                        r_blob = session.get(blob_url, timeout=20)
                        if r_blob.status_code != 200 or len(r_blob.content) < 1000:
                            consecutivo += 1
                            continue

                        content_bytes = r_blob.content
                        consecutivo += 1
                        descargadas_tribunal += 1

                        metadata = {
                            "radicado": radicado,
                            "magistrado_ponente": magistrado,
                            "fecha_providencia": fecha_prov,
                            "expediente": radicado,
                            "tema": f"Fallo de Segunda Instancia - {name} ({clase_proceso})",
                            "resuelve": "Sentencia de Tribunal Departamental",
                            "url_origen": canonical_url
                        }

                        filename = f"{radicado}.pdf"
                        local_path, drive_link, drive_id = drive_manager.save_sentence_file(
                            corte=self.name,
                            ano=ano,
                            tipo=slug,
                            filename=filename,
                            content_bytes=content_bytes,
                            metadata=metadata
                        )

                        db_record = {
                            "corte": self.name,
                            "radicado": radicado,
                            "tipo": slug,
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
                            "tipo": slug,
                            "consecutivo": consecutivo,
                            "tamano_bytes": len(content_bytes),
                            "magistrado": magistrado,
                            "drive_link": drive_link,
                            "archivo_local": local_path,
                            "mensaje": f"Descargada {radicado} ({len(content_bytes)//1024} KB) en Google Drive ({name})."
                        })

                        time.sleep(settings.request_delay_seconds)

                    except Exception as ex_t:
                        print(f"Error procesando documento {radicado}: {ex_t}")
                        consecutivo += 1
                        continue

                progress_callback({
                    "tipo_evento": "SERIE_FINALIZADA",
                    "corte": self.name,
                    "ano": ano,
                    "tipo": slug,
                    "mensaje": f"Finalizado {name} ({ano}): {descargadas_tribunal} providencias guardadas en Drive."
                })
