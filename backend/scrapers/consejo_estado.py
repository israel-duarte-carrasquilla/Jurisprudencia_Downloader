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

class ConsejoEstadoScraper(BaseScraper):
    def __init__(self):
        super().__init__("Consejo de Estado")
        self.base_url = "https://samai.consejodeestado.gov.co/TitulacionRelatoria/BuscadorProvidenciasTituladas.aspx"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://samai.consejodeestado.gov.co",
            "Referer": self.base_url
        }
        self.secciones_def = [
            ("Plena", "Sala Plena", "Sala_Plena_Contenciosa_y_SUJ", "Sala Plena (SUJ y Pérdida de Investidura)"),
            ("SalasEspeciales", "Sala Especial", "Salas_Especiales_de_Decision", "Salas Especiales de Decisión (1 a 26)"),
            ("Segunda", "Seccion Segunda", "Seccion_Segunda_Laboral_Subsecciones_A_y_B", "Sección Segunda (Laboral - Subsecciones A y B)"),
            ("Tercera", "Seccion Tercera", "Seccion_Tercera_Contractual_y_Dano_Subsecciones_A_B_C", "Sección Tercera (Contratos & Daño - Subsecciones A, B y C)"),
            ("Cuarta", "Seccion Cuarta", "Seccion_Cuarta_Tributaria_Financiera", "Sección Cuarta (Tributaria, Financiera y Aduanera)"),
            ("Primera", "Seccion Primera", "Seccion_Primera_General_Ambiental", "Sección Primera (General y Ambiental)"),
            ("Quinta", "Seccion Quinta", "Seccion_Quinta_Electoral", "Sección Quinta (Electoral)"),
            ("Consulta", "Sala de Consulta", "Sala_Consulta_y_Servicio_Civil", "Sala de Consulta y Servicio Civil")
        ]

    def _normalize_seccion(self, seccion_raw: str, default_fallback: str = "Seccion_Segunda_Laboral_Subsecciones_A_y_B") -> str:
        s_low = seccion_raw.lower()
        if "especial" in s_low:
            return "Salas_Especiales_de_Decision"
        elif "plena" in s_low or "unificacion" in s_low or "suj" in s_low:
            return "Sala_Plena_Contenciosa_y_SUJ"
        elif "segunda" in s_low or "laboral" in s_low:
            return "Seccion_Segunda_Laboral_Subsecciones_A_y_B"
        elif "tercera" in s_low or "contractual" in s_low or "antijuridico" in s_low:
            return "Seccion_Tercera_Contractual_y_Dano_Subsecciones_A_B_C"
        elif "cuarta" in s_low or "tributari" in s_low or "aduaner" in s_low or "financier" in s_low:
            return "Seccion_Cuarta_Tributaria_Financiera"
        elif "quinta" in s_low or "electoral" in s_low:
            return "Seccion_Quinta_Electoral"
        elif "consulta" in s_low or "servicio civil" in s_low:
            return "Sala_Consulta_y_Servicio_Civil"
        elif "primera" in s_low:
            return "Seccion_Primera_General_Ambiental"
        return default_fallback

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
        Descarga providencias del Consejo de Estado segmentadas con precisión por cada Sección en SAMAI.
        """
        session = requests.Session()
        session.headers.update(self.headers)

        # Determinar qué secciones explorar según los tipos seleccionados
        secciones_a_explorar = []
        tipos_upper = [t.upper() for t in tipos]

        if "ALL" in tipos_upper or not tipos:
            secciones_a_explorar = self.secciones_def
        else:
            for s_code, s_query, s_slug, s_label in self.secciones_def:
                if any(t in s_code.upper() or s_code.upper() in t for t in tipos_upper):
                    secciones_a_explorar.append((s_code, s_query, s_slug, s_label))
            if not secciones_a_explorar:
                secciones_a_explorar = self.secciones_def

        for ano in range(ano_fin, ano_inicio - 1, -1):
            if stop_event.is_set():
                break

            for s_code, s_query, s_slug, s_label in secciones_a_explorar:
                if stop_event.is_set():
                    break

                progress_callback({
                    "tipo_evento": "INFO",
                    "corte": self.name,
                    "ano": ano,
                    "tipo": s_slug,
                    "mensaje": f"Consultando providencias del Consejo de Estado ({s_label}) para el año {ano} en SAMAI..."
                })

                # 1. Cargar formulario inicial
                try:
                    r1 = session.get(self.base_url, timeout=15)
                    soup1 = BeautifulSoup(r1.text, "html.parser")
                    form_data = {inp.get("name"): inp.get("value", "") for inp in soup1.find_all("input") if inp.get("name")}
                except Exception as e:
                    progress_callback({
                        "tipo_evento": "ERROR",
                        "corte": self.name,
                        "ano": ano,
                        "tipo": s_slug,
                        "mensaje": f"No se pudo conectar al portal SAMAI ({s_label}): {e}"
                    })
                    continue

                # 2. Enviar búsqueda específica por Sección y Año
                form_data["__EVENTTARGET"] = "ctl00$MainContent$BusquedaRapidaLinkButton"
                form_data["__EVENTARGUMENT"] = ""
                form_data["ctl00$MainContent$BusquedaRapidaTextBox"] = f"{s_query} {ano}"

                try:
                    r2 = session.post(self.base_url, data=form_data, timeout=20)
                    soup2 = BeautifulSoup(r2.text, "html.parser")
                except Exception as e:
                    progress_callback({
                        "tipo_evento": "ERROR",
                        "corte": self.name,
                        "ano": ano,
                        "tipo": s_slug,
                        "mensaje": f"Error al ejecutar búsqueda SAMAI para {s_label} {ano}: {e}"
                    })
                    continue

                doc_buttons = soup2.find_all("a", id=re.compile(r"TitulacionesRepeater.*documentlink"))
                if not doc_buttons:
                    progress_callback({
                        "tipo_evento": "INFO",
                        "corte": self.name,
                        "ano": ano,
                        "tipo": s_slug,
                        "mensaje": f"No se registraron providencias para {s_label} en {ano}."
                    })
                    continue

                progress_callback({
                    "tipo_evento": "INFO",
                    "corte": self.name,
                    "ano": ano,
                    "tipo": s_slug,
                    "mensaje": f"Encontradas {len(doc_buttons)} providencias de {s_label} para el año {ano}. Iniciando descarga..."
                })

                current_inputs = {inp.get("name"): inp.get("value", "") for inp in soup2.find_all("input") if inp.get("name")}
                consecutivo = 1
                descargadas_seccion = 0

                for btn in doc_buttons:
                    if stop_event.is_set():
                        break

                    while pause_event.is_set():
                        if stop_event.is_set():
                            break
                        time.sleep(0.5)

                    btn_id = btn.get("id", "")
                    name_target = btn_id.replace("_", "$")

                    # Extraer contenedor padre completo que contiene "Núm. del proceso" y "Sala de decisión"
                    row_el = btn.find_parent("div", class_="row")
                    if not row_el or "proceso" not in row_el.text.lower():
                        curr = btn
                        while curr and curr.parent:
                            curr = curr.parent
                            if "núm. del proceso" in curr.text.lower() or "sala de decisión" in curr.text.lower():
                                row_el = curr
                                break

                    card_text = row_el.text if row_el else ""

                    # Extraer radicado oficial de 23 dígitos
                    rad_match = re.search(r'N[uú]m\.\s*del\s*proceso[:\s]+(\d{23})', card_text, re.I)
                    if not rad_match:
                        rad_match = re.search(r'\b(\d{23})\b', card_text)

                    if rad_match:
                        radicado = rad_match.group(1)
                    else:
                        int_match = re.search(r'Interno[:\s]+([0-9\-]+)', card_text, re.I)
                        if int_match:
                            radicado = f"CE-INT-{int_match.group(1).strip()}"
                        else:
                            radicado = f"CE-{s_code[:3]}-{ano}-{consecutivo:03d}"

                    # Extraer sala / sección
                    sala_match = re.search(r'Sala\s+de\s+decisi[oó]n[:\s]+([^\n\r]+)', card_text, re.I)
                    if sala_match:
                        seccion_raw = sala_match.group(1).strip()
                    else:
                        sec_fallback = re.search(r'(Secci[oó]n\s+(?:Primera|Segunda|Tercera|Cuarta|Quinta)|Sala\s+de\s+Consulta)', card_text, re.I)
                        seccion_raw = sec_fallback.group(1) if sec_fallback else s_label

                    seccion_slug = self._normalize_seccion(seccion_raw, default_fallback=s_slug)

                    # Extraer ponente
                    pon_match = re.search(r'Titular[:\s]+([^\n\r,;]{4,60})', card_text, re.I)
                    ponente = pon_match.group(1).strip() if pon_match else "Consejero Ponente"

                    # Extraer clase de proceso
                    clase_match = re.search(r'Clase\s+del\s+proceso[:\s]+([^\n\r]+)', card_text, re.I)
                    clase_proceso = clase_match.group(1).strip() if clase_match else "Contencioso Administrativo"

                    # Extraer fecha providencia
                    fec_match = re.search(r'Providencia\s+del[:\s]+([^\n\r]+)', card_text, re.I)
                    fecha_prov = fec_match.group(1).strip() if fec_match else str(ano)

                    canonical_url = f"https://samai.consejodeestado.gov.co/doc/{radicado}"

                    if sentencia_exists(canonical_url, radicado=radicado):
                        progress_callback({
                            "tipo_evento": "EXISTENTE",
                            "corte": self.name,
                            "radicado": radicado,
                            "ano": ano,
                            "tipo": seccion_slug,
                            "consecutivo": consecutivo,
                            "mensaje": f"{radicado} ({seccion_raw}) ya registrada en Drive."
                        })
                        consecutivo += 1
                        continue

                    progress_callback({
                        "tipo_evento": "PROBANDO",
                        "corte": self.name,
                        "radicado": radicado,
                        "ano": ano,
                        "tipo": seccion_slug,
                        "consecutivo": consecutivo,
                        "mensaje": f"Descargando {radicado} ({seccion_raw}, Ponente: {ponente})..."
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

                        # Consultar VerProvidencia
                        r_vp = session.get(vp_url, timeout=15)
                        vp_content_unescaped = html.unescape(r_vp.text)
                        blob_match = re.search(r'https://[a-zA-Z0-9_\-\.]+\.blob\.core\.windows\.net/[^\'\"\s\<\>]+', vp_content_unescaped)
                        if not blob_match:
                            consecutivo += 1
                            continue

                        blob_url = blob_match.group(0)

                        # Descargar PDF oficial
                        r_blob = session.get(blob_url, timeout=20)
                        if r_blob.status_code != 200 or len(r_blob.content) < 1000:
                            consecutivo += 1
                            continue

                        content_bytes = r_blob.content
                        consecutivo += 1
                        descargadas_seccion += 1

                        metadata = {
                            "radicado": radicado,
                            "magistrado_ponente": ponente,
                            "fecha_providencia": fecha_prov,
                            "expediente": radicado,
                            "tema": f"{clase_proceso} - {seccion_raw}",
                            "resuelve": "Fallo oficial del Consejo de Estado adjunto",
                            "url_origen": canonical_url
                        }

                        filename = f"{radicado}.pdf"
                        local_path, drive_link, drive_id = drive_manager.save_sentence_file(
                            corte=self.name,
                            ano=ano,
                            tipo=seccion_slug,
                            filename=filename,
                            content_bytes=content_bytes,
                            metadata=metadata
                        )

                        db_record = {
                            "corte": self.name,
                            "radicado": radicado,
                            "tipo": seccion_slug,
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
                            "tipo": seccion_slug,
                            "consecutivo": consecutivo,
                            "tamano_bytes": len(content_bytes),
                            "magistrado": metadata["magistrado_ponente"],
                            "drive_link": drive_link,
                            "archivo_local": local_path,
                            "mensaje": f"Descargada {radicado} en {seccion_slug} ({len(content_bytes)//1024} KB) en Google Drive."
                        })

                        time.sleep(settings.request_delay_seconds)

                    except Exception as ex:
                        print(f"Error procesando documento CE {radicado}: {ex}")
                        consecutivo += 1
                        continue

                progress_callback({
                    "tipo_evento": "SERIE_FINALIZADA",
                    "corte": self.name,
                    "ano": ano,
                    "tipo": s_slug,
                    "mensaje": f"Finalizada {s_label} ({ano}): {descargadas_seccion} providencias guardadas en Drive."
                })
