"""Metricas, umbral, costo y pruebas de falsificacion."""
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


def auc_pr(y, puntajes) -> float:
    """Area bajo la curva precision-exhaustividad. Es la metrica principal aqui."""
    return float(average_precision_score(np.asarray(y), np.asarray(puntajes)))


def roc_auc(y, puntajes) -> float:
    y = np.asarray(y)
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(roc_auc_score(y, np.asarray(puntajes)))


import pandas as pd

from src.config import CARTERA_TARJETAS, COSTO_FN, COSTO_FP


def permutar(seq_cat, seq_num, mascara, rng, variante="P1"):
    """Baraja el orden de cada secuencia sin tocar los eventos.

    P1 baraja solo la historia y deja el ancla al final. P2 baraja las 20 posiciones.
    """
    if variante not in {"P1", "P2"}:
        raise ValueError(f"variante desconocida: {variante}")
    cat, num = seq_cat.copy(), seq_num.copy()
    for i in range(mascara.shape[0]):
        posiciones = np.flatnonzero(mascara[i])
        if variante == "P1":
            posiciones = posiciones[:-1]        # deja fuera el ancla
        if len(posiciones) < 2:
            continue
        barajadas = rng.permutation(posiciones)
        cat[i, posiciones] = seq_cat[i, barajadas]
        num[i, posiciones] = seq_num[i, barajadas]
    return cat, num


def metricas_en_umbral(y, puntajes, umbral: float) -> dict:
    y = np.asarray(y).astype(int)
    pred = (np.asarray(puntajes) >= umbral).astype(int)
    vp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    vn = int(((pred == 0) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    precision = vp / (vp + fp) if vp + fp else 0.0
    exhaustividad = vp / (vp + fn) if vp + fn else 0.0
    f1 = (2 * precision * exhaustividad / (precision + exhaustividad)
          if precision + exhaustividad else 0.0)
    return {"precision": precision, "exhaustividad": exhaustividad, "f1": f1,
            "vp": vp, "fp": fp, "vn": vn, "fn": fn}


def desglose_por_mecanismo(meta, puntajes, umbral: float) -> pd.DataFrame:
    """Exhaustividad separada por mecanismo de fraude."""
    d = pd.DataFrame({
        "mecanismo": np.asarray(meta["mecanismo"]),
        "es_fraude": np.asarray(meta["es_fraude"]).astype(int),
        "puntaje": np.asarray(puntajes),
    })
    d = d[d["es_fraude"] == 1]
    d["detectado"] = (d["puntaje"] >= umbral).astype(int)
    return d.groupby("mecanismo").agg(
        n=("detectado", "size"),
        exhaustividad=("detectado", "mean"),
        puntaje_medio=("puntaje", "mean"),
    )


def costo_esperado(y, puntajes, umbral, costo_fn=COSTO_FN, costo_fp=COSTO_FP) -> float:
    """Q4,200 por fraude que se escapa, Q180 por legitima bloqueada."""
    m = metricas_en_umbral(y, puntajes, umbral)
    return m["fn"] * costo_fn + m["fp"] * costo_fp


def barrer_umbrales(y, puntajes, n: int = 200) -> pd.DataFrame:
    filas = []
    for u in np.linspace(0.0, 1.0, n):
        m = metricas_en_umbral(y, puntajes, u)
        filas.append({
            "umbral": u,
            "costo": m["fn"] * COSTO_FN + m["fp"] * COSTO_FP,
            "precision": m["precision"],
            "exhaustividad": m["exhaustividad"],
            "f1": m["f1"],
        })
    return pd.DataFrame(filas)


def elegir_umbral(y_val, puntajes_val, n: int = 200) -> float:
    """Sale de validacion, se congela, y se aplica una sola vez a prueba."""
    tabla = barrer_umbrales(y_val, puntajes_val, n=n)
    return float(tabla.loc[tabla["costo"].idxmin(), "umbral"])


def escalar_a_cartera_mensual(costo_bloque, n_dias_bloque, n_tarjetas_simuladas,
                              n_tarjetas_cartera=CARTERA_TARJETAS) -> float:
    """Lleva el costo del bloque simulado a la cartera de 1.4 millones, por mes."""
    return (costo_bloque
            * (30.0 / n_dias_bloque)
            * (n_tarjetas_cartera / n_tarjetas_simuladas))
