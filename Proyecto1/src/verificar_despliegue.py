"""Verifica un servicio desplegado contra los seis casos guardados.

Uso desde Proyecto1/ (solo biblioteca estandar, no carga PyTorch):

    python -m src.verificar_despliegue https://mi-servicio.onrender.com \
        --salida ../evidencias/verificacion_render.json

Comprueba /health, la interfaz en /, los seis puntajes de casos_inferencia.json
con tolerancia 1e-6, una entrada invalida (422) y mide la latencia vista por el
cliente (incluye red). No envia datos reales: solo los casos sinteticos guardados.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter
import urllib.error
import urllib.request

RAIZ = Path(__file__).resolve().parents[1]
CASOS = RAIZ / 'artefactos' / 'causal_v2' / 'casos_inferencia.json'
TOLERANCIA = 1e-6


def solicitar(url, cuerpo=None, limite=90):
    datos = None if cuerpo is None else json.dumps(cuerpo).encode()
    peticion = urllib.request.Request(url, data=datos, method='GET' if datos is None else 'POST',
                                      headers={'Content-Type': 'application/json',
                                               'User-Agent': 'verificador-riesgo/1.0'})
    inicio = perf_counter()
    try:
        with urllib.request.urlopen(peticion, timeout=limite) as r:
            estado, texto, cabeceras = r.status, r.read().decode(), r.headers
    except urllib.error.HTTPError as e:
        estado, texto, cabeceras = e.code, e.read().decode(), e.headers
    ms = (perf_counter() - inicio) * 1000
    try:
        contenido = json.loads(texto)
    except ValueError:
        contenido = texto
    return estado, contenido, cabeceras.get('X-Request-ID'), ms


def verificar(base, repeticiones=20):
    base = base.rstrip('/')
    casos = json.loads(CASOS.read_text())
    informe = {'servicio': base, 'fecha_utc': datetime.now(timezone.utc).isoformat(),
               'tolerancia': TOLERANCIA, 'comprobaciones': []}

    def anotar(nombre, ok, **extra):
        informe['comprobaciones'].append({'nombre': nombre, 'ok': bool(ok), **extra})
        print(f"[{'OK' if ok else 'FALLA'}] {nombre} {json.dumps(extra, ensure_ascii=False)}")

    # La primera llamada puede despertar un servicio suspendido: se mide aparte.
    estado, salud, rid, ms = solicitar(f'{base}/health')
    anotar('health', estado == 200 and isinstance(salud, dict) and salud.get('estado') == 'ok',
           estado_http=estado, respuesta=salud, id_solicitud=rid, ms_primera_llamada=round(ms, 1))
    informe['version_modelo'] = salud.get('version_modelo') if isinstance(salud, dict) else None

    estado, pagina, rid, _ = solicitar(f'{base}/')
    anotar('interfaz', estado == 200 and 'Riesgo transaccional' in str(pagina), estado_http=estado)

    for caso in casos:
        estado, r, rid, ms = solicitar(f'{base}/predict', {'transacciones': caso['transacciones']})
        puntaje = r.get('puntaje_riesgo') if isinstance(r, dict) else None
        diferencia = None if puntaje is None else abs(puntaje - caso['puntaje_b_esperado'])
        anotar(f"caso_{caso['id_tx']}_{caso['mecanismo']}",
               estado == 200 and diferencia is not None and diferencia <= TOLERANCIA,
               estado_http=estado, esperado=caso['puntaje_b_esperado'], obtenido=puntaje,
               diferencia=diferencia, id_solicitud=rid, version=r.get('version_modelo') if isinstance(r, dict) else None)

    invalido = [dict(casos[0]['transacciones'][0], monto=-1)]
    estado, r, rid, _ = solicitar(f'{base}/predict', {'transacciones': invalido})
    anotar('entrada_invalida_422', estado == 422, estado_http=estado, id_solicitud=rid)

    cuerpo = {'transacciones': casos[2]['transacciones']}
    tiempos = [solicitar(f'{base}/predict', cuerpo)[3] for _ in range(repeticiones)]
    tiempos.sort()
    informe['latencia_cliente_ms'] = {
        'n': repeticiones, 'mediana': round(statistics.median(tiempos), 1),
        'p95': round(tiempos[max(0, int(0.95 * repeticiones) - 1)], 1),
        'max': round(tiempos[-1], 1), 'nota': 'Incluye red entre el cliente y el servidor',
    }
    print('Latencia (ms):', informe['latencia_cliente_ms'])
    informe['todo_ok'] = all(c['ok'] for c in informe['comprobaciones'])
    return informe


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('url', help='URL base del servicio, p. ej. https://x.onrender.com')
    parser.add_argument('--salida', type=Path, help='Ruta del informe JSON')
    parser.add_argument('--repeticiones', type=int, default=20)
    args = parser.parse_args()
    informe = verificar(args.url, args.repeticiones)
    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + '\n')
        print(f'Informe: {args.salida}')
    sys.exit(0 if informe['todo_ok'] else 1)


if __name__ == '__main__':
    main()
