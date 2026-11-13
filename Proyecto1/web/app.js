'use strict';
// Interfaz de demostracion: llama a la API del mismo origen (rutas relativas).

const MAX_EVENTOS = 20;
const CAMPOS = ['marca_tiempo', 'monto', 'rubro', 'canal', 'ciudad'];
const NUMERICOS = new Set(['marca_tiempo', 'monto']);

const $ = (id) => document.getElementById(id);
const estado = { demo: null, ejemploActivo: null, umbral: null };

// ---------- Utilidades ----------
function formatoPuntaje(x) {
  if (x === 0) return '0';
  if (x < 0.0001) return x.toExponential(2);
  return x.toFixed(4);
}

function leerValor(campo, texto) {
  const t = texto.trim();
  if (!NUMERICOS.has(campo)) return t;
  if (t === '') return null;
  const n = Number(t.replace(',', '.'));
  // Si no es numero se envia el texto tal cual para que la API lo rechace (422).
  return Number.isFinite(n) ? n : t;
}

async function pedirJSON(url, opciones = {}, limiteMs = 30000) {
  const control = new AbortController();
  const temporizador = setTimeout(() => control.abort(), limiteMs);
  try {
    const r = await fetch(url, { ...opciones, signal: control.signal });
    let cuerpo = null;
    try { cuerpo = await r.json(); } catch { /* respuesta sin JSON */ }
    return { ok: r.ok, status: r.status, cuerpo, idSolicitud: r.headers.get('X-Request-ID') };
  } finally {
    clearTimeout(temporizador);
  }
}

// ---------- Tabla de transacciones ----------
function filas() { return Array.from($('filas').querySelectorAll('tr[data-fila]')); }

function agregarFila(tx = {}) {
  if (filas().length >= MAX_EVENTOS) return;
  const fila = $('plantilla-fila').content.firstElementChild.cloneNode(true);
  fila.dataset.fila = '';
  for (const campo of CAMPOS) {
    const input = fila.querySelector(`[data-campo="${campo}"]`);
    input.value = tx[campo] ?? '';
    input.addEventListener('input', alEditar);
  }
  fila.querySelector('.quitar').addEventListener('click', () => { fila.remove(); alEditar(); });
  $('filas').appendChild(fila);
}

function cargarTransacciones(lista) {
  $('filas').innerHTML = '';
  lista.slice(0, MAX_EVENTOS).forEach(agregarFila);
  actualizarTabla();
}

function leerTransacciones() {
  return filas().map((fila) => {
    const tx = {};
    for (const campo of CAMPOS) {
      tx[campo] = leerValor(campo, fila.querySelector(`[data-campo="${campo}"]`).value);
    }
    return tx;
  });
}

function actualizarTabla() {
  const todas = filas();
  todas.forEach((fila, i) => {
    const ancla = i === todas.length - 1;
    fila.classList.toggle('ancla', ancla);
    fila.querySelector('.indice').textContent = ancla ? `${i + 1} · actual` : String(i + 1);
    fila.querySelectorAll('input').forEach((el) => el.removeAttribute('aria-invalid'));
  });
  const vacio = $('filas').querySelector('.vacio-fila');
  if (todas.length === 0 && !vacio) {
    $('filas').insertAdjacentHTML('beforeend',
      '<tr class="vacio-fila"><td colspan="7" class="vacio">Sin transacciones. Elige un ejemplo o agrega una.</td></tr>');
  } else if (todas.length > 0 && vacio) {
    vacio.remove();
  }
  $('contador').textContent = `${todas.length} de ${MAX_EVENTOS} eventos`;
  $('agregar').disabled = todas.length >= MAX_EVENTOS;
  $('texto-json').value = JSON.stringify({ transacciones: leerTransacciones() }, null, 2);
}

function alEditar() {
  marcarEjemplo(null);
  actualizarTabla();
}

function nuevaFilaSugerida() {
  const lista = leerTransacciones();
  const ultima = lista[lista.length - 1];
  if (!ultima) {
    agregarFila({ marca_tiempo: 150, monto: 100, rubro: 'supermercado', canal: 'chip', ciudad: 'guatemala' });
  } else {
    const t = typeof ultima.marca_tiempo === 'number' ? ultima.marca_tiempo + 0.1 : '';
    agregarFila({ ...ultima, marca_tiempo: t === '' ? '' : Number(t.toFixed(4)) });
  }
  alEditar();
}

// ---------- Ejemplos ----------
function marcarEjemplo(id) {
  estado.ejemploActivo = id;
  document.querySelectorAll('.ejemplo').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.id === id)));
}

function pintarEjemplos(ejemplos) {
  const cont = $('ejemplos');
  cont.innerHTML = '';
  for (const ej of ejemplos) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'ejemplo';
    b.dataset.id = ej.id;
    b.setAttribute('aria-pressed', 'false');
    const etiqueta = ej.tipo === 'fraude' ? 'Fraude sintético' : 'Legítima sintética';
    b.innerHTML = `<span class="ejemplo__etiqueta ejemplo__etiqueta--${ej.tipo}"></span>
      <span class="ejemplo__titulo"></span><span class="ejemplo__desc"></span>`;
    b.querySelector('.ejemplo__etiqueta').textContent = `${etiqueta} · ${ej.transacciones.length} eventos`;
    b.querySelector('.ejemplo__titulo').textContent = ej.nombre;
    b.querySelector('.ejemplo__desc').textContent = ej.descripcion;
    b.addEventListener('click', () => {
      cargarTransacciones(ej.transacciones);
      marcarEjemplo(ej.id);
      ocultarResultado();
    });
    cont.appendChild(b);
  }
}

function llenarListas(vocab) {
  const pares = [['lista-rubros', vocab.rubros], ['lista-canales', vocab.canales], ['lista-ciudades', vocab.ciudades]];
  for (const [id, valores] of pares) {
    $(id).innerHTML = valores.map((v) => `<option value="${v}"></option>`).join('');
  }
}

// ---------- Resultado y errores ----------
function ocultarResultado() {
  $('resultado').hidden = true;
  $('errores').hidden = true;
}

function mostrarResultado(cuerpo, idSolicitud, ms) {
  const p = cuerpo.puntaje_riesgo;
  const u = estado.umbral;
  const alto = u !== null && p >= u;
  const caja = $('resultado');
  caja.className = `resultado ${alto ? 'resultado--alto' : 'resultado--bajo'}`;
  const ej = estado.demo?.ejemplos.find((e) => e.id === estado.ejemploActivo);
  const comparacion = ej
    ? `<dt>Puntaje esperado</dt><dd>${formatoPuntaje(ej.puntaje_esperado)} (${
        Math.abs(ej.puntaje_esperado - p) <= 1e-6 ? 'coincide con el experimento' : 'difiere del experimento'})</dd>`
    : '';
  const veredicto = u === null ? '' : alto
    ? 'Por encima del umbral de referencia: priorizar revisión.'
    : 'Por debajo del umbral de referencia: sin prioridad de revisión.';
  caja.innerHTML = `
    <div class="resultado__cifra">${formatoPuntaje(p)}</div>
    <div class="resultado__veredicto">${veredicto}</div>
    <div class="barra" role="img" aria-label="Puntaje ${formatoPuntaje(p)} frente a umbral ${u?.toFixed(3) ?? '—'}">
      <div class="barra__relleno" style="width:${Math.max(p * 100, 0.5)}%"></div>
      ${u === null ? '' : `<div class="barra__umbral" style="left:${u * 100}%"></div>`}
    </div>
    <div class="barra__leyenda"><span>0</span><span>umbral ${u?.toFixed(3) ?? '—'}</span><span>1</span></div>
    <dl class="detalles">
      ${comparacion}
      <dt>Versión del modelo</dt><dd></dd>
      <dt>ID de solicitud</dt><dd></dd>
      <dt>Tiempo total</dt><dd>${Math.round(ms)} ms (incluye red)</dd>
    </dl>`;
  const dds = caja.querySelectorAll('.detalles dd');
  dds[dds.length - 3].textContent = cuerpo.version_modelo;
  dds[dds.length - 2].textContent = idSolicitud ?? '—';
  caja.hidden = false;
}

function describirCampo(loc) {
  // loc llega como ["body", "transacciones", 3, "monto"]
  const partes = loc.filter((x) => x !== 'body');
  const i = partes.findIndex((x) => typeof x === 'number');
  if (i >= 0) {
    const campo = partes[i + 1];
    return { fila: partes[i], campo, texto: `Transacción ${partes[i] + 1}${campo ? ` · ${campo}` : ''}` };
  }
  return { fila: null, campo: null, texto: partes.join(' · ') || 'Solicitud' };
}

function mostrarErrores(titulo, mensajes) {
  const caja = $('errores');
  caja.innerHTML = '<strong></strong><ul></ul>';
  caja.querySelector('strong').textContent = titulo;
  const ul = caja.querySelector('ul');
  for (const m of mensajes) {
    const li = document.createElement('li');
    li.textContent = m;
    ul.appendChild(li);
  }
  caja.hidden = false;
}

function marcarInvalidos(detalles) {
  const todas = filas();
  for (const d of detalles) {
    const { fila, campo } = describirCampo(d.campo || []);
    if (fila === null || !todas[fila]) continue;
    const objetivo = campo ? todas[fila].querySelector(`[data-campo="${campo}"]`) : null;
    (objetivo ? [objetivo] : todas[fila].querySelectorAll('input'))
      .forEach((el) => el.setAttribute('aria-invalid', 'true'));
  }
}

function manejarError(resp) {
  const { status, cuerpo, idSolicitud } = resp;
  const sufijo = idSolicitud ? ` (ID ${idSolicitud})` : '';
  if (status === 422) {
    const detalle = cuerpo?.detail;
    if (Array.isArray(detalle)) {
      marcarInvalidos(detalle);
      mostrarErrores(`Datos inválidos${sufijo}`,
        detalle.map((d) => `${describirCampo(d.campo || []).texto}: ${d.mensaje}`));
    } else {
      mostrarErrores(`Datos inválidos${sufijo}`, [String(detalle ?? 'Revisa las transacciones.')]);
    }
  } else if (status === 503) {
    mostrarErrores(`Modelo no disponible${sufijo}`, ['El servicio está iniciando o no pudo cargar el modelo. Intenta de nuevo en unos segundos.']);
  } else {
    mostrarErrores(`Error del servicio (HTTP ${status})${sufijo}`, [String(cuerpo?.detail ?? 'Error inesperado.')]);
  }
}

// ---------- Acciones ----------
async function predecir() {
  ocultarResultado();
  actualizarTabla();
  const transacciones = leerTransacciones();
  if (transacciones.length === 0) {
    mostrarErrores('No hay transacciones', ['Elige un ejemplo o agrega al menos una transacción.']);
    return;
  }
  const boton = $('predecir');
  boton.disabled = true;
  boton.setAttribute('aria-busy', 'true');
  boton.querySelector('.boton__texto').textContent = 'Calculando…';
  const inicio = performance.now();
  try {
    const resp = await pedirJSON('predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transacciones }),
    });
    if (resp.ok) mostrarResultado(resp.cuerpo, resp.idSolicitud, performance.now() - inicio);
    else manejarError(resp);
  } catch (err) {
    const motivo = err.name === 'AbortError'
      ? 'La solicitud tardó más de 30 s. Si el servicio estaba suspendido, puede estar arrancando: intenta de nuevo.'
      : 'No se pudo conectar con el servicio. Revisa tu conexión o intenta de nuevo.';
    mostrarErrores('Sin respuesta del servicio', [motivo]);
  } finally {
    boton.disabled = false;
    boton.removeAttribute('aria-busy');
    boton.querySelector('.boton__texto').textContent = 'Calcular riesgo';
  }
}

function aplicarJSON() {
  $('error-json').textContent = '';
  let datos;
  try {
    datos = JSON.parse($('texto-json').value);
  } catch (e) {
    $('error-json').textContent = `JSON inválido: ${e.message}`;
    return;
  }
  const lista = Array.isArray(datos) ? datos : datos?.transacciones;
  if (!Array.isArray(lista)) {
    $('error-json').textContent = 'Se esperaba {"transacciones": [...]} o una lista.';
    return;
  }
  if (lista.length > MAX_EVENTOS) {
    $('error-json').textContent = `Se cargaron solo las primeras ${MAX_EVENTOS} de ${lista.length} transacciones.`;
  }
  cargarTransacciones(lista.map((tx) => (tx && typeof tx === 'object' ? tx : {})));
  marcarEjemplo(null);
  ocultarResultado();
}

async function revisarSalud() {
  const caja = $('estado-servicio');
  try {
    const r = await pedirJSON('health', {}, 60000);
    if (r.ok) {
      caja.className = 'estado estado--ok';
      $('estado-texto').textContent = `Servicio activo · ${r.cuerpo.version_modelo}`;
    } else {
      caja.className = 'estado estado--error';
      $('estado-texto').textContent = `Servicio no disponible (HTTP ${r.status})`;
    }
  } catch {
    caja.className = 'estado estado--error';
    $('estado-texto').textContent = 'Sin conexión con el servicio';
  }
}

async function iniciar() {
  $('agregar').addEventListener('click', nuevaFilaSugerida);
  $('limpiar').addEventListener('click', () => { cargarTransacciones([]); marcarEjemplo(null); ocultarResultado(); });
  $('predecir').addEventListener('click', predecir);
  $('aplicar-json').addEventListener('click', aplicarJSON);
  $('alternar-json').addEventListener('click', () => {
    const panel = $('panel-json');
    panel.hidden = !panel.hidden;
    $('alternar-json').setAttribute('aria-expanded', String(!panel.hidden));
  });

  revisarSalud();
  try {
    const r = await pedirJSON('demo.json');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    estado.demo = r.cuerpo;
    estado.umbral = r.cuerpo.umbral_referencia;
    $('umbral-texto').textContent = estado.umbral.toFixed(3);
    $('costo-fn').textContent = r.cuerpo.costos.fn.toLocaleString('es-GT');
    $('costo-fp').textContent = r.cuerpo.costos.fp.toLocaleString('es-GT');
    llenarListas(r.cuerpo.vocabularios);
    pintarEjemplos(r.cuerpo.ejemplos);
    const primero = r.cuerpo.ejemplos[0];
    cargarTransacciones(primero.transacciones);
    marcarEjemplo(primero.id);
  } catch {
    $('ejemplos').textContent = 'No se pudieron cargar los ejemplos. Puedes pegar un JSON manualmente.';
    cargarTransacciones([]);
  }
}

iniciar();
