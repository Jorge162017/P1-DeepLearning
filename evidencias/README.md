# Evidencias del pase a producción

| Archivo | Qué demuestra |
|---|---|
| `verificacion_docker_linux_amd64.json` | Imagen Docker Linux (amd64, emulada en Mac ARM64): `/health`, interfaz, seis casos dentro de 1e-6, 422 y latencia local |
| `registro_docker_linux_amd64.log` | Registros JSON por solicitud del contenedor (sin datos de transacciones) |
| `memoria_docker_linux_amd64.json` | Memoria del contenedor tras las pruebas (~356 MiB) |

| `verificacion_render.json` | Servicio público: `/health`, interfaz, seis casos (diferencia máxima 2.98e-08), 422 y latencia desde el cliente |
| `registro_render.log` | Extracto de logs de Render con las solicitudes de la verificación y de las capturas |
| `capturas/render_*.png` | Interfaz pública en escritorio y móvil: inicio, fraude F3, legítima y error 422 |
| `capturas/local_*.png` | Interfaz local antes de publicar |

Servicio: <https://riesgo-transaccional.onrender.com> (Render Free, 13 nov 2026).

Pendiente: captura y fecha de una persona ajena al equipo completando una predicción.
