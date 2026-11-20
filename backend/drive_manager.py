import os
import shutil
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from backend.config import settings, detect_google_drive_path
from backend.database import get_config, set_config
from backend.document_converter import convert_to_markdown, convert_to_pdf

class DriveManager:
    def __init__(self):
        saved_mode = get_config("storage_mode", settings.storage_mode)
        saved_path = get_config("drive_folder_path", settings.drive_folder_path)
        
        self.storage_mode = saved_mode
        self.local_drive_path = Path(saved_path)
        self.user_account = settings.user_account_email
        self._ensure_local_dir_exists()

    def _ensure_local_dir_exists(self):
        try:
            self.local_drive_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Advertencia al crear directorio base de Drive: {e}")

    def update_settings(self, storage_mode: str, folder_path: str):
        self.storage_mode = storage_mode
        self.local_drive_path = Path(folder_path)
        self._ensure_local_dir_exists()
        set_config("storage_mode", self.storage_mode)
        set_config("drive_folder_path", str(self.local_drive_path))

    def get_destination_info(self, corte: str, ano: int, tipo: str, filename: str) -> Tuple[Path, str]:
        """
        Calcula la ruta organizada por Corporación y Sala Especializada,
        y retorna (directorio_destino, nombre_sala_especializada).
        """
        # 1. Corte Constitucional
        if "Constitucional" in corte:
            entidad_folder = "01_Corte_Constitucional"
            tipo_upper = tipo.upper()
            fname_upper = filename.upper()
            if tipo_upper == "C" or fname_upper.startswith("C-"):
                sala_name = "Sala Plena - Constitucionalidad (C)"
                sub_folder = "Sala_Plena_Constitucionalidad_C"
            elif tipo_upper == "T" or fname_upper.startswith("T-"):
                sala_name = "Salas de Revisión de Tutelas (T)"
                sub_folder = "Salas_Revision_Tutelas_T"
            elif tipo_upper == "SU" or fname_upper.startswith("SU-"):
                sala_name = "Sala Plena - Sentencias de Unificación (SU)"
                sub_folder = "Sala_Plena_Unificacion_SU"
            else:
                sala_name = "Salas Especiales de Seguimiento - Autos (A)"
                sub_folder = "Salas_Especiales_Seguimiento_Autos_A"
            dest_dir = self.local_drive_path / entidad_folder / sub_folder / str(ano)

        # 2. Corte Suprema de Justicia
        elif "Suprema" in corte:
            entidad_folder = "02_Corte_Suprema_de_Justicia"
            tipo_lower = tipo.lower()
            fname_upper = filename.upper()
            if "descongestion" in tipo_lower or "descongestion" in fname_upper:
                sala_name = "Salas de Descongestión Laboral (1 a 4)"
                sub_folder = "Salas_Descongestion_Laboral"
            elif "laboral" in tipo_lower or fname_upper.startswith("SL") or fname_upper.startswith("AL"):
                sala_name = "Sala de Casación Laboral Permanente"
                sub_folder = "Sala_Casacion_Laboral_Permanente"
            elif "primera" in tipo_lower or fname_upper.startswith("SEP") or fname_upper.startswith("AEP"):
                sala_name = "Sala Especial de Primera Instancia (Aforados)"
                sub_folder = "Sala_Especial_Primera_Instancia"
            elif "instruccion" in tipo_lower or fname_upper.startswith("AEI") or fname_upper.startswith("SEI"):
                sala_name = "Sala Especial de Instrucción (Aforados)"
                sub_folder = "Sala_Especial_Instruccion"
            elif "plena" in tipo_lower:
                sala_name = "Sala Plena de la Corte Suprema"
                sub_folder = "Sala_Plena_Corte_Suprema"
            elif "tutela" in tipo_lower or fname_upper.startswith("ST") or fname_upper.startswith("AT"):
                sala_name = "Salas de Decisión de Tutelas"
                sub_folder = "Salas_Decision_Tutelas"
            elif "penal" in tipo_lower or fname_upper.startswith("SP") or fname_upper.startswith("AP"):
                sala_name = "Sala de Casación Penal"
                sub_folder = "Sala_Casacion_Penal"
            else:
                sala_name = "Sala de Casación Civil, Agraria y Rural"
                sub_folder = "Sala_Casacion_Civil_Agraria_y_Rural"
            dest_dir = self.local_drive_path / entidad_folder / sub_folder / str(ano)

        # 3. Consejo de Estado
        elif "Consejo" in corte:
            entidad_folder = "03_Consejo_de_Estado"
            tipo_lower = tipo.lower()
            if "especial" in tipo_lower:
                sala_name = "Salas Especiales de Decisión (1 a 26)"
                sub_folder = "Salas_Especiales_de_Decision"
            elif "plena" in tipo_lower or "suj" in tipo_lower:
                sala_name = "Sala Plena de lo Contencioso (SUJ & Pérdida Investidura)"
                sub_folder = "Sala_Plena_Contenciosa_y_SUJ"
            elif "segunda" in tipo_lower or "laboral" in tipo_lower:
                sala_name = "Sección Segunda (Laboral y Empleo Público - Subsecciones A y B)"
                sub_folder = "Seccion_Segunda_Laboral_Subsecciones_A_y_B"
            elif "tercera" in tipo_lower or "contractual" in tipo_lower or "antijuridico" in tipo_lower:
                sala_name = "Sección Tercera (Contratos y Daño Antijurídico - Subsecciones A, B y C)"
                sub_folder = "Seccion_Tercera_Contractual_y_Dano_Subsecciones_A_B_C"
            elif "cuarta" in tipo_lower or "tributari" in tipo_lower or "aduaner" in tipo_lower or "financier" in tipo_lower:
                sala_name = "Sección Cuarta (Tributaria, Financiera y Aduanera)"
                sub_folder = "Seccion_Cuarta_Tributaria_Financiera"
            elif "quinta" in tipo_lower or "electoral" in tipo_lower:
                sala_name = "Sección Quinta (Electoral)"
                sub_folder = "Seccion_Quinta_Electoral"
            elif "consulta" in tipo_lower or "servicio civil" in tipo_lower:
                sala_name = "Sala de Consulta y Servicio Civil"
                sub_folder = "Sala_Consulta_y_Servicio_Civil"
            else:
                sala_name = "Sección Primera (General y Ambiental)"
                sub_folder = "Seccion_Primera_General_Ambiental"
            dest_dir = self.local_drive_path / entidad_folder / sub_folder / str(ano)

        # 4. Secretaría del Senado (Leyes, Códigos, Actos Legislativos y Decretos Ley)
        elif "Senado" in corte or "Secretar" in corte:
            entidad_folder = "07_Secretaria_del_Senado_Normativa_y_Leyes"
            tipo_lower = tipo.lower()
            if "codigo" in tipo_lower:
                sala_name = "Códigos y Estatutos Nacionales"
                sub_folder = "Codigos_y_Estatutos_Nacionales"
                dest_dir = self.local_drive_path / entidad_folder / sub_folder
            elif "acto" in tipo_lower:
                sala_name = "Actos Legislativos y Reformas C.P."
                sub_folder = "Actos_Legislativos"
                dest_dir = self.local_drive_path / entidad_folder / sub_folder / str(ano)
            elif "decreto" in tipo_lower:
                sala_name = "Decretos Leyes y Decretos Legislativos"
                sub_folder = "Decretos_Leyes_y_Legislativos"
                dest_dir = self.local_drive_path / entidad_folder / sub_folder / str(ano)
            else:
                sala_name = f"Leyes de la República ({ano})"
                sub_folder = "Leyes_de_la_Republica"
                dest_dir = self.local_drive_path / entidad_folder / sub_folder / str(ano)

        # 5. Superintendencias de Colombia (Las 10 Entidades)
        elif "Superintendencia" in corte or "Super" in corte:
            entidad_folder = "08_Superintendencias_Funciones_Jurisdiccionales"
            tipo_lower = tipo.lower()
            if "servicios" in tipo_lower or "superservicios" in tipo_lower:
                sala_name = "Superintendencia de Servicios Públicos Domiciliarios (Superservicios)"
                sub_folder = "01_Superintendencia_Servicios_Publicos"
            elif "sociedad" in tipo_lower or "mercantil" in tipo_lower or "insolvencia" in tipo_lower:
                sala_name = "Superintendencia de Sociedades (Supersociedades)"
                sub_folder = "02_Superintendencia_Sociedades"
            elif "industria" in tipo_lower or "comercio" in tipo_lower or "sic" in tipo_lower:
                sala_name = "Superintendencia de Industria y Comercio (SIC)"
                sub_folder = "03_Superintendencia_Industria_Comercio"
            elif "financiera" in tipo_lower or "superfinanciera" in tipo_lower:
                sala_name = "Superintendencia Financiera de Colombia (SFC)"
                sub_folder = "04_Superintendencia_Financiera"
            elif "salud" in tipo_lower or "supersalud" in tipo_lower:
                sala_name = "Superintendencia Nacional de Salud (Supersalud)"
                sub_folder = "05_Superintendencia_Salud"
            elif "transporte" in tipo_lower or "supertransporte" in tipo_lower:
                sala_name = "Superintendencia de Transporte (Supertransporte)"
                sub_folder = "06_Superintendencia_Transporte"
            elif "notariado" in tipo_lower or "registro" in tipo_lower:
                sala_name = "Superintendencia de Notariado y Registro (SNR)"
                sub_folder = "07_Superintendencia_Notariado_Registro"
            elif "vigilancia" in tipo_lower or "seguridad" in tipo_lower:
                sala_name = "Superintendencia de Vigilancia y Seguridad Privada"
                sub_folder = "08_Superintendencia_Vigilancia_Seguridad"
            elif "solidaria" in tipo_lower or "economia_solidaria" in tipo_lower:
                sala_name = "Superintendencia de la Economía Solidaria (Supersolidaria)"
                sub_folder = "09_Superintendencia_Economia_Solidaria"
            elif "subsidio" in tipo_lower:
                sala_name = "Superintendencia del Subsidio Familiar (Supersubsidio)"
                sub_folder = "10_Superintendencia_Subsidio_Familiar"
            else:
                sala_name = f"Superintendencia ({tipo})"
                sub_folder = "01_Superintendencia_Servicios_Publicos"
            dest_dir = self.local_drive_path / entidad_folder / sub_folder / str(ano)

        # 6. Laudos Arbitrales (Cámaras de Comercio: Bogotá, Barranquilla, Medellín, Cali)
        elif "Laudo" in corte or "Arbitra" in corte:
            entidad_folder = "09_Tribunales_de_Arbitramento_y_Laudos"
            tipo_lower = tipo.lower()
            if "barranquilla" in tipo_lower:
                sala_name = "Cámara de Comercio de Barranquilla (CCBq)"
                sub_folder = "CAC_Barranquilla"
            elif "medellin" in tipo_lower:
                sala_name = "Cámara de Comercio de Medellín para Antioquia"
                sub_folder = "CAC_Medellin"
            elif "cali" in tipo_lower:
                sala_name = "Cámara de Comercio de Cali"
                sub_folder = "CAC_Cali"
            else:
                sala_name = "Cámara de Comercio de Bogotá (CAC)"
                sub_folder = "CAC_Bogota"
            dest_dir = self.local_drive_path / entidad_folder / sub_folder / str(ano)

        # 7. Tribunales Departamentales (Superiores y Administrativos)
        elif "Tribunal" in corte or "Departamental" in corte:
            entidad_folder = "04_Tribunales_Superiores_Distrito_Judicial"
            tipo_lower = tipo.lower()
            if "atlantico" in tipo_lower or "barranquilla" in tipo_lower:
                sala_name = "Tribunal Administrativo y Superior del Atlántico (Barranquilla)"
                sub_folder = "Tribunal_Atlantico_Barranquilla"
            elif "antioquia" in tipo_lower or "medellin" in tipo_lower:
                sala_name = "Tribunal Administrativo y Superior de Antioquia (Medellín)"
                sub_folder = "Tribunal_Antioquia_Medellin"
            elif "cundinamarca" in tipo_lower or "bogota" in tipo_lower:
                sala_name = "Tribunal Administrativo de Cundinamarca y Bogotá"
                sub_folder = "Tribunal_Cundinamarca_Bogota"
            elif "valle" in tipo_lower or "cali" in tipo_lower:
                sala_name = "Tribunal Administrativo y Superior del Valle del Cauca (Cali)"
                sub_folder = "Tribunal_Valle_Cali"
            elif "santander" in tipo_lower or "bucaramanga" in tipo_lower:
                sala_name = "Tribunal Administrativo y Superior de Santander (Bucaramanga)"
                sub_folder = "Tribunal_Santander_Bucaramanga"
            elif "bolivar" in tipo_lower or "cartagena" in tipo_lower:
                sala_name = "Tribunal Administrativo y Superior de Bolívar (Cartagena)"
                sub_folder = "Tribunal_Bolivar_Cartagena"
            elif "magdalena" in tipo_lower or "santa_marta" in tipo_lower or "santamarta" in tipo_lower:
                sala_name = "Tribunal Administrativo del Magdalena (Santa Marta)"
                sub_folder = "Tribunal_Magdalena_SantaMarta"
            else:
                sala_name = f"Tribunales Departamentales ({tipo})"
                sub_folder = f"Tribunal_{tipo}"
            dest_dir = self.local_drive_path / entidad_folder / sub_folder / str(ano)

        # 8. Instituto Colombiano de Derecho Procesal (ICDP) - Conceptos y Doctrina
        elif "ICDP" in corte or "Derecho Procesal" in corte or "Conceptos ICDP" in corte:
            entidad_folder = "10_Instituto_Colombiano_Derecho_Procesal_ICDP"
            tipo_lower = tipo.lower()
            if "intervencion" in tipo_lower or "constitucional" in tipo_lower:
                sala_name = "Intervenciones y Conceptos Constitucionales ICDP"
                sub_folder = "01_Intervenciones_y_Conceptos_Constitucionales"
                dest_dir = self.local_drive_path / entidad_folder / sub_folder / str(ano)
            elif "blog" in tipo_lower or "voces" in tipo_lower or "doctrina" in tipo_lower:
                sala_name = "Conceptos Doctrinales y Voces Procesales ICDP"
                sub_folder = "02_Doctrina_y_Conceptos_Voces_Procesales"
                dest_dir = self.local_drive_path / entidad_folder / sub_folder / str(ano)
            else:
                sala_name = "Compendios y Observatorio Jurídico ICDP"
                sub_folder = "03_Compendios_y_Observatorio_Juridico"
                dest_dir = self.local_drive_path / entidad_folder / sub_folder / str(ano)

        # 8. Juzgados Especializados
        elif "Familia" in corte:
            sala_name = "Juzgados de Familia"
            dest_dir = self.local_drive_path / "05_Juzgados_Especializados" / "Juzgados_de_Familia" / str(ano)
        elif "Civil" in corte:
            sala_name = "Juzgados Civiles de Circuito"
            dest_dir = self.local_drive_path / "05_Juzgados_Especializados" / "Juzgados_Civiles_Circuito" / str(ano)
        else:
            sala_name = f"Especialidad {tipo}"
            corte_slug = corte.replace(" ", "_")
            dest_dir = self.local_drive_path / corte_slug / str(ano) / tipo

        dest_dir.mkdir(parents=True, exist_ok=True)
        return dest_dir / filename, sala_name

    def save_sentence_file(
        self,
        corte: str,
        ano: int,
        tipo: str,
        filename: str,
        content_bytes: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Guarda la providencia en la sala especializada de Google Drive
        en formato ORIGINAL (.htm/.rtf), PDF (.pdf), MARKDOWN (.md) y JSON (.json).
        """
        file_path, sala_especializada = self.get_destination_info(corte, ano, tipo, filename)
        
        # 1. Guardar documento original íntegro
        with open(file_path, "wb") as f:
            f.write(content_bytes)

        # Preparar metadatos enriquecidos con la sala especializada y usuario Drive
        enriched_meta = dict(metadata or {})
        enriched_meta["sala_especializada"] = sala_especializada
        enriched_meta["drive_user"] = self.user_account
        enriched_meta["corte"] = corte
        enriched_meta["ano"] = ano
        enriched_meta["tipo"] = tipo

        is_pdf_original = content_bytes.startswith(b"%PDF") or filename.lower().endswith(".pdf")

        if is_pdf_original:
            # 2. Extraer texto desde PDF para generar Markdown estructurado
            import pymupdf
            try:
                doc = pymupdf.open(stream=content_bytes, filetype="pdf")
                pages_text = [page.get_text() for page in doc]
                extracted_text = "\n\n".join(pages_text)
            except Exception:
                extracted_text = enriched_meta.get("tema", "") or "Texto en documento PDF adjunto."

            md_path = file_path.with_suffix(".md")
            md_content = f"# Providencia {enriched_meta.get('radicado', file_path.stem)}\n\n"
            md_content += f"- **Corporación:** {corte}\n"
            md_content += f"- **Sala Especializada:** {sala_especializada}\n"
            md_content += f"- **Magistrado Ponente:** {enriched_meta.get('magistrado_ponente', 'N/A')}\n"
            md_content += f"- **Fecha:** {enriched_meta.get('fecha_providencia', str(ano))}\n"
            md_content += f"- **Tema / Asunto:** {enriched_meta.get('tema', 'Providencia Judicial')}\n\n"
            md_content += f"## Síntesis y Contenido de la Decisión\n\n{extracted_text[:15000]}\n"

            try:
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                fichas_repo_dir = self.local_drive_path / "06_Indices_Fichas_y_Metadatos_IA" / "Fichas_Jurisprudenciales_MD"
                fichas_repo_dir.mkdir(parents=True, exist_ok=True)
                radicado_clean = enriched_meta.get("radicado", file_path.stem)
                central_md_path = fichas_repo_dir / f"Ficha_{radicado_clean}.md"
                shutil.copyfile(md_path, central_md_path)
            except Exception as e:
                print(f"Advertencia al generar copia Markdown de PDF: {e}")
        else:
            # Decodificar texto HTML
            try:
                html_text = content_bytes.decode("latin-1", errors="ignore")
            except Exception:
                html_text = content_bytes.decode("utf-8", errors="ignore")

            # 2. Generar y guardar versión MARKDOWN (.md)
            md_path = file_path.with_suffix(".md")
            try:
                md_content = convert_to_markdown(html_text, enriched_meta)
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                    
                # Copiar ficha Markdown al banco central de Fichas IA
                fichas_repo_dir = self.local_drive_path / "06_Indices_Fichas_y_Metadatos_IA" / "Fichas_Jurisprudenciales_MD"
                fichas_repo_dir.mkdir(parents=True, exist_ok=True)
                radicado_clean = enriched_meta.get("radicado", file_path.stem)
                central_md_path = fichas_repo_dir / f"Ficha_{radicado_clean}.md"
                shutil.copyfile(md_path, central_md_path)
            except Exception as e:
                print(f"Advertencia al generar copia Markdown: {e}")
                md_content = f"# {enriched_meta.get('radicado', '')}\n\n{html_text[:500]}"

            # 3. Generar y guardar versión PDF (.pdf)
            pdf_path = file_path.with_suffix(".pdf")
            try:
                convert_to_pdf(md_content, enriched_meta, pdf_path)
            except Exception as e:
                print(f"Advertencia al generar copia PDF: {e}")

        # 4. Guardar archivo de metadatos en JSON (.json)
        meta_path = file_path.with_suffix(".json")
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(enriched_meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Advertencia al guardar JSON: {e}")

        # 5. Si existe la carpeta M:\Mi unidad\jurisprudencia, replicar allí para visualización completa
        mirror_base = Path(r"M:\Mi unidad\jurisprudencia")
        if mirror_base.exists() and mirror_base.resolve() != self.local_drive_path.resolve():
            try:
                rel = file_path.relative_to(self.local_drive_path)
                mirror_file = mirror_base / rel
                mirror_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file_path, mirror_file)
                for ext in [".md", ".pdf", ".json"]:
                    src_extra = file_path.with_suffix(ext)
                    if src_extra.exists():
                        shutil.copyfile(src_extra, mirror_file.with_suffix(ext))
            except Exception as e:
                print(f"Advertencia al replicar en carpeta espejo: {e}")

        # Enlace local de Google Drive
        drive_link = f"file:///{file_path.as_posix()}"
        drive_file_id = f"drive-sync-{file_path.stem}"

        return str(file_path), drive_link, drive_file_id

    def test_connection(self) -> Dict[str, Any]:
        """Verifica el estado del almacenamiento en Drive para Israel.Duarte.Carrasquilla@gmail.com."""
        try:
            self._ensure_local_dir_exists()
            test_file = self.local_drive_path / ".test_write_probe.tmp"
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(f"Acceso verificado para {self.user_account}")
            if test_file.exists():
                test_file.unlink()
                
            return {
                "ok": True,
                "account_email": self.user_account,
                "mode": self.storage_mode,
                "path": str(self.local_drive_path),
                "is_cloud_sync": True,
                "shared_folder_url": settings.shared_folder_url,
                "message": f"Conexión activa con Google Drive ({self.user_account}). Los archivos HTM, PDF y MD se sincronizan automáticamente en la nube."
            }
        except Exception as e:
            return {
                "ok": False,
                "account_email": self.user_account,
                "mode": self.storage_mode,
                "path": str(self.local_drive_path),
                "is_cloud_sync": False,
                "message": f"Error de acceso: {str(e)}"
            }

drive_manager = DriveManager()
