# Proyecto final: distribución en pareja

Jorge López: primera mitad (modelo, inferencia y API).
Compañero: segunda mitad (interfaz, despliegue, evidencias y elaboración de toda
la presentación final: diapositivas y PDF).
Ambos: integración, revisión técnica, ensayo, exposición y respuestas a preguntas.

El PDF establece tríos; este plan sigue la decisión de trabajar en pareja.
Confirmen con el docente que acepta esa modalidad. Entrega: 15 de noviembre de
2026, 23:59; presentación de 10 minutos y 5 de preguntas (fechas del PDF: 9 y 13).

## Objetivo y alcance compartido

Publicar una demostración de detección de fraude con el modelo B (GRU) del
Proyecto 1. Una persona externa debe poder ingresar transacciones y obtener
un puntaje de riesgo sin entrenar el modelo ni preparar un entorno local.
Usar datos sintéticos y explicar sus límites; no presentar el demo como un
sistema bancario validado. No hace falta entrenar una arquitectura nueva.

## Primera mitad — Jorge

### 1. Preparación causal e inferencia (cambios iniciales implementados)

- [x] Separar características de etiquetas y particiones experimentales.
- [x] Calcular la ciudad base con las 19 transacciones anteriores al ancla,
  con desempate alfabético y ciudad actual cuando no existe historia.
- [x] Compartir preparación entre entrenamiento e inferencia y aceptar
  categorías desconocidas con índice 0.
- [x] Agregar pruebas de independencia del futuro y paridad de características.

### 2. Regenerar y validar el modelo

- [x] Reentrenar A, B y C con la preparación corregida y regenerar escaladores,
  pesos, resultados y figuras en `Proyecto1/artefactos/causal_v2/`. Los archivos
  directamente en `Proyecto1/artefactos/` conservan el Proyecto 1 original.
- [x] Mantener la hipótesis y el criterio original; documentar el cambio causal
  y comparar resultados anteriores y corregidos. No ajustar decisiones mirando
  repetidamente prueba; declarar que el conjunto ya se usó en Proyecto 1.
- [x] Recalcular umbrales en validación y reportar comparación con A, métricas
  de prueba, permutaciones y límites (incluido F4).
- [x] Guardar metadatos de versión del preprocesamiento, configuración,
  arquitectura, semilla, métricas y umbral junto a los nuevos artefactos.
- [x] Comprobar la exportación de pesos de B en CPU y la paridad del puntaje
  en seis casos guardados. Informe en `Proyecto1/docs/VALIDACION_CAUSAL.md`.
- [x] Implementar el cargador reutilizable de B y medir latencia en CPU;
  código en `Proyecto1/src/inferencia.py` y mediciones en
  `Proyecto1/docs/LATENCIA_CPU.md`. Integración local con la API completada.

### 3. API y contrato

- [x] Implementar carga única del modelo y escaladores al iniciar el servicio,
  evaluación con `eval()` y sin gradientes, y versiones compatibles.
- [x] Crear `POST /predict` y `GET /health`. Validar entrada y devolver errores
  claros, puntaje, versión del modelo y, si se expone, umbral y decisión sugerida.
- [x] Incorporar pruebas de predicción real con artefactos corregidos,
  datos inválidos, categorías nuevas y secuencias cortas.
- [x] Fijar dependencias reproducibles y documentar ejecución y ejemplo de uso.

Contrato implementado para coordinar la interfaz: JSON con `transacciones`, una lista
cronológica de 1 a 20 eventos de una sola tarjeta, cada uno con `marca_tiempo`
(días desde un origen fijo documentado), `monto` positivo en Q, `rubro`, `canal`
y `ciudad`. No se piden etiquetas. Ejemplo de formato de salida:
`{"puntaje_riesgo": 0.72, "version_modelo": "..."}`. El contrato completo y ejecutable está en `Proyecto1/docs/API.md`;
revisarlo juntos antes de desarrollar la conexión de la interfaz.

### 4. Documentación a cargo de Jorge

- [x] README raíz: problemática, usuario, decisión, supuestos, modelo planteado
  y validación de hipótesis. Distinguir resultados originales y corregidos.
- [x] Explicar ingeniería de características, esquema de entrada, origen de
  tiempo, categorías desconocidas, umbral, costos y limitaciones.

## Segunda mitad — Compañero

### 5. Interfaz de demostración

- [x] Crear una página para ingresar o pegar transacciones, con ejemplos
  sintéticos legítimos y sospechosos listos para ejecutar.
- [x] Mostrar puntaje y explicación de uso, estados de carga y errores de API.
  No presentar el puntaje como probabilidad calibrada sin comprobarlo.
- [x] Conectar con el contrato acordado y probar secuencias cortas y entradas
  inválidas. La API real ya está disponible en el repositorio; usarla para
  la integración y para todas las evidencias de la versión publicada.

### 6. Despliegue, monitoreo y pruebas de uso

- [x] Elegir hosting que soporte las dependencias de PyTorch y documentar
  configuración, arranque y ubicación de artefactos.
- [ ] Publicar API e interfaz y comprobar uso desde otro dispositivo o sesión.
- [x] Registrar fecha/hora, identificador de petición, versión de modelo,
  duración y resultado/estado de las solicitudes sin guardar datos sensibles.
- [x] Documentar cómo revisar salud, errores y latencia. Explicar qué harían
  ante deriva y cuándo recalibrar/reentrenar; distinguir propuesta e implementación.
- [ ] Reunir capturas, registros de uso y resultados de pruebas en `evidencias/`.
  Verificar que una persona ajena al equipo pueda completar una predicción.

### 7. Arquitectura y documentación a cargo del compañero

- [ ] README raíz: planificación con fechas/responsables, herramientas y
  arquitectura, evidencia de producción e instrucciones de acceso/ejecución.
- [x] Diagrama: datos → preparación → entrenamiento → artefactos → servicio →
  interfaz, más registros/monitoreo. Aclarar qué ocurre fuera de línea y en línea.
- [ ] Agregar enlaces reales al servicio, API, evidencias y presentación PDF.

Avance del 13 nov (Angel): interfaz en `Proyecto1/web/` servida por la API,
Docker verificado en Linux, `render.yaml`, verificador y `docs/DESPLIEGUE.md`
en el PR `companero/interfaz-deploy`. Falta publicar en Render, capturas,
prueba externa, enlaces finales y la presentación.

### 8. Presentación completa — Compañero

- [ ] Crear **todas** las diapositivas: problemática, usuario y decisión,
  planificación, supuestos, modelo, validación de hipótesis, arquitectura,
  demo, evidencias, operación y limitaciones. Jorge no tiene asignada la
  elaboración de diapositivas.
- [ ] Usar el README raíz y `Proyecto1/docs/VALIDACION_CAUSAL.md` como fuentes
  de las cifras corregidas. Explicar por qué se mantiene B y por qué C no
  cumplió su criterio; no tomar las métricas históricas como resultados actuales.
- [ ] Ajustar el material a 10 minutos, preparar la demostración y exportar
  el PDF final dentro del repositorio, enlazándolo desde el README raíz.
  El PDF de Proyecto 1 es material de partida y no la entrega final.
- [ ] Compartir el material con Jorge para que ambos puedan revisarlo, ensayar
  y responder preguntas. Crear el material corresponde al compañero; la
  participación oral y el dominio del contenido corresponden a ambos.


## Integración y cierre — ambos

- [ ] Revisar juntos el contrato y los resultados de las pruebas, comprobar
  la integración y poder explicar cualquier archivo o decisión.
- [ ] Completar las siete secciones del README raíz y actualizar declaración
  de IA con los usos del final y lo verificado por ustedes.
- [ ] Ensayar 10 minutos: Jorge presenta problema/modelo/validación (5 minutos)
  y compañero arquitectura/demo/evidencias/límites (5 minutos). Ambos responden.
- [x] Clonar en un entorno limpio y seguir el README para verificar reproducción.
  Verificación en clon local independiente: 134 pruebas y HTTP real correctos.
  Informe: `Proyecto1/docs/REPRODUCCION_LIMPIA.md`.
- [ ] Verificar repositorio público o compartido con docente, enviar el enlace
  antes del límite y confirmar que la última versión incluye todos los archivos.

## Plan de fechas sugerido

| Fecha | Jorge | Compañero |
|---|---|---|
| 11 nov | Preparación causal, pruebas, contrato y reentrenamiento | Interfaz inicial y selección de hosting |
| 12 nov | API, nuevos artefactos y validación | Conexión de interfaz, despliegue y registros |
| 13 nov | Integración y presentación si corresponde | Demo, evidencias y presentación si corresponde |
| 14 nov | Revisar integración y estudiar material para exponer | Pruebas externas, todas las diapositivas, PDF y README |
| 15 nov | Revisar entrega y enlaces con margen antes de 23:59 | Revisar entrega y enlaces con margen antes de 23:59 |

## Dónde desplegar — decisión e implementación del compañero

Opciones revisadas el **11 de noviembre de 2026**. Esta sección es una guía para
el compañero; todavía no se ha contratado ni desplegado ningún servicio.
Confirmar precio y disponibilidad en la cuenta antes de activar un plan.

### Recomendación: Render para la API

Render tiene una [guía oficial para FastAPI](https://render.com/docs/deploy-fastapi)
y permite conectar el repositorio de GitHub a un Web Service. Es la ruta sugerida
para publicar la API actual sin cambiar el framework. Elegir el plan después
de medir consumo de memoria en Linux; **2 GB es un punto de partida propuesto**,
no una necesidad medida ni una garantía de capacidad.

El plan Free tiene 512 MB de RAM y se suspende tras 15 minutos sin tráfico;
al reactivarse hay una espera. Su memoria podría resultar insuficiente para
PyTorch y las demás librerías aunque los pesos sean pequeños. No hemos medido
este proceso en ese plan. Fuentes: [planes de cómputo](https://render.com/docs/compute-plans)
y [límites del plan gratuito](https://render.com/docs/free). Para una demo con
horario fijo, valorar un plan de pago y revisar su costo antes de elegirlo.

Configuración inicial propuesta para que el compañero la verifique
([versión de Python en Render](https://render.com/docs/python-version)):

| Parámetro | Valor |
|---|---|
| Repositorio / rama | `Jorge162017/P1-DeepLearning`, `main` |
| Servicio | Web Service de Python |
| Root Directory | `Proyecto1` |
| Python | `3.13.12` mediante `PYTHON_VERSION` |
| Instalación | `python -m pip install -r requirements-api.txt` |
| Start Command | `python -m uvicorn src.api:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Hilos | `RIESGO_HILOS=1` inicialmente; ajustar a los recursos y medir |
| Artefactos | `artefactos/causal_v2/`, incluidos en Git |

La instalación limpia que verificamos es de macOS ARM64. El compañero debe
validar instalación y puntajes en Linux, usar la distribución de PyTorch para
CPU que corresponda ([selector oficial](https://pytorch.org/get-started/locally/))
y comprobar que no se descarguen dependencias de GPU innecesarias. Conservar las
versiones entrenadas y registrar cualquier ajuste de dependencias para el hosting.
No volver a entrenar durante el arranque o el despliegue.

Para la interfaz, un **Static Site de Render** sirve si el resultado es HTML/CSS/JS
estático; esa modalidad está descrita en [Render Free](https://render.com/docs/free).
Si la interfaz necesita un servidor propio, elegir el servicio adecuado a su
framework. Cuando navegador y API estén en orígenes distintos, el compañero debe
configurar CORS para el origen publicado de la interfaz y probarlo en navegador;
la API actual todavía no incluye esa configuración. Documentar las URLs finales.

### Alternativa: Hugging Face Spaces con Docker

Es una opción orientada a demos de modelos. Usar un Space Docker que arranque
FastAPI en `0.0.0.0:7860`, con `sdk: docker` y `app_port: 7860`; hace falta crear
y probar el Dockerfile. Ver [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker).

CPU Basic ofrece 2 vCPU y 16 GB de RAM, sin costo por hora de ese hardware, pero
**no asumir que crear un Space Docker sea gratuito**: la documentación actual
indica un plan de pago para crear nuevos Spaces de cómputo. Revisar las condiciones
de la cuenta. Fuentes: [Spaces Overview](https://huggingface.co/docs/hub/en/spaces-overview)
y [hardware y suspensión](https://huggingface.co/docs/hub/spaces-gpus).

### Criterios para dar por terminado el despliegue

- [ ] Elegir proveedor y presupuesto; registrar la configuración real.
- [ ] Conseguir `/health` público en estado correcto y comprobar los seis casos
  guardados contra `casos_inferencia.json` en el hosting, con tolerancia 1e-6.
  Investigar diferencias; no cambiar la tolerancia solo para ocultarlas.
- [ ] Conectar la interfaz a la API real, probar errores y confirmar CORS si aplica.
- [ ] Medir RAM, arranque y latencia en el servidor; las cifras locales no
  describen automáticamente el rendimiento de un plan de hosting.
- [ ] Probar desde otro dispositivo o sesión y guardar capturas y registros
  de uso sin transacciones sensibles, incluyendo la versión del modelo.
- [ ] Agregar enlaces reales y evidencia al README y al PDF de presentación.

## Estado de entrega de la mitad de Jorge

La implementación y documentación asignadas a Jorge están completas: preparación
causal, reentrenamiento y validación, artefactos, cargador CPU, latencia local,
API HTTP, README técnico y reproducción desde un clon y entorno aislados.
La reproducción limpia pasó 134 pruebas y solicitudes HTTP reales.

Quedan como actividades compartidas la coordinación con el compañero, revisión
de la integración y preparación para exponer y contestar preguntas. La interfaz,
el hosting, las evidencias externas y **toda la elaboración de la presentación**
corresponden al compañero según este reparto.

## Git: subir el trabajo en varios commits

Cada persona trabaja en su rama (`jorge/modelo-api` y `companero/interfaz-deploy`)
y sube avances después de cada unidad funcional. Integrar cambios revisados a
la rama principal; no dejar todo para un único commit final.

Secuencia sugerida de commits (hacerlos cuando el cambio correspondiente exista):

| Responsable | Commit | Contenido |
|---|---|---|
| Jorge | `fix: preparar ventanas causales sin informacion futura` | Preparación compartida y pruebas de regresión |
| Jorge | `docs: distribuir trabajo y definir contrato de inferencia` | Este plan y contrato |
| Jorge | `feat: regenerar modelos con preprocesamiento causal` | Artefactos, metadatos y resultados corregidos |
| Jorge | `feat: agregar API de riesgo con carga del modelo` | Endpoints y validación |
| Jorge | `test: verificar inferencia y documentar validacion` | Pruebas de integración y secciones técnicas |
| Compañero | `feat: crear interfaz y ejemplos de transacciones` | Formulario y ejemplos |
| Compañero | `feat: conectar interfaz con API de riesgo` | Conexión y manejo de errores |
| Compañero | `deploy: configurar servicio y monitoreo` | Hosting, arranque y registros |
| Compañero | `docs: agregar arquitectura y evidencias de uso` | Diagrama, capturas y registros |
| Compañero | `docs: agregar presentacion final completa en PDF` | Todas las diapositivas y PDF final |
| Ambos | `docs: completar README de entrega` | Siete secciones, IA y enlaces verificados |
| Ambos | `fix: resolver hallazgos de verificacion final` | Solo correcciones reales que surjan |

Usar `git add` con archivos concretos, revisar `git diff --staged`, hacer
`git commit` y `git push` en cada avance. Coordinar los cambios al README raíz.
Registrar el traslado de la carpeta original a `Proyecto1/` en un commit
independiente de los cambios funcionales. No subir cachés,
entornos virtuales ni secretos. Los commits de funcionalidades pendientes se harán al implementar y verificar cada tarea.
