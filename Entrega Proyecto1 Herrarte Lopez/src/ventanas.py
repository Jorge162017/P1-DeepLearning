"""Ventanas de K transacciones, agregados causales y particion temporal."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.config import CANALES, CIUDADES, K, RUBROS, ConfigGenerador

COLUMNAS_AGREGADAS = [
    # rasgos del ancla
    "monto_log", "hora", "dia_semana", "es_ciudad_base", "es_extranjero",
    "monto_rel_mediana",
    # agregados causales sobre las 19 previas
    "n_ultima_hora", "n_ultimas_24h", "monto_medio_ventana", "monto_max_ventana",
    "monto_std_ventana", "rubros_distintos", "ciudades_distintas",
    "canales_distintos", "hueco_medio",
]

_CIUDADES_EXTRANJERAS = set(CIUDADES[6:])


@dataclass
class Dataset:
    meta: pd.DataFrame
    agregados: pd.DataFrame
    seq_cat: np.ndarray   # (n, K, 3) int64: rubro, canal, ciudad
    seq_num: np.ndarray   # (n, K, 7) float32
    mascara: np.ndarray   # (n, K) bool


def asignar_particion(marca_tiempo: np.ndarray, config: ConfigGenerador) -> np.ndarray:
    t = np.asarray(marca_tiempo, dtype=float)
    p = np.full(len(t), "embargo", dtype=object)
    p[t < config.dia_fin_entrenamiento + 1] = "entrenamiento"
    p[(t >= config.dia_inicio_validacion) & (t < config.dia_fin_validacion + 1)] = "validacion"
    p[t >= config.dia_inicio_prueba] = "prueba"
    return p.astype(str)


def _lejania(ciudad: str, ciudad_base: str) -> float:
    if ciudad == ciudad_base:
        return 0.0
    return 2.0 if ciudad in _CIUDADES_EXTRANJERAS else 1.0


def construir_dataset(df: pd.DataFrame, config: ConfigGenerador) -> Dataset:
    """Una fila por transaccion. La ventana mira hacia atras y no pasa de K."""
    df = df.sort_values(["id_tarjeta", "marca_tiempo"]).reset_index(drop=True)
    n = len(df)

    cod_rubro = {v: i + 1 for i, v in enumerate(RUBROS)}     # 0 reservado a relleno/OOV
    cod_canal = {v: i + 1 for i, v in enumerate(CANALES)}
    cod_ciudad = {v: i + 1 for i, v in enumerate(CIUDADES)}

    seq_cat = np.zeros((n, K, 3), dtype=np.int64)
    seq_num = np.zeros((n, K, 7), dtype=np.float32)
    mascara = np.zeros((n, K), dtype=bool)
    agregados = np.zeros((n, len(COLUMNAS_AGREGADAS)), dtype=np.float64)

    for _, bloque in df.groupby("id_tarjeta", sort=False):
        idx = bloque.index.to_numpy()
        montos = bloque["monto"].to_numpy(dtype=float)
        tiempos = bloque["marca_tiempo"].to_numpy(dtype=float)
        rubros = bloque["rubro"].to_numpy()
        canales = bloque["canal"].to_numpy()
        ciudades = bloque["ciudad"].to_numpy()
        # ciudad base = la mas frecuente en la historia de la tarjeta
        ciudad_base = pd.Series(ciudades).mode().iloc[0]

        # precalculados para no repetir la busqueda en cada ventana
        c_rubro = np.array([cod_rubro[r] for r in rubros], dtype=np.int64)
        c_canal = np.array([cod_canal[c] for c in canales], dtype=np.int64)
        c_ciudad = np.array([cod_ciudad[c] for c in ciudades], dtype=np.int64)
        lejania = np.array([_lejania(c, ciudad_base) for c in ciudades], dtype=np.float64)
        log_monto = np.log1p(montos)
        hora = (tiempos % 1.0) * 24.0
        dia = np.floor(tiempos) % 7
        sin_h, cos_h = np.sin(2 * np.pi * hora / 24.0), np.cos(2 * np.pi * hora / 24.0)
        sin_d, cos_d = np.sin(2 * np.pi * dia / 7.0), np.cos(2 * np.pi * dia / 7.0)
        es_extranjera = np.array([c in _CIUDADES_EXTRANJERAS for c in ciudades], dtype=float)

        for j in range(len(bloque)):
            desde = max(0, j - (K - 1))
            hist = slice(desde, j)             # solo las previas, sin el ancla
            vent = slice(desde, j + 1)         # previas + ancla, para la secuencia
            fila = idx[j]

            # --- secuencia (alineada a la derecha; el ancla queda en K-1) ---
            largo = j + 1 - desde
            pos = slice(K - largo, K)
            seq_cat[fila, pos, 0] = c_rubro[vent]
            seq_cat[fila, pos, 1] = c_canal[vent]
            seq_cat[fila, pos, 2] = c_ciudad[vent]

            t_vent = tiempos[vent]
            huecos = np.diff(t_vent, prepend=t_vent[0])
            seq_num[fila, pos, 0] = log_monto[vent]
            seq_num[fila, pos, 1] = np.log1p(huecos * 86400.0)
            seq_num[fila, pos, 2] = sin_h[vent]
            seq_num[fila, pos, 3] = cos_h[vent]
            seq_num[fila, pos, 4] = sin_d[vent]
            seq_num[fila, pos, 5] = cos_d[vent]
            seq_num[fila, pos, 6] = lejania[vent]
            mascara[fila, pos] = True

            # agregados sobre las mismas 19 previas, ni una mas
            m_hist = montos[hist]
            t_hist = tiempos[hist]
            hay = len(m_hist) > 0
            mediana = float(np.median(m_hist)) if hay else 0.0
            agregados[fila] = [
                log_monto[j],
                hora[j],
                dia[j],
                float(ciudades[j] == ciudad_base),
                es_extranjera[j],
                float(montos[j] / mediana) if mediana > 0 else 0.0,
                float(np.sum(t_hist > tiempos[j] - 1.0 / 24.0)) if hay else 0.0,
                float(np.sum(t_hist > tiempos[j] - 1.0)) if hay else 0.0,
                float(np.mean(m_hist)) if hay else 0.0,
                float(np.max(m_hist)) if hay else 0.0,
                float(np.std(m_hist)) if hay else 0.0,
                float(len(set(rubros[hist]))),
                float(len(set(ciudades[hist]))),
                float(len(set(canales[hist]))),
                float(np.mean(np.diff(t_hist))) if len(t_hist) > 1 else 0.0,
            ]

    meta = df[["id_tx", "id_tarjeta", "marca_tiempo", "es_fraude",
               "mecanismo", "id_episodio"]].copy()
    meta["particion"] = asignar_particion(meta["marca_tiempo"].to_numpy(), config)
    return Dataset(
        meta=meta.reset_index(drop=True),
        agregados=pd.DataFrame(agregados, columns=COLUMNAS_AGREGADAS),
        seq_cat=seq_cat, seq_num=seq_num, mascara=mascara,
    )


def ajustar_escaladores(seq_num, mascara, indices_entrenamiento) -> dict:
    """Media y desviacion por rasgo, solo con posiciones observadas de entrenamiento."""
    sel = mascara & np.asarray(indices_entrenamiento, dtype=bool)[:, None]
    obs = seq_num[sel]                      # (n_observadas, 7)
    return {"medias": obs.mean(axis=0), "desviaciones": obs.std(axis=0) + 1e-8}


def aplicar_escaladores(seq_num, mascara, escaladores) -> np.ndarray:
    z = (seq_num - escaladores["medias"]) / escaladores["desviaciones"]
    z = np.where(mascara[..., None], z, 0.0)   # el relleno queda en cero
    return z.astype(np.float32)


def ajustar_escaladores_agregados(agregados, indices_entrenamiento) -> dict:
    sub = agregados.loc[np.asarray(indices_entrenamiento, dtype=bool)]
    return {"medias": sub.mean().to_numpy(),
            "desviaciones": sub.std().to_numpy() + 1e-8}


def aplicar_escaladores_agregados(agregados, escaladores) -> pd.DataFrame:
    z = (agregados.to_numpy() - escaladores["medias"]) / escaladores["desviaciones"]
    return pd.DataFrame(z, columns=agregados.columns, index=agregados.index)
