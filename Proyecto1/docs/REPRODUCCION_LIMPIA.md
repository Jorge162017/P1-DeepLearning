# Reproducción en un entorno limpio

Verificación realizada el 2026-11-11 (UTC), en esta misma computadora,
en una copia temporal independiente y con un entorno virtual sin paquetes del sistema.

## Por qué se hace

La ejecución de desarrollo puede depender de librerías instaladas previamente o
archivos fuera del repositorio. Esta comprobación permite verificar que el código
y las dependencias declaradas bastan para instalar, probar y servir predicciones.
No requiere otra computadora: requiere aislar la copia y las dependencias.

## Procedimiento y alcance

1. Clonar el repositorio local con `git clone --no-hardlinks` a una carpeta temporal.
   Commit verificado: `333cd1cb7e3a964c147ee8cfaa93281adf89e5ce`, el mismo HEAD de la copia de trabajo y de
   `origin/main` al iniciar la verificación. Es un clon local, no una nueva
   descarga desde GitHub; no comprueba permisos de acceso de otros usuarios.
2. Copiar únicamente el README raíz, todavía pendiente de commit, para seguir
   sus instrucciones. No se copiaron código, modelos o dependencias adicionales:
   estos proceden del commit clonado.
3. Crear un entorno virtual nuevo con Python 3.13.12. Inicialmente contenía solo
   pip y no compartía paquetes del sistema ni del usuario.
4. Instalar desde `Proyecto1/requirements-api.txt`, con descarga de dependencias
   y sin reutilizar la caché de pip. `pip check` no encontró incompatibilidades.
5. Comprobar que NumPy, pandas, PyTorch, scikit-learn, FastAPI y pytest se importan
   desde el nuevo entorno. Quitar `PYTHONPATH` y `PYTHONHOME` heredados y desactivar
   paquetes del usuario durante la ejecución.
6. Ejecutar la suite completa desde el clon con cuatro hilos: **134 pruebas
   aprobadas en 49.69 segundos**. Se registró una advertencia de deprecación de
   una dependencia de TestClient; no hubo fallos.
7. Arrancar Uvicorn desde el clon y comprobar solicitudes HTTP reales a
   `/health`, `/predict` y `/openapi.json`. Cerrar el servidor al terminar.

No se repitió el entrenamiento completo: se verificó que el repositorio entrega
los artefactos necesarios para ejecutar y probar la API sin reentrenar.

## Resultado HTTP

- `/health`: HTTP 200, modelo B causal_v2 disponible en CPU.
- `/predict`: HTTP 200, puntaje `0.041290659457445145` para el ejemplo guardado.
- `/openapi.json`: esquema con los dos endpoints comprobado.
- Versión: `B-causal_v2-259f9467e2d3`.

El primer sondeo limitó el arranque a 10 segundos y agotó la espera. Se repitió
con límite de 60 segundos; el segundo arranque llegó a `/health` en
2.677 segundos. Este tiempo incluye arranque e importaciones;
no es la latencia de una predicción ni garantiza un tiempo en el hosting.

## Evidencias

- [Instalación](registro_instalacion_limpia.log).
- [Aislamiento de dependencias](aislamiento_entorno_limpio.json).
- [Versiones instaladas](dependencias_entorno_limpio.txt).
- [Suite completa](registro_pruebas_entorno_limpio.log).
- [Resultado HTTP](prueba_api_entorno_limpio.json).
- [Registros de Uvicorn](registro_api_entorno_limpio.log).

La reproducción aislada local quedó verificada en macOS ARM64 y Python 3.13.12.
El despliegue en otro sistema y el uso de una persona externa siguen pendientes.
