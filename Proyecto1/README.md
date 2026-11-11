# Proyecto 1. Monitoreo transaccional

Angel Herrarte y Jorge López. Deep Learning 2026, Universidad del Valle.

Investigamos si el orden de las transacciones trae información que las variables
agregadas no tienen, y cuánto vale eso en quetzales. Los datos son sintéticos, con
generador propio (Ruta A).

## Proyecto Final: reentrenamiento causal

La continuación del final usa `artefactos/causal_v2/`. La comparación corregida,
los controles y las conclusiones están en [docs/VALIDACION_CAUSAL.md](docs/VALIDACION_CAUSAL.md).
Los resultados, PDFs, figuras y notebook originales se conservan como antecedente.
La tabla de abajo corresponde al **Proyecto 1 original**, no a la ejecución causal.

El cargador reutilizable de B en CPU y sus instrucciones están en
[docs/SIGUIENTE_PASO_CPU.md](docs/SIGUIENTE_PASO_CPU.md).

## Cómo nos fue en el Proyecto 1 original

| | AUC-PR validación | AUC-PR prueba | P1 historia barajada | P2 orden destruido |
|---|---|---|---|---|
| A, agregados | 0.810 | 0.549 | 0.810 | 0.810 |
| B, GRU | 0.882 | 0.610 | 0.678 | 0.018 |
| C, híbrido | 0.857 | 0.600 | 0.705 | 0.133 |

B le gana a A y se cae cuando destruimos el orden. A no se mueve, que era el control.
La ventaja se concentra en F1, el único mecanismo que construimos para depender del
orden.

La apuesta C no se cumplió: quedó 0.026 por debajo de B cuando pedíamos 0.02 por
arriba.

Recomendamos complementar el motor actual, no reemplazarlo.

## Cómo correrlo

Hace falta [`uv`](https://docs.astral.sh/uv/) y macOS o Linux. Python 3.12 se descarga
solo, no toca el Python del sistema.

```bash
uv venv --python 3.12
uv pip install numpy pandas scikit-learn scipy torch matplotlib pytest jupyterlab nbformat
```

Las pruebas, incluida la que verifica que el señuelo sirve:

```bash
uv run pytest -q
```

El notebook original (sus salidas guardadas son históricas). Para el final usar
el comando de reentrenamiento causal documentado al final de este README:

```bash
uv run jupyter nbconvert --to notebook --execute --inplace proyecto1_herrarte_lopez.ipynb
```

Toda la aleatoriedad sale de `numpy.random.default_rng(semilla)` y de
`torch.manual_seed(semilla)`, las dos con 42 por omisión en `ConfigGenerador`. Con la
misma semilla salen los mismos datos y los mismos puntajes.

### Cómo está organizado

```
src/config.py       constantes y ConfigGenerador
src/generador.py    perfiles de tarjeta, tráfico legítimo, F1 a F4 y el señuelo
src/ventanas.py     ventanas de 20, agregados causales, partición, escaladores
src/modelos.py      A boosting, B GRU, C híbrido, y sus bucles de entrenamiento
src/evaluacion.py   AUC-PR, umbral por costo, permutación, desglose por mecanismo
src/experimento.py  arma todo y devuelve los resultados
src/figuras.py      las cinco figuras del informe
tests/              63 pruebas
artefactos/         pesos, escaladores, vocabularios y la config del generador
```

El código vive en módulos y no adentro del notebook. El notebook cuenta, los módulos
calculan. Lo hicimos así para que el Proyecto Final no tenga que reconstruir nada.

## Versiones

| | |
|---|---|
| Python | 3.12.13 |
| torch | 2.14.0 |
| scikit-learn | 1.9.0 |
| numpy | 2.5.2 |
| pandas | 3.0.5 |
| scipy | 1.18.1 |
| matplotlib | 3.11.1 |
| pytest | 9.1.1 |
| jupyterlab | 4.6.3 |

Desarrollado en macOS 15 (Darwin 25.6.0), Apple M5. LightGBM no está instalado a
propósito, por lo que explicamos en la tercera decisión.

## Uso de IA

Usamos Claude (Anthropic) como herramienta de apoyo. Las decisiones de diseño, los
criterios de evaluación y la verificación de los resultados son nuestras. Abajo queda
en qué nos apoyamos y qué comprobamos por nuestra cuenta.

### En qué nos apoyamos

Discusión del diseño experimental (qué ruta de datos, qué unidad de predicción, qué
mecanismos de fraude generar, cómo armar el señuelo), escritura del código de `src/` y
las pruebas de `tests/`, y redacción del informe, la presentación y este README.

### Qué verificamos nosotros

Corrimos la suite completa. Cada cosa que la rúbrica penaliza tiene una prueba que falla
si se rompe: la partición temporal con embargo, los escaladores ajustados solo con
entrenamiento, los agregados causales, F4 retenido y los umbrales elegidos sobre
validación. Revisamos a mano la verificación del señuelo antes de aceptar cualquier
conclusión sobre el orden, mirando la importancia de variables del boosting para ubicar
de dónde salía la señal que quedaba. Y comprobamos el control de la permutación: el
AUC-PR de A tiene que quedar idéntico hasta el último decimal, y si se moviera el error
sería nuestro.

### Tres decisiones

**Ruta A en vez de Ruta B.** Consideramos IEEE-CIS y el dataset de IBM/TabFormer. Nos
decidimos por los sintéticos porque permiten el desglose por mecanismo, que con datos
reales es imposible: ahí la etiqueta dice fraude y no dice de qué tipo. Ese desglose es
lo que muestra que B gana solo en F1 y empata en F3, y por lo tanto que la línea base no
está amañada. Además, varios de los datasets públicos más citados, como el
`creditcard.csv` de ULB, no traen identificador de tarjeta, así que ni siquiera se
pueden armar secuencias. Lo que perdimos es credibilidad externa, y va como la primera
limitación del informe.

**El señuelo termina en la compra grande, igual que el fraude.** Nuestro primer diseño
invertía el episodio completo, con la compra grande al inicio. Falló con ROC-AUC de
1.000, y al revisar la importancia de variables vimos que `monto_max_ventana` valía 185
en F1 y 3,830 en el señuelo. El problema era conceptual: razonábamos sobre agregados de
episodio, pero el modelo usa ventanas por transacción, así que poner la compra grande
primero la metía en la historia de todas las anclas siguientes. Rediseñamos para que
ambos terminen en la compra grande y lo único distinto sea el orden de las compritas,
en rampa para el fraude y revueltas para el señuelo. Con eso bajó a 0.539 en el cobro.

**`HistGradientBoostingClassifier` de scikit-learn como línea base, ni logística ni
LightGBM.** Contra la logística: la rúbrica pide un modelo competitivo, y ganarle a una
línea base floja no probaría nada sobre el orden. A saca 0.810 de AUC-PR y empata con B
en F2 y F3, así que es un rival de verdad. Contra LightGBM: en macOS ARM, importar
`lightgbm` y después correr un GRU de PyTorch da segfault (SIGSEGV, exit 139), porque
las dos librerías cargan su propio runtime de OpenMP. Lo reprodujimos aislando cada
import. `HistGradientBoosting` es el mismo algoritmo de boosting por histogramas, se
lleva bien con torch, y no agrega dependencias.

## Candidato al Proyecto Final

### Qué modelo nos quedaríamos

El B, el GRU secuencial, en `artefactos/modelo_b_gru.pt`. No C, aunque haya quedado
cerca: su hipótesis no se cumplió bajo el criterio que fijamos antes de abrir prueba, y
quedarnos con él sería elegir mirando el conjunto de prueba.

Para volver a producir los puntajes también hacen falta:

| Archivo | Qué trae |
|---|---|
| `artefactos/modelo_b_gru.pt` | los pesos del GRU |
| `artefactos/escaladores.json` | medias y desviaciones, ajustadas solo con entrenamiento |
| `artefactos/vocabularios.json` | códigos de rubro, canal y ciudad; el 0 es relleno o categoría no vista |
| `artefactos/config_generador.json` | la configuración completa del generador |
| `artefactos/modelo_a_boosting.pkl` | la línea base, para poder rehacer la comparación |

### Quién lo usaría

El motor de autorización, en línea, cuando llega la transacción. La decisión es
bloquear o dejar pasar.

El puntaje de B no reemplaza al motor actual, entra como una señal más. Lo que
recomendamos es correr los dos y bloquear si cualquiera pasa su umbral, o meter el
puntaje de B como una variable adicional del motor de reglas.

El otro consumidor sería el analista de fraude, que lo usaría para ordenar la cola de
revisión manual.

### Contrato de entrada y salida

```
Entrada
  Las ultimas 20 transacciones de la tarjeta, ordenadas por marca_tiempo de mas
  vieja a mas nueva, terminando en la que se esta autorizando. Cada una:
    marca_tiempo : float   dias desde un origen fijo
    monto        : float   quetzales, mayor que cero
    rubro        : str     vocabulario cerrado; si no esta, va al indice 0
    canal        : str     chip, contactless, ecommerce o atm
    ciudad       : str     vocabulario cerrado; si no esta, va al indice 0
  Si hay menos de 20, se rellena por la izquierda y se enmascara.

Salida
  puntaje_riesgo : float entre 0 y 1
  El umbral lo decide quien consume el puntaje, no el modelo.

Umbral sugerido
  El que minimice 4200 * FN + 180 * FP sobre un bloque de validacion reciente.
  Aqui nos dio 0.648, pero eso hay que recalibrarlo contra datos reales.

Latencia
  Es un GRU de una capa con estado oculto 64 sobre 20 pasos, o sea milisegundos
  en CPU. El costo real esta en armar la ventana de 20, no en la red.
```

### Límites, riesgos y lo que falta

Sabemos que F4 no se detecta. Los cargos chicos y recurrentes del mismo comercio pasan
debajo de cualquier umbral de velocidad y los tres modelos los dejan ir. Eso necesita
otra defensa, algo que busque recurrencia en semanas y no en horas.

Los quetzales están inflados. La tasa de fraude simulada, 0.6% de las transacciones,
está muy por encima de la de una cartera real, así que las cifras absolutas de ahorro no
son un pronóstico. Solo el porcentaje se sostiene.

Y un modelo supervisado defiende contra lo que ya pasó. F4 lo demuestra dentro del
propio experimento.

El riesgo más grande es que el señuelo no exista en los datos reales. Todo el resultado
depende de que haya clientes legítimos con la misma firma agregada que un ataque de
prueba y cobro. Si en los datos del banco esos clientes no aparecen, los agregados
bastarían y el modelo secuencial no aportaría nada. Después de eso viene la deriva de
comportamiento, porque el umbral se calibró sobre una distribución fija y el
comportamiento de compra cambia con temporadas y campañas. Y el vocabulario es cerrado,
así que un rubro o una ciudad nuevos caen al índice 0 y el modelo los trata como
relleno.

Lo que más falta son transacciones reales con identificador de tarjeta, marca de tiempo
y etiqueta de fraude, para ver si la ventaja del orden sobrevive fuera del simulador.
Después, la fecha en que se confirmó cada fraude y no solo la de la transacción, porque
las etiquetas reales llegan con semanas de retraso y eso cambia cómo se puede entrenar
sin fuga. Y el costo real de un bloqueo: los Q180 salen del enunciado, y si el costo
reputacional se pareciera al del fraude, el umbral subiría y la ventaja de B se
achicaría.

## Preparación causal para el Proyecto Final

`src.ventanas.construir_caracteristicas` comparte la preparación de entrenamiento
con `preparar_inferencia(transacciones, escaladores["secuencia"])`. Esta última
recibe entre 1 y 20 eventos cronológicos de una tarjeta, sin etiquetas, con
`marca_tiempo`, `monto`, `rubro`, `canal` y `ciudad`; devuelve arrays `cat`, `num`
y `mascara` con lote de tamaño 1, listos para convertir a tensores de PyTorch.
Los eventos desconocidos conservan máscara verdadera y categoría 0.

La ciudad base es ahora la moda de las 19 transacciones previas al ancla
(desempate alfabético); sin historia es la ciudad del ancla. La lejanía de toda
la ventana se calcula respecto a esa base. Esto permite reproducir exactamente
la última ventana sin acceder a transacciones futuras ni a historia adicional.

Los pesos, escaladores, métricas, figuras y umbrales directamente en `artefactos/`
y los resultados anteriores de este README son históricos: la ciudad base se
calculaba con la historia completa. Para continuar con la preparación corregida,
usar el bundle `artefactos/causal_v2/`, nunca mezclar sus pesos y escaladores con
los originales. El reparto completo está en `../DISTRIBUCION_PROYECTO_FINAL.md`.

### Reproducir la ejecución causal

Entorno utilizado: Python 3.13.12 en CPU. Desde `Proyecto1/`:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-reentrenamiento.txt
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 python -m src.reentrenar --hilos 4
python -m pytest -q
```

El entrenamiento conserva 6,000 tarjetas, 180 días, semilla 42 y 12 épocas;
selecciona la mejor época con validación y mantiene el criterio original de C.
El script guarda pesos, escaladores, vocabularios, umbrales, métricas JSON,
puntajes NPZ, resultados, cinco figuras y metadatos con versiones y SHA-256.
También recarga B en CPU para comprobar la exportación con casos sintéticos.

El bundle ya se incluye en el repositorio: para probarlo no hace falta reentrenar.
El script rechaza sobrescribir `artefactos/causal_v2/`; si se quiere repetir,
conservar esa carpeta fuera del destino antes de correrlo. No ejecutar el notebook
original para actualizar el final: escribe en las rutas de los artefactos históricos.
La reproducción numérica se refiere al mismo entorno, semilla y configuración;
no se garantiza identidad de bits entre plataformas o versiones distintas.

El informe declara que prueba ya se usó en Proyecto 1: esta ejecución corrige
la preparación y reevalúa, sin convertir ese conjunto en una prueba inédita.

### Uso de IA en la continuación del final

Se utilizó Codex (OpenAI) para corregir la preparación causal, organizar el plan,
implementar el comando de reentrenamiento, ejecutar los modelos y las pruebas,
exportar artefactos y preparar documentación. Las comprobaciones automatizadas
se registran con los resultados; ambos integrantes deben revisar y poder explicar
el código, las métricas y las decisiones antes de presentar.

### Usar B en CPU sin reentrenar

Crear `PredictorFraudeCPU()` una vez y reutilizar `predecir(transacciones)`.
La salida contiene `puntaje_riesgo` y `version_modelo`; `umbral_sugerido`
está disponible por separado. Valida integridad y compatibilidad de los archivos
al cargar y ejecuta en modo evaluación sin gradientes.

```bash
python -m src.inferencia --entrada ejemplos/solicitud_riesgo.json
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 python -m src.medir_latencia --hilos 4
```

Ver [guía del cargador](docs/SIGUIENTE_PASO_CPU.md) y
[mediciones de latencia](docs/LATENCIA_CPU.md). La API HTTP se implementará
a continuación; el uso por consola ya permite verificar la inferencia local.
