# Siguiente paso: cargar B en CPU

Usar exclusivamente `artefactos/causal_v2/` para la nueva preparación. Los pesos
que están directamente en `artefactos/` pertenecen al Proyecto 1 original.

## Lo que entrega el reentrenamiento

- Pesos `modelo_b_gru.pt` como `state_dict`.
- `metadatos.json` con argumentos de `ModeloSecuencial`, umbral, versiones,
  configuración, huellas de código y SHA-256 de los archivos del bundle.
- `escaladores.json` con la sección `secuencia`, y `vocabularios.json`.
- `casos_inferencia.json` con entradas sintéticas y puntajes esperados obtenidos
  desde las ventanas del experimento antes de guardar los pesos.
- `verificacion_cpu.json` con la comparación entre esos puntajes y los obtenidos
  al recargar los pesos en CPU y preparar de nuevo las entradas sin etiquetas.

## Cargador implementado

`src.inferencia.PredictorFraudeCPU` comprueba los tres archivos requeridos contra
el manifiesto SHA-256, la versión de preparación, ventana, arquitectura,
escaladores y el contenido y orden exacto de los vocabularios. Carga los pesos
una vez en CPU con `weights_only=True` y `strict=True`, deja el modelo en `eval()`
y desactiva gradientes. Los errores de artefactos se reportan como
`ErrorArtefactos`; las entradas inválidas, como `ValueError`.

La API pública es:

```python
from src.inferencia import PredictorFraudeCPU

predictor = PredictorFraudeCPU()  # una vez al arrancar el proceso
resultado = predictor.predecir(transacciones)  # reutilizar por cada solicitud
# {"puntaje_riesgo": ..., "version_modelo": "B-causal_v2-..."}
umbral = predictor.umbral_sugerido  # politica opcional, separada del puntaje
```

La ruta predeterminada se resuelve respecto al módulo, no al directorio desde el
que se arranque. También acepta `PredictorFraudeCPU(ruta_bundle)`. Para desplegar
solo B bastan `metadatos.json`, `modelo_b_gru.pt`, `escaladores.json` y
`vocabularios.json`; no se leen modelos A/C, resultados pickle ni figuras.
El manifiesto completo se conserva aunque no se copien los archivos no requeridos.

Ejecutar una predicción sin servidor desde `Proyecto1/`:

```bash
python -m src.inferencia --entrada ejemplos/solicitud_riesgo.json
```

El ejemplo es una ventana sintética guardada; el puntaje corresponde a la última
transacción, no a todo el episodio. Una etiqueta de mecanismo no garantiza que
el modelo detecte cada transacción de ese mecanismo.

El cargador no modifica globalmente los hilos de PyTorch. El benchmark los fija
al arrancar; el futuro servicio deberá fijarlos una vez según sus recursos.

## Verificación y medición

Las pruebas de `tests/test_cargador_cpu.py` verifican paridad en los seis casos,
CPU, modo evaluación, ausencia de gradientes, reutilización de la carga,
ventanas cortas, categorías desconocidas, errores de entrada y artefactos
faltantes, corruptos o incompatibles.

Para repetir la medición local:

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 python -m src.medir_latencia --hilos 4
```

Los resultados están en `docs/latencia_cpu.json` y se explican en
`docs/LATENCIA_CPU.md`. Se miden carga, preparación, inferencia y `predecir`
completo, con calentamiento y mediana/percentil 95. La carga medida excluye
importaciones, no vacía la caché de disco y todavía no incluye HTTP, red,
concurrencia ni el hosting definitivo.

## Qué sigue

Integrar una instancia del cargador con `POST /predict` y `GET /health`,
definir el manejo de errores HTTP y los registros de uso. Al desplegar, repetir
la medición en el servidor y agregar pruebas del contrato de la API.

## Contrato de entrada fijado para continuar

Una lista cronológica de 1 a 20 transacciones de **una sola tarjeta**, con:

| Campo | Significado |
|---|---|
| `marca_tiempo` | Número finito de días desde un origen fijo |
| `monto` | Número finito, mayor que cero, en quetzales |
| `rubro` | Texto no vacío |
| `canal` | Texto no vacío |
| `ciudad` | Texto no vacío |

Conservar el orden recibido en empates de tiempo. La última transacción es el
ancla que se evalúa. La ciudad base es la moda de las 19 previas; en empate,
la primera alfabéticamente; sin historia, la ciudad actual. Categorías nuevas
se codifican como 0 pero el evento conserva máscara verdadera. Menos de 20
transacciones se rellenan a la izquierda.

En la simulación, el día de semana es `floor(marca_tiempo) % 7`. Antes de aceptar
fechas de calendario hay que definir un origen que conserve esta convención.
La salida sigmoide se presenta como puntaje de riesgo; la ponderación de clases
impide asumir sin validación que sea una probabilidad calibrada.

La verificación de exportación existente se puede repetir, sin entrenar:

```bash
cd Proyecto1
python -c 'from pathlib import Path; from src.reentrenar import verificar_bundle_cpu; print(verificar_bundle_cpu(Path("artefactos/causal_v2")))'
```

Esta comprobación original sigue disponible. La interfaz reutilizable y la
medición local ya están implementadas; la integración con la API es el siguiente paso.
