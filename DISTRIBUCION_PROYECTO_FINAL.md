# Proyecto final: distribución en pareja

Jorge López: primera mitad (modelo, inferencia y API).
Compañero: segunda mitad (interfaz, despliegue y evidencias).
Ambos: integración, revisión técnica y presentación.

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
- [ ] Revisar juntos el contrato y los resultados de las pruebas.

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
  `Proyecto1/docs/LATENCIA_CPU.md`. Siguiente paso: integrar con la API.

### 3. API y contrato

- [ ] Implementar carga única del modelo y escaladores al iniciar el servicio,
  evaluación con `eval()` y sin gradientes, y versiones compatibles.
- [ ] Crear `POST /predict` y `GET /health`. Validar entrada y devolver errores
  claros, puntaje, versión del modelo y, si se expone, umbral y decisión sugerida.
- [ ] Incorporar pruebas de predicción real con artefactos corregidos,
  datos inválidos, categorías nuevas y secuencias cortas.
- [ ] Fijar dependencias reproducibles y documentar ejecución y ejemplo de uso.

Contrato inicial para coordinar la interfaz: JSON con `transacciones`, una lista
cronológica de 1 a 20 eventos de una sola tarjeta, cada uno con `marca_tiempo`
(días desde un origen fijo documentado), `monto` positivo en Q, `rubro`, `canal`
y `ciudad`. No se piden etiquetas. Ejemplo de salida propuesto:
`{"puntaje_riesgo": 0.72, "version_modelo": "..."}`. Acordar este contrato
antes de desarrollar la conexión de la interfaz.

### 4. Documentación a cargo de Jorge

- [ ] README raíz: problemática, usuario, decisión, supuestos, modelo planteado
  y validación de hipótesis. Distinguir resultados originales y corregidos.
- [ ] Explicar ingeniería de características, esquema de entrada, origen de
  tiempo, categorías desconocidas, umbral, costos y limitaciones.

## Segunda mitad — Compañero

### 5. Interfaz de demostración

- [ ] Crear una página para ingresar o pegar transacciones, con ejemplos
  sintéticos legítimos y sospechosos listos para ejecutar.
- [ ] Mostrar puntaje y explicación de uso, estados de carga y errores de API.
  No presentar el puntaje como probabilidad calibrada sin comprobarlo.
- [ ] Conectar con el contrato acordado y probar secuencias cortas y entradas
  inválidas. Puede comenzar con una respuesta simulada claramente identificada
  mientras Jorge termina la API; quitarla en la versión publicada.

### 6. Despliegue, monitoreo y pruebas de uso

- [ ] Elegir hosting que soporte las dependencias de PyTorch y documentar
  configuración, arranque y ubicación de artefactos.
- [ ] Publicar API e interfaz y comprobar uso desde otro dispositivo o sesión.
- [ ] Registrar fecha/hora, identificador de petición, versión de modelo,
  duración y resultado/estado de las solicitudes sin guardar datos sensibles.
- [ ] Documentar cómo revisar salud, errores y latencia. Explicar qué harían
  ante deriva y cuándo recalibrar/reentrenar; distinguir propuesta e implementación.
- [ ] Reunir capturas, registros de uso y resultados de pruebas en `evidencias/`.
  Verificar que una persona ajena al equipo pueda completar una predicción.

### 7. Arquitectura y documentación a cargo del compañero

- [ ] README raíz: planificación con fechas/responsables, herramientas y
  arquitectura, evidencia de producción e instrucciones de acceso/ejecución.
- [ ] Diagrama: datos → preparación → entrenamiento → artefactos → servicio →
  interfaz, más registros/monitoreo. Aclarar qué ocurre fuera de línea y en línea.
- [ ] Agregar enlaces reales al servicio, API, evidencias y presentación PDF.
- [ ] Preparar las diapositivas de arquitectura, demo, operación y límites.

## Integración y cierre — ambos

- [ ] Revisar cambios del otro y poder explicar cualquier archivo o decisión.
- [ ] Completar las siete secciones del README raíz y actualizar declaración
  de IA con los usos del final y lo verificado por ustedes.
- [ ] Crear la presentación final en PDF; la presentación original de Proyecto 1
  es material de partida, no la presentación final completa.
- [ ] Ensayar 10 minutos: Jorge presenta problema/modelo/validación (5 minutos)
  y compañero arquitectura/demo/evidencias/límites (5 minutos). Ambos responden.
- [ ] Clonar en un entorno limpio y seguir el README para verificar reproducción.
- [ ] Verificar repositorio público o compartido con docente, enviar el enlace
  antes del límite y confirmar que la última versión incluye todos los archivos.

## Plan de fechas sugerido

| Fecha | Jorge | Compañero |
|---|---|---|
| 11 nov | Preparación causal, pruebas, contrato y reentrenamiento | Interfaz inicial y selección de hosting |
| 12 nov | API, nuevos artefactos y validación | Conexión de interfaz, despliegue y registros |
| 13 nov | Integración y presentación si corresponde | Demo, evidencias y presentación si corresponde |
| 14 nov | Reproducción y documentación | Pruebas externas, PDF y README |
| 15 nov | Revisar entrega y enlaces con margen antes de 23:59 | Revisar entrega y enlaces con margen antes de 23:59 |

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
| Ambos | `docs: completar README y presentacion final` | Siete secciones, IA, enlaces y PDF |
| Ambos | `fix: resolver hallazgos de verificacion final` | Solo correcciones reales que surjan |

Usar `git add` con archivos concretos, revisar `git diff --staged`, hacer
`git commit` y `git push` en cada avance. Coordinar los cambios al README raíz.
Registrar el traslado de la carpeta original a `Proyecto1/` en un commit
independiente de los cambios funcionales. No subir cachés,
entornos virtuales ni secretos. Los commits de funcionalidades pendientes se harán al implementar y verificar cada tarea.
