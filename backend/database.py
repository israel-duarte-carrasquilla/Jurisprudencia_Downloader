import sqlite3
import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.config import DB_PATH

# Cache en memoria de alta velocidad para verificación instantánea O(1)
_CACHE_LOCK = threading.Lock()
_KNOWN_URLS: set = set()
_KNOWN_RADICADOS: set = set()
_CACHE_LOADED = False

def ensure_cache_loaded():
    """Carga los identificadores conocidos en memoria RAM para evitar consultas y lecturas repetidas a disco."""
    global _CACHE_LOADED, _KNOWN_URLS, _KNOWN_RADICADOS
    if not _CACHE_LOADED:
        with _CACHE_LOCK:
            if not _CACHE_LOADED:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT url_origen, radicado FROM sentencias")
                    rows = cursor.fetchall()
                    _KNOWN_URLS = {r['url_origen'] for r in rows if r['url_origen']}
                    _KNOWN_RADICADOS = {str(r['radicado']).strip().lower() for r in rows if r['radicado']}
                    conn.close()
                    _CACHE_LOADED = True
                except Exception as e:
                    print(f"Advertencia al precargar cache de sentencias: {e}")

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla de sentencias judiciales
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sentencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corte TEXT NOT NULL,
            radicado TEXT NOT NULL,
            tipo TEXT NOT NULL,
            ano INTEGER NOT NULL,
            consecutivo INTEGER NOT NULL,
            magistrado_ponente TEXT,
            fecha_providencia TEXT,
            expediente TEXT,
            tema TEXT,
            resuelve TEXT,
            url_origen TEXT NOT NULL UNIQUE,
            archivo_local TEXT,
            tamano_bytes INTEGER DEFAULT 0,
            estado TEXT DEFAULT 'DESCARGADO',
            drive_link TEXT,
            drive_file_id TEXT,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sentencias_radicado ON sentencias(radicado)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sentencias_url ON sentencias(url_origen)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sentencias_corte ON sentencias(corte)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sentencias_ano_tipo ON sentencias(ano, tipo)')

    # Tabla de trabajos de crawling (histórico)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crawler_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corte TEXT NOT NULL,
            ano_inicio INTEGER NOT NULL,
            ano_fin INTEGER NOT NULL,
            tipos_json TEXT NOT NULL,
            estado TEXT DEFAULT 'EN_PROGRESO', -- 'EN_PROGRESO', 'PAUSADO', 'COMPLETADO', 'DETENIDO', 'ERROR'
            total_procesadas INTEGER DEFAULT 0,
            total_descargadas INTEGER DEFAULT 0,
            total_existentes INTEGER DEFAULT 0,
            total_errores INTEGER DEFAULT 0,
            mensaje_actual TEXT,
            iniciado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finalizado_en TIMESTAMP
        )
    ''')

    # Tabla de configuraciones persistentes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_config (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL,
            actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_sentencia(data: Dict[str, Any]) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO sentencias (
            corte, radicado, tipo, ano, consecutivo,
            magistrado_ponente, fecha_providencia, expediente,
            tema, resuelve, url_origen, archivo_local,
            tamano_bytes, estado, drive_link, drive_file_id
        ) VALUES (
            :corte, :radicado, :tipo, :ano, :consecutivo,
            :magistrado_ponente, :fecha_providencia, :expediente,
            :tema, :resuelve, :url_origen, :archivo_local,
            :tamano_bytes, :estado, :drive_link, :drive_file_id
        )
        ON CONFLICT(url_origen) DO UPDATE SET
            magistrado_ponente = excluded.magistrado_ponente,
            fecha_providencia = excluded.fecha_providencia,
            expediente = excluded.expediente,
            tema = excluded.tema,
            resuelve = excluded.resuelve,
            archivo_local = excluded.archivo_local,
            tamano_bytes = excluded.tamano_bytes,
            estado = excluded.estado,
            drive_link = COALESCE(excluded.drive_link, sentencias.drive_link),
            drive_file_id = COALESCE(excluded.drive_file_id, sentencias.drive_file_id),
            actualizado_en = CURRENT_TIMESTAMP
    ''', data)
    
    last_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Actualizar inmediatamente la caché en memoria RAM
    with _CACHE_LOCK:
        if data.get("url_origen"):
            _KNOWN_URLS.add(data["url_origen"])
        if data.get("radicado"):
            _KNOWN_RADICADOS.add(str(data["radicado"]).strip().lower())

    return last_id

def sentencia_exists(url_origen: str, radicado: Optional[str] = None) -> bool:
    """
    Verifica instantáneamente en memoria O(1) si la providencia ya está descargada en base de datos.
    No requiere consultas repetidas a disco ni apertura continua de conexiones.
    """
    ensure_cache_loaded()
    if url_origen and url_origen in _KNOWN_URLS:
        return True
    if radicado and str(radicado).strip().lower() in _KNOWN_RADICADOS:
        return True
    return False

def get_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM sentencias")
    total_sentencias = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(tamano_bytes) FROM sentencias")
    total_bytes = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM sentencias WHERE drive_link IS NOT NULL OR estado = 'SUBIDO_DRIVE'")
    en_drive = cursor.fetchone()[0]
    
    cursor.execute("SELECT tipo, COUNT(*) as count FROM sentencias GROUP BY tipo")
    por_tipo = {row['tipo']: row['count'] for row in cursor.fetchall()}
    
    cursor.execute("SELECT ano, COUNT(*) as count FROM sentencias GROUP BY ano ORDER BY ano DESC")
    por_ano = {row['ano']: row['count'] for row in cursor.fetchall()}
    
    cursor.execute("SELECT corte, COUNT(*) as count FROM sentencias GROUP BY corte")
    por_corte = {row['corte']: row['count'] for row in cursor.fetchall()}

    conn.close()
    
    return {
        "total_sentencias": total_sentencias,
        "total_bytes": total_bytes,
        "total_megabytes": round(total_bytes / (1024 * 1024), 2),
        "en_drive": en_drive,
        "por_tipo": por_tipo,
        "por_ano": por_ano,
        "por_corte": por_corte
    }

def get_sentencias(
    search: str = "",
    corte: str = "",
    tipo: str = "",
    ano: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM sentencias WHERE 1=1"
    params = []
    
    if search:
        query += " AND (radicado LIKE ? OR magistrado_ponente LIKE ? OR tema LIKE ? OR expediente LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])
    if corte:
        query += " AND corte = ?"
        params.append(corte)
    if tipo:
        query += " AND tipo = ?"
        params.append(tipo)
    if ano:
        query += " AND ano = ?"
        params.append(ano)
        
    query += " ORDER BY ano DESC, consecutivo DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def set_config(key: str, value: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO app_config (clave, valor, actualizado_en)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor, actualizado_en = CURRENT_TIMESTAMP
    ''', (key, value))
    conn.commit()
    conn.close()

def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM app_config WHERE clave = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return default

# Inicializar tablas automáticamente al importar
init_db()

