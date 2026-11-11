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
class Caracteristicas:
    agregados: pd.DataFrame
    seq_cat: np.ndarray
    seq_num: np.ndarray
    mascara: np.ndarray


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


def construir_caracteristicas(df: pd.DataFrame) -> Caracteristicas:
    """Preparacion compartida por entrenamiento e inferencia, sin etiquetas.

    Cada ancla usa como ciudad base la moda de sus 19 transacciones previas.
    Los empates se resuelven alfabeticamente; sin historia usa la ciudad actual.
    Toda la ventana se expresa respecto a esa base. No requiere historia adicional.
    """
    requeridas = {"id_tarjeta", "marca_tiempo", "monto", "rubro", "canal", "ciudad"}
    faltantes = requeridas - set(df.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas: {sorted(faltantes)}")
    if df.empty or df[list(requeridas)].isna().any().any():
        raise ValueError("Se requieren transacciones completas y no vacias")
    for columna in ["marca_tiempo", "monto"]:
        if not pd.api.types.is_numeric_dtype(df[columna]) or not np.isfinite(df[columna]).all():
            raise ValueError(f"{columna} debe contener numeros finitos")
    if (df["monto"] <= 0).any():
        raise ValueError("monto debe ser mayor que cero")
    for columna in ["rubro", "canal", "ciudad"]:
        if not df[columna].map(lambda v: isinstance(v, str) and bool(v.strip())).all():
            raise ValueError(f"{columna} debe contener textos no vacios")
    df = df.sort_values(["id_tarjeta", "marca_tiempo"], kind="stable").reset_index(drop=True)
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

        # precalculados para no repetir la busqueda en cada ventana
        c_rubro = np.array([cod_rubro.get(r, 0) for r in rubros], dtype=np.int64)
        c_canal = np.array([cod_canal.get(c, 0) for c in canales], dtype=np.int64)
        c_ciudad = np.array([cod_ciudad.get(c, 0) for c in ciudades], dtype=np.int64)
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
            ciudad_base = (pd.Series(ciudades[hist]).mode().iloc[0]
                           if j > desde else ciudades[j])

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
            seq_num[fila, pos, 6] = [_lejania(c, ciudad_base) for c in ciudades[vent]]
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

    return Caracteristicas(
        agregados=pd.DataFrame(agregados, columns=COLUMNAS_AGREGADAS),
        seq_cat=seq_cat, seq_num=seq_num, mascara=mascara,
    )


def construir_dataset(df: pd.DataFrame, config: ConfigGenerador) -> Dataset:
    """Agrega etiquetas y particion experimental a las caracteristicas compartidas."""
    df = df.sort_values(["id_tarjeta", "marca_tiempo"], kind="stable").reset_index(drop=True)
    rasgos = construir_caracteristicas(df)
    meta = df[["id_tx", "id_tarjeta", "marca_tiempo", "es_fraude",
               "mecanismo", "id_episodio"]].copy()
    meta["particion"] = asignar_particion(meta["marca_tiempo"].to_numpy(), config)
    return Dataset(meta=meta, agregados=rasgos.agregados, seq_cat=rasgos.seq_cat,
                   seq_num=rasgos.seq_num, mascara=rasgos.mascara)


def preparar_inferencia(transacciones, escaladores) -> dict:
    """Prepara una tarjeta; devuelve solo su ultima ventana, sin etiquetas.

    Entrada: de 1 a 20 eventos con marca_tiempo (dias desde el origen fijo),
    monto, rubro, canal y ciudad. El orden recibido debe ser cronologico.
    escaladores es la seccion 'secuencia' del JSON guardado en entrenamiento.
    La salida son arrays numpy con dimension de lote 1.
    """
    df = pd.DataFrame(transacciones).copy()
    if not 1 <= len(df) <= K:
        raise ValueError(f"Se requieren entre 1 y {K} transacciones")
    if "id_tarjeta" in df and df["id_tarjeta"].nunique(dropna=False) != 1:
        raise ValueError("La ventana debe pertenecer a una sola tarjeta")
    df["id_tarjeta"] = 0
    rasgos = construir_caracteristicas(df)
    if not df["marca_tiempo"].is_monotonic_increasing:
        raise ValueError("Las transacciones deben estar en orden cronologico")
    medias = np.asarray(escaladores["medias"], dtype=float)
    desv = np.asarray(escaladores["desviaciones"], dtype=float)
    if (medias.shape != (7,) or desv.shape != (7,) or
            not np.isfinite(medias).all() or not np.isfinite(desv).all() or
            (desv <= 0).any()):
        raise ValueError("Escaladores de secuencia invalidos")
    return {
        "cat": rasgos.seq_cat[-1:].copy(),
        "num": aplicar_escaladores(rasgos.seq_num[-1:], rasgos.mascara[-1:],
                                  {"medias": medias, "desviaciones": desv}),
        "mascara": rasgos.mascara[-1:].copy(),
    }


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
