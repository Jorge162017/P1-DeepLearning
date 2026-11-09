import numpy as np
import pytest
from src.evaluacion import desglose_por_mecanismo, metricas_en_umbral, permutar


def _datos(n=50, K=20):
    rng = np.random.default_rng(0)
    cat = rng.integers(1, 9, (n, K, 3))
    num = rng.normal(size=(n, K, 7)).astype(np.float32)
    mascara = np.zeros((n, K), dtype=bool)
    for i in range(n):
        mascara[i, K - (5 + i % 15):] = True     # historias de largo variable
    cat[~mascara] = 0
    num[~mascara] = 0.0
    return cat, num, mascara


def test_p1_deja_el_ancla_en_su_lugar():
    cat, num, mascara = _datos()
    c2, n2 = permutar(cat, num, mascara, np.random.default_rng(1), variante="P1")
    assert np.array_equal(c2[:, -1], cat[:, -1])
    assert np.array_equal(n2[:, -1], num[:, -1])


def test_p2_puede_mover_el_ancla():
    cat, num, mascara = _datos()
    c2, _ = permutar(cat, num, mascara, np.random.default_rng(1), variante="P2")
    assert not np.array_equal(c2[:, -1], cat[:, -1])


def test_la_permutacion_conserva_el_multiconjunto_de_eventos():
    """Los eventos siguen siendo los mismos, solo cambia el orden. De eso depende
    que la prueba signifique algo."""
    cat, num, mascara = _datos()
    for variante in ["P1", "P2"]:
        c2, n2 = permutar(cat, num, mascara, np.random.default_rng(2), variante=variante)
        for i in range(len(cat)):
            obs = mascara[i]
            assert np.array_equal(np.sort(cat[i, obs, 0]), np.sort(c2[i, obs, 0]))
            assert np.allclose(np.sort(num[i, obs, 0]), np.sort(n2[i, obs, 0]))


def test_la_permutacion_no_toca_el_relleno():
    cat, num, mascara = _datos()
    c2, n2 = permutar(cat, num, mascara, np.random.default_rng(3), variante="P2")
    assert (c2[~mascara] == 0).all()
    assert (n2[~mascara] == 0).all()


def test_la_permutacion_es_reproducible():
    cat, num, mascara = _datos()
    a = permutar(cat, num, mascara, np.random.default_rng(9), variante="P1")[0]
    b = permutar(cat, num, mascara, np.random.default_rng(9), variante="P1")[0]
    assert np.array_equal(a, b)


def test_la_permutacion_no_muta_la_entrada():
    cat, num, mascara = _datos()
    copia = cat.copy()
    permutar(cat, num, mascara, np.random.default_rng(4), variante="P2")
    assert np.array_equal(cat, copia)


def test_metricas_en_umbral():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.1, 0.8, 0.6, 0.9])
    m = metricas_en_umbral(y, p, 0.5)
    assert m["vp"] == 2 and m["fp"] == 1 and m["fn"] == 0 and m["vn"] == 1
    assert m["exhaustividad"] == pytest.approx(1.0)
    assert m["precision"] == pytest.approx(2 / 3)
    assert m["f1"] == pytest.approx(0.8)


def test_desglose_por_mecanismo():
    import pandas as pd
    meta = pd.DataFrame({
        "es_fraude": [1, 1, 1, 0, 1],
        "mecanismo": ["F1", "F1", "F3", "legitimo", "F4"],
    })
    p = np.array([0.9, 0.2, 0.95, 0.1, 0.05])
    d = desglose_por_mecanismo(meta, p, umbral=0.5)
    assert d.loc["F1", "n"] == 2
    assert d.loc["F1", "exhaustividad"] == pytest.approx(0.5)
    assert d.loc["F3", "exhaustividad"] == pytest.approx(1.0)
    assert d.loc["F4", "exhaustividad"] == pytest.approx(0.0)
    assert "legitimo" not in d.index          # solo mecanismos de fraude
