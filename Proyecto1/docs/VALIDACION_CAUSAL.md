# Validación del reentrenamiento causal

Ejecución UTC: 2026-11-11T14:37:24.009560+00:00. Preprocesamiento: `causal_v2`.

## Diseño fijado antes de esta ejecución

Se conserva el generador original: 6,000 tarjetas, 180 días, semilla 42,
ventanas de 20, 12 épocas, Adam (1e-3), lotes de 256 y entrenamiento en CPU.
Se conserva la mejor época de cada GRU por average precision en validación
(denominada AUC-PR en el Proyecto 1). El umbral minimiza Q4,200 × FN + Q180 × FP
en una rejilla de 200 valores sobre validación. No se optimiza en prueba.

Hipótesis original de C: superar al mejor de A y B en al menos 0.02 de
AUC-PR en validación y conservar la exhaustividad de B (tolerancia 0.02)
en al menos dos mecanismos de validación. Este es el criterio ya codificado;
no se modifica para obtener un resultado favorable.

La corrección usa la moda de las 19 transacciones anteriores como ciudad base,
con desempate alfabético; sin historia usa la ciudad actual. Todos los eventos
de la ventana se expresan respecto a esa base. Los escaladores se ajustan
exclusivamente en entrenamiento. Los empates temporales conservan el orden recibido.

**Limitación:** el conjunto de prueba ya fue observado en Proyecto 1.
Esta ejecución es una reevaluación tras corregir una fuga, no una evaluación
independiente con datos nuevos. No se hicieron búsquedas de hiperparámetros.
Las diferencias también pueden reflejar versiones de librerías distintas.

## Datos y particiones

| Partición | Transacciones | Fraudes | Tasa |
|---|---:|---:|---:|
| embargo | 10840 | 95 | 0.8764% |
| entrenamiento | 322903 | 1948 | 0.6033% |
| prueba | 75459 | 620 | 0.8216% |
| validacion | 75536 | 518 | 0.6858% |

## Métricas anteriores y corregidas

Los valores anteriores corresponden a los artefactos originales con ciudad base
calculada sobre la historia completa; se toman de la tabla del notebook original
con cuatro decimales de precisión publicada.

| Modelo | Val. anterior | Val. causal | Prueba anterior | Prueba causal | Umbral causal |
|---|---:|---:|---:|---:|---:|
| A | 0.8101 | 0.809183 | 0.5486 | 0.549369 | 0.668342 |
| B | 0.8822 | 0.874442 | 0.6103 | 0.608519 | 0.733668 |
| C | 0.8566 | 0.863147 | 0.5999 | 0.608834 | 0.804020 |

## Permutaciones sobre validación

| Modelo | Original | P1: historia barajada | P2: todas las posiciones |
|---|---:|---:|---:|
| A | 0.809183 | 0.809183 | 0.809183 |
| B | 0.874442 | 0.683456 | 0.016908 |
| C | 0.863147 | 0.797279 | 0.263453 |

P2 también cambia la posición del ancla, por lo que su caída no aísla
por sí sola el valor del orden histórico; P1 conserva el ancla.

## Métricas con umbrales congelados

| Modelo | Precisión | Exhaustividad | F1 | VP | FP | VN | FN | Costo bloque (Q) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 0.3413 | 0.6710 | 0.4524 | 416 | 803 | 74036 | 204 | 1001340 |
| B | 0.5292 | 0.6726 | 0.5923 | 417 | 371 | 74468 | 203 | 919380 |
| C | 0.4830 | 0.6887 | 0.5678 | 427 | 457 | 74382 | 193 | 892860 |

## Exhaustividad por mecanismo en prueba

| Mecanismo | n | A | B | C |
|---|---:|---:|---:|---:|
| F1 | 211 | 0.8531 | 0.8578 | 0.9052 |
| F2 | 103 | 1.0000 | 1.0000 | 1.0000 |
| F3 | 133 | 1.0000 | 1.0000 | 1.0000 |
| F4 | 173 | 0.0000 | 0.0000 | 0.0000 |

## Compuertas y veredicto

- ROC-AUC señuelo en cobro: **0.538646** (máximo original: 0.60).
- ROC-AUC señuelo en todas las anclas: **0.617119** (techo original: 0.70).
- Margen de C: **-0.011295** (exigido: +0.02).
- Condición por mecanismo: **True**.
- Hipótesis de C cumplida: **False**.

B frente a A en validación: +0.065258.
La candidatura de B para el demo debe leerse con estas métricas y con los límites
de datos sintéticos. Ni los costos absolutos ni los porcentajes de ahorro
son pronósticos de desempeño bancario real. F4 queda fuera del entrenamiento.

## Interpretación para la selección del demo

B conserva la mejor AUC-PR de validación y supera A por 0.065258; se mantiene
como candidato para el demo. La mejor época de B fue la 5 (de 12); la de C fue
la 4. No se eligió el último estado del entrenamiento.

C obtiene una AUC-PR de prueba ligeramente mayor que B (0.608834 frente a
0.608519) y un menor costo en ese bloque. Eso se reporta, pero no justifica
cambiar la selección mirando prueba: C no alcanzó el margen de +0.02 en
validación y su hipótesis original sigue sin cumplirse.

Con sus umbrales de validación, B y A tienen exhaustividad de F1 cercana
(0.8578 y 0.8531). En el bloque de prueba B reduce los falsos positivos de
803 a 371, con 203 fraudes no detectados frente a 204 de A. La mejora actual
no debe narrarse como una gran ganancia de exhaustividad de F1. Al barajar
solo la historia de B, su AUC-PR de validación baja de 0.874442 a 0.683456:
esa es evidencia adicional de que aprovecha el orden en este simulador.

Los tres modelos siguen con exhaustividad cero en F4. El servicio demostrará
un puntaje sintético y sus límites; no cubrirá todos los mecanismos de fraude.

## Artefactos para continuar con B en CPU

Carpeta: `artefactos/causal_v2/`. Los artefactos originales no se sobrescriben.

- `modelo_b_gru.pt`: state_dict, sin requerir GPU.
- `escaladores.json`: usar la sección `secuencia`.
- `vocabularios.json`: códigos por índice + 1; 0 para desconocidos/relleno.
- `metadatos.json`: arquitectura, versiones, semilla, umbrales y hashes.
- `casos_inferencia.json`: entradas sintéticas y puntajes esperados para comprobar carga.
- `verificacion_cpu.json`: comprobación de exportación y paridad, no un servidor de producción.
- `resumen_metricas.json`, `resultados.pkl` y `puntajes.npz`: resultados auditables.
- `figuras/`: las cinco figuras regeneradas.

El contrato usa `marca_tiempo` en días desde un origen fijo: la simulación comienza
en día 0 y el día de semana se calcula como piso(día) módulo 7. La integración
de fechas reales debe fijar y conservar esa convención. El puntaje es una salida
sigmoide de un modelo con ponderación de clases; no se afirma que esté calibrado.

Las instrucciones reproducibles y los controles de exportación están en el README.

## Verificación de la entrega

La suite completa terminó con **88 pruebas aprobadas en 42.86 segundos**.
El registro está en `docs/registro_pruebas.log`; el entrenamiento y sus épocas
están en `docs/registro_reentrenamiento.log`. Se verificaron también las huellas
del código contra `metadatos.json`, la integridad de los archivos exportados y
las métricas recalculadas a partir de los puntajes guardados.

B recargado en CPU coincidió en los seis casos sintéticos guardados con error
absoluto máximo **5.960464477539063e-08**, frente a tolerancia de 1e-6.
La implementación del cargador reutilizable y la medición de latencia son el
siguiente paso; esta comprobación valida la exportación, no sustituye esa tarea.
