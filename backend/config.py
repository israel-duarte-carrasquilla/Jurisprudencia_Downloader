import os
from pathlib import Path
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DB_PATH = BASE_DIR / "jurisprudencia.db"

def detect_google_drive_path() -> str:
    """Detecta la carpeta oficial 'jurisprudencia' en Google Drive (Israel.Duarte.Carrasquilla@gmail.com)."""
    primary_m = r"M:\Mi unidad\jurisprudencia"
    if os.path.exists(r"M:\Mi unidad"):
        os.makedirs(primary_m, exist_ok=True)
        return primary_m

    # Alternativas por si en Windows cambia la letra de unidad asignada
    for drive in [r"M:\\", r"I:\\", r"J:\\", r"G:\\"]:
        target_dir = os.path.join(drive, "Mi unidad", "jurisprudencia")
        if os.path.exists(os.path.join(drive, "Mi unidad")):
            os.makedirs(target_dir, exist_ok=True)
            return target_dir

    return str(DOWNLOADS_DIR / "jurisprudencia")



class Settings:
    def __init__(self):
        self.app_name: str = "JurisprudenciaBot Colombia"
        self.user_account_email: str = "Israel.Duarte.Carrasquilla@gmail.com"
        self.shared_folder_url: str = "https://drive.google.com/drive/folders/1Wy9jIetIcQ4vw0R-IeafGC7-8GGDaaIZ?usp=sharing"
        self.shared_folder_id: str = "1Wy9jIetIcQ4vw0R-IeafGC7-8GGDaaIZ"
        self.host: str = "127.0.0.1"
        self.port: int = 8000
        
        # Almacenamiento
        self.storage_mode: str = "local_drive"  # 'local_drive' sincronizada con Google Drive
        self.drive_folder_path: str = detect_google_drive_path()
        self.google_drive_folder_id: Optional[str] = "1Wy9jIetIcQ4vw0R-IeafGC7-8GGDaaIZ"
        
        # Parámetros por defecto de descarga
        self.max_workers: int = 3
        self.request_delay_seconds: float = 0.3
        self.max_consecutive_errors: int = 35  # para detectar fin de sentencias de un año (ej: sentencias C arrancan en 015 o 022)
        self.timeout_seconds: int = 5
        
        # Formatos obligatorios de guardado
        self.save_formats: List[str] = ["htm", "pdf", "md", "json"]


        
        # Cortes habilitadas
        self.enabled_courts: List[str] = [
            "Corte Constitucional",
            "Corte Suprema de Justicia",
            "Consejo de Estado"
        ]

settings = Settings()
