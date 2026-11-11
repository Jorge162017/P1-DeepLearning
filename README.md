# Proyecto final — Riesgo de fraude transaccional

Deep Learning y Sistemas Inteligentes, Universidad del Valle, 2026.
Modelo de origen: **Proyecto 1, monitoreo transaccional**.

El proyecto convierte una GRU que evalúa secuencias de transacciones en un servicio
HTTP de puntaje de riesgo. **La API funciona y está probada localmente.** La
interfaz, el despliegue público y las evidencias de uso por una persona externa
siguen pendientes. Este documento organiza las siete secciones del enunciado y
las instrucciones de ejecución.

La implementación y los artefactos están en [Proyecto1/](Proyecto1/). La ejecución
vigente usa exclusivamente [artefactos/causal_v2/](Proyecto1/artefactos/causal_v2/).
Los archivos directamente en `Proyecto1/artefactos/`, el notebook y los PDF del
Proyecto 1 conservan los resultados originales y no son la evaluación corregida.

## 1. Problemática, usuario y decisión

En el caso simulado del Proyecto 1, un motor antifraude evalúa variables resumidas,
como montos, frecuencia y diversidad de ciudades o canales. La pregunta es si el
**orden de las transacciones** aporta información adicional para detectar fraude,
y si esa información permite reducir el costo de errores frente a una línea base
competitiva que utiliza agregados de la misma ventana.

El usuario principal previsto es un analista de fraude que consulta el puntaje de
la transacción actual para priorizar revisión. Otro consumidor posible es un motor
de autorización que incorpore el puntaje como señal adicional a sus reglas. La
integración con un motor bancario real queda fuera del alcance de esta demostración.

La unidad de predicción es **una transacción**, representada junto a sus últimas
19 transacciones previas de la misma tarjeta. El resultado apoya la decisión de
revisar, permitir o bloquear según la política del consumidor. La API actual
entrega puntaje y versión; no aplica bloqueos ni devuelve una decisión automática.

Los costos experimentales son **Q4,200 por fraude no detectado (FN)** y **Q180 por
transacción legítima bloqueada (FP)**. Ambos proceden del caso del Proyecto 1 y
no de una medición de costos de un banco. El objetivo del final es demostrar un
servicio utilizable y justificar su modelo, contrato y límites.

## 2. Planificación

El trabajo se distribuye en pareja. Jorge López está a cargo de preparación,
modelos, inferencia, API y sus secciones técnicas. El compañero está a cargo de
interfaz, despliegue, arquitectura de la solución y evidencias de uso externo.
El compañero también elabora **todas las diapositivas y el PDF final**.
La integración, revisión, ensayo, exposición y respuestas a preguntas son compartidos. El nombre del segundo
integrante debe completarse antes de la entrega.

| Etapa | Responsable | Estado |
|---|---|---|
| Preparación causal y pruebas sin información futura | Jorge | Implementada |
| Reentrenamiento y validación de A, B y C | Jorge | Ejecutados; artefactos y métricas guardados |
| Cargador de B en CPU y medición local | Jorge | Implementado y verificado |
| API de predicción y salud | Jorge | Implementada y probada localmente |
| Interfaz, despliegue y evidencias externas | Compañero | Pendientes |
| Reproducción en entorno limpio | Jorge / ambos | Verificada en clon local y entorno aislado; 134 pruebas aprobadas |
| Revisión conjunta | Ambos | Pendiente |
| Todas las diapositivas y PDF final | Compañero | Pendientes |
| Revisión del material y ensayo oral | Ambos | Pendientes |

El [plan de trabajo](DISTRIBUCION_PROYECTO_FINAL.md) contiene las tareas y el
calendario propuesto del 11 al 15 de noviembre. Las fechas de presentación del
enunciado son 9 y 13 de noviembre; la entrega límite es el **15 de noviembre de
2026 a las 23:59**. El compañero debe completar esta sección con su nombre,
fechas reales de integración y despliegue y cualquier ajuste al calendario.
Las opciones de hosting están en el [reparto de trabajo](DISTRIBUCION_PROYECTO_FINAL.md#dónde-desplegar--decisión-e-implementación-del-compañero).

## 3. Supuestos y límites

### Datos y disponibilidad de información

Los datos son sintéticos: 6,000 tarjetas y 180 días, con semilla 42. La ejecución
produce 484,738 transacciones. Su distribución y los patrones de fraude fueron
construidos por el equipo; no equivalen a una cartera bancaria real.

| Mecanismo | Patrón simulado | Disponibilidad |
|---|---|---|
| F1 | Compras pequeñas en rampa y un cobro grande | Entrenamiento, validación y prueba |
| F2 | Transacciones en ciudades lejanas con poca separación temporal | Entrenamiento, validación y prueba |
| F3 | Ráfaga de ecommerce caro de madrugada | Entrenamiento, validación y prueba |
| F4 | Cargos pequeños recurrentes, o goteo lento | Solo prueba |

Existe además un señuelo legítimo de F1: microcompras desordenadas y un cobro
grande final. Permite comprobar que la ventaja secuencial no dependa únicamente
de que la línea base reconozca un monto grande. Este señuelo es una condición
del simulador; su presencia en transacciones reales está por verificar.

Se supone que el consumidor dispone de las transacciones observadas hasta el
momento de evaluar el ancla y puede formar una ventana cronológica de una sola
tarjeta. No se requieren etiquetas de fraude ni información futura en inferencia.
El servicio no consulta ni almacena un historial: recibe la ventana en cada petición.

### Usuario y entorno

Los montos se expresan en quetzales y las marcas temporales en días desde un
origen fijo. En la simulación el día de semana es `floor(marca_tiempo) % 7`.
No se aceptan fechas de calendario directamente: su integración requiere fijar
una conversión que conserve la misma convención temporal del entrenamiento.

Se reciben entre 1 y 20 eventos. Menos de 20 se rellenan a la izquierda y se
identifican con una máscara. Las categorías desconocidas se codifican con 0,
igual que el índice reservado para relleno; la máscara distingue un evento
observado de una posición de relleno. No se supone que el modelo generalice
correctamente a categorías nuevas por el hecho de aceptarlas técnicamente.

El servicio se ejecuta en CPU y carga los artefactos una vez por proceso. Los
resultados de latencia disponibles son locales, con cuatro hilos y sin HTTP ni
red; el hosting definitivo necesita su propia medición.

### Límites de la conclusión

Los tres modelos tienen exhaustividad cero en F4. Una ventana de 20 eventos y
un modelo supervisado sobre estos mecanismos no ofrecen cobertura general de
fraude. Cambios de comportamiento o de prevalencia pueden deteriorar el resultado.

El puntaje es una salida sigmoide de un modelo entrenado con ponderación de
clases; no se presenta como probabilidad calibrada. El umbral y los ahorros
simulados no se trasladan directamente a un banco real. Tanto los costos absolutos
como los porcentajes de ahorro requieren validación externa.

El conjunto de prueba ya se observó en Proyecto 1. La ejecución del final es una
**reevaluación tras corregir la preparación**, no una prueba independiente con
datos nuevos. Tampoco se garantiza identidad numérica entre versiones o plataformas.

## 4. Modelo planteado y preparación

Se reutiliza **B, la GRU del Proyecto 1**, manteniendo la arquitectura original.
Se corrigió el cálculo de características y se reentrenaron A, B y C para comparar
los tres bajo esa misma preparación. No se buscó una arquitectura nueva ni se
ajustaron hiperparámetros en función de los resultados de prueba.

### Características compartidas por entrenamiento e inferencia

`construir_caracteristicas` y `preparar_inferencia` en
[src/ventanas.py](Proyecto1/src/ventanas.py) comparten las transformaciones:

- Tres variables categóricas por evento: rubro, canal y ciudad.
- Siete variables numéricas: `log1p(monto)`, `log1p(segundos desde el evento
  anterior en la ventana)`, seno y coseno de hora, seno y coseno de día de semana
  y lejanía respecto a la ciudad base del ancla.
- Ventanas de 20 posiciones, alineadas a la derecha con el ancla al final.
  El primer evento observado de cada ventana tiene intervalo temporal cero.
- Medias y desviaciones calculadas exclusivamente con posiciones observadas
  de entrenamiento; el relleno conserva valores numéricos cero tras escalar.

La **ciudad base** es la moda de las 19 transacciones anteriores al ancla. Los
empates se resuelven alfabéticamente; sin historia se usa la ciudad actual. Toda
la ventana se expresa respecto a esa base. La lejanía vale 0 en la base, 2 en
otra ciudad del vocabulario extranjero y 1 en las demás ciudades distintas.

La preparación original calculaba la ciudad base con toda la historia de la
tarjeta, incluyendo el futuro del ancla. Se eliminó ese acceso para que agregar
transacciones futuras no cambie las características pasadas y para reproducir la
última ventana usando solo los eventos recibidos. Este cambio afecta tanto a la
secuencia como a los agregados; por eso se regeneraron todos los modelos y escaladores.

### Arquitectura y comparación

| Modelo | Entrada | Arquitectura |
|---|---|---|
| A, línea base | 15 agregados de la misma ventana | `HistGradientBoostingClassifier`, 400 iteraciones, aprendizaje 0.05 y pesos de clase |
| B, candidato del servicio | Secuencia de eventos | Tres embeddings de dimensión 8; GRU de una capa con estado oculto 64; cabeza 64 → 32 → 1, ReLU y dropout 0.2 |
| C, híbrido | Secuencia y los 15 agregados | GRU de B; concatena estado oculto y agregados antes de la cabeza |

B recibe 31 características por paso (24 de embeddings y 7 numéricas). La cabeza
produce un logit al que se aplica sigmoide durante inferencia. Las implementaciones
están en [src/modelos.py](Proyecto1/src/modelos.py).

B y C se entrenan en CPU durante 12 épocas con Adam, tasa 0.001, lotes de 256,
semilla 42 y `BCEWithLogitsLoss` ponderada por el desbalance de entrenamiento.
Se restaura la época con mejor average precision en validación: época 5 para B
y 4 para C. La arquitectura, versiones, configuración y huellas de archivos
quedan en [metadatos.json](Proyecto1/artefactos/causal_v2/metadatos.json).

## 5. Validación de hipótesis y selección

### Hipótesis y criterio de éxito

La pregunta original es si la secuencia aporta valor frente a agregados de la
misma ventana. Se contrasta B contra A y se baraja el orden de los eventos para
observar si B utiliza la historia. No se introduce ahora un margen nuevo para
esa comparación.

La hipótesis formal de **C** conserva el criterio codificado del Proyecto 1,
anterior a esta ejecución: superar al mejor de A y B por **al menos 0.02 de
AUC-PR absoluto en validación**, y conservar la exhaustividad de B con tolerancia
de 0.02 en al menos dos mecanismos de validación. No se redefine el criterio
para obtener un resultado favorable.

La métrica principal es `average_precision_score` de scikit-learn, denominada
**AUC-PR** en este proyecto. No se usa exactitud como criterio principal debido
al desbalance de clases. Validación y prueba tienen prevalencias distintas,
incluida la incorporación de F4 en prueba: sus AUC-PR no se interpretan como
una medida directa de deterioro temporal.

### Protocolo y controles

| Partición | Días de anclaje | Transacciones | Fraudes |
|---|---|---:|---:|
| Entrenamiento | 0–119 | 322,903 | 1,948 |
| Embargo | 120–121 y 150–151 | 10,840 | 95 |
| Validación | 122–149 | 75,536 | 518 |
| Prueba | 152–179 | 75,459 | 620 |

Las tarjetas pueden aparecer en varios bloques: la separación es temporal.
Cada ventana puede usar historia observada antes de su ancla. Las anclas del
embargo se excluyen del ajuste y de las métricas. F4 aparece únicamente en prueba.

Los escaladores se ajustan en entrenamiento. La época y el umbral se seleccionan
con validación; prueba se utiliza para reportar resultados con esas decisiones
congeladas. Se conservan semilla, datos, arquitectura y 12 épocas originales,
sin búsqueda de hiperparámetros durante esta reevaluación.

### Resultados originales frente a resultados causales

Los valores originales proceden de la tabla publicada del notebook, con cuatro
decimales; los corregidos corresponden a `causal_v2`. Las versiones de librerías
también difieren respecto a las reportadas en Proyecto 1, por lo que no se atribuye
cada diferencia numérica exclusivamente a la corrección de ciudad base.

| Modelo | Validación original | Validación causal | Prueba original | Prueba causal | Umbral causal |
|---|---:|---:|---:|---:|---:|
| A | 0.8101 | 0.809183 | 0.5486 | 0.549369 | 0.668342 |
| **B** | **0.8822** | **0.874442** | **0.6103** | **0.608519** | **0.733668** |
| C | 0.8566 | 0.863147 | 0.5999 | 0.608834 | 0.804020 |

B supera a A por **0.065258** de AUC-PR en validación. C queda **0.011295 por
debajo de B**: aunque cumple la condición de conservación por mecanismo, no
alcanza el margen de +0.02. **La hipótesis de C no se cumplió.**

C obtiene una AUC-PR de prueba ligeramente mayor y menor costo en ese bloque.
Se reporta ese resultado, pero no se cambia la selección mirando prueba: se
mantiene B como candidato del servicio por su desempeño en validación y el
criterio original de C.

### Evidencia sobre el orden

| Modelo | Validación original de la ejecución causal | P1: barajar historia, mantener ancla | P2: barajar todas las posiciones |
|---|---:|---:|---:|
| A | 0.809183 | 0.809183 | 0.809183 |
| B | 0.874442 | 0.683456 | 0.016908 |
| C | 0.863147 | 0.797279 | 0.263453 |

A conserva su resultado porque no lee la secuencia. La caída de B bajo P1
apoya que utiliza el orden histórico dentro del simulador. P2 también desplaza
el ancla, de modo que su caída no aísla por sí sola el valor de la historia.

El boosting que intenta separar F1 del señuelo con agregados obtiene ROC-AUC
**0.538646 en el cobro**, bajo el máximo original de 0.60, y **0.617119 en todas
las anclas**, bajo el techo de 0.70. Ambas comprobaciones pasan.

### Umbral, costos y errores

Cada umbral minimiza `4200 × FN + 180 × FP` sobre una rejilla de 200 valores
en validación. El de B es **0.7336683417085427**. Se guarda como sugerencia
separada del puntaje; no constituye una política validada para datos reales.

| Modelo | Precisión en prueba | Exhaustividad | FP | FN | Costo del bloque (Q) |
|---|---:|---:|---:|---:|---:|
| A | 0.3413 | 0.6710 | 803 | 204 | 1,001,340 |
| B | 0.5292 | 0.6726 | 371 | 203 | 919,380 |
| C | 0.4830 | 0.6887 | 457 | 193 | 892,860 |

Con estos umbrales, la exhaustividad de F1 de B y A es cercana (0.8578 y 0.8531).
La mejora de B en el bloque se concentra en reducir falsos positivos; no se
presenta como una gran ganancia de exhaustividad de F1. F2 y F3 tienen
exhaustividad 1.0 en los tres modelos; F4 tiene 0.0 en los tres.

Las métricas completas, desglose por mecanismo, figuras y limitaciones están en
[VALIDACION_CAUSAL.md](Proyecto1/docs/VALIDACION_CAUSAL.md) y
[resumen_metricas.json](Proyecto1/artefactos/causal_v2/resumen_metricas.json).

## 6. Herramientas y arquitectura del servicio

La implementación actual usa Python, NumPy y pandas para preparación,
scikit-learn para A y métricas, PyTorch para B/C, FastAPI para HTTP, Uvicorn
para servir la aplicación y pytest con TestClient para las pruebas.

El entrenamiento ocurre fuera del servicio: genera datos, prepara ventanas,
valida modelos y exporta artefactos. Al iniciar la API, el cargador verifica
integridad, versión, arquitectura, escaladores y orden de vocabularios; carga B
en CPU una sola vez por proceso y activa evaluación sin gradientes. Cada petición
prepara una ventana con la misma lógica y devuelve puntaje y versión.

`GET /health` informa disponibilidad y `POST /predict` realiza la predicción.
Los registros JSON incluyen fecha UTC, identificador de solicitud, método,
ruta, estado HTTP, duración y versión, sin guardar las transacciones.

Guías: [API](Proyecto1/docs/API.md), [cargador CPU](Proyecto1/docs/SIGUIENTE_PASO_CPU.md)
y [latencia local](Proyecto1/docs/LATENCIA_CPU.md).

**Por completar por el compañero:** diagrama de la arquitectura final con
interfaz, hosting y monitoreo; herramientas de despliegue y cómo se revisarán
salud, errores, latencia y deriva en el entorno publicado.

## 7. Evidencias del pase a producción

| Evidencia | Estado y ubicación |
|---|---|
| Suite completa | 134 pruebas aprobadas; [registro](Proyecto1/docs/registro_pruebas_api.log) |
| Reproducción aislada | Instalación desde cero y 134 pruebas en un clon local; [informe](Proyecto1/docs/REPRODUCCION_LIMPIA.md) |
| Predicción real por HTTP local | Uvicorn: `/health` y `/predict`; [resultado](Proyecto1/docs/prueba_api_local.json) y [registros](Proyecto1/docs/registro_api_local.log) |
| Paridad de exportación de B | Seis casos, error máximo 5.96e-08 con tolerancia 1e-6; [verificación](Proyecto1/artefactos/causal_v2/verificacion_cpu.json) |
| Latencia local | Ventana de 20: mediana 1.865 ms y p95 1.974 ms para `predecir`, sin HTTP/red; [medición](Proyecto1/docs/latencia_cpu.json) |
| Interfaz y enlace público | Pendientes del compañero |
| Capturas y registros desde otro equipo | Pendientes del compañero |
| Presentación final en PDF | Elaboración completa a cargo del compañero; revisión y ensayo de ambos. El PDF de Proyecto 1 es antecedente |

La prueba HTTP local demuestra integración del modelo con el servicio. Todavía
falta demostrar el uso externo que solicita el enunciado. Antes de entregar,
completar esta sección con enlaces reales, capturas y evidencia del despliegue.

## Ejecución desde el repositorio

Entorno utilizado: Python 3.13.12. Desde la raíz, con Python 3.13 instalado:

```bash
cd Proyecto1
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-api.txt
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Con el servidor activo, abrir `http://127.0.0.1:8000/docs` o ejecutar en otra
terminal desde `Proyecto1/`:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/predict \
  -H 'Content-Type: application/json' \
  --data-binary @ejemplos/solicitud_riesgo.json
```

### Contrato de entrada y salida

`POST /predict` recibe un objeto con `transacciones`, una lista de 1 a 20 eventos
cronológicos de una sola tarjeta. La última transacción es la evaluada; en empates
de tiempo se conserva el orden recibido. La API no recibe identificadores de tarjeta:
el consumidor es responsable de construir una ventana de una sola tarjeta.

| Campo por evento | Tipo y significado |
|---|---|
| `marca_tiempo` | Número finito, días desde el origen fijo |
| `monto` | Número finito positivo, quetzales |
| `rubro` | Texto no vacío |
| `canal` | Texto no vacío |
| `ciudad` | Texto no vacío |

No se admiten etiquetas ni campos adicionales. Se devuelve `puntaje_riesgo`
entre 0 y 1 y `version_modelo`. El [ejemplo JSON](Proyecto1/ejemplos/solicitud_riesgo.json)
se puede ejecutar sin generar datos ni reentrenar. Un puntaje de un evento no
representa el riesgo del episodio completo.

Errores: `422` para entrada inválida, `503` si el modelo no está disponible y
`500` para un fallo interno de inferencia. Las respuestas incluyen `X-Request-ID`.

### Pruebas, predicción por consola y reproducción del entrenamiento

Con el entorno activado, desde `Proyecto1/`:

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 python -m pytest -q
python -m src.inferencia --entrada ejemplos/solicitud_riesgo.json
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 python -m src.medir_latencia --hilos 4
```

Los artefactos entrenados ya están incluidos; servir predicciones no requiere
entrenar. Para repetir el experimento, el comando es:

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 python -m src.reentrenar --hilos 4
```

El comando se niega a sobrescribir `artefactos/causal_v2/`: conservar primero
esa carpeta fuera del destino antes de repetirlo. No ejecutar el notebook
original para actualizar el final, porque escribe en las rutas históricas.
La instalación desde cero se verificó en un clon local independiente y un
entorno virtual sin paquetes del sistema: 134 pruebas aprobadas y solicitudes
HTTP reales correctas. Ver [reproducción limpia](Proyecto1/docs/REPRODUCCION_LIMPIA.md).
Esta comprobación local no sustituye la prueba del despliegue público.

## Uso de inteligencia artificial

En Proyecto 1 se utilizó Claude (Anthropic) para apoyar diseño experimental,
código, pruebas y redacción; la declaración original está en
[Proyecto1/README.md](Proyecto1/README.md#uso-de-ia).

En la continuación del final se utilizó Codex (OpenAI) para corregir la preparación
causal, organizar tareas, implementar y ejecutar reentrenamiento, exportación,
cargador CPU, benchmark, API, pruebas y documentación. Las verificaciones
registradas incluyen causalidad, paridad con casos guardados, integridad de
artefactos, métricas recalculadas y solicitudes HTTP reales locales.

Ambos integrantes deben revisar y poder explicar el código, las decisiones y
los resultados. La revisión conjunta y el ensayo de preguntas siguen pendientes;
los registros automatizados no sustituyen esa preparación.
