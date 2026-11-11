# Latencia local del modelo B en CPU

Medición UTC: 2026-11-11T15:18:32.059128+00:00. Modelo: `B-causal_v2-259f9467e2d3`.

Entorno: macOS-26.2-arm64-arm-64bit-Mach-O, Python 3.13.12, PyTorch 2.13.0, 4 hilos de CPU.

## Método

Se reutilizó una instancia del cargador. Para cada longitud (1 y 20 eventos)
se usó un caso sintético guardado, con 30 predicciones de calentamiento y
300 repeticiones medidas. Se midieron por separado preparación (validación,
características y conversión a tensores), inferencia y la interfaz pública
`predecir` completa. Esta última tiene su propia medición; no es una suma
de percentiles. Se utilizó un reloj monotónico de alta resolución.

No hay red, HTTP ni solicitudes concurrentes. Son dos entradas concretas en
este equipo, no una garantía de latencia en el hosting. Los percentiles de
carga se basan en 10 repeticiones y son descriptivos de esa muestra pequeña.

## Carga de artefactos

- Primera carga en el proceso: **4.852 ms**.
- Cargas repetidas: mediana **1.238 ms**, p95 **1.303 ms**.

La carga incluye lectura y SHA-256 de los tres archivos necesarios para B,
validación de metadatos y construcción del modelo. Excluye importaciones de
Python/PyTorch y arranque del proceso. No se vació la caché de disco; por tanto
la primera medición no representa un arranque con disco frío.

## Predicción con el modelo cargado

| Eventos | Etapa | Mediana (ms) | p95 (ms) |
|---:|---|---:|---:|
| 1 | Preparación | 0.872 | 0.918 |
| 1 | Inferencia | 0.220 | 0.233 |
| 1 | Predicción completa | 1.094 | 1.138 |
| 20 | Preparación | 1.639 | 1.738 |
| 20 | Inferencia | 0.225 | 0.242 |
| 20 | Predicción completa | 1.865 | 1.974 |

La preparación consume la mayor parte del tiempo en estas mediciones.
No se requiere volver a cargar los pesos por transacción.

## Reproducción y pruebas

Desde `Proyecto1/`, con el entorno documentado en el README:

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 python -m src.medir_latencia --hilos 4
python -m src.inferencia --entrada ejemplos/solicitud_riesgo.json
```

Datos completos: `docs/latencia_cpu.json` y `docs/registro_latencia_cpu.log`.
La suite completa pasó **111 pruebas en 42.64 segundos**; registro en
`docs/registro_pruebas_cargador.log`. Incluye la paridad de los seis casos,
integridad, incompatibilidades, errores de entrada y reutilización de pesos.

La integración local con la API ya está implementada; ver [API.md](API.md).
Falta medir el servicio desplegado.
