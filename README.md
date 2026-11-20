# JurisprudenciaBot Colombia • Descarga Masiva, Taxonomía por Especialidad & Buscador IA

Sistema integral para la extracción masiva de jurisprudencia judicial colombiana, organización jerárquica por especialidad en **Google Drive** y **Buscador Semántico apoyado con Inteligencia Artificial (IA)**.

Enlace a la carpeta compartida en Google Drive:
[Google Drive - Jurisprudencia](https://drive.google.com/drive/folders/1Wy9jIetIcQ4vw0R-IeafGC7-8GGDaaIZ?usp=sharing)

---

## 🗂️ 1. Taxonomía y Especialidades Creadas en Google Drive

Las sentencias se organizan y clasifican automáticamente en la carpeta compartida según la corporación y su especialidad jurídica:

```text
Google Drive/jurisprudencia/
├── 01_Corte_Constitucional/
│   ├── Constitucionalidad_C/
│   ├── Tutelas_T/
│   ├── Unificacion_SU/
│   └── Autos_Sala_Plena/
├── 02_Corte_Suprema_de_Justicia/
│   ├── Sala_Casacion_Civil_Agraria_y_Rural/
│   ├── Sala_Casacion_Laboral/
│   ├── Sala_Casacion_Penal/
│   └── Sala_Especial_Primera_Instancia/
├── 03_Consejo_de_Estado/
│   ├── Seccion_Primera_General/
│   ├── Seccion_Segunda_Laboral_y_Empleo_Publico/
│   ├── Seccion_Tercera_Contractual_y_Dano_Antijuridico/
│   ├── Seccion_Cuarta_Tributario_y_Financiero/
│   └── Seccion_Quinta_Electoral/
├── 04_Tribunales_Superiores_y_Administrativos/
│   ├── Tribunal_Superior_Sala_Civil/
│   ├── Tribunal_Superior_Sala_Familia/
│   ├── Tribunal_Superior_Sala_Laboral/
│   ├── Tribunal_Superior_Sala_Penal/
│   └── Tribunales_Administrativos/
├── 05_Juzgados_Especializados/
│   ├── Juzgados_Civiles_Circuito/
│   ├── Juzgados_Civiles_Municipales/
│   ├── Juzgados_de_Familia/
│   ├── Juzgados_Laborales/
│   ├── Juzgados_Penales/
│   ├── Juzgados_Administrativos/
│   └── Juzgados_Promiscuos/
└── 06_Indices_y_Metadatos_IA/
    ├── Fichas_Jurisprudenciales/
    └── Resumenes_Analiticos_IA/
```

Cada carpeta incluye un archivo explicativo `LEEME_COMPETENCIAS.txt` con la descripción de los asuntos que tramita dicha especialidad.

---

## 🤖 2. Buscador Apoyado con Inteligencia Artificial (IA)

El sistema incorpora un motor de búsqueda y análisis jurídico que permite consultar en lenguaje natural:
- **Detección de Intención Jurídica**: Identifica automáticamente la rama del derecho aplicable (Constitucional, Civil, Familia, Laboral, Penal o Administrativo).
- **Ranking Semántico**: Cruza la consulta con los extractos, ponentes, temas y decisiones de las providencias registradas.
- **Dictamen y Síntesis Asistido por IA**:
  - Genera una respuesta jurídica estructurada en Markdown:
    1. *Tesis jurisprudencial dominante*.
    2. *Criterios y estándares de las Altas Cortes y Juzgados*.
    3. *Providencias clave citadas expresamente*.
    4. *Criterio de aplicación práctica*.
  - Funciona con **Gemini 2.5 Flash** (si se proporciona API Key) o con el **Motor de Síntesis Jurídica Local** (100% offline y gratuito).
- **Fichas Jurisprudenciales IA**: Con un solo clic en la tabla de sentencias, la IA redacta una ficha de análisis del caso y la guarda automáticamente en Google Drive (`06_Indices_y_Metadatos_IA/Fichas_Jurisprudenciales/Ficha_[RADICADO].md` y `.json`).

---

## 🚀 3. Cómo Ejecutar la Aplicación

### Lanzador rápido (Windows):
Doble clic en:
```text
run.bat
```
*(Inicia el servidor y abre el navegador automáticamente).*

### Desde la terminal:
```bash
python main.py
```
Abra en su navegador:
```text
http://localhost:8000
```

---

## 💻 4. Pestañas de la Aplicación Web

1. **Buscador Apoyado con IA**: Formulario de preguntas jurídicas en lenguaje natural, sugerencias interactivas y dictámenes con citas.
2. **Robot de Descarga Masiva**: Selector de corporación, tipos de providencia (C, T, SU, A), rango de años y consola de terminal en tiempo real.
3. **Carpetas & Especialidades Drive**: Visualizador del árbol de especialidades en Drive con conteo de documentos y acceso directo.
4. **Repositorio de Sentencias**: Tabla con búsqueda reactiva, visualización y generación de Fichas Jurisprudenciales IA.
