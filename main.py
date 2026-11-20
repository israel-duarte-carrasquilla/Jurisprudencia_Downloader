import os
from pathlib import Path
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.api import api_app
from backend.database import init_db
from backend.config import settings

# Inicializar Base de Datos SQLite
init_db()

# Directorio de archivos estáticos
STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Montar static files
api_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@api_app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Robot de Jurisprudencia Judicial activo. Interfaz web en preparación."}

if __name__ == "__main__":
    print(f"================================================================")
    print(f"  ROBOT DE JURISPRUDENCIA JUDICIAL & DESCARGA MASIVA A DRIVE   ")
    print(f"================================================================")
    print(f"  Servidor iniciado en: http://localhost:{settings.port}")
    print(f"  Carpeta destino Drive: {settings.drive_folder_path}")
    print(f"================================================================")
    uvicorn.run("main:api_app", host="127.0.0.1", port=settings.port, reload=False)
