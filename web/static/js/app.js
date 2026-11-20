// JurisprudenciaBot Frontend Engine

let isRunning = false;
let isPaused = false;
let pollInterval = null;
let searchTimeout = null;

// Tab Management
function switchTab(tabKey) {
  // Normalizar el identificador (ej: 'crawler', 'tab-crawler', 'btn-tab-crawler')
  const cleanKey = tabKey.replace('btn-', '').replace('tab-', '').replace('content-', '');

  // 1. Ocultar todos los paneles de pestaña
  document.querySelectorAll('.tab-content').forEach(el => {
    el.classList.add('hidden');
  });

  // 2. Desactivar estilos de todos los botones de pestaña
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active', 'text-brand-400', 'border-brand-500');
    btn.classList.add('text-slate-400', 'border-transparent');
  });

  // 3. Mostrar el contenido de la pestaña seleccionada
  const targetContent = document.getElementById('tab-content-' + cleanKey) || document.getElementById(tabKey);
  if (targetContent) {
    targetContent.classList.remove('hidden');
  }

  // 4. Activar visualmente el botón de la pestaña
  const targetBtn = document.getElementById('btn-tab-' + cleanKey) || document.getElementById(tabKey);
  if (targetBtn) {
    targetBtn.classList.add('active', 'text-brand-400', 'border-brand-500');
    targetBtn.classList.remove('text-slate-400', 'border-transparent');
  }

  // Cargar datos correspondientes
  if (cleanKey === 'taxonomy') {
    fetchTaxonomy();
  } else if (cleanKey === 'database') {
    fetchSentencias();
  }
}


// DOM Elements
const statTotalSentencias = document.getElementById('stat-total-sentencias');
const statTotalDrive = document.getElementById('stat-total-drive');
const statTotalMegabytes = document.getElementById('stat-total-megabytes');

const botStatusBadge = document.getElementById('bot-status-badge');
const botStatusText = document.getElementById('bot-status-text');

// AI Elements
const aiSearchInput = document.getElementById('ai-search-input');
const btnAiSearch = document.getElementById('btn-ai-search');
const aiResponseContainer = document.getElementById('ai-response-container');
const aiMarkdownOutput = document.getElementById('ai-markdown-output');
const aiSourcesGrid = document.getElementById('ai-sources-grid');
const aiLoadingBox = document.getElementById('ai-loading-box');
const aiEngineBadge = document.getElementById('ai-engine-badge');

// Crawler Elements
const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const btnPause = document.getElementById('btn-pause');
const btnResume = document.getElementById('btn-resume');
const btnClearLogs = document.getElementById('btn-clear-logs');
const terminalLogs = document.getElementById('terminal-logs');
const currentTaskStatus = document.getElementById('current-task-status');

const selectCorte = document.getElementById('select-corte');
const inputAnoInicio = document.getElementById('input-ano-inicio');
const inputAnoFin = document.getElementById('input-ano-fin');
const inputSearch = document.getElementById('input-search');
const btnRefreshTable = document.getElementById('btn-refresh-table');
const sentenciasTbody = document.getElementById('sentencias-tbody');
const taxonomyGrid = document.getElementById('taxonomy-grid');

// Live Progress Elements
const progressRadicado = document.getElementById('progress-radicado');
const progressBarFill = document.getElementById('progress-bar-fill');
const progressDescargadas = document.getElementById('progress-descargadas');
const progressExistentes = document.getElementById('progress-existentes');
const progressExploradas = document.getElementById('progress-exploradas');
const progressPulseRing = document.getElementById('progress-pulse-ring');
const progressPulseDot = document.getElementById('progress-pulse-dot');

// Salas y Especialidades por Corporación Judicial
const salasPorCorte = {
  'Corte Constitucional': [
    { value: 'C', label: 'Sala Plena (Constitucionalidad C)', checked: true },
    { value: 'T', label: 'Salas de Revisión 1 a 9 (Tutelas T)', checked: true },
    { value: 'SU', label: 'Sala Plena (Unificación Jurisprudencial SU)', checked: true },
    { value: 'A', label: 'Salas Especiales de Seguimiento (Autos A)', checked: true }
  ],
  'Corte Suprema de Justicia': [
    { value: 'Civil', label: 'Sala de Casación Civil, Agraria y Rural', checked: true },
    { value: 'Laboral', label: 'Sala de Casación Laboral Permanente', checked: true },
    { value: 'Descongestion', label: 'Salas de Descongestión Laboral (1 a 4)', checked: true },
    { value: 'Penal', label: 'Sala de Casación Penal Ordinaria', checked: true },
    { value: 'PrimeraInstancia', label: 'Sala Especial de Primera Instancia (Aforados)', checked: true },
    { value: 'Instruccion', label: 'Sala Especial de Instrucción (Aforados)', checked: true },
    { value: 'Tutelas', label: 'Salas de Decisión de Tutela (Civil, Laboral, Penal)', checked: true }
  ],
  'Consejo de Estado': [
    { value: 'Plena', label: 'Sala Plena (SUJ y Pérdida de Investidura)', checked: true },
    { value: 'SalasEspeciales', label: 'Salas Especiales de Decisión (1 a 26)', checked: true },
    { value: 'Segunda', label: 'Sección Segunda (Laboral - Subsecciones A y B)', checked: true },
    { value: 'Tercera', label: 'Sección Tercera (Contratos & Daño - Subsecciones A, B y C)', checked: true },
    { value: 'Cuarta', label: 'Sección Cuarta (Tributaria, Financiera y Aduanera)', checked: true },
    { value: 'Primera', label: 'Sección Primera (General y Ambiental)', checked: true },
    { value: 'Quinta', label: 'Sección Quinta (Electoral)', checked: true },
    { value: 'Consulta', label: 'Sala de Consulta y Servicio Civil', checked: false }
  ],
  'Secretaría del Senado': [
    { value: 'Leyes', label: 'Leyes de la República (por año cronológico)', checked: true },
    { value: 'Codigos', label: 'Códigos y Estatutos Nacionales', checked: true },
    { value: 'Actos', label: 'Actos Legislativos (Reformas C.P.)', checked: false }
  ],
  'Superintendencias': [
    { value: 'Superservicios', label: '1. Superservicios (Servicios Públicos Domiciliarios)', checked: true },
    { value: 'Supersociedades', label: '2. Supersociedades (Mercantil e Insolvencia)', checked: true },
    { value: 'SIC', label: '3. SIC (Industria, Comercio, Consumidor y Marcas)', checked: true },
    { value: 'Superfinanciera', label: '4. Superfinanciera (Bancario y Mercado de Valores)', checked: true },
    { value: 'Supersalud', label: '5. Supersalud (Salud, EPS e IPS)', checked: true },
    { value: 'Supertransporte', label: '6. Supertransporte (Tránsito, Puertos e Infraestructura)', checked: true },
    { value: 'Supernotariado', label: '7. Supernotariado (Notariado y Registro)', checked: true },
    { value: 'Supervigilancia', label: '8. Supervigilancia (Vigilancia y Seguridad Privada)', checked: true },
    { value: 'Supersolidaria', label: '9. Supersolidaria (Economía Solidaria y Cooperativas)', checked: true },
    { value: 'Supersubsidio', label: '10. Supersubsidio (Cajas de Compensación Familiar)', checked: true }
  ],
  'Laudos Arbitrales': [
    { value: 'Bogota', label: 'Cámara de Comercio de Bogotá (CAC - Nacional e Internacional)', checked: true },
    { value: 'Barranquilla', label: 'Cámara de Comercio de Barranquilla (CCBq)', checked: true },
    { value: 'Medellin', label: 'Cámara de Comercio de Medellín para Antioquia', checked: true },
    { value: 'Cali', label: 'Cámara de Comercio de Cali', checked: true }
  ],
  'Tribunales Departamentales': [
    { value: 'Atlantico', label: 'Tribunal Superior y Administrativo del Atlántico (Barranquilla)', checked: true },
    { value: 'Antioquia', label: 'Tribunal Superior y Administrativo de Antioquia (Medellín)', checked: true },
    { value: 'Cundinamarca', label: 'Tribunal Superior de Bogotá y Administrativo de Cundinamarca', checked: true },
    { value: 'Valle', label: 'Tribunal Superior y Administrativo del Valle del Cauca (Cali)', checked: true },
    { value: 'Santander', label: 'Tribunal Superior y Administrativo de Santander (Bucaramanga)', checked: true },
    { value: 'Bolivar', label: 'Tribunal Superior y Administrativo de Bolívar (Cartagena)', checked: true },
    { value: 'Magdalena', label: 'Tribunal Superior y Administrativo del Magdalena (Santa Marta)', checked: true },
    { value: 'Boyaca', label: 'Tribunal Superior y Administrativo de Boyacá (Tunja)', checked: false },
    { value: 'Caldas', label: 'Tribunal Superior y Administrativo de Caldas (Manizales)', checked: false },
    { value: 'Meta', label: 'Tribunal Superior y Administrativo del Meta (Villavicencio)', checked: false }
  ],
  'Instituto Colombiano de Derecho Procesal (ICDP)': [
    { value: 'Intervenciones', label: 'Intervenciones y Conceptos Constitucionales (2001 - 2026)', checked: true },
    { value: 'Doctrina', label: 'Doctrina y Conceptos (Voces Procesales - Blog)', checked: true },
    { value: 'Compendios', label: 'Compendios Jurisprudenciales y Observatorio', checked: true }
  ]
};

function updateSalasCheckboxes() {
  const selected = selectCorte ? selectCorte.value : 'Todas las Entidades';
  const container = document.getElementById('salas-checkboxes-container');
  if (!container) return;

  if (selected === 'Todas las Entidades') {
    container.innerHTML = `
      <div class="col-span-2 p-3 rounded-xl bg-indigo-950/40 border border-indigo-500/40 text-indigo-200 text-xs flex items-center gap-3">
        <input type="checkbox" value="ALL" checked class="hidden">
        <div class="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center flex-shrink-0 text-base">
          <i class="fa-solid fa-layer-group"></i>
        </div>
        <div>
          <span class="font-bold text-white text-[12px]">Descarga Global Multicorporación Activada</span>
          <p class="text-[11px] text-indigo-300 mt-0.5">Se descargarán automáticamente todas las cortes judiciales (<b>Corte Constitucional</b>, <b>Suprema</b>, <b>Consejo de Estado</b>), las <b>10 Superintendencias</b> (Superservicios, Sociedades, etc.), <b>Laudos Arbitrales</b> (Bogotá, Barranquilla, Medellín, Cali), <b>Tribunales Departamentales</b>, la <b>Secretaría del Senado</b> (Leyes y Códigos) y los <b>Conceptos del ICDP</b>.</p>
        </div>
      </div>
    `;
    return;
  }

  const list = salasPorCorte[selected] || salasPorCorte['Corte Constitucional'];
  container.innerHTML = list.map(item => `
    <label class="flex items-center p-2.5 rounded-xl bg-slate-800/80 border border-slate-700/80 cursor-pointer hover:bg-slate-800 transition">
      <input type="checkbox" value="${item.value}" ${item.checked ? 'checked' : ''} class="form-checkbox text-brand-600 rounded bg-slate-900 border-slate-700 mr-2 focus:ring-0">
      <span class="font-medium text-slate-200">${escapeHtml(item.label)}</span>
    </label>
  `).join('');
}

// Iniciar aplicación
document.addEventListener('DOMContentLoaded', () => {
  fetchStats();
  fetchSentencias();
  fetchTaxonomy();
  startPolling();

  if (selectCorte) {
    selectCorte.addEventListener('change', updateSalasCheckboxes);
    updateSalasCheckboxes();
  }

  // AI Search Events
  btnAiSearch.addEventListener('click', handleAiSearch);
  aiSearchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleAiSearch();
  });

  // Crawler Events
  btnStart.addEventListener('click', handleStart);
  btnStop.addEventListener('click', handleStop);
  btnPause.addEventListener('click', handlePause);
  btnResume.addEventListener('click', handleResume);
  btnClearLogs.addEventListener('click', () => {
    terminalLogs.innerHTML = '<div class="text-slate-500">// Consola de eventos limpiada.</div>';
  });

  // Table search
  inputSearch.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      fetchSentencias(inputSearch.value.trim());
    }, 300);
  });

  btnRefreshTable.addEventListener('click', () => {
    fetchSentencias(inputSearch.value.trim());
  });
});

// Polling de Estado y Logs
function startPolling() {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(async () => {
    await fetchStatus();
    await fetchLogs();
  }, 1500);
}

// ==============================================================
// FUNCIONALIDAD DEL BUSCADOR APOYADO CON IA
// ==============================================================
function setAiQuery(text) {
  aiSearchInput.value = text;
  handleAiSearch();
}

async function handleAiSearch() {
  const query = aiSearchInput.value.trim();
  if (!query) {
    alert('Por favor escriba una pregunta o consulta jurídica para la IA.');
    return;
  }

  aiLoadingBox.classList.remove('hidden');
  aiResponseContainer.classList.add('hidden');

  try {
    const res = await fetch('/api/ai/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query, limit: 10 })
    });
    const data = await res.json();

    aiLoadingBox.classList.add('hidden');
    aiResponseContainer.classList.remove('hidden');

    // Renderizar Markdown
    if (window.marked && data.synthesis_markdown) {
      aiMarkdownOutput.innerHTML = marked.parse(data.synthesis_markdown);
    } else {
      aiMarkdownOutput.innerHTML = `<pre class="whitespace-pre-wrap">${escapeHtml(data.synthesis_markdown || '')}</pre>`;
    }

    aiEngineBadge.textContent = data.mode === 'gemini_llm' ? 'Gemini 2.5 Flash' : 'Motor Jurídico Semántico';

    // Renderizar Fuentes y Sentencias Citadas
    const sources = data.sources || [];
    if (sources.length === 0) {
      aiSourcesGrid.innerHTML = `
        <div class="col-span-2 text-xs text-slate-500 p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          No hay providencias coincidentes en el acervo local. Puede iniciar una descarga masiva en la pestaña del Robot para incorporar más jurisprudencia.
        </div>
      `;
    } else {
      aiSourcesGrid.innerHTML = sources.map(s => `
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-2 hover:border-slate-700 transition">
          <div class="flex items-center justify-between">
            <span class="px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              ${s.radicado}
            </span>
            <span class="text-[11px] text-slate-400 font-mono">${s.corte} (${s.ano})</span>
          </div>
          <div class="text-xs text-slate-300">
            <span class="font-semibold text-slate-400">Ponente:</span> ${escapeHtml(s.magistrado_ponente || 'No registrado')}
          </div>
          <p class="text-xs text-slate-400 line-clamp-2">
            ${escapeHtml(s.tema || s.resuelve || 'Sin extracto disponible')}
          </p>
          <div class="pt-2 flex items-center justify-between border-t border-slate-800/80">
            <span class="text-[10px] text-emerald-400 flex items-center gap-1">
              <i class="fa-solid fa-cloud-check"></i> Google Drive
            </span>
            <div class="flex items-center gap-1">
              <a href="/api/sentencias/${s.id}/file?format=pdf" target="_blank" class="inline-flex items-center gap-1 bg-rose-500/20 hover:bg-rose-600 text-rose-300 hover:text-white px-2 py-0.5 rounded text-[10px] font-semibold transition border border-rose-500/30">
                <i class="fa-solid fa-file-pdf"></i> PDF
              </a>
              <a href="/api/sentencias/${s.id}/file?format=md" target="_blank" class="inline-flex items-center gap-1 bg-sky-500/20 hover:bg-sky-600 text-sky-300 hover:text-white px-2 py-0.5 rounded text-[10px] font-semibold transition border border-sky-500/30">
                <i class="fa-brands fa-markdown"></i> MD
              </a>
              <a href="/api/sentencias/${s.id}/file?format=htm" target="_blank" class="inline-flex items-center gap-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white px-2 py-0.5 rounded text-[10px] transition border border-slate-700">
                HTM
              </a>
            </div>
          </div>
        </div>
      `).join('');
    }

    aiResponseContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    aiLoadingBox.classList.add('hidden');
    alert('Error al realizar la consulta con el motor de IA.');
    console.error(err);
  }
}

function copyAiResponse() {
  const text = aiMarkdownOutput.innerText;
  navigator.clipboard.writeText(text).then(() => {
    alert('¡Dictamen jurisprudencial copiado al portapapeles!');
  });
}

// ==============================================================
// TAXONOMÍA DE ESPECIALIDADES DE GOOGLE DRIVE
// ==============================================================
async function fetchTaxonomy() {
  try {
    const res = await fetch('/api/taxonomy');
    const data = await res.json();
    const list = data.taxonomia || [];

    if (!taxonomyGrid) return;

    taxonomyGrid.innerHTML = list.map(item => `
      <div class="bg-slate-950/60 border border-slate-800 rounded-2xl p-5 space-y-3 hover:border-slate-700 transition">
        <div class="flex items-start justify-between">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-sm">
              <i class="fa-solid fa-folder"></i>
            </div>
            <div>
              <h3 class="text-xs font-bold text-white tracking-wide">${escapeHtml(item.label)}</h3>
              <p class="text-[11px] text-slate-400">${item.subcarpetas.length} Especialidades</p>
            </div>
          </div>
        </div>
        <p class="text-[11px] text-slate-400 line-clamp-2">${escapeHtml(item.descripcion)}</p>

        <div class="pt-2 border-t border-slate-800/80 space-y-1.5">
          ${item.subcarpetas.map(sub => `
            <div class="flex items-center justify-between text-xs py-1 px-2 rounded-lg bg-slate-900/60 border border-slate-800/40">
              <span class="text-slate-300 font-mono text-[11px] truncate flex items-center gap-1.5">
                <i class="fa-regular fa-folder text-slate-500 text-[10px]"></i>
                ${escapeHtml(sub.label)}
              </span>
              <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full ${sub.archivos > 0 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-500'}">
                ${sub.archivos} docs
              </span>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error cargando taxonomía:', err);
  }
}

// Generar Ficha Jurisprudencial IA
async function handleGenerateFicha(sentenciaId) {
  try {
    const res = await fetch(`/api/ai/analyze-sentence/${sentenciaId}`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      alert(`¡Ficha Jurisprudencial IA generada con éxito!\nGuardada en Google Drive:\n${data.ficha_md}`);
      fetchTaxonomy();
    }
  } catch (err) {
    alert('No se pudo generar la ficha.');
  }
}

// ==============================================================
// GESTIÓN DEL ROBOT DE DESCARGA MASIVA
// ==============================================================
async function fetchStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();

    statTotalSentencias.textContent = (data.total_sentencias || 0).toLocaleString();
    statTotalDrive.textContent = (data.en_drive || 0).toLocaleString();
    statTotalMegabytes.textContent = `${data.total_megabytes || 0} MB`;
  } catch (err) {
    console.error('Error stats:', err);
  }
}

async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    const status = await res.json();

    isRunning = status.is_running;
    isPaused = status.is_paused;

    btnStart.disabled = isRunning;
    btnStop.disabled = !isRunning;
    btnPause.disabled = !isRunning || isPaused;
    btnResume.disabled = !isRunning || !isPaused;

    if (isRunning && !isPaused) {
      botStatusBadge.className = 'flex items-center space-x-2 text-xs px-3 py-1.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/30';
      botStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-brand-400 animate-ping"></span><span class="font-semibold">Descargando...</span>';
    } else if (isRunning && isPaused) {
      botStatusBadge.className = 'flex items-center space-x-2 text-xs px-3 py-1.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30';
      botStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-400"></span><span class="font-semibold">Pausado</span>';
    } else {
      botStatusBadge.className = 'flex items-center space-x-2 text-xs px-3 py-1.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700';
      botStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-400"></span><span class="font-semibold">Listo</span>';
    }

    if (status.ultimo_mensaje) {
      currentTaskStatus.textContent = status.ultimo_mensaje;
    }

    // Actualizar Monitor de Progreso en Vivo
    if (progressRadicado) {
      progressRadicado.textContent = status.radicado_actual || (isRunning ? 'Sondeando...' : 'En espera');
    }
    if (progressDescargadas) {
      progressDescargadas.textContent = (status.descargadas_sesion || 0).toLocaleString();
    }
    if (progressExistentes) {
      progressExistentes.textContent = (status.existentes_sesion || 0).toLocaleString();
    }
    if (progressExploradas) {
      progressExploradas.textContent = (status.total_exploradas || 0).toLocaleString();
    }
    if (progressBarFill) {
      if (isRunning && !isPaused) {
        const total = status.total_exploradas || 0;
        const pct = Math.min(100, Math.max(12, ((total * 7) % 95) + 5));
        progressBarFill.style.width = `${pct}%`;
      } else if (!isRunning) {
        progressBarFill.style.width = status.total_exploradas > 0 ? '100%' : '0%';
      }
    }
    if (progressPulseRing && progressPulseDot) {
      if (isRunning && !isPaused) {
        progressPulseRing.className = 'animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75';
        progressPulseDot.className = 'relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500';
      } else if (isRunning && isPaused) {
        progressPulseRing.className = 'hidden';
        progressPulseDot.className = 'relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500';
      } else {
        progressPulseRing.className = 'hidden';
        progressPulseDot.className = 'relative inline-flex rounded-full h-2.5 w-2.5 bg-slate-500';
      }
    }

    if (isRunning && status.descargadas_sesion > 0) {
      fetchStats();
    }
  } catch (err) {
    console.error(err);
  }
}

async function fetchLogs() {
  try {
    const res = await fetch('/api/logs');
    const data = await res.json();
    const logs = data.logs || [];

    if (logs.length > 0 && terminalLogs) {
      terminalLogs.innerHTML = logs.map(l => `
        <div class="log-line">
          <span class="log-time">[${l.timestamp}]</span>
          <span class="log-${l.level}">[${l.level}]</span>
          <span class="text-slate-200">${escapeHtml(l.message)}</span>
        </div>
      `).join('');
      terminalLogs.scrollTop = terminalLogs.scrollHeight;
    }
  } catch (err) {
    console.error(err);
  }
}

async function handleStart() {
  const corte = selectCorte.value;
  const ano_inicio = parseInt(inputAnoInicio.value, 10);
  const ano_fin = parseInt(inputAnoFin.value, 10);

  const tipos = [];
  document.querySelectorAll('#salas-checkboxes-container input[type="checkbox"]:checked').forEach(cb => {
    tipos.push(cb.value);
  });

  if (tipos.length === 0 && corte !== 'Todas las Entidades') {
    return alert('Seleccione al menos una sala o tipo de providencia.');
  }

  if (corte === 'Todas las Entidades' && tipos.length === 0) {
    tipos.push('ALL');
  }

  try {
    const res = await fetch('/api/crawler/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ corte, ano_inicio, ano_fin, tipos })
    });
    const result = await res.json();
    if (result.ok) {
      await fetchStatus();
      await fetchLogs();
    } else {
      alert(result.detail || 'No se pudo iniciar.');
    }
  } catch (err) {
    alert('Error al comunicar con el servidor.');
  }
}

async function handleStop() {
  try {
    await fetch('/api/crawler/stop', { method: 'POST' });
    await fetchStatus();
  } catch (err) {}
}

async function handlePause() {
  try {
    await fetch('/api/crawler/pause', { method: 'POST' });
    await fetchStatus();
  } catch (err) {}
}

async function handleResume() {
  try {
    await fetch('/api/crawler/resume', { method: 'POST' });
    await fetchStatus();
  } catch (err) {}
}

// ==============================================================
// REPOSITORIO DE SENTENCIAS
// ==============================================================
async function fetchSentencias(search = '') {
  try {
    const url = `/api/sentencias?limit=50&search=${encodeURIComponent(search)}`;
    const res = await fetch(url);
    const data = await res.json();
    const items = data.items || [];

    if (items.length === 0) {
      sentenciasTbody.innerHTML = `
        <tr>
          <td colspan="6" class="py-10 text-center text-slate-500">
            <i class="fa-solid fa-folder-open text-2xl mb-2 text-slate-600 block"></i>
            No se encontraron sentencias con el filtro actual. Inicie una descarga en la pestaña del Robot.
          </td>
        </tr>
      `;
      return;
    }

    sentenciasTbody.innerHTML = items.map(s => {
      let badgeClass = 'badge-c';
      if (s.tipo === 'T') badgeClass = 'badge-t';
      else if (s.tipo === 'SU') badgeClass = 'badge-su';
      else if (s.tipo === 'A') badgeClass = 'badge-a';

      return `
        <tr class="hover:bg-slate-800/40 transition">
          <td class="py-3 px-4 font-mono font-semibold">
            <span class="px-2 py-0.5 rounded text-[11px] font-bold ${badgeClass}">${s.radicado}</span>
          </td>
          <td class="py-3 px-4 font-mono text-slate-400">${s.ano}</td>
          <td class="py-3 px-4 text-slate-200 font-medium">${escapeHtml(s.magistrado_ponente || 'N/A')}</td>
          <td class="py-3 px-4 text-slate-400 max-w-md truncate" title="${escapeHtml(s.tema || '')}">
            ${escapeHtml(s.tema || 'Sin extracto')}
          </td>
          <td class="py-3 px-4">
            <div class="flex items-center gap-1">
              <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30">PDF</span>
              <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-sky-500/15 text-sky-300 border border-sky-500/30">MD</span>
              <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-800 text-slate-400 border border-slate-700">HTM</span>
              <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">JSON</span>
            </div>
          </td>
          <td class="py-3 px-4 text-right whitespace-nowrap space-x-1">
            <a href="/api/sentencias/${s.id}/file?format=pdf" target="_blank" class="inline-flex items-center gap-1 bg-rose-600/20 hover:bg-rose-600 text-rose-300 hover:text-white px-2 py-1 rounded-lg text-[10px] font-semibold transition border border-rose-500/30" title="Descargar PDF">
              <i class="fa-solid fa-file-pdf"></i> PDF
            </a>
            <a href="/api/sentencias/${s.id}/file?format=md" target="_blank" class="inline-flex items-center gap-1 bg-sky-600/20 hover:bg-sky-600 text-sky-300 hover:text-white px-2 py-1 rounded-lg text-[10px] font-semibold transition border border-sky-500/30" title="Ver Markdown">
              <i class="fa-brands fa-markdown"></i> MD
            </a>
            <a href="/api/sentencias/${s.id}/file?format=htm" target="_blank" class="inline-flex items-center gap-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white px-2 py-1 rounded-lg text-[10px] font-medium transition border border-slate-700" title="Ver Original">
              <i class="fa-solid fa-code"></i> HTM
            </a>
            <button onclick="handleGenerateFicha(${s.id})" class="inline-flex items-center gap-1 bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white px-2 py-1 rounded-lg text-[10px] font-medium transition border border-indigo-500/30" title="Generar Ficha IA">
              <i class="fa-solid fa-wand-magic-sparkles"></i> Ficha IA
            </button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error(err);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
