// Genera presentacion_final.pptx (exportar luego a PDF con LibreOffice o PowerPoint).
// Uso, desde la raiz del repositorio:
//   URL_SERVICIO=https://... node presentacion/generar_presentacion.js
// Requiere pptxgenjs (npm install pptxgenjs). Cifras: README raiz y
// Proyecto1/artefactos/causal_v2/resumen_metricas.json (resultados causales).
const path = require('path');
const fs = require('fs');
const pptxgen = require('pptxgenjs');

const RAIZ = path.resolve(__dirname, '..');
const URL_SERVICIO = process.env.URL_SERVICIO || '';
const URL_REPO = 'github.com/Jorge162017/P1-DeepLearning';
const SALIDA = path.join(__dirname, 'presentacion_final.pptx');

const metricas = JSON.parse(fs.readFileSync(
  path.join(RAIZ, 'Proyecto1/artefactos/causal_v2/resumen_metricas.json'), 'utf8'));
const verificacionRender = path.join(RAIZ, 'evidencias/verificacion_render.json');
const render = fs.existsSync(verificacionRender)
  ? JSON.parse(fs.readFileSync(verificacionRender, 'utf8')) : null;

// Paleta: tinta (confianza), rojo senal (riesgo), verde azulado (legitimo).
const K = {
  tinta: '14213D', rojo: 'D62839', verde: '1B998B', ambar: 'C77D12',
  texto: '1B1F24', suave: '5B6470', fondoSuave: 'EEF2F7', blanco: 'FFFFFF',
  hielo: 'CADCFC', borde: 'D5DBE3',
};
const FUENTE_TIT = 'Cambria';
const FUENTE = 'Calibri';

const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9'; // 10 x 5.625 in
pres.author = 'Jorge López y Angel Herrarte';
pres.title = 'Riesgo de fraude transaccional en producción';
pres.theme = { headFontFace: FUENTE_TIT, bodyFontFace: FUENTE };

pres.defineSlideMaster({
  title: 'PORTADA',
  background: { color: K.tinta },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.6, y: 1.35, w: 8.8, h: 1.4,
      fontFace: FUENTE_TIT, fontSize: 36, bold: true, color: K.blanco, valign: 'bottom', align: 'left', margin: 0 },
      text: '' } },
    { placeholder: { options: { name: 'body', type: 'body', x: 0.6, y: 2.95, w: 8.8, h: 1.3,
      fontFace: FUENTE, fontSize: 16, color: K.hielo, valign: 'top', margin: 0 }, text: '' } },
  ],
});

pres.defineSlideMaster({
  title: 'CONTENIDO',
  background: { color: K.blanco },
  margin: [0.5, 0.5, 0.5, 0.5],
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.5, y: 0.28, w: 7.8, h: 0.7,
      fontFace: FUENTE_TIT, fontSize: 26, bold: true, color: K.tinta, valign: 'middle', align: 'left', margin: 0 },
      text: '' } },
    { text: { text: 'Riesgo transaccional · Proyecto final · Deep Learning 2026',
      options: { x: 0.5, y: 5.22, w: 6, h: 0.25, fontFace: FUENTE, fontSize: 9, color: K.suave, margin: 0 } } },
  ],
  slideNumber: { x: 9.0, y: 5.22, w: 0.5, h: 0.25, fontFace: FUENTE, fontSize: 9, color: K.suave, align: 'right' },
});

// ---------- Utilidades ----------
let n = 0;
const nombre = (s) => `${s}_${++n}`;

// Motivo visual: secuencia de transacciones; la ultima (ancla) resaltada.
function secuencia(slide, x, y, { cantidad = 20, d = 0.16, gap = 0.08, color = K.hielo, ancla = K.rojo } = {}) {
  for (let i = 0; i < cantidad; i++) {
    slide.addShape(pres.shapes.OVAL, {
      x: x + i * (d + gap), y, w: d, h: d,
      fill: { color: i === cantidad - 1 ? ancla : color },
      line: { color: i === cantidad - 1 ? ancla : color },
      objectName: nombre('evento'),
    });
  }
}

// Etiqueta de presentador (quien expone la diapositiva).
function presentador(slide, quien) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 8.5, y: 0.42, w: 1.0, h: 0.32, rectRadius: 0.16,
    fill: { color: K.fondoSuave }, line: { color: K.fondoSuave }, objectName: nombre('presentador'),
  });
  slide.addText(quien, { x: 8.5, y: 0.42, w: 1.0, h: 0.32, fontFace: FUENTE, fontSize: 10,
    color: K.tinta, bold: true, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
}

function numero(slide, x, y, texto, color) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: 0.42, h: 0.42, fill: { color }, line: { color },
    objectName: nombre('numero') });
  slide.addText(texto, { x, y, w: 0.42, h: 0.42, fontFace: FUENTE, fontSize: 14, bold: true,
    color: K.blanco, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
}

function tarjeta(slide, x, y, w, h, { fondo = K.fondoSuave } = {}) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08,
    fill: { color: fondo }, line: { color: fondo }, objectName: nombre('tarjeta') });
}

function texto(slide, contenido, opciones) {
  slide.addText(contenido, { fontFace: FUENTE, color: K.texto, margin: 0, valign: 'top',
    isTextBox: true, ...opciones });
}

function cifra(slide, x, y, w, valor, etiqueta, color = K.tinta) {
  texto(slide, valor, { x, y, w, h: 0.62, fontFace: FUENTE_TIT, fontSize: 30, bold: true, color });
  texto(slide, etiqueta, { x, y: y + 0.64, w, h: 0.5, fontSize: 12, color: K.suave });
}

function vinetas(items, tam = 14) {
  return items.map((t, i) => ({
    text: t, options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 6, fontSize: tam },
  }));
}

const f3 = (x) => x.toFixed(3);
const auc = metricas.auc_pr;
const prueba = metricas.metricas_prueba;

// ---------- 1. Portada ----------
pres.addSection({ title: 'Inicio' });
let s = pres.addSlide({ masterName: 'PORTADA', sectionTitle: 'Inicio' });
s.addText('Riesgo de fraude transaccional en producción', { placeholder: 'title' });
s.addText([
  { text: 'Modelo B (GRU) del Proyecto 1 como servicio web', options: { breakLine: true } },
  { text: 'Jorge López · Angel Herrarte', options: { breakLine: true, bold: true, color: K.blanco } },
  { text: 'Deep Learning y Sistemas Inteligentes · Universidad del Valle · noviembre 2026' },
], { placeholder: 'body' });
secuencia(s, 0.6, 0.85);
texto(s, '19 transacciones de historia + 1 que se evalúa', { x: 0.6, y: 1.08, w: 6, h: 0.3,
  fontSize: 11, color: K.hielo });
s.addNotes('Jorge abre (20 s): presentarse ambos. Mensaje central: llevamos a producción la GRU del ' +
  'Proyecto 1, que puntúa el riesgo de una transacción usando el orden de las 19 anteriores. ' +
  'Primera mitad Jorge (problema, modelo, validación); segunda mitad Angel (arquitectura, demo, evidencias, límites).');

// ---------- 2. Problema ----------
pres.addSection({ title: 'Problema y modelo' });
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Problema y modelo' });
s.addText('¿Aporta el orden de las transacciones?', { placeholder: 'title' });
presentador(s, 'Jorge');
const columnas = [
  ['1', 'Problema', 'Un motor antifraude usa agregados (montos, frecuencia, ciudades). ¿La secuencia aporta información adicional y reduce el costo de errores?', K.tinta],
  ['2', 'Usuario', 'Analista de fraude que prioriza revisiones. Opcional: motor de autorización que usa el puntaje como señal extra.', K.verde],
  ['3', 'Decisión', 'Revisar, permitir o bloquear según su propia política. El servicio entrega puntaje y versión; no bloquea.', K.rojo],
];
columnas.forEach(([num, titulo, desc, color], i) => {
  const x = 0.5 + i * 3.07;
  tarjeta(s, x, 1.2, 2.86, 2.45);
  numero(s, x + 0.2, 1.38, num, color);
  texto(s, titulo, { x: x + 0.75, y: 1.42, w: 1.9, h: 0.36, fontSize: 18, bold: true, color: K.tinta });
  texto(s, desc, { x: x + 0.2, y: 1.98, w: 2.46, h: 1.6, fontSize: 14 });
});
cifra(s, 0.5, 3.92, 3, 'Q4,200', 'costo por fraude no detectado (FN)', K.rojo);
cifra(s, 3.57, 3.92, 3, 'Q180', 'costo por legítima bloqueada (FP)', K.tinta);
texto(s, 'Costos del caso simulado del Proyecto 1, no de un banco real.', { x: 6.64, y: 4.05, w: 2.86,
  h: 0.8, fontSize: 12, color: K.suave, italic: true });
s.addNotes('Jorge (50 s): la unidad de predicción es una transacción con sus 19 previas de la misma tarjeta. ' +
  'El usuario es un analista que prioriza revisiones. El modelo no decide: entrega un puntaje y el ' +
  'consumidor aplica su política. Los costos FN/FP vienen del caso simulado.');

// ---------- 3. Planificacion ----------
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Problema y modelo' });
s.addText('Planificación: 11 al 15 de noviembre', { placeholder: 'title' });
presentador(s, 'Jorge');
const etapas = [
  ['11 nov', 'Jorge', 'Preparación causal, reentrenamiento de A, B y C, cargador CPU, API y reproducción limpia (134 pruebas)', K.tinta],
  ['13 nov', 'Angel', 'Interfaz web, imagen Docker verificada en Linux, configuración de Render y monitoreo', K.verde],
  ['14 nov', 'Angel · ambos', 'Publicación, pruebas desde otro dispositivo, diapositivas y revisión conjunta', K.ambar],
  ['15 nov', 'Ambos', 'Ensayo, revisión de enlaces y entrega antes de las 23:59', K.rojo],
];
s.addShape(pres.shapes.LINE, { x: 0.75, y: 1.62, w: 8.5, h: 0, line: { color: K.borde, width: 2 },
  objectName: nombre('linea_tiempo') });
etapas.forEach(([fecha, quien, desc, color], i) => {
  const x = 0.5 + i * 2.3;
  s.addShape(pres.shapes.OVAL, { x: x + 0.12, y: 1.47, w: 0.3, h: 0.3, fill: { color }, line: { color },
    objectName: nombre('hito') });
  texto(s, fecha, { x, y: 1.95, w: 2.1, h: 0.4, fontFace: FUENTE_TIT, fontSize: 20, bold: true, color });
  texto(s, quien, { x, y: 2.37, w: 2.1, h: 0.3, fontSize: 12, bold: true, color: K.suave });
  texto(s, desc, { x, y: 2.72, w: 2.1, h: 1.6, fontSize: 14 });
});
texto(s, 'La interfaz y el despliegue estaban planificados para el 11 y 12 de noviembre; se completaron el 13. ' +
  'Detalle por etapa en la sección 2 del README.', { x: 0.5, y: 4.55, w: 9, h: 0.5, fontSize: 12,
  color: K.suave, italic: true });
s.addNotes('Jorge (40 s): reparto en pareja. Jorge: datos, modelo, API. Angel: interfaz, despliegue, ' +
  'evidencias y presentación. Mencionar el retraso de la interfaz (13 en vez de 11-12) y que no afectó la entrega.');

// ---------- 4. Supuestos ----------
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Problema y modelo' });
s.addText('Supuestos sobre datos, usuario y entorno', { placeholder: 'title' });
presentador(s, 'Jorge');
const cab = (t) => ({ text: t, options: { bold: true, color: K.blanco, fill: { color: K.tinta } } });
s.addTable([
  [cab('Mecanismo'), cab('Patrón simulado'), cab('Disponible en')],
  ['F1', 'Compras pequeñas en rampa y un cobro grande', 'Todas las particiones'],
  ['F2', 'Ciudades lejanas con poca separación temporal', 'Todas las particiones'],
  ['F3', 'Ráfaga de ecommerce caro de madrugada', 'Todas las particiones'],
  [{ text: 'F4', options: { color: K.rojo, bold: true } }, 'Goteo lento: cargos pequeños recurrentes',
    { text: 'Solo prueba', options: { color: K.rojo, bold: true } }],
], { x: 0.5, y: 1.2, w: 5.2, colW: [1.0, 2.7, 1.5], fontFace: FUENTE, fontSize: 12, color: K.texto,
  border: { type: 'solid', pt: 0.75, color: K.borde }, rowH: 0.48, valign: 'middle', margin: 0.06 });
texto(s, 'Además, un señuelo legítimo parecido a F1 para comprobar que el modelo no solo reacciona al monto.',
  { x: 0.5, y: 3.75, w: 5.2, h: 0.6, fontSize: 12, color: K.suave, italic: true });
tarjeta(s, 6.0, 1.2, 3.5, 3.55);
texto(s, vinetas([
  'Datos sintéticos: 6,000 tarjetas, 180 días, 484,738 transacciones.',
  'El consumidor envía 1 a 20 eventos de una tarjeta, en orden; sin etiquetas.',
  'El servicio corre en CPU y no guarda historial.',
  'Tiempo en días desde un origen fijo; fechas reales requieren conversión.',
]), { x: 6.2, y: 1.38, w: 3.1, h: 3.25 });
s.addNotes('Jorge (45 s): todo es sintético y lo diseñamos nosotros, por eso no afirmamos desempeño bancario. ' +
  'F4 solo aparece en prueba: es un fraude que el modelo nunca vio. El servicio recibe la ventana completa ' +
  'en cada petición; no consulta historial.');

// ---------- 5. Modelo ----------
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Problema y modelo' });
s.addText('Modelo B: GRU sobre la secuencia de eventos', { placeholder: 'title' });
presentador(s, 'Jorge');
const capas = [
  ['20 eventos', 'rubro, canal, ciudad + 7 numéricas'],
  ['Embeddings', '3 × dimensión 8'],
  ['GRU', '1 capa, estado 64'],
  ['Cabeza', '64 → 32 → 1, dropout 0.2'],
  ['Puntaje', 'sigmoide, 0 a 1'],
];
capas.forEach(([t, d], i) => {
  const x = 0.5 + i * 1.86;
  const ultimo = i === capas.length - 1;
  tarjeta(s, x, 1.25, 1.6, 1.15, { fondo: ultimo ? K.tinta : K.fondoSuave });
  texto(s, t, { x: x + 0.12, y: 1.37, w: 1.36, h: 0.36, fontSize: 15, bold: true, color: ultimo ? K.blanco : K.tinta });
  texto(s, d, { x: x + 0.12, y: 1.75, w: 1.36, h: 0.6, fontSize: 12, color: ultimo ? K.hielo : K.suave });
  if (!ultimo) {
    s.addShape(pres.shapes.RIGHT_TRIANGLE, { x: x + 1.65, y: 1.73, w: 0.16, h: 0.2, rotate: 0,
      fill: { color: K.borde }, line: { color: K.borde }, flipH: false, objectName: nombre('flecha') });
  }
});
tarjeta(s, 0.5, 2.75, 4.4, 2.15, { fondo: 'FDECEE' });
texto(s, 'Cambio justificado', { x: 0.7, y: 2.9, w: 4.0, h: 0.35, fontSize: 16, bold: true, color: K.rojo });
texto(s, 'La ciudad base se calculaba con toda la historia de la tarjeta, incluido el futuro. Ahora usa ' +
  'solo las 19 transacciones previas. Se reentrenaron A, B y C con la misma preparación, sin tocar arquitectura ni épocas.',
  { x: 0.7, y: 3.3, w: 4.0, h: 1.55, fontSize: 14 });
s.addTable([
  [cab('Modelo'), cab('Entrada')],
  ['A · línea base', 'Boosting con 15 agregados de la ventana'],
  [{ text: 'B · servicio', options: { bold: true } }, 'Secuencia de eventos (GRU)'],
  ['C · híbrido', 'GRU + los 15 agregados'],
], { x: 5.1, y: 2.75, w: 4.4, colW: [1.4, 3.0], fontFace: FUENTE, fontSize: 12, color: K.texto,
  border: { type: 'solid', pt: 0.75, color: K.borde }, rowH: 0.42, valign: 'middle', margin: 0.06 });
s.addNotes('Jorge (60 s): reutilizamos la GRU del Proyecto 1 sin cambiar arquitectura. El cambio importante ' +
  'fue de datos: la ciudad base miraba el futuro, una fuga de información. Al corregirla, reentrenamos los tres ' +
  'modelos con la misma preparación para comparar en igualdad. 12 épocas, Adam 0.001, semilla 42; se restaura ' +
  'la mejor época por AUC-PR de validación.');

// ---------- 6. Validacion ----------
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Problema y modelo' });
s.addText('Hipótesis frente a la línea base', { placeholder: 'title' });
presentador(s, 'Jorge');
s.addChart(pres.charts.BAR, [
  { name: 'Validación', labels: ['A · base', 'B · GRU', 'C · híbrido'], values: ['A', 'B', 'C'].map((m) => auc[m].validacion) },
  { name: 'Prueba', labels: ['A · base', 'B · GRU', 'C · híbrido'], values: ['A', 'B', 'C'].map((m) => auc[m].prueba) },
], {
  x: 0.4, y: 1.1, w: 4.9, h: 3.9, barDir: 'col', barGapWidthPct: 60,
  chartColors: [K.tinta, '9AA7BD'], showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0.000',
  dataLabelFontSize: 10, dataLabelColor: K.texto, dataLabelFontFace: FUENTE,
  valAxisMinVal: 0, valAxisMaxVal: 1, valAxisLabelFormatCode: '0.0', valAxisLabelFontSize: 10,
  catAxisLabelFontSize: 11, catAxisLabelColor: K.suave, valAxisLabelColor: K.suave,
  catAxisLabelFontFace: FUENTE, valAxisLabelFontFace: FUENTE,
  valGridLine: { color: 'E3E7ED', size: 0.5 }, catGridLine: { style: 'none' },
  showLegend: true, legendPos: 'b', legendFontSize: 11, legendFontFace: FUENTE, legendColor: K.suave,
  showTitle: true, title: 'AUC-PR (average precision)', titleFontSize: 13, titleColor: K.tinta, titleFontFace: FUENTE,
});
const dif = auc.B.validacion - auc.A.validacion;
const difC = auc.C.validacion - auc.B.validacion;
const hallazgos = [
  ['✓', `B supera a A por +${f3(dif)} en validación`, 'La secuencia aporta frente a agregados de la misma ventana.', K.verde],
  ['✗', `C: pedía +0.020 sobre B; quedó ${f3(difC)}`, 'Criterio fijado antes de entrenar. La hipótesis de C no se cumplió.', K.rojo],
  ['=', 'Se mantiene B en el servicio', 'C rinde algo mejor en prueba, pero no se elige mirando prueba.', K.tinta],
];
hallazgos.forEach(([icono, titulo, desc, color], i) => {
  const y = 1.2 + i * 1.25;
  numero(s, 5.6, y, icono, color);
  texto(s, titulo, { x: 6.15, y: y - 0.02, w: 3.35, h: 0.5, fontSize: 15, bold: true, color: K.tinta });
  texto(s, desc, { x: 6.15, y: y + 0.48, w: 3.35, h: 0.6, fontSize: 12, color: K.suave });
});
s.addNotes(`Jorge (70 s): métrica AUC-PR por el desbalance; no usamos exactitud. B ${f3(auc.B.validacion)} contra A ` +
  `${f3(auc.A.validacion)} en validación. Para C el criterio, fijado antes, era superar al mejor por 0.02; quedó ` +
  `${f3(-difC)} por debajo de B, así que no se cumplió. Prueba ya se observó en Proyecto 1: es una reevaluación, ` +
  'no una prueba independiente. No cambiamos la selección mirando prueba.');

// ---------- 7. Orden y costos ----------
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Problema y modelo' });
s.addText('B usa el orden, y reduce falsos positivos', { placeholder: 'title' });
presentador(s, 'Jorge');
const perm = metricas.permutacion.B;
s.addChart(pres.charts.BAR, [{ name: 'B', labels: ['Orden original', 'P1: barajar historia', 'P2: barajar todo'],
  values: [auc.B.validacion, perm.P1, perm.P2] }], {
  x: 0.4, y: 1.1, w: 4.4, h: 3.6, barDir: 'col', barGapWidthPct: 70,
  chartColors: [K.tinta, K.ambar, K.rojo], showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0.000',
  dataLabelFontSize: 10, dataLabelColor: K.texto, dataLabelFontFace: FUENTE,
  valAxisMinVal: 0, valAxisMaxVal: 1, valAxisLabelFormatCode: '0.0', valAxisLabelFontSize: 10,
  catAxisLabelFontSize: 11, catAxisLabelColor: K.suave, valAxisLabelColor: K.suave,
  catAxisLabelFontFace: FUENTE, valAxisLabelFontFace: FUENTE,
  valGridLine: { color: 'E3E7ED', size: 0.5 }, catGridLine: { style: 'none' }, showLegend: false,
  showTitle: true, title: 'AUC-PR de B en validación al barajar', titleFontSize: 13, titleColor: K.tinta, titleFontFace: FUENTE,
});
const fila = (m, resaltar) => {
  const p = prueba[m];
  const o = resaltar ? { bold: true } : {};
  const costo = metricas.economia[m].costo_bloque.toLocaleString('en-US');
  return [{ text: m, options: o }, { text: p.precision.toFixed(2), options: o },
    { text: p.exhaustividad.toFixed(2), options: o }, { text: String(p.fp), options: o },
    { text: String(p.fn), options: o }, { text: `Q${costo}`, options: o }];
};
s.addTable([
  [cab('Prueba'), cab('Precisión'), cab('Exhaust.'), cab('FP'), cab('FN'), cab('Costo')],
  fila('A'), fila('B', true), fila('C'),
], { x: 5.05, y: 1.25, w: 4.45, colW: [0.6, 0.8, 0.75, 0.55, 0.55, 1.2], fontFace: FUENTE, fontSize: 12,
  color: K.texto, border: { type: 'solid', pt: 0.75, color: K.borde }, rowH: 0.42, valign: 'middle',
  align: 'center', margin: 0.04 });
texto(s, vinetas([
  `B reduce falsos positivos de ${prueba.A.fp} a ${prueba.B.fp} frente a A con exhaustividad similar.`,
  'F2 y F3: exhaustividad 1.0. F4: 0.0 en los tres modelos.',
], 13), { x: 5.05, y: 3.15, w: 4.45, h: 1.2 });
texto(s, 'Umbral elegido en validación minimizando 4200·FN + 180·FP. Costos simulados.',
  { x: 5.05, y: 4.45, w: 4.45, h: 0.4, fontSize: 11, color: K.suave, italic: true });
s.addNotes(`Jorge (50 s): al barajar la historia y mantener el ancla, B cae de ${f3(auc.B.validacion)} a ` +
  `${f3(perm.P1)}: usa el orden. A no cambia porque no lee secuencia. En prueba, con el umbral de validación, ` +
  `B reduce FP de ${prueba.A.fp} a ${prueba.B.fp}. Ningún modelo detecta F4. Aquí Jorge cede la palabra a Angel.`);

// ---------- 8. Arquitectura ----------
pres.addSection({ title: 'Producción' });
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Producción' });
s.addText('Arquitectura: entrenar fuera, servir en línea', { placeholder: 'title' });
presentador(s, 'Angel');
tarjeta(s, 0.5, 1.15, 3.6, 3.85);
texto(s, 'FUERA DE LÍNEA · una vez', { x: 0.7, y: 1.27, w: 3.2, h: 0.3, fontSize: 11, bold: true, color: K.suave });
const off = ['Generador sintético', 'Preparación causal', 'Entrenamiento A, B, C', 'Validación y paridad CPU'];
off.forEach((t, i) => {
  const y = 1.65 + i * 0.6;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.75, y, w: 3.1, h: 0.42, rectRadius: 0.06,
    fill: { color: K.blanco }, line: { color: K.borde, width: 1 }, objectName: nombre('paso_off') });
  texto(s, t, { x: 0.9, y, w: 2.8, h: 0.42, fontSize: 13, valign: 'middle' });
});
s.addShape(pres.shapes.CAN, { x: 0.75, y: 4.1, w: 3.1, h: 0.7, fill: { color: K.tinta }, line: { color: K.tinta },
  objectName: nombre('artefactos') });
texto(s, 'artefactos/causal_v2 (pesos, escaladores, metadatos)', { x: 0.85, y: 4.22, w: 2.9, h: 0.55,
  fontSize: 11, color: K.blanco, align: 'center', valign: 'middle' });

s.addShape(pres.shapes.LINE, { x: 3.9, y: 4.45, w: 0.85, h: 0, line: { color: K.tinta, width: 1.5, endArrowType: 'triangle' },
  objectName: nombre('copia') });
texto(s, 'se copian a la imagen', { x: 3.9, y: 4.55, w: 1.0, h: 0.4, fontSize: 9, color: K.suave, align: 'center' });

tarjeta(s, 4.85, 1.15, 4.65, 3.85, { fondo: 'E7F5F3' });
texto(s, 'EN LÍNEA · contenedor Docker en Render', { x: 5.05, y: 1.27, w: 4.3, h: 0.3, fontSize: 11, bold: true, color: K.verde });
const caja = (x, y, w, h, t, sub, fondo = K.blanco, color = K.texto) => {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: fondo },
    line: { color: fondo === K.blanco ? K.borde : fondo, width: 1 }, objectName: nombre('caja') });
  texto(s, [{ text: t, options: { bold: true, breakLine: !!sub } }, ...(sub ? [{ text: sub, options: { fontSize: 10 } }] : [])],
    { x: x + 0.1, y, w: w - 0.2, h, fontSize: 12, valign: 'middle', color });
};
caja(5.1, 1.65, 2.05, 0.7, 'Cargador B (CPU)', 'verifica huellas y versión');
caja(5.1, 2.65, 2.05, 0.7, 'FastAPI', '/predict · /health', K.tinta, K.blanco);
caja(5.1, 3.65, 2.05, 0.7, 'Registros JSON', 'sin datos de transacciones');
caja(7.35, 2.65, 1.95, 0.7, 'Interfaz web /', 'mismo origen');
caja(7.35, 1.65, 1.95, 0.7, 'Analista o externo', 'navegador', K.rojo, K.blanco);
caja(7.35, 3.65, 1.95, 0.7, 'Logs y health check', 'panel de Render');
const flecha = (x, y, w, h) => s.addShape(pres.shapes.LINE, { x, y, w, h,
  line: { color: K.suave, width: 1.25, endArrowType: 'triangle' }, objectName: nombre('flecha') });
flecha(6.12, 2.35, 0, 0.3);
flecha(6.12, 3.35, 0, 0.3);
flecha(8.32, 2.35, 0, 0.3);
flecha(7.35, 3.0, -0.2, 0);
flecha(7.15, 4.0, 0.2, 0);
s.addNotes('Angel (60 s): separamos dos mundos. Fuera de línea se genera, entrena y valida; el resultado son ' +
  'artefactos versionados. En línea solo se cargan: el servicio nunca entrena. Un solo contenedor Docker sirve ' +
  'la API y la interfaz desde el mismo origen, sin CORS. Si un artefacto no coincide con su huella, no arranca. ' +
  'Cada solicitud deja un registro JSON con ID, estado, duración y versión, sin montos ni ciudades.');

// ---------- 9. Demo ----------
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Producción' });
s.addText('Demo: una persona externa obtiene puntaje', { placeholder: 'title' });
presentador(s, 'Angel');
const capturas = path.join(RAIZ, 'evidencias/capturas');
const inicio = fs.existsSync(path.join(capturas, 'render_inicio.png')) ? 'render_inicio.png' : 'local_inicio.png';
const resultado = fs.existsSync(path.join(capturas, 'render_resultado_f3.png')) ? 'render_resultado_f3.png' : 'local_resultado_f3.png';
s.addImage({ path: path.join(capturas, inicio), x: 0.5, y: 1.15, w: 5.2, h: 3.25, objectName: 'captura_interfaz',
  altText: 'Interfaz web con ejemplos sintéticos de transacciones legítimas y fraudulentas' });
s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.15, w: 5.2, h: 3.25, fill: { type: 'none' },
  line: { color: K.borde, width: 1 }, objectName: nombre('marco') });
s.addImage({ path: path.join(capturas, resultado), x: 5.95, y: 1.15, w: 3.55, h: 0.91, objectName: 'captura_resultado',
  altText: 'Resultado: puntaje 0.9998 por encima del umbral de referencia 0.734' });
texto(s, vinetas([
  'Elegir un ejemplo o pegar JSON (1 a 20 eventos).',
  'Calcular: puntaje, umbral de referencia, versión e ID de solicitud.',
  'Errores claros: un monto negativo marca la celda (422).',
], 13), { x: 5.95, y: 2.3, w: 3.55, h: 1.9 });
tarjeta(s, 0.5, 4.55, 9.0, 0.5, { fondo: K.tinta });
texto(s, URL_SERVICIO ? `Probar en vivo: ${URL_SERVICIO}` : 'Probar en vivo: enlace público pendiente de publicar',
  { x: 0.7, y: 4.55, w: 8.6, h: 0.5, fontSize: 14, bold: true, color: K.blanco, valign: 'middle' });
s.addNotes('Angel (90 s): DEMO EN VIVO. Abrir la URL unos minutos antes (el plan gratuito duerme tras 15 min). ' +
  '1) Legítima habitual: puntaje casi 0. 2) Fraude F3: 0.9998, por encima del umbral. 3) Fraude F1: 0.04, ' +
  'un falso negativo real, lo mostramos a propósito. 4) Cambiar un monto a -5: error 422 en la celda. ' +
  'Si falla la red, usar estas capturas.');

// ---------- 10. Evidencias ----------
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Producción' });
s.addText('Evidencias del pase a producción', { placeholder: 'title' });
presentador(s, 'Angel');
const stats = render
  ? [['6/6', 'casos idénticos en Render (tolerancia 1e-6)', K.verde],
     [`${Math.round(render.latencia_cliente_ms.mediana)} ms`, 'mediana de latencia desde el cliente', K.tinta],
     ['140', 'pruebas automáticas aprobadas', K.tinta],
     ['356 MiB', 'RAM del contenedor; plan de 512 MB', K.tinta]]
  : [['6/6', 'casos idénticos en Linux (tolerancia 1e-6)', K.verde],
     ['140', 'pruebas automáticas aprobadas', K.tinta],
     ['356 MiB', 'RAM del contenedor; plan de 512 MB', K.tinta],
     ['8.9e-8', 'diferencia máxima de puntaje', K.tinta]];
stats.forEach(([v, e, c], i) => cifra(s, 0.5 + i * 2.3, 1.2, 2.1, v, e, c));
s.addTable([
  [cab('Evidencia'), cab('Dónde')],
  ['Servicio público e interfaz', URL_SERVICIO || 'pendiente de publicar'],
  ['Verificación contra los seis casos', render ? 'evidencias/verificacion_render.json' : 'evidencias/verificacion_docker_linux_amd64.json'],
  ['Registros JSON por solicitud', 'evidencias/ y logs de Render'],
  ['Capturas de uso', 'evidencias/capturas/'],
  ['Suite de pruebas y reproducción limpia', 'Proyecto1/tests · docs/REPRODUCCION_LIMPIA.md'],
], { x: 0.5, y: 2.65, w: 9.0, colW: [3.4, 5.6], fontFace: FUENTE, fontSize: 12, color: K.texto,
  border: { type: 'solid', pt: 0.75, color: K.borde }, rowH: 0.36, valign: 'middle', margin: 0.06 });
s.addNotes('Angel (60 s): el verificador corre los seis casos guardados contra el servicio publicado y compara ' +
  'con tolerancia 1e-6. Todo está en la carpeta evidencias del repositorio. Los registros prueban el uso sin ' +
  'guardar datos sensibles.');

// ---------- 11. Operacion ----------
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Producción' });
s.addText('Operación y monitoreo', { placeholder: 'title' });
presentador(s, 'Angel');
tarjeta(s, 0.5, 1.15, 4.4, 3.3, { fondo: 'E7F5F3' });
numero(s, 0.7, 1.32, '✓', K.verde);
texto(s, 'Implementado', { x: 1.25, y: 1.36, w: 3.4, h: 0.36, fontSize: 18, bold: true, color: K.verde });
texto(s, vinetas([
  'Salud: GET /health y health check de Render.',
  'Registro JSON por solicitud: fecha, ID, ruta, estado, duración y versión.',
  'Errores: filtrar estado 422 y 5xx en los logs.',
  'Latencia: duracion_ms en servidor y verificador desde el cliente.',
], 13), { x: 0.75, y: 1.95, w: 3.95, h: 2.9 });
tarjeta(s, 5.1, 1.15, 4.4, 3.3);
numero(s, 5.3, 1.32, '→', K.ambar);
texto(s, 'Propuesto', { x: 5.85, y: 1.36, w: 3.4, h: 0.36, fontSize: 18, bold: true, color: K.ambar });
texto(s, vinetas([
  'Deriva de datos: agregados diarios anónimos y PSI; PSI > 0.2 sostenido = revisar.',
  'Desempeño: recalcular AUC-PR con contracargos cada mes.',
  'Recalibrar el umbral si cambian prevalencia o costos.',
  'Reentrenar ante nuevos mecanismos (F4) con la misma validación causal.',
], 13), { x: 5.35, y: 1.95, w: 3.95, h: 2.9 });
s.addNotes('Angel (45 s): separamos lo que existe de lo que proponemos. Hoy: salud, registros y verificación. ' +
  'Propuesta: vigilar deriva con PSI y recalcular métricas con etiquetas tardías. Recalibrar si cambia la ' +
  'prevalencia o los costos; reentrenar si aparece un mecanismo nuevo.');

// ---------- 12. Limites y recomendacion ----------
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Producción' });
s.addText('Límites y recomendación al comité', { placeholder: 'title' });
presentador(s, 'Angel');
texto(s, 'Límites', { x: 0.5, y: 1.15, w: 4.4, h: 0.4, fontSize: 18, bold: true, color: K.rojo });
texto(s, vinetas([
  'F4 (goteo lento): exhaustividad 0 en los tres modelos.',
  'F1 puede pasar inadvertido; la demo muestra un caso.',
  'Datos y costos sintéticos: no se trasladan a un banco.',
  'Puntaje no calibrado; prueba ya vista en Proyecto 1.',
]), { x: 0.5, y: 1.65, w: 4.4, h: 3.0 });
tarjeta(s, 5.1, 1.15, 4.4, 3.85, { fondo: K.tinta });
texto(s, 'Recomendación', { x: 5.35, y: 1.35, w: 3.9, h: 0.4, fontSize: 18, bold: true, color: K.blanco });
texto(s, [
  { text: 'Mantener B en producción como demostración y señal de priorización, ', options: { color: K.blanco } },
  { text: 'no como bloqueo automático.', options: { color: K.blanco, bold: true, breakLine: true } },
  { text: ' ', options: { breakLine: true, fontSize: 6 } },
  { text: 'Antes de un uso real: validar con datos reales, calibrar el puntaje e implementar el monitoreo de deriva.',
    options: { color: K.hielo } },
], { x: 5.35, y: 1.9, w: 3.9, h: 2.9, fontSize: 15 });
s.addNotes('Angel (45 s): cerrar con la decisión que pide el comité. Recomendamos mantener B como ' +
  'demostración y señal de priorización, porque supera a la línea base y usa el orden, pero no como bloqueo ' +
  'automático por sus límites. Invitar a preguntas; cualquiera de los dos responde.');

// ---------- 13. Cierre ----------
pres.addSection({ title: 'Cierre' });
s = pres.addSlide({ masterName: 'PORTADA', sectionTitle: 'Cierre' });
s.addText('Gracias. ¿Preguntas?', { placeholder: 'title' });
s.addText([
  { text: URL_SERVICIO ? `Demo: ${URL_SERVICIO}` : 'Demo: enlace público pendiente', options: { breakLine: true } },
  { text: `Repositorio: ${URL_REPO}`, options: { breakLine: true } },
  { text: 'Jorge López · Angel Herrarte', options: { bold: true, color: K.blanco } },
], { placeholder: 'body' });
secuencia(s, 0.6, 0.85);
s.addNotes('Ambos responden. Preguntas probables: por qué AUC-PR, por qué no C, qué es la fuga corregida, ' +
  'qué pasa con F4, cómo se monitorearía la deriva, por qué Render y Docker, qué pasa si el servicio duerme.');

pres.writeFile({ fileName: SALIDA }).then(() => console.log(`Escrito ${path.relative(RAIZ, SALIDA)}`));
