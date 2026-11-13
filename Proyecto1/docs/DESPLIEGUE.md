# Despliegue y operación

Un único servicio sirve la API (`/predict`, `/health`, `/docs`) y la interfaz
web (`/`). Al compartir origen no hace falta CORS y basta un enlace.

## Imagen Docker

`Proyecto1/Dockerfile` usa `python:3.13.12-slim`, instala `torch==2.13.0` desde
el índice oficial de CPU de PyTorch (sin dependencias de GPU) y el resto de
`requirements-api.txt` con las versiones fijadas del entrenamiento. Copia solo
`src/`, `artefactos/causal_v2/` y `web/`; no entrena ni modifica artefactos.
Corre como usuario sin privilegios y escucha en `$PORT` (8000 por defecto).

```bash
cd Proyecto1
docker build --platform linux/amd64 -t riesgo-api .
docker run --rm -p 8000:8000 riesgo-api
```

Interfaz: `http://127.0.0.1:8000/`.

Variables: `PORT` (puerto, la asigna el hosting), `RIESGO_HILOS` (hilos de
PyTorch, 1 por defecto en la imagen) y `RIESGO_BUNDLE` (ruta de artefactos).

### Verificación en Linux (13 nov 2026)

Imagen `linux/amd64` construida y ejecutada en Docker 29.4.2 sobre un Mac ARM64,
es decir, **con emulación**. Resultados en [`evidencias/`](../../evidencias/):

| Comprobación | Resultado |
|---|---|
| `/health` | 200, `B-causal_v2-259f9467e2d3`, CPU |
| Seis casos de `casos_inferencia.json` | Todos dentro de 1e-6; diferencia máxima 8.9e-8 |
| Entrada inválida | 422 |
| PyTorch en la imagen | `2.13.0+cpu`, x86_64, 1 hilo |
| Memoria del contenedor en reposo tras las pruebas | ~356 MiB |
| Tamaño de la imagen | 431 MB |

La latencia medida con emulación (mediana 7.3 ms en localhost) no describe el
hosting. Las cifras del servidor real se obtienen con el verificador de abajo.

## Render

`render.yaml` (raíz del repositorio) define un Web Service Docker con
`rootDir: Proyecto1`, `healthCheckPath: /health` y `RIESGO_HILOS=1`.

Pasos (requieren la cuenta de quien despliega):

1. En Render: **New → Blueprint** y elegir el repositorio. Render lee `render.yaml`.
   Alternativa manual: **New → Web Service**, runtime Docker, Root Directory
   `Proyecto1`, Health Check Path `/health`.
2. Elegir el plan. El plan Free (512 MB) debería alcanzar según los ~356 MiB
   medidos, pero con poco margen y se suspende tras 15 minutos sin tráfico; la
   primera solicitud después tarda en responder. Para la presentación, abrir la
   página unos minutos antes o usar un plan de pago.
3. Esperar a que `/health` responda y ejecutar el verificador contra la URL pública.

### Despliegue realizado (13 nov 2026)

- URL: <https://riesgo-transaccional.onrender.com>.
- Creado como Blueprint desde el repositorio público, rama `main`, plan Free
  (512 MB, 0.15 CPU), región Oregon. Render construye la imagen con el Dockerfile.
- Verificador: `/health` 200, interfaz 200, seis casos dentro de 1e-6 (diferencia
  máxima 2.98e-08), entrada inválida 422. Latencia desde Guatemala con red:
  mediana 280 ms, p95 1,275 ms. En el servidor `/predict` tarda 9 a 15 ms.
- El plan Free no muestra memoria ni CPU; no hubo reinicios por memoria.
- Evidencias en [`evidencias/`](../../evidencias/README.md).

## Verificar un despliegue

Desde `Proyecto1/`, sin PyTorch (solo biblioteca estándar):

```bash
python -m src.verificar_despliegue https://<servicio>.onrender.com --salida ../evidencias/verificacion_render.json
```

Comprueba `/health`, la interfaz, los seis puntajes con tolerancia 1e-6 y un 422.
También mide la latencia vista por el cliente, con la red incluida. Termina con
código 1 si alguna comprobación falla.
La primera llamada se registra aparte porque puede despertar un servicio suspendido.

## Registros y monitoreo

**Implementado.** Cada solicitud genera una línea JSON en la salida estándar
(visible en *Logs* de Render) con `fecha_utc`, `id_solicitud`, `metodo`, `ruta`,
`estado_http`, `duracion_ms` y `version_modelo`. No se registran montos, ciudades,
rubros ni el cuerpo de la solicitud. La respuesta incluye `X-Request-ID`, que la
interfaz muestra para cruzar un resultado con su registro. Render usa `/health`
para reiniciar el servicio si deja de responder.

Cómo revisar:

- **Salud:** `GET /health` o el estado del servicio en Render.
- **Errores:** filtrar en los logs `"estado_http": 422` (entradas inválidas) y
  `"estado_http": 5` (fallos del servicio o modelo no disponible).
- **Latencia:** `duracion_ms` en los logs (tiempo en el servidor) y el
  verificador (tiempo del cliente). Métricas de CPU y RAM en el panel de Render.

**Propuesta, no implementada:**

- *Deriva de datos:* guardar agregados diarios anónimos de las entradas
  (distribución de montos, proporción de canales y ciudades, tasa de categorías
  desconocidas) y compararlos con el entrenamiento mediante PSI. Un PSI > 0.2
  sostenido o muchas categorías desconocidas indicaría revisar el modelo.
- *Deriva de desempeño:* requiere etiquetas confirmadas (contracargos) que
  llegan con semanas de retraso. Con ellas se recalcula AUC-PR y exhaustividad
  por mecanismo cada mes.
- *Recalibrar* el umbral si cambia la tasa de fraude o los costos FN/FP sin que
  cambie el patrón. *Reentrenar* si cae el desempeño, aparece un mecanismo nuevo
  (como F4, que hoy no se detecta) o cambian los vocabularios. Cualquier versión
  nueva debe pasar la misma validación causal y la verificación de paridad antes
  de reemplazar a `B-causal_v2`.
- *Alertas:* tasa de 5xx > 1 % o p95 de `duracion_ms` > 500 ms en 15 minutos.
