import re
import os
from typing import Dict, Any, Optional
from pathlib import Path
import markdownify
import pymupdf

def clean_html_for_conversion(html_text: str) -> str:
    """Elimina scripts, estilos, comentarios y basura antes de convertir."""
    # Eliminar scripts y estilos
    cleaned = re.sub(r'<script[\s\S]*?</script>', '', html_text, flags=re.IGNORECASE)
    cleaned = re.sub(r'<style[\s\S]*?</style>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<!--[\s\S]*?-->', '', cleaned)
    return cleaned

def convert_to_markdown(html_text: str, metadata: Dict[str, Any]) -> str:
    """Convierte el documento a un formato Markdown estructurado y profesional."""
    cleaned_html = clean_html_for_conversion(html_text)
    body_md = markdownify.markdownify(
        cleaned_html,
        heading_style="ATX",
        strip=["script", "style", "head", "meta", "link"],
        bullets="-"
    )
    
    # Limpiar saltos de línea excesivos
    body_md = re.sub(r'\n{3,}', '\n\n', body_md).strip()

    radicado = metadata.get("radicado", "S/R")
    corte = metadata.get("corte", "Rama Judicial")
    sala = metadata.get("sala_especializada", "Sala Especializada")
    mp = metadata.get("magistrado_ponente", "No registrado")
    fecha = metadata.get("fecha_providencia", "N/A")
    expediente = metadata.get("expediente", "N/A")
    tema = metadata.get("tema", "Sin extracto registrado")
    resuelve = metadata.get("resuelve", "")
    drive_user = metadata.get("drive_user", "Israel.Duarte.Carrasquilla@gmail.com")

    header_md = f"""# REPÚBLICA DE COLOMBIA • RAMA JUDICIAL
## {corte.upper()}
### {sala.upper()}
# Sentencia {radicado}

---

### 📋 Ficha Técnica de la Providencia

| Atributo | Detalle |
| :--- | :--- |
| **Número de Providencia** | `{radicado}` |
| **Corporación Judicial** | {corte} |
| **Sala Especializada** | **{sala}** |
| **Magistrado(a) Ponente** | {mp} |
| **Fecha de Providencia** | {fecha} |
| **Número de Expediente** | {expediente} |
| **Custodia Google Drive** | `{drive_user}` |

---

### ⚖️ Síntesis del Asunto / Asunto Jurídico
> {tema}

"""
    if resuelve:
        header_md += f"""### 📌 Resuelve / Decisión
> {resuelve}

---

"""

    header_md += "## 📖 TEXTO COMPLETO DE LA PROVIDENCIA\n\n"
    return header_md + body_md

def convert_to_pdf(markdown_content: str, metadata: Dict[str, Any], output_pdf_path: Path):
    """
    Genera un documento PDF estructurado y legible utilizando PyMuPDF.
    Ajusta márgenes, encabezados de la Rama Judicial y saltos de página.
    """
    doc = pymupdf.open()
    
    # Extraer texto plano formateado del markdown
    plain_text = markdown_content
    # Reemplazar encabezados markdown para visualización limpia
    plain_text = re.sub(r'#+\s*', '', plain_text)
    plain_text = plain_text.replace('**', '').replace('`', '').replace('> ', '  » ')

    # Configuración de página A4 / Carta
    page_rect = pymupdf.Rect(0, 0, 612, 792)  # Carta (Letter)
    margin = 54  # 0.75 pulgadas
    text_rect = pymupdf.Rect(margin, margin + 40, page_rect.width - margin, page_rect.height - margin - 30)

    # Dividir texto en párrafos para fluir entre páginas
    paragraphs = plain_text.split('\n')
    current_page = doc.new_page(width=page_rect.width, height=page_rect.height)
    
    # Encabezado institucional en primera página
    current_page.draw_rect(
        pymupdf.Rect(margin, margin - 15, page_rect.width - margin, margin + 25),
        color=(0.1, 0.2, 0.4),
        fill=(0.95, 0.97, 1.0)
    )
    current_page.insert_text(
        pymupdf.Point(margin + 10, margin + 5),
        f"RAMA JUDICIAL • {metadata.get('corte', '').upper()} • {metadata.get('sala_especializada', '').upper()}",
        fontsize=8.5,
        fontname="helv",
        color=(0.1, 0.2, 0.4)
    )
    current_page.insert_text(
        pymupdf.Point(margin + 10, margin + 18),
        f"PROVIDENCIA {metadata.get('radicado', '')} • GOOGLE DRIVE: Israel.Duarte.Carrasquilla@gmail.com",
        fontsize=7.5,
        fontname="helv",
        color=(0.3, 0.3, 0.3)
    )

    y = margin + 45
    line_height = 13
    font_size = 9.5
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            y += line_height * 0.7
            continue

        # Si el párrafo es muy largo, envolver por líneas
        words = para.split(' ')
        current_line = []
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            # Aproximación de ancho de texto
            if len(test_line) > 95:
                # Escribir línea previa
                if y > text_rect.y1:
                    current_page = doc.new_page(width=page_rect.width, height=page_rect.height)
                    y = margin + 30
                current_page.insert_text(
                    pymupdf.Point(margin, y),
                    ' '.join(current_line[:-1]),
                    fontsize=font_size,
                    fontname="helv"
                )
                y += line_height
                current_line = [word]

        if current_line:
            if y > text_rect.y1:
                current_page = doc.new_page(width=page_rect.width, height=page_rect.height)
                y = margin + 30
            current_page.insert_text(
                pymupdf.Point(margin, y),
                ' '.join(current_line),
                fontsize=font_size,
                fontname="helv"
            )
            y += line_height

    # Añadir número de página en pie de cada hoja
    total_pages = len(doc)
    for idx, page in enumerate(doc, 1):
        footer_text = f"Página {idx} de {total_pages} • Providencia {metadata.get('radicado', '')}"
        page.insert_text(
            pymupdf.Point(page_rect.width / 2 - 50, page_rect.height - margin + 10),
            footer_text,
            fontsize=8,
            fontname="helv",
            color=(0.5, 0.5, 0.5)
        )

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_pdf_path))
    doc.close()
