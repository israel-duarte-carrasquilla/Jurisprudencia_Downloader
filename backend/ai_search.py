import re
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from backend.database import get_db_connection, get_config
from backend.config import BASE_DIR

class AISearchEngine:
    def __init__(self):
        # Mapeo de palabras clave a especialidades jurídicas
        self.specialty_keywords = {
            "Constitucional": [
                "tutela", "constitucion", "derecho fundamental", "debido proceso",
                "igualdad", "libertad", "accion de tutela", "constitucionalidad",
                "inexequible", "exequible", "unificacion", "su-", "c-", "t-"
            ],
            "Civil y Comercial": [
                "contrato", "incumplimiento", "responsabilidad civil", "danos y perjuicios",
                "perjuicio moral", "lucro cesante", "dano emergente", "compraventa",
                "hipoteca", "propiedad", "prescripcion adquisitiva", "usucapion",
                "arrendamiento", "juzgado civil", "sala civil"
            ],
            "Familia": [
                "patria potestad", "custodia", "alimentos", "cuota alimentaria",
                "divorcio", "cesacion de efectos civiles", "union marital de hecho",
                "sociedad conyugal", "patrimonio de familia", "afectacion a vivienda",
                "adopcion", "menor de edad", "ninos y ninas", "juzgado de familia"
            ],
            "Laboral y Seguridad Social": [
                "pension", "sobrevivientes", "vejez", "invalidez", "estabilidad laboral",
                "fuero de salud", "maternidad", "despido", "contrato de trabajo",
                "salario", "prestaciones", "indemnizacion laboral", "juzgado laboral", "colpensiones"
            ],
            "Penal": [
                "delito", "pena", "homicidio", "estafa", "hurto", "libertad condicional",
                "medida de aseguramiento", "fiscalia", "juez penal", "casacion penal", "imputacion"
            ],
            "Administrativo": [
                "reparacion directa", "nulidad y restablecimiento", "consejo de estado",
                "contratacion estatal", "falla del servicio", "acto administrativo", "danio antijuridico"
            ]
        }

    def detect_legal_intent(self, query: str) -> Dict[str, Any]:
        """Detecta las ramas del derecho y especialidades asociadas a la consulta del usuario."""
        q_lower = query.lower()
        matched_specialties = []
        
        for specialty, keywords in self.specialty_keywords.items():
            score = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', q_lower))
            if score > 0:
                matched_specialties.append((specialty, score))
                
        matched_specialties.sort(key=lambda x: x[1], reverse=True)
        top_specialties = [s[0] for s in matched_specialties[:2]] if matched_specialties else ["General"]
        
        return {
            "query": query,
            "especialidades_detectadas": top_specialties,
            "palabras_clave": [w for w in re.findall(r'\b\w{4,}\b', q_lower) if w not in [
                "para", "como", "sobre", "cual", "cuales", "donde", "cuando", "este", "esta", "sentencia", "jurisprudencia"
            ]]
        }

    def search_and_rank(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Busca y pondera semánticamente providencias en la base de datos."""
        intent = self.detect_legal_intent(query)
        keywords = intent["palabras_clave"]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todas las sentencias candidatas
        cursor.execute("SELECT * FROM sentencias ORDER BY ano DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        if not rows:
            return []

        scored_results = []
        for row in rows:
            score = 0
            text_target = f"{row.get('radicado', '')} {row.get('magistrado_ponente', '')} {row.get('tema', '')} {row.get('resuelve', '')}".lower()
            
            # Puntuación por coincidencia exacta de radicado
            if query.lower() in row.get("radicado", "").lower():
                score += 100
                
            # Puntuación por palabras clave
            for kw in keywords:
                if kw in text_target:
                    score += 15
                if kw in (row.get("tema") or "").lower():
                    score += 25
                if kw in (row.get("resuelve") or "").lower():
                    score += 20
                    
            # Puntuación por especialidad detectada
            corte = row.get("corte", "")
            for esp in intent["especialidades_detectadas"]:
                if esp == "Constitucional" and "Constitucional" in corte:
                    score += 10
                elif esp in ["Civil y Comercial", "Laboral y Seguridad Social", "Penal"] and "Suprema" in corte:
                    score += 10

            if score > 0 or not keywords:
                res_item = dict(row)
                res_item["relevance_score"] = score
                res_item["detected_specialty"] = intent["especialidades_detectadas"][0]
                scored_results.append(res_item)

        scored_results.sort(key=lambda x: (x["relevance_score"], x.get("ano", 0)), reverse=True)
        return scored_results[:limit]

    def generate_ai_legal_synthesis(
        self,
        query: str,
        results: List[Dict[str, Any]],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera la respuesta del buscador apoyado con IA.
        Si hay Gemini API Key configurada, utiliza google-genai para redactar la síntesis.
        Si no, utiliza el motor de síntesis jurídica local con citas exactas.
        """
        intent = self.detect_legal_intent(query)
        
        # Verificar si hay una API Key personalizada del usuario
        active_key = api_key or get_config("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
        
        if active_key and active_key.startswith("AIza") and results:
            try:
                from google import genai
                client = genai.Client(api_key=active_key)
                
                contexto_providencias = ""
                for idx, r in enumerate(results[:5], 1):
                    contexto_providencias += f"\n--- Sentencia #{idx}: {r.get('radicado')} ({r.get('corte')} - {r.get('ano')}) ---\n"
                    contexto_providencias += f"Magistrado Ponente: {r.get('magistrado_ponente')}\n"
                    contexto_providencias += f"Tema/Extracto: {r.get('tema')}\n"
                    contexto_providencias += f"Fallo/Resuelve: {r.get('resuelve')}\n"

                prompt = f"""Eres un jurista experto y asistente de investigación jurisprudencial de Colombia.
El usuario realiza la siguiente consulta jurídica:
"{query}"

A continuación tienes los extractos de las providencias más relevantes encontradas en la base de datos:
{contexto_providencias}

Redacta una respuesta jurídica rigurosa y estructurada en formato Markdown que contenga:
1. **Resumen de la Tesis Jurisprudencial**: Respuesta directa y concreta a la consulta planteada.
2. **Criterios y Fundamentos Aplicables**: Explicación de los estándares fijados por las Altas Cortes y juzgados correspondientes.
3. **Análisis de Providencias Clave**: Mención expresa de los radicados citados con su Magistrado Ponente y ratio decidendi.
4. **Conclusión y Aplicabilidad Práctica**.

Sé formal, preciso y cita siempre los radicados."""

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                
                return {
                    "mode": "gemini_llm",
                    "query": query,
                    "intent": intent,
                    "synthesis_markdown": response.text,
                    "total_sources": len(results),
                    "sources": results[:5]
                }
            except Exception as e:
                print(f"Fallo en Gemini API, usando motor de síntesis local: {e}")

        # Motor de Síntesis Jurídica Local (Garantizado sin requerir API externa)
        return self._generate_local_legal_synthesis(query, intent, results)

    def _generate_local_legal_synthesis(
        self,
        query: str,
        intent: Dict[str, Any],
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Genera una síntesis jurídica analítica local a partir de las providencias indexadas."""
        if not results:
            markdown = f"""### ⚖️ Síntesis Jurídica IA
No se encontraron providencias registradas que coincidan directamente con la consulta: **"{query}"**.

**Sugerencias del asistente jurídico:**
- Inicie una descarga en el panel superior para los años y corporaciones pertinentes (Corte Constitucional, Corte Suprema o Juzgados).
- Verifique términos como: *{', '.join(intent.get('palabras_clave', []))}*.
- Ajuste el rango de búsqueda en la barra superior.
"""
            return {
                "mode": "local_nlp",
                "query": query,
                "intent": intent,
                "synthesis_markdown": markdown,
                "total_sources": 0,
                "sources": []
            }

        top = results[0]
        especialidad = intent["especialidades_detectadas"][0]
        
        md_lines = [
            f"### ⚖️ Análisis Jurisprudencial Asistido por IA",
            f"**Consulta:** *«{query}»*  ",
            f"**Especialidad Jurídica Identificada:** `{especialidad}` | **Providencias analizadas:** `{len(results)}`",
            "",
            "#### 1. Tesis y Precedente Relevante",
            f"De conformidad con la jurisprudencia consolidada de la corporación judicial, en relación con **{query}**, la regla de derecho aplicable establece que las decisiones deben fundarse en la garantía de los derechos fundamentales y la estricta aplicación del ordenamiento legal aplicable a la especialidad.",
            "",
            "#### 2. Providencias Emblemáticas Identificadas en el Acervo",
        ]

        for idx, r in enumerate(results[:4], 1):
            rad = r.get("radicado", "S/R")
            corte = r.get("corte", "Entidad Judicial")
            ano = r.get("ano", "")
            mp = r.get("magistrado_ponente", "No registrado")
            tema = r.get("tema", "Extracto no disponible")
            resuelve = r.get("resuelve", "Consultar texto íntegro")
            
            md_lines.extend([
                f"- **{rad} ({ano}) - {corte}**",
                f"  - **Magistrado(a) Ponente:** {mp}",
                f"  - **Síntesis del Asunto:** {tema}",
                f"  - **Criterio / Decisión:** {resuelve[:220]}...",
                f"  - 📁 *Ubicación en Drive:* `{r.get('archivo_local', 'Google Drive')}`",
                ""
            ])

        md_lines.extend([
            "#### 3. Criterio de Aplicación Práctica",
            f"Para controversias radicadas ante la especialidad **{especialidad}** (Corte Suprema, Tribunales o Juzgados Civiles/Familia/Laboral), se aconseja invocar las providencias arriba reseñadas verificando los supuestos fácticos y la vigencia de la línea jurisprudencial en el expediente digital guardado en Google Drive."
        ])

        return {
            "mode": "local_nlp",
            "query": query,
            "intent": intent,
            "synthesis_markdown": "\n".join(md_lines),
            "total_sources": len(results),
            "sources": results[:5]
        }

ai_search_engine = AISearchEngine()
