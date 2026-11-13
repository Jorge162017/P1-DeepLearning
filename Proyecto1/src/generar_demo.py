"""Genera web/demo.json con ejemplos sinteticos y la politica de referencia.

Ejecutar desde Proyecto1/: python -m src.generar_demo

Los ejemplos salen de artefactos/causal_v2/casos_inferencia.json (datos sinteticos
de validacion/entrenamiento ya publicados en el repositorio). El umbral y los costos
salen de metadatos.json. No se entrena ni se recalcula nada.
"""
import json
from pathlib import Path

from src.inferencia import BUNDLE_PREDETERMINADO

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / 'web' / 'demo.json'

# Orden y textos de cada caso guardado, identificados por id_tx.
DESCRIPCIONES = {
    76: ('Legítima habitual', 'legitimo',
         'Compras cotidianas en la ciudad habitual de la tarjeta.'),
    52423: ('Señuelo legítimo', 'legitimo',
            'Microcompras desordenadas y un cobro grande, pero legítimas: '
            'parecido superficial con F1.'),
    6416: ('Fraude F1 (rampa)', 'fraude',
           'Compras pequeñas en rampa y un cobro grande. Es el patrón más difícil: '
           'en este caso el puntaje queda bajo el umbral (falso negativo).'),
    1405: ('Fraude F2 (ciudades lejanas)', 'fraude',
           'Transacciones en ciudades lejanas con poca separación temporal.'),
    20511: ('Fraude F3 (ráfaga ecommerce)', 'fraude',
            'Ráfaga de ecommerce caro de madrugada.'),
    0: ('Secuencia corta (1 evento)', 'legitimo',
        'Tarjeta sin historia: el modelo rellena la ventana. Sirve para probar '
        'secuencias cortas.'),
}


def construir(ruta_bundle=BUNDLE_PREDETERMINADO):
    ruta_bundle = Path(ruta_bundle)
    casos = json.loads((ruta_bundle / 'casos_inferencia.json').read_text())
    metadatos = json.loads((ruta_bundle / 'metadatos.json').read_text())
    vocab = json.loads((ruta_bundle / 'vocabularios.json').read_text())
    por_id = {c['id_tx']: c for c in casos}
    faltan = set(DESCRIPCIONES) - set(por_id)
    if faltan:
        raise ValueError(f'Casos ausentes en casos_inferencia.json: {sorted(faltan)}')

    ejemplos = []
    for id_tx, (nombre, tipo, descripcion) in DESCRIPCIONES.items():
        caso = por_id[id_tx]
        ejemplos.append({
            'id': f'caso_{id_tx}', 'nombre': nombre, 'tipo': tipo,
            'descripcion': descripcion, 'mecanismo': caso['mecanismo'],
            'puntaje_esperado': caso['puntaje_b_esperado'],
            'transacciones': caso['transacciones'],
        })

    return {
        'nota': 'Generado por src/generar_demo.py; no editar a mano.',
        'version_preprocesamiento': metadatos['version_preprocesamiento'],
        'umbral_referencia': metadatos['umbrales']['B'],
        'costos': metadatos['costos'],
        'vocabularios': {'rubros': vocab['rubros'], 'canales': vocab['canales'],
                         'ciudades': vocab['ciudades']},
        'ejemplos': ejemplos,
    }


def main():
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text(json.dumps(construir(), ensure_ascii=False, indent=2) + '\n')
    print(f'Escrito {DESTINO.relative_to(RAIZ)}')


if __name__ == '__main__':
    main()
