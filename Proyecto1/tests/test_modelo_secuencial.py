import numpy as np
import torch
from src.modelos import (ModeloSecuencial, entrenar_secuencial,
                         puntajes_secuencial)

K, N_RUBROS, N_CANALES, N_CIUDADES = 20, 11, 5, 11


def _lote(n=64, semilla=0):
    g = torch.Generator().manual_seed(semilla)
    return {
        "cat": torch.stack([
            torch.randint(0, N_RUBROS, (n, K), generator=g),
            torch.randint(0, N_CANALES, (n, K), generator=g),
            torch.randint(0, N_CIUDADES, (n, K), generator=g),
        ], dim=2),
        "num": torch.randn(n, K, 7, generator=g),
        "mascara": torch.ones(n, K, dtype=torch.bool),
        "agregados": torch.randn(n, 15, generator=g),
        "y": torch.randint(0, 2, (n,), generator=g).float(),
    }


def test_forma_de_salida_y_modo_b():
    m = ModeloSecuencial(N_RUBROS, N_CANALES, N_CIUDADES, n_agregados=0)
    lote = _lote()
    assert m(lote["cat"], lote["num"], lote["mascara"], None).shape == (64,)


def test_modo_hibrido_acepta_agregados():
    m = ModeloSecuencial(N_RUBROS, N_CANALES, N_CIUDADES, n_agregados=15)
    lote = _lote()
    assert m(lote["cat"], lote["num"], lote["mascara"], lote["agregados"]).shape == (64,)


def test_el_relleno_no_altera_la_salida():
    """Agregar pasos enmascarados al inicio no deberia cambiar nada."""
    torch.manual_seed(0)
    m = ModeloSecuencial(N_RUBROS, N_CANALES, N_CIUDADES).eval()
    lote = _lote(n=8)
    corto = lote["mascara"].clone()
    corto[:, :5] = False                       # los 5 primeros pasos son relleno
    with torch.no_grad():
        a = m(lote["cat"], lote["num"], corto, None)
        cat2, num2 = lote["cat"].clone(), lote["num"].clone()
        cat2[:, :5] = 99 % N_RUBROS            # basura en las posiciones enmascaradas
        num2[:, :5] = 1234.0
        b = m(cat2, num2, corto, None)
    assert torch.allclose(a, b, atol=1e-5), "el enmascarado no esta funcionando"


def test_el_orden_importa_para_el_modelo():
    """Si invertimos la secuencia, un GRU tiene que dar otra cosa."""
    torch.manual_seed(0)
    m = ModeloSecuencial(N_RUBROS, N_CANALES, N_CIUDADES).eval()
    lote = _lote(n=16)
    with torch.no_grad():
        directo = m(lote["cat"], lote["num"], lote["mascara"], None)
        inverso = m(lote["cat"].flip(1), lote["num"].flip(1), lote["mascara"], None)
    assert not torch.allclose(directo, inverso)


def test_aprende_un_patron_de_orden_sintetico():
    """Positivo si el ultimo numerico supera al primero. Eso solo se ve en el orden."""
    torch.manual_seed(0)
    n = 1200
    num = torch.randn(n, K, 7)
    y = (num[:, -1, 0] > num[:, 0, 0]).float()
    datos = {
        "cat": torch.zeros(n, K, 3, dtype=torch.long),
        "num": num,
        "mascara": torch.ones(n, K, dtype=torch.bool),
        "agregados": torch.zeros(n, 0),
        "y": y,
    }
    ent = {k: v[:900] for k, v in datos.items()}
    val = {k: v[900:] for k, v in datos.items()}
    m = ModeloSecuencial(N_RUBROS, N_CANALES, N_CIUDADES, n_agregados=0)
    historial = entrenar_secuencial(m, ent, val, peso_positivo=1.0, epocas=15, semilla=0)
    # entrenar_secuencial restaura la MEJOR epoca, no la ultima
    assert max(h["auc_pr_val"] for h in historial) > 0.75


def test_puntajes_estan_en_cero_uno():
    m = ModeloSecuencial(N_RUBROS, N_CANALES, N_CIUDADES)
    p = puntajes_secuencial(m, _lote(n=32))
    assert p.shape == (32,)
    assert ((p >= 0) & (p <= 1)).all()


def test_la_inicializacion_depende_solo_de_la_semilla():
    """Armar el modelo ya consume el RNG global de torch.

    Si no sembramos antes, los pesos iniciales dependen de lo que haya corrido en
    el proceso y la misma semilla termina dando resultados distintos.
    """
    torch.manual_seed(123)
    a = ModeloSecuencial(N_RUBROS, N_CANALES, N_CIUDADES)
    torch.randn(1000)                      # ensucia el estado global
    torch.manual_seed(123)
    b = ModeloSecuencial(N_RUBROS, N_CANALES, N_CIUDADES)
    for (n1, p1), (n2, p2) in zip(a.named_parameters(), b.named_parameters()):
        assert n1 == n2
        assert torch.equal(p1, p2), f"{n1} difiere: la siembra no es suficiente"
