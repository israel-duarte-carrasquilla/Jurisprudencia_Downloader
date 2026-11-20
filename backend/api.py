from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import json
import os

from backend.database import (
    get_stats,
    get_sentencias,
    get_config,
    set_config,
    get_db_connection
)
from backend.crawler_engine import crawler_engine
from backend.drive_manager import drive_manager
from backend.config import settings

api_app = FastAPI(title="Robot de Jurisprudencia Judicial", version="1.0.0")

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic para peticiones
class StartCrawlerRequest(BaseModel):
    corte: str = Field(default="Todas las Entidades")
    ano_inicio: int = Field(default=1991, ge=1991, le=2030)
    ano_fin: int = Field(default=2026, ge=1991, le=2030)
    tipos: List[str] = Field(default=["ALL"])

class UpdateConfigRequest(BaseModel):
    storage_mode: str
    drive_folder_path: str
    request_delay_seconds: float = 0.8

@api_app.get("/api/stats")
def read_stats():
    """Retorna métricas globales de la base de datos."""
    return get_stats()

@api_app.get("/api/status")
def read_status():
    """Retorna el estado en tiempo real del motor de rastreo."""
    return crawler_engine.get_status()

@api_app.get("/api/scheduler")
def read_scheduler():
    """Retorna la configuración y estado de la programación automática nocturna (3:00 AM)."""
    if hasattr(crawler_engine, "scheduler"):
        return crawler_engine.scheduler.get_info()
    return {"activo": False, "mensaje": "Programador no inicializado"}

@api_app.get("/api/logs")
def read_logs():
    """Retorna los eventos y logs recientes de la sesión."""
    return {"logs": crawler_engine.get_logs()}

@api_app.post("/api/crawler/start")
def start_crawler(req: StartCrawlerRequest):
    if req.ano_inicio > req.ano_fin:
        raise HTTPException(status_code=400, detail="El año de inicio no puede ser mayor al año de fin.")
    
    success, msg = crawler_engine.start(
        corte=req.corte,
        ano_inicio=req.ano_inicio,
        ano_fin=req.ano_fin,
        tipos=req.tipos
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}

@api_app.post("/api/crawler/pause")
def pause_crawler():
    success, msg = crawler_engine.pause()
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}

@api_app.post("/api/crawler/resume")
def resume_crawler():
    success, msg = crawler_engine.resume()
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}

@api_app.post("/api/crawler/stop")
def stop_crawler():
    success, msg = crawler_engine.stop()
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}

@api_app.get("/api/sentencias")
def list_sentencias(
    search: str = Query(default=""),
    corte: str = Query(default=""),
    tipo: str = Query(default=""),
    ano: Optional[int] = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0)
):
    rows = get_sentencias(
        search=search,
        corte=corte,
        tipo=tipo,
        ano=ano,
        limit=limit,
        offset=offset
    )
    return {"items": rows, "count": len(rows), "offset": offset, "limit": limit}

@api_app.get("/api/sentencias/{sentencia_id}/file")
def download_sentencia_file(sentencia_id: int, format: str = Query(default="htm")):
    """
    Descarga la providencia en el formato solicitado:
    format = 'htm' (original), 'pdf' (documento PDF), 'md' (Markdown), 'json' (metadatos).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT archivo_local, radicado FROM sentencias WHERE id = ?", (sentencia_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row["archivo_local"]:
        raise HTTPException(status_code=404, detail="Sentencia no encontrada en la base de datos.")
        
    orig_path = Path(row["archivo_local"])
    target_path = orig_path
    
    fmt = format.lower()
    if fmt == "pdf":
        target_path = orig_path.with_suffix(".pdf")
    elif fmt == "md":
        target_path = orig_path.with_suffix(".md")
    elif fmt == "json":
        target_path = orig_path.with_suffix(".json")

    if not target_path.exists():
        # Si el formato derivado aún no existe, servir el original
        target_path = orig_path

    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Archivo {target_path.name} no encontrado en Drive.")
        
    media_types = {
        ".pdf": "application/pdf",
        ".md": "text/markdown; charset=utf-8",
        ".htm": "text/html; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".json": "application/json; charset=utf-8"
    }
    media_type = media_types.get(target_path.suffix.lower(), "application/octet-stream")
    return FileResponse(path=str(target_path), filename=target_path.name, media_type=media_type)

@api_app.get("/api/config")
def read_config():
    return {
        "storage_mode": drive_manager.storage_mode,
        "drive_folder_path": str(drive_manager.local_drive_path),
        "user_account_email": drive_manager.user_account,
        "shared_folder_url": settings.shared_folder_url,
        "request_delay_seconds": settings.request_delay_seconds,
        "save_formats": settings.save_formats,
        "enabled_courts": settings.enabled_courts
    }


@api_app.post("/api/config")
def update_config(req: UpdateConfigRequest):
    drive_manager.update_settings(req.storage_mode, req.drive_folder_path)
    settings.request_delay_seconds = req.request_delay_seconds
    return {"ok": True, "message": "Configuración guardada exitosamente."}

@api_app.post("/api/drive/test")
def test_drive():
    result = drive_manager.test_connection()
    return result

# ===============================================================
# ENDPOINTS DEL BUSCADOR APOYADO CON INTELIGENCIA ARTIFICIAL (IA)
# ===============================================================
class AISearchRequest(BaseModel):
    query: str
    api_key: Optional[str] = None
    limit: int = 15

@api_app.post("/api/ai/search")
def ai_search(req: AISearchRequest):
    """
    Buscador asistido por IA:
    1. Analiza y detecta la intención y especialidad jurídica (Civil, Familia, Penal, etc.).
    2. Realiza ranking semántico de las providencias disponibles.
    3. Genera síntesis jurídica con citas exactas (vía Gemini LLM si hay API Key o motor local NLP).
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="La consulta jurídica no puede estar vacía.")
        
    from backend.ai_search import ai_search_engine
    
    # 1. Búsqueda y ranking semántico
    ranked_results = ai_search_engine.search_and_rank(req.query, limit=req.limit)
    
    # 2. Generación de síntesis jurídica asistida
    synthesis = ai_search_engine.generate_ai_legal_synthesis(
        query=req.query,
        results=ranked_results,
        api_key=req.api_key
    )
    
    return synthesis

@api_app.post("/api/ai/analyze-sentence/{sentencia_id}")
def ai_analyze_sentence(sentencia_id: int):
    """Genera una Ficha Jurisprudencial de IA y la respalda en Google Drive."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sentencias WHERE id = ?", (sentencia_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Sentencia no encontrada.")
        
    s = dict(row)
    radicado = s.get("radicado", "S_R")
    
    # Guardar Ficha Jurisprudencial en Drive
    fichas_dir = drive_manager.local_drive_path / "06_Indices_y_Metadatos_IA" / "Fichas_Jurisprudenciales"
    fichas_dir.mkdir(parents=True, exist_ok=True)
    
    ficha_md_path = fichas_dir / f"Ficha_{radicado}.md"
    ficha_json_path = fichas_dir / f"Ficha_{radicado}.json"
    
    ficha_data = {
        "radicado": radicado,
        "corte": s.get("corte"),
        "ano": s.get("ano"),
        "tipo": s.get("tipo"),
        "magistrado_ponente": s.get("magistrado_ponente"),
        "fecha": s.get("fecha_providencia"),
        "expediente": s.get("expediente"),
        "sintesis_tema": s.get("tema"),
        "decision_resuelve": s.get("resuelve"),
        "archivo_asociado": s.get("archivo_local"),
        "generado_el": datetime.now().isoformat()
    }
    
    with open(ficha_json_path, "w", encoding="utf-8") as f:
        json.dump(ficha_data, f, ensure_ascii=False, indent=2)
        
    with open(ficha_md_path, "w", encoding="utf-8") as f:
        f.write(f"# FICHA JURISPRUDENCIAL IA - {radicado}\n\n")
        f.write(f"- **Entidad:** {s.get('corte')}\n")
        f.write(f"- **Año:** {s.get('ano')}\n")
        f.write(f"- **Magistrado Ponente:** {s.get('magistrado_ponente')}\n")
        f.write(f"- **Fecha:** {s.get('fecha_providencia')}\n")
        f.write(f"- **Expediente:** {s.get('expediente')}\n\n")
        f.write(f"## SÍNTESIS DEL CASO\n{s.get('tema')}\n\n")
        f.write(f"## DECISIÓN / RATIO DECIDENDI\n{s.get('resuelve')}\n")
        
    return {
        "ok": True,
        "radicado": radicado,
        "ficha_md": str(ficha_md_path),
        "ficha_json": str(ficha_json_path),
        "data": ficha_data
    }

@api_app.get("/api/taxonomy")
def get_taxonomy():
    """Devuelve la estructura de carpetas por Salas Especializadas y el recuento de archivos."""
    from backend.setup_taxonomy import TAXONOMIA_SALAS_ESPECIALIZADAS, TARGET_ACCOUNT_EMAIL
    base_path = drive_manager.local_drive_path
    
    structure = []
    for entidad, data in TAXONOMIA_SALAS_ESPECIALIZADAS.items():
        entidad_dir = base_path / entidad
        salas_list = []
        for s_key, s_desc in data["salas"].items():
            sala_dir = entidad_dir / s_key
            file_count = 0
            if sala_dir.exists():
                file_count = sum(len(files) for _, _, files in os.walk(sala_dir))
            salas_list.append({
                "nombre": s_key,
                "label": s_key.replace("_", " "),
                "descripcion": s_desc,
                "archivos": file_count,
                "path": str(sala_dir)
            })
            
        structure.append({
            "entidad": entidad,
            "label": entidad.replace("_", " "),
            "descripcion": data["descripcion"],
            "subcarpetas": salas_list
        })
        
    return {
        "base_path": str(base_path),
        "drive_user": TARGET_ACCOUNT_EMAIL,
        "taxonomia": structure
    }


