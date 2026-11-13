import json

from fastapi.testclient import TestClient
import pytest

from src.api import CARPETA_WEB, crear_app
from src.generar_demo import construir


@pytest.fixture(scope='module')
def cliente():
    with TestClient(crear_app(hilos=4)) as cliente:
        yield cliente


@pytest.fixture(scope='module')
def demo():
    return json.loads((CARPETA_WEB / 'demo.json').read_text())


def test_pagina_y_recursos_se_sirven(cliente):
    r = cliente.get('/')
    assert r.status_code == 200
    assert 'text/html' in r.headers['content-type']
    assert 'Riesgo transaccional' in r.text
    assert r.headers['X-Request-ID']
    for recurso in ['app.js', 'estilos.css', 'demo.json']:
        assert cliente.get(f'/{recurso}').status_code == 200


def test_rutas_de_api_no_quedan_ocultas_por_la_interfaz(cliente):
    assert cliente.get('/health').json()['estado'] == 'ok'
    assert cliente.get('/docs').status_code == 200
    assert '/predict' in cliente.get('/openapi.json').json()['paths']
    assert cliente.get('/no-existe').status_code == 404


def test_demo_json_esta_sincronizado_con_artefactos(demo):
    # Si cambian los artefactos, hay que regenerar: python -m src.generar_demo
    assert demo == json.loads(json.dumps(construir()))


def test_demo_incluye_ejemplos_legitimos_fraude_y_secuencia_corta(demo):
    tipos = {e['tipo'] for e in demo['ejemplos']}
    assert tipos == {'legitimo', 'fraude'}
    assert any(len(e['transacciones']) < 20 for e in demo['ejemplos'])
    assert 0 < demo['umbral_referencia'] < 1


def test_cada_ejemplo_de_la_interfaz_da_el_puntaje_esperado(cliente, demo):
    for ejemplo in demo['ejemplos']:
        r = cliente.post('/predict', json={'transacciones': ejemplo['transacciones']})
        assert r.status_code == 200, ejemplo['id']
        assert r.json()['puntaje_riesgo'] == pytest.approx(ejemplo['puntaje_esperado'], abs=1e-6)


def test_error_de_validacion_identifica_fila_y_campo(cliente, demo):
    # La interfaz usa 'campo' para marcar la celda invalida.
    eventos = [dict(tx) for tx in demo['ejemplos'][0]['transacciones']]
    eventos[3]['monto'] = 'abc'
    r = cliente.post('/predict', json={'transacciones': eventos})
    assert r.status_code == 422
    campos = [d['campo'] for d in r.json()['detail']]
    assert ['body', 'transacciones', 3, 'monto'] in campos
