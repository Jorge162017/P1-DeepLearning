# Evidencias del pase a producción

| Archivo | Qué demuestra |
|---|---|
| `verificacion_docker_linux_amd64.json` | Imagen Docker Linux (amd64, emulada en Mac ARM64): `/health`, interfaz, seis casos dentro de 1e-6, 422 y latencia local |
| `registro_docker_linux_amd64.log` | Registros JSON por solicitud del contenedor (sin datos de transacciones) |
| `memoria_docker_linux_amd64.json` | Memoria del contenedor tras las pruebas (~356 MiB) |

Pendiente tras publicar en Render:

- `verificacion_render.json`: `python -m src.verificar_despliegue <URL> --salida ../evidencias/verificacion_render.json`
- Capturas de la interfaz desde otro dispositivo o sesión, con resultado e ID de solicitud.
- Extracto de los logs de Render con las solicitudes de esa prueba.
- Prueba de una persona ajena al equipo completando una predicción.
