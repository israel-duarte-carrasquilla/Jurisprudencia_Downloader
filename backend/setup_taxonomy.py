import os
from pathlib import Path
from typing import Dict, Any

from backend.config import detect_google_drive_path

TARGET_DRIVE_FOLDER_ID = "1Wy9jIetIcQ4vw0R-IeafGC7-8GGDaaIZ"
TARGET_ACCOUNT_EMAIL = "Israel.Duarte.Carrasquilla@gmail.com"
DEFAULT_TARGET_PATH = Path(detect_google_drive_path())

TAXONOMIA_SALAS_ESPECIALIZADAS = {
    "01_Corte_Constitucional": {
        "descripcion": "Guardián de la supremacía e integridad de la Constitución Política.",
        "salas": {
            "Sala_Plena_Constitucionalidad_C": "Control abstracto de constitucionalidad de leyes y decretos leyes (Sentencias C).",
            "Salas_Revision_Tutelas_T": "Salas de Revisión 1 a 9 encargadas de tutelas de derechos fundamentales (Sentencias T).",
            "Sala_Plena_Unificacion_SU": "Sentencias de unificación de jurisprudencia en materia de tutela (Sentencias SU).",
            "Salas_Especiales_Seguimiento_Autos_A": "Autos de cumplimiento, medidas cautelares y seguimiento a estados de cosas inconstitucionales (Autos A: T-025, T-760, T-388, T-302)."
        }
    },
    "02_Corte_Suprema_de_Justicia": {
        "descripcion": "Máximo tribunal de la jurisdicción ordinaria en Colombia estructurado en sus Salas de Casación, Salas Especiales y Tutelas.",
        "salas": {
            "Sala_Casacion_Civil_Agraria_y_Rural": "Recursos extraordinarios de casación y revisión en derecho civil, comercial, familia, responsabilidad y agrario (SC / AC).",
            "Sala_Casacion_Laboral_Permanente": "Casación laboral en contratos individuales, convenciones colectivas, pensiones y seguridad social (SL / AL).",
            "Salas_Descongestion_Laboral": "Salas de Descongestión Laboral 1 a 4 (Ley 1781 de 2016) para evacuación masiva de procesos laborales.",
            "Sala_Casacion_Penal": "Casación y revisión en procesos penales ordinarios y justicia transicional (SP / AP).",
            "Sala_Especial_Primera_Instancia": "Juzgamiento de aforados constitucionales (congresistas, ministros, gobernadores) en primera instancia (SEP / AEP).",
            "Sala_Especial_Instruccion": "Investigación e instrucción penal de aforados constitucionales y congresistas (AEI).",
            "Sala_Plena_Corte_Suprema": "Decisiones de gobierno judicial, unificación institucional y conflictos de competencia entre salas.",
            "Salas_Decision_Tutelas": "Salas de Decisión de Tutela Civil (STC), Laboral (STL) y Penal (STP)."
        }
    },
    "03_Consejo_de_Estado": {
        "descripcion": "Tribunal supremo de lo contencioso administrativo y órgano consultivo del Gobierno Nacional.",
        "salas": {
            "Sala_Plena_Contenciosa_y_SUJ": "Sentencias de Unificación Jurisprudencial (SUJ) y Pérdida de Investidura de Congresistas en Sala Plena.",
            "Salas_Especiales_de_Decision": "Salas Especiales de Decisión 1 a 26 de Pérdida de Investidura (primera instancia / doble conformidad Ley 2080 y Ley 1437).",
            "Seccion_Primera_General_Ambiental": "Demandas contra actos generales, derecho ambiental, propiedad industrial y pérdida de investidura de concejales/diputados.",
            "Seccion_Segunda_Laboral_Subsecciones_A_y_B": "Controversias laborales de empleados públicos, régimen pensional, carrera administrativa y docentes (Subsección A, B y Sala).",
            "Seccion_Tercera_Contractual_y_Dano_Subsecciones_A_B_C": "Contratación estatal (Ley 80/Ley 1150), reparación directa, responsabilidad extracontractual del Estado y anulación de laudos arbitrales (Subsecciones A, B y C).",
            "Seccion_Cuarta_Tributaria_Financiera": "Impuestos nacionales (DIAN: Renta, IVA), tributos territoriales (ICA, Predial), aduanas, régimen cambiario y financiero.",
            "Seccion_Quinta_Electoral": "Nulidad de elecciones populares (Presidencia, Congreso, Alcaldías), inhabilidades, incompatibilidades y doble militancia.",
            "Sala_Consulta_y_Servicio_Civil": "Conceptos jurídicos solicitados por el Gobierno Nacional y resolución de conflictos de competencias administrativas."
        }
    },
    "04_Tribunales_Superiores_Distrito_Judicial": {
        "descripcion": "Segunda instancia colegiada de los distritos judiciales y tribunales administrativos departamentales territoriales.",
        "salas": {
            "Tribunal_Atlantico_Barranquilla": "Tribunal Superior de Barranquilla (Salas Civil, Laboral, Penal, Familia) y Tribunal Administrativo del Atlántico.",
            "Tribunal_Antioquia_Medellin": "Tribunal Superior de Medellín / Antioquia y Tribunal Administrativo de Antioquia.",
            "Tribunal_Cundinamarca_Bogota": "Tribunal Superior de Distrito Judicial de Bogotá y Tribunal Administrativo de Cundinamarca.",
            "Tribunal_Valle_Cali": "Tribunal Superior de Cali y Tribunal Administrativo del Valle del Cauca.",
            "Tribunal_Santander_Bucaramanga": "Tribunal Superior de Bucaramanga y Tribunal Administrativo de Santander.",
            "Tribunal_Bolivar_Cartagena": "Tribunal Superior de Cartagena y Tribunal Administrativo de Bolívar.",
            "Tribunal_Magdalena_SantaMarta": "Tribunal Superior de Santa Marta y Tribunal Administrativo del Magdalena.",
            "Tribunal_Boyaca_Tunja": "Tribunal Superior de Tunja y Tribunal Administrativo de Boyacá.",
            "Tribunal_Caldas_Manizales": "Tribunal Superior de Manizales y Tribunal Administrativo de Caldas.",
            "Tribunal_Meta_Villavicencio": "Tribunal Superior de Villavicencio y Tribunal Administrativo del Meta.",
            "Sala_Civil_Superior": "Apelaciones de procesos civiles ordinarios, contractuales, ejecutivos y de responsabilidad en tribunales.",
            "Sala_Laboral_Superior": "Apelaciones en litigios ordinarios laborales individuales y reclamos pensionales.",
            "Sala_Penal_Superior": "Apelaciones de sentencias condenatorias/absolutorias, control de garantías y justicia transicional.",
            "Sala_Familia_Superior": "Apelaciones de procesos de familia, custodia, alimentos y régimen patrimonial conyugal."
        }
    },
    "05_Juzgados_Especializados": {
        "descripcion": "Juzgados de primera y única instancia categorizados por su especialidad material.",
        "salas": {
            "Juzgados_Civiles_Circuito": "Procesos civiles de mayor cuantía, contractuales y extracontractuales.",
            "Juzgados_Civiles_Municipales": "Procesos civiles de menor y mínima cuantía.",
            "Juzgados_de_Familia": "Custodia, alimentos, patria potestad, divorcios y sucesiones.",
            "Juzgados_Laborales": "Demandas laborales individuales y contra administradoras de fondos de pensiones.",
            "Juzgados_Penales": "Control de garantías, jueces de conocimiento penal y ejecución de penas.",
            "Juzgados_Administrativos": "Litigios contenciosos contra entidades públicas en primera instancia."
        }
    },
    "06_Indices_Fichas_y_Metadatos_IA": {
        "descripcion": "Fichas jurisprudenciales en Markdown, resúmenes analíticos y bancos de doctrina IA.",
        "salas": {
            "Fichas_Jurisprudenciales_MD": "Fichas analíticas completas en Markdown (.md) listas para lectura y LLMs.",
            "Indices_Estructurados_JSON": "Extractos en JSON con metadatos estructurados para interoperabilidad.",
            "Resumenes_Doctrina_IA": "Síntesis y dictámenes temáticos generados por el Asistente de IA."
        }
    },
    "07_Secretaria_del_Senado_Normativa_y_Leyes": {
        "descripcion": "Compilación oficial de Leyes de la República, Códigos Nacionales y Actos Legislativos del Congreso.",
        "salas": {
            "Leyes_de_la_Republica": "Leyes ordinarias, estatutarias, orgánicas y leyes marco con notas de vigencia constitucional (organizadas por año).",
            "Codigos_y_Estatutos_Nacionales": "Códigos sustantivos y procesales de Colombia (Civil, CGP, CPACA, Comercio, Penal, Laboral, Policía, Tránsito, Estatuto Tributario, Consumidor).",
            "Actos_Legislativos": "Reformas a la Constitución Política aprobadas por el Congreso de la República.",
            "Decretos_Leyes_y_Legislativos": "Decretos leyes por facultades extraordinarias y decretos legislativos de estados de excepción."
        }
    },
    "08_Superintendencias_Funciones_Jurisdiccionales": {
        "descripcion": "Decisiones jurisdiccionales (Art. 116 C.P.), resoluciones de apelación y doctrina de las 10 Superintendencias de Colombia.",
        "salas": {
            "01_Superintendencia_Servicios_Publicos": "Superservicios: Recursos de apelación de usuarios, régimen tarifario, acueducto, aseo, alcantarillado, energía y gas (Ley 142 de 1994).",
            "02_Superintendencia_Sociedades": "Supersociedades: Delegatura de Procedimientos Mercantiles (conflictos entre accionistas, responsabilidad administradores) y Delegatura de Insolvencia (Reorganización Ley 1116 y liquidación).",
            "03_Superintendencia_Industria_Comercio": "SIC: Delegatura de Asuntos Jurisdiccionales (Protección al Consumidor y Competencia Desleal), Propiedad Industrial (Marcas/Patentes) y Datos Personales.",
            "04_Superintendencia_Financiera": "Superfinanciera: Delegatura para Funciones Jurisdiccionales (controversias contra bancos, aseguradoras y fiduciarias por consumidores financieros).",
            "05_Superintendencia_Salud": "Supersalud: Función Jurisdiccional (Art. 41 Ley 1122 de 2007 - cobertura PBS, incapacidades, glosas y reembolsos médicos EPS/IPS).",
            "06_Superintendencia_Transporte": "Supertransporte: Vigilancia, sanciones e inspección a concesiones viales, puertos, aeropuertos y transporte terrestre automotor.",
            "07_Superintendencia_Notariado_Registro": "Supernotariado: Resoluciones de apelación registral de inmuebles, vigilancia a notarías y formalización de tierras.",
            "08_Superintendencia_Vigilancia_Seguridad": "Supervigilancia: Vigilancia armada privada, departamentos de seguridad empresarial, blindajes y escoltas.",
            "09_Superintendencia_Economia_Solidaria": "Supersolidaria: Cooperativas de ahorro y crédito, fondos de empleados, mutuales e intervenciones financieras.",
            "10_Superintendencia_Subsidio_Familiar": "Supersubsidio: Cajas de compensación familiar, subsidio en dinero y especie, y medidas cautelares administrativas."
        }
    },
    "09_Tribunales_de_Arbitramento_y_Laudos": {
        "descripcion": "Laudos arbitrales proferidos por tribunales de arbitramento de Cámaras de Comercio del país.",
        "salas": {
            "CAC_Bogota": "Laudos arbitrales del Centro de Arbitraje y Conciliación de la Cámara de Comercio de Bogotá (CCB) en derecho comercial, societario, infraestructura y contratos.",
            "CAC_Barranquilla": "Laudos arbitrales del Centro de Conciliación y Arbitraje de la Cámara de Comercio de Barranquilla (CCBq) en controversias comerciales y portuarias.",
            "CAC_Medellin": "Laudos arbitrales del Centro de Arbitraje de la Cámara de Comercio de Medellín para Antioquia en contratos empresariales e ingeniería.",
            "CAC_Cali": "Laudos arbitrales del Centro de Conciliación y Arbitraje de la Cámara de Comercio de Cali (Suroccidente colombiano)."
        }
    },
    "10_Instituto_Colombiano_Derecho_Procesal_ICDP": {
        "descripcion": "Conceptos jurídicos, memoriales de intervención procesal ante la Corte Constitucional, doctrina de Voces Procesales y compendios del Instituto Colombiano de Derecho Procesal (ICDP).",
        "salas": {
            "01_Intervenciones_y_Conceptos_Constitucionales": "Conceptos técnicos y memoriales de intervención jurídica del ICDP en demandas de inconstitucionalidad (D-), tutelas (T-) y tratados (LAT-).",
            "02_Doctrina_y_Conceptos_Voces_Procesales": "Conceptos doctrinales, artículos especializados y debates procesales del Blog Voces Procesales del ICDP (Civil, Penal, Administrativo, Disciplinario e IA).",
            "03_Compendios_y_Observatorio_Juridico": "Compendios jurisprudenciales analíticos y publicaciones del Observatorio Jurídico del ICDP."
        }
    }
}

def create_taxonomy_structure(base_path: Path = DEFAULT_TARGET_PATH) -> bool:
    """Crea la estructura organizada y categorizada por Salas Especializadas."""
    try:
        base_path.mkdir(parents=True, exist_ok=True)
        
        for entidad, data in TAXONOMIA_SALAS_ESPECIALIZADAS.items():
            entidad_dir = base_path / entidad
            entidad_dir.mkdir(parents=True, exist_ok=True)
            
            readme_path = entidad_dir / "LEEME_COMPETENCIAS_SALAS.txt"
            name_clean = entidad.replace("_", " ")
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(f"=== {name_clean} ===\n")
                f.write(f"TITULAR GOOGLE DRIVE: {TARGET_ACCOUNT_EMAIL}\n\n")
                f.write(f"DESCRIPCIÓN:\n{data['descripcion']}\n\n")
                f.write("SALAS ESPECIALIZADAS Y COMPETENCIAS:\n")
                for sala, desc in data["salas"].items():
                    sala_clean = sala.replace("_", " ")
                    f.write(f" • {sala_clean}\n   -> {desc}\n\n")
                    
            for sala in data["salas"].keys():
                sala_dir = entidad_dir / sala
                sala_dir.mkdir(parents=True, exist_ok=True)
                
        return True
    except Exception as e:
        print(f"Error creando estructura de salas especializadas: {e}")
        return False

if __name__ == "__main__":
    success = create_taxonomy_structure()
    print(f"Taxonomía de salas especializadas creada en {DEFAULT_TARGET_PATH}: {success}")
