from pathlib import Path
from backend.database import get_db_connection
from backend.drive_manager import drive_manager

def migrate_existing_sentences():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM sentencias").fetchall()
    print(f"Generando copias en PDF, MD y JSON para {len(rows)} sentencias...")

    for r in rows:
        s = dict(r)
        radicado = s["radicado"]
        file_path, sala = drive_manager.get_destination_info(s["corte"], s["ano"], s["tipo"], f"{radicado}.htm")
        print(f"Procesando {radicado} -> Sala: {sala}")

        orig = s.get("archivo_local")
        content = b""
        if orig and Path(orig).exists():
            with open(orig, "rb") as f:
                content = f.read()
        else:
            dummy_html = f"<html><body><h1>{radicado}</h1><p>{s.get('tema', '')}</p><p>{s.get('resuelve', '')}</p></body></html>"
            content = dummy_html.encode("utf-8")

        new_path, drive_link, drive_id = drive_manager.save_sentence_file(
            corte=s["corte"],
            ano=s["ano"],
            tipo=s["tipo"],
            filename=f"{radicado}.htm",
            content_bytes=content,
            metadata=s
        )

        conn.execute("UPDATE sentencias SET archivo_local = ? WHERE id = ?", (str(file_path), s["id"]))

    conn.commit()
    conn.close()
    print("¡Migración y generación multi-formato completada exitosamente!")

if __name__ == "__main__":
    migrate_existing_sentences()
