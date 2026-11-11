# API de riesgo transaccional

Usa B causal_v2 en CPU. Carga una instancia por proceso al iniciar y la reutiliza
para todas las solicitudes. Si el bundle es incompleto o incompatible, el proceso
falla al arrancar. No se entrena desde la API.

## Ejecutar

Desde `Proyecto1/`, con el entorno Python del README:

```bash
python -m pip install -r requirements-api.txt
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Documentación interactiva: `http://127.0.0.1:8000/docs`.
Esquema OpenAPI: `http://127.0.0.1:8000/openapi.json`.

Configuración opcional: `RIESGO_BUNDLE` (ruta de artefactos) y `RIESGO_HILOS`
(entero positivo; por defecto 4). El bundle predeterminado se resuelve respecto
al módulo. Con varios workers cada proceso carga su propio modelo; esta entrega
local se verifica con un solo proceso. No modifica los archivos del entrenamiento.

## Contrato

| Método | Ruta | Resultado |
|---|---|---|
| GET | `/health` | Estado de disponibilidad, dispositivo y versión |
| POST | `/predict` | Puntaje y versión del modelo |

Ejemplo reproducible:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/predict \
  -H 'Content-Type: application/json' \
  --data-binary @ejemplos/solicitud_riesgo.json
```

Entrada: `{"transacciones": [...]}`, de 1 a 20 eventos de una sola tarjeta en
orden cronológico. Cada evento contiene solo `marca_tiempo` (días desde el origen
fijo de la simulación), `monto` (positivo en Q), `rubro`, `canal` y `ciudad`.
Números finitos, textos no vacíos y sin etiquetas ni campos adicionales.
Se aceptan categorías nuevas mediante el índice 0 y ventanas cortas con relleno.
Las fechas de calendario aún requieren definir una conversión al origen fijo.

Salida: `{"puntaje_riesgo": 0.04, "version_modelo": "B-causal_v2-..."}`.
El ejemplo numérico es ilustrativo; los puntajes exactos de los casos guardados
se verifican en pruebas. No se bloquea una transacción automáticamente: el umbral
es una política separada y el puntaje no se presenta como probabilidad calibrada.

Errores:

- `422`: JSON, campos, cantidad, tipos, montos u orden inválidos.
- `503`: modelo no disponible.
- `500`: fallo interno de inferencia, con mensaje genérico al consumidor.

Cada respuesta tiene `X-Request-ID`. El registro JSON contiene fecha UTC,
identificador, método, ruta, estado HTTP, duración y versión. No guarda el cuerpo
ni los valores de las transacciones. La duración del middleware es local al
servidor y no mide el tiempo de red del usuario.

## Pruebas y estado

`tests/test_api.py` prueba predicciones reales contra los seis casos del
experimento, carga única por arranque, disponibilidad, documentación, errores,
JSON inválido, categorías nuevas y registros. Ejecutar desde `Proyecto1/`:

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 python -m pytest -q
```

La suite completa pasó **134 pruebas en 43.27 segundos**, con registro en
`docs/registro_pruebas_api.log`. Una ejecución adicional con Uvicorn y HTTP
real comprobó `/health` y `/predict`; evidencia en `docs/prueba_api_local.json`
y `docs/registro_api_local.log`. El servidor de esa prueba se cerró al terminar.

Esta es una API local verificable. El enlace público, interfaz, despliegue y
capturas de uso desde otro equipo siguen en las tareas de integración.

Se usaron el ciclo de vida y el cliente de pruebas documentados por FastAPI:
[gestión de lifespan](https://fastapi.tiangolo.com/advanced/events/) y
[TestClient](https://fastapi.tiangolo.com/tutorial/testing/).
