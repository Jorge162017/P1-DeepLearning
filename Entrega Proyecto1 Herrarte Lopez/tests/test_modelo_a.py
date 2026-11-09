import numpy as np
import pytest
from src.evaluacion import auc_pr, roc_auc
from src.modelos import entrenar_a, puntajes_a


def test_auc_pr_perfecto_y_aleatorio():
    y = np.array([0, 0, 0, 1, 1])
    assert auc_pr(y, np.array([0.1, 0.2, 0.3, 0.9, 0.95])) == pytest.approx(1.0)
    assert roc_auc(y, np.array([0.1, 0.2, 0.3, 0.9, 0.95])) == pytest.approx(1.0)


def test_roc_auc_de_puntaje_constante_es_media():
    y = np.array([0, 1, 0, 1])
    assert roc_auc(y, np.full(4, 0.5)) == pytest.approx(0.5)


def test_a_aprende_una_senal_obvia():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(2000, 5))
    y = (X[:, 0] + rng.normal(0, 0.3, 2000) > 1.0).astype(int)
    modelo = entrenar_a(X[:1500], y[:1500], X[1500:], y[1500:])
    p = puntajes_a(modelo, X[1500:])
    assert p.shape == (500,)
    assert ((p >= 0) & (p <= 1)).all()
    assert auc_pr(y[1500:], p) > 0.75


def test_a_es_reproducible():
    rng = np.random.default_rng(1)
    X, y = rng.normal(size=(800, 4)), rng.integers(0, 2, 800)
    a = puntajes_a(entrenar_a(X[:600], y[:600], X[600:], y[600:], semilla=3), X[600:])
    b = puntajes_a(entrenar_a(X[:600], y[:600], X[600:], y[600:], semilla=3), X[600:])
    assert np.allclose(a, b)
