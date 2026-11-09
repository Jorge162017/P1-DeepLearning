import numpy as np
import pytest
from src.config import CARTERA_TARJETAS, COSTO_FN, COSTO_FP
from src.evaluacion import (barrer_umbrales, costo_esperado, elegir_umbral,
                            escalar_a_cartera_mensual)


def test_costo_esperado_cuenta_bien():
    y = np.array([1, 1, 0, 0])
    p = np.array([0.9, 0.1, 0.9, 0.1])
    # umbral 0.5 -> 1 VP, 1 FN, 1 FP, 1 VN
    assert costo_esperado(y, p, 0.5) == pytest.approx(COSTO_FN + COSTO_FP)


def test_umbral_cero_bloquea_todo():
    y = np.array([1, 0, 0, 0])
    p = np.array([0.9, 0.8, 0.7, 0.6])
    assert costo_esperado(y, p, 0.0) == pytest.approx(3 * COSTO_FP)


def test_umbral_uno_no_bloquea_nada():
    y = np.array([1, 1, 0, 0])
    p = np.array([0.9, 0.8, 0.7, 0.6])
    assert costo_esperado(y, p, 1.01) == pytest.approx(2 * COSTO_FN)


def test_el_umbral_elegido_minimiza_el_costo_en_validacion():
    rng = np.random.default_rng(0)
    y = rng.binomial(1, 0.02, 4000)
    p = np.clip(rng.normal(0.15 + 0.55 * y, 0.15), 0, 1)
    u = elegir_umbral(y, p)
    tabla = barrer_umbrales(y, p)
    assert costo_esperado(y, p, u) == pytest.approx(tabla["costo"].min())
    assert 0.0 <= u <= 1.0


def test_el_umbral_favorece_la_exhaustividad():
    """Con Q4200 contra Q180 sale mas barato bloquear de mas, asi que el umbral baja."""
    rng = np.random.default_rng(1)
    y = rng.binomial(1, 0.02, 4000)
    p = np.clip(rng.normal(0.15 + 0.55 * y, 0.15), 0, 1)
    assert elegir_umbral(y, p) < 0.5


def test_barrido_devuelve_columnas_esperadas():
    rng = np.random.default_rng(2)
    y = rng.binomial(1, 0.05, 500)
    p = rng.random(500)
    t = barrer_umbrales(y, p, n=50)
    assert list(t.columns) == ["umbral", "costo", "precision", "exhaustividad", "f1"]
    assert len(t) == 50


def test_escalado_a_cartera_mensual():
    # Q1000 en 28 dias con 6000 tarjetas simuladas
    r = escalar_a_cartera_mensual(1000.0, n_dias_bloque=28, n_tarjetas_simuladas=6000)
    assert r == pytest.approx(1000.0 * (30 / 28) * (CARTERA_TARJETAS / 6000))
