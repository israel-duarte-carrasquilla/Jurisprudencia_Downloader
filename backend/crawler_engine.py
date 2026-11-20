import threading
import time
from datetime import datetime
from collections import deque
from typing import Dict, Any, List, Optional
from backend.scrapers import get_scraper
from backend.database import get_db_connection

class CrawlerEngine:
    def __init__(self):
        self.is_running = False
        self.is_paused = False
        self.current_job_id: Optional[int] = None
        
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None

        # Métricas de sesión
        self.stats = {
            "estado": "DETENIDO",  # DETENIDO, EJECUTANDO, PAUSADO, FINALIZADO
            "corte": "",
            "ano_actual": 0,
            "tipo_actual": "",
            "radicado_actual": "",
            "consecutivo_actual": 0,
            "total_exploradas": 0,
            "descargadas_sesion": 0,
            "existentes_sesion": 0,
            "errores_sesion": 0,
            "bytes_descargados_sesion": 0,
            "iniciado_en": None,
            "ultimo_mensaje": "Robot listo para iniciar."
        }

        # Búfer circular para logs en vivo (últimos 150 eventos)
        self.logs_buffer = deque(maxlen=150)
        self.lock = threading.RLock()

    def add_log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "message": message,
            "extra": extra or {}
        }
        with self.lock:
            self.logs_buffer.append(entry)
            self.stats["ultimo_mensaje"] = message

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            status = dict(self.stats)
            status["is_running"] = self.is_running
            status["is_paused"] = self.is_paused
            return status

    def get_logs(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.logs_buffer)

    def start(self, corte: str, ano_inicio: int, ano_fin: int, tipos: List[str]):
        if self.is_running:
            return False, "Ya hay una tarea de descarga en ejecución."

        self.stop_event.clear()
        self.pause_event.clear()
        self.is_running = True
        self.is_paused = False

        is_all_entities = (corte.strip().lower() in ["todas las entidades", "todas", "todas las cortes", "all"])

        self.stats.update({
            "estado": "EJECUTANDO",
            "corte": "Todas las Entidades" if is_all_entities else corte,
            "descargadas_sesion": 0,
            "existentes_sesion": 0,
            "errores_sesion": 0,
            "bytes_descargados_sesion": 0,
            "iniciado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ultimo_mensaje": f"Iniciando descarga global en todas las entidades ({ano_inicio} - {ano_fin})..." if is_all_entities else f"Iniciando descarga masiva de {corte} ({ano_inicio} - {ano_fin})..."
        })

        if is_all_entities:
            self.add_log("INFO", f"Comenzando rastreo global para TODAS las entidades (Corte Constitucional, Corte Suprema, Consejo de Estado, Secretaría del Senado, 10 Superintendencias, Laudos Arbitrales, Tribunales Departamentales e ICDP) años {ano_inicio} a {ano_fin}")
        else:
            self.add_log("INFO", f"Comenzando rastreo de {corte} para los años {ano_inicio} a {ano_fin} con tipos {tipos}")

        def run_worker():
            try:
                if is_all_entities:
                    cortes_plan = [
                        ("Corte Constitucional", ["C", "T", "SU", "A"]),
                        ("Corte Suprema de Justicia", ["Civil", "Laboral", "Penal", "Descongestion", "PrimeraInstancia", "Instruccion", "Tutelas"]),
                        ("Consejo de Estado", ["Plena", "SalasEspeciales", "Segunda", "Tercera", "Cuarta", "Primera", "Quinta", "Consulta"]),
                        ("Secretaría del Senado", ["Leyes", "Codigos", "Actos"]),
                        ("Superintendencias", ["ALL"]),
                        ("Laudos Arbitrales", ["Bogota", "Barranquilla", "Medellin", "Cali"]),
                        ("Tribunales Departamentales", ["Atlantico", "Antioquia", "Cundinamarca", "Valle", "Santander", "Bolivar", "Magdalena", "Boyaca", "Caldas", "Meta"]),
                        ("Instituto Colombiano de Derecho Procesal (ICDP)", ["Intervenciones", "Doctrina", "Compendios"])
                    ]
                    for nombre_corte, default_tipos in cortes_plan:
                        if self.stop_event.is_set():
                            break
                        with self.lock:
                            self.stats["corte"] = nombre_corte
                        self.add_log("INFO", f"🏛️ [DESCARGA GLOBAL] Iniciando rastreo de: {nombre_corte}...")
                        try:
                            scraper = get_scraper(nombre_corte)
                            scraper.crawl_range(
                                ano_inicio=ano_inicio,
                                ano_fin=ano_fin,
                                tipos=default_tipos,
                                stop_event=self.stop_event,
                                pause_event=self.pause_event,
                                progress_callback=self._on_progress
                            )
                        except Exception as e_corte:
                            self.add_log("ERROR", f"Error en rastreo de {nombre_corte}: {e_corte}")
                            continue

                    if self.stop_event.is_set():
                        self.add_log("WARNING", "Proceso global cancelado por el usuario.")
                        self.stats["estado"] = "DETENIDO"
                    else:
                        self.add_log("SUCCESS", "¡Rastreo masivo global completado exitosamente para todas las entidades!")
                        self.stats["estado"] = "FINALIZADO"
                else:
                    scraper = get_scraper(corte)
                    scraper.crawl_range(
                        ano_inicio=ano_inicio,
                        ano_fin=ano_fin,
                        tipos=tipos,
                        stop_event=self.stop_event,
                        pause_event=self.pause_event,
                        progress_callback=self._on_progress
                    )
                    if self.stop_event.is_set():
                        self.add_log("WARNING", "Proceso de descarga cancelado por el usuario.")
                        self.stats["estado"] = "DETENIDO"
                    else:
                        self.add_log("SUCCESS", "¡Rastreo masivo finalizado exitosamente!")
                        self.stats["estado"] = "FINALIZADO"
            except Exception as e:
                self.add_log("ERROR", f"Error crítico en el proceso de descarga: {str(e)}")
                self.stats["estado"] = "ERROR"
            finally:
                self.is_running = False
                self.is_paused = False

        self.worker_thread = threading.Thread(target=run_worker, daemon=True)
        self.worker_thread.start()
        return True, "Proceso iniciado correctamente."

    def pause(self):
        if not self.is_running:
            return False, "No hay ningún proceso activo para pausar."
        self.is_paused = True
        self.pause_event.set()
        self.stats["estado"] = "PAUSADO"
        self.add_log("INFO", "Proceso pausado temporalmente.")
        return True, "Proceso pausado."

    def resume(self):
        if not self.is_running or not self.is_paused:
            return False, "El proceso no está en pausa."
        self.is_paused = False
        self.pause_event.clear()
        self.stats["estado"] = "EJECUTANDO"
        self.add_log("INFO", "Proceso reanudado.")
        return True, "Proceso reanudado."

    def stop(self):
        if not self.is_running:
            return False, "No hay ningún proceso activo para detener."
        self.stop_event.set()
        self.pause_event.clear()
        self.is_running = False
        self.is_paused = False
        self.stats["estado"] = "DETENIDO"
        self.add_log("WARNING", "Detención solicitada. Finalizando operaciones pendientes...")
        return True, "Proceso detenido."

    def _on_progress(self, event: Dict[str, Any]):
        tipo = event.get("tipo_evento", "")
        with self.lock:
            # Mantener actualizados siempre el radicado y corporación en curso
            if "radicado" in event:
                self.stats["radicado_actual"] = event["radicado"]
            if "ano" in event:
                self.stats["ano_actual"] = event["ano"]
            if "tipo" in event:
                self.stats["tipo_actual"] = event["tipo"]
            if "consecutivo" in event:
                self.stats["consecutivo_actual"] = event["consecutivo"]

            if tipo == "DESCARGADA":
                self.stats["descargadas_sesion"] += 1
                self.stats["total_exploradas"] += 1
                self.stats["bytes_descargados_sesion"] += event.get("tamano_bytes", 0)
                self.add_log("SUCCESS", event.get("mensaje", ""), event)
            elif tipo == "EXISTENTE":
                self.stats["existentes_sesion"] += 1
                self.stats["total_exploradas"] += 1
                self.add_log("INFO", event.get("mensaje", ""), event)
            elif tipo == "PROBANDO":
                self.stats["total_exploradas"] += 1
                self.stats["ultimo_mensaje"] = event.get("mensaje", "")
            elif tipo == "NO_ENCONTRADA":
                self.add_log("INFO", event.get("mensaje", ""), event)
            elif tipo == "SERIE_FINALIZADA":
                self.add_log("INFO", event.get("mensaje", ""), event)
            elif tipo == "ERROR":
                self.stats["errores_sesion"] += 1
                self.add_log("ERROR", event.get("mensaje", ""), event)
            else:
                self.add_log("INFO", event.get("mensaje", ""), event)

class NightlyScheduler:
    """Programador de tareas en segundo plano que ejecuta la descarga global cada madrugada a las 02:00 AM (Legal Jurisprudence AI - 1991 a la fecha)."""
    def __init__(self, engine: CrawlerEngine):
        self.engine = engine
        self.target_hour = 2        # 02:00 AM
        self.target_minute = 0
        self.start_year = 1991      # Constitución Política de 1991 a la fecha
        self.enabled = True
        self.last_run_date = None
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="NightlyAutoCrawlerThread")
        self.thread.start()

    def _run_loop(self):
        while True:
            try:
                if self.enabled:
                    now = datetime.now()
                    today = now.date()
                    if now.hour == self.target_hour and now.minute == self.target_minute and self.last_run_date != today:
                        if not self.engine.is_running:
                            self.last_run_date = today
                            current_year = now.year
                            self.engine.add_log("INFO", f"⏰ [PROGRAMACIÓN NOCTURNA 02:00 AM - LEGAL JURISPRUDENCE AI] Iniciando descarga automática masiva en TODAS LAS ENTIDADES ({self.start_year} - {current_year})...")
                            self.engine.start(corte="Todas las Entidades", ano_inicio=self.start_year, ano_fin=current_year, tipos=["ALL"])
            except Exception as e:
                print(f"Error en bucle de programador nocturno: {e}")
            time.sleep(25)

    def get_info(self) -> Dict[str, Any]:
        now = datetime.now()
        is_before_2am = (now.hour < self.target_hour) or (now.hour == self.target_hour and now.minute < self.target_minute)
        next_run = "Hoy a las 02:00 AM" if is_before_2am else "Mañana a las 02:00 AM"
        return {
            "activo": self.enabled,
            "hora_programada": "02:00 AM",
            "rango_anos": f"{self.start_year} - {now.year}",
            "entidades": "Todas las Entidades (Cortes, Superintendencias, Laudos, Senado, Tribunales e ICDP)",
            "metodologia": "Legal Jurisprudence AI (El Juez de la IA) - Corpora 1991 a la fecha",
            "ultima_ejecucion": str(self.last_run_date) if self.last_run_date else "Pendiente para próxima madrugada",
            "proxima_ejecucion": next_run
        }

crawler_engine = CrawlerEngine()
crawler_engine.scheduler = NightlyScheduler(crawler_engine)
