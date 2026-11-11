"""Generador sintetico de transacciones. Reproducible por semilla."""
import numpy as np
import pandas as pd

from src.config import ConfigGenerador, RUBROS, CANALES, CIUDADES


def generar_perfiles(config: ConfigGenerador, rng: np.random.Generator) -> pd.DataFrame:
    """Un perfil de comportamiento por tarjeta, estable toda la simulacion."""
    n = config.n_tarjetas
    return pd.DataFrame({
        "id_tarjeta": np.arange(n),
        # monto tipico: mu en escala log, muy variable entre tarjetas
        "monto_mu": rng.normal(3.9, 0.7, n),
        "monto_sigma": rng.uniform(0.35, 0.85, n),
        # ~0.45 al dia, o sea unas 80 por tarjeta en 180 dias. Con tasas mas
        # altas las ventanas ya no caben en memoria.
        "tx_por_dia": rng.gamma(shape=2.0, scale=0.16, size=n) + 0.12,
        "ciudad_base": rng.choice(CIUDADES[:6], n),  # base siempre nacional
        "mezcla_rubros": list(rng.dirichlet(np.ones(len(RUBROS)) * 0.6, n)),
        "mezcla_canales": list(rng.dirichlet(np.array([3.0, 2.0, 1.5, 0.8]), n)),
        "hora_pico": rng.uniform(9.0, 20.0, n),
    })


def generar_trafico_legitimo(
    perfiles: pd.DataFrame, config: ConfigGenerador, rng: np.random.Generator
) -> pd.DataFrame:
    """Transacciones normales: ritmo, monto y rubro segun el perfil de cada tarjeta."""
    filas = []
    for p in perfiles.itertuples(index=False):
        n_tx = max(20, int(rng.poisson(p.tx_por_dia * config.n_dias)))
        # tiempos: dia uniforme mas hora circadiana alrededor de la hora pico
        t = np.sort(rng.uniform(0, config.n_dias, n_tx))
        hora = (p.hora_pico + rng.normal(0, 3.0, n_tx)) % 24
        t = np.floor(t) + hora / 24.0
        t = np.sort(np.clip(t, 0, config.n_dias - 1e-6))

        montos = rng.lognormal(p.monto_mu, p.monto_sigma, n_tx)
        rubros = rng.choice(RUBROS, n_tx, p=p.mezcla_rubros)
        canales = rng.choice(CANALES, n_tx, p=p.mezcla_canales)
        # 96% en la ciudad base; el resto viaje legitimo
        en_base = rng.random(n_tx) < 0.96
        ciudades = np.where(en_base, p.ciudad_base, rng.choice(CIUDADES, n_tx))

        filas.append(pd.DataFrame({
            "id_tarjeta": p.id_tarjeta,
            "marca_tiempo": t,
            "monto": np.round(montos, 2),
            "rubro": rubros,
            "canal": canales,
            "ciudad": ciudades,
        }))

    df = pd.concat(filas, ignore_index=True)
    df = df.sort_values(["id_tarjeta", "marca_tiempo"]).reset_index(drop=True)
    df["es_fraude"] = 0
    df["mecanismo"] = "legitimo"
    df.insert(0, "id_tx", np.arange(len(df)))
    return df


SEGUNDO = 1.0 / 86400.0  # un segundo, en unidades de dia


def _plantilla_episodio(rng: np.random.Generator):
    """Micro-compras, compra grande, huecos y rubros de un episodio.

    Los micro-montos salen sin ordenar; quien llama decide como acomodarlos.
    """
    n_micro = int(rng.integers(3, 7))
    micros = np.round(rng.uniform(5, 40, n_micro), 2)
    grande = round(float(rng.uniform(2000, 8000)), 2)
    huecos = np.append(
        rng.uniform(20, 180, n_micro) * SEGUNDO,   # segundos entre micro-compras
        rng.uniform(60, 600) * SEGUNDO,            # pausa antes del cobro
    )
    rubros = rng.choice(RUBROS, n_micro + 1, replace=True)
    return micros, grande, huecos, rubros


def _barajar_no_ordenado(micros, rng):
    """Baraja evitando que quede ascendente, para que el senuelo no imite la rampa."""
    for _ in range(10):
        p = rng.permutation(micros)
        if not np.all(np.diff(p) >= 0):
            return p
    return micros[::-1] if len(micros) > 1 else micros


def _inyectar_episodio_escalado(perfiles, config, rng, n_episodios, escalado):
    """Micro-compras que terminan en una compra grande.

    escalado=True son los montos de menor a mayor, que es F1. escalado=False los
    baraja y la etiqueta queda legitima. Los dos terminan en la compra grande a
    proposito: si el senuelo empezara con ella, entraria en la historia de las
    anclas siguientes y los agregados los separarian sin mirar el orden.
    """
    mecanismo = "F1" if escalado else "senuelo_f1"
    ciudad_por_tarjeta = dict(zip(perfiles["id_tarjeta"], perfiles["ciudad_base"]))
    tarjetas = rng.choice(perfiles["id_tarjeta"].to_numpy(), n_episodios, replace=True)
    nuevas = []
    for episodio, id_tarjeta in enumerate(tarjetas):
        micros, grande, huecos, rubros = _plantilla_episodio(rng)
        micros = np.sort(micros) if escalado else _barajar_no_ordenado(micros, rng)
        montos = np.append(micros, grande)
        inicio = rng.uniform(1.0, config.n_dias - 1.0)
        tiempos = inicio + np.cumsum(huecos)
        nuevas.append(pd.DataFrame({
            "id_tarjeta": id_tarjeta,
            "marca_tiempo": tiempos,
            "monto": montos,
            "rubro": rubros,
            "canal": "ecommerce",
            "ciudad": ciudad_por_tarjeta[id_tarjeta],
            "es_fraude": 1 if escalado else 0,
            "mecanismo": mecanismo,
            "id_episodio": episodio,
        }))
    return pd.concat(nuevas, ignore_index=True)


def _inyectar_f2(legitimo, config, rng, n_episodios):
    """Viaje imposible: una transaccion en ciudad lejana minutos despues de la anterior."""
    base = legitimo.sample(n=n_episodios, random_state=int(rng.integers(1e9)))
    nuevas = []
    for episodio, fila in enumerate(base.itertuples()):
        lejana = rng.choice([c for c in CIUDADES if c != fila.ciudad])
        nuevas.append({
            "id_tarjeta": fila.id_tarjeta,
            "marca_tiempo": fila.marca_tiempo + rng.uniform(120, 900) * SEGUNDO,
            "monto": round(float(rng.lognormal(4.4, 0.6)), 2),
            "rubro": rng.choice(RUBROS),
            "canal": rng.choice(["chip", "atm"]),
            "ciudad": lejana,
            "es_fraude": 1,
            "mecanismo": "F2",
            "id_episodio": episodio,
        })
    return pd.DataFrame(nuevas)


def _inyectar_f3(legitimo, perfiles, config, rng, n_episodios):
    """Toma de cuenta: rafaga de ecommerce caro, de madrugada, en rubros que la
    tarjeta nunca uso."""
    rubros_por_tarjeta = legitimo.groupby("id_tarjeta")["rubro"].agg(set).to_dict()
    tarjetas = rng.choice(perfiles["id_tarjeta"].to_numpy(), n_episodios, replace=True)
    nuevas = []
    for episodio, id_tarjeta in enumerate(tarjetas):
        n = int(rng.integers(3, 8))
        inicio = np.floor(rng.uniform(1.0, config.n_dias - 1.0)) + rng.uniform(1.0, 5.0) / 24.0
        usados = rubros_por_tarjeta.get(id_tarjeta, set())
        disponibles = [r for r in RUBROS if r not in usados] or RUBROS
        nuevas.append(pd.DataFrame({
            "id_tarjeta": id_tarjeta,
            "marca_tiempo": inicio + np.cumsum(rng.uniform(90, 900, n) * SEGUNDO),
            "monto": np.round(rng.uniform(900, 5000, n), 2),
            "rubro": rng.choice(disponibles, n),
            "canal": "ecommerce",
            "ciudad": rng.choice(CIUDADES[6:]),  # extranjero
            "es_fraude": 1,
            "mecanismo": "F3",
            "id_episodio": episodio,
        }))
    return pd.concat(nuevas, ignore_index=True)


def _inyectar_f4(perfiles, config, rng, n_episodios):
    """Goteo lento: cargos chicos del mismo comercio cada pocos dias. Solo en prueba."""
    ciudad_por_tarjeta = dict(zip(perfiles["id_tarjeta"], perfiles["ciudad_base"]))
    tarjetas = rng.choice(perfiles["id_tarjeta"].to_numpy(), n_episodios, replace=True)
    nuevas = []
    for episodio, id_tarjeta in enumerate(tarjetas):
        n = int(rng.integers(4, 9))
        inicio = rng.uniform(config.dia_inicio_prueba, config.dia_fin_prueba - 12)
        tiempos = inicio + np.cumsum(rng.uniform(2.0, 4.0, n))
        tiempos = tiempos[tiempos <= config.dia_fin_prueba]
        if len(tiempos) < 3:
            continue
        nuevas.append(pd.DataFrame({
            "id_tarjeta": id_tarjeta,
            "marca_tiempo": tiempos,
            "monto": np.round(rng.uniform(80, 200, len(tiempos)), 2),
            "rubro": rng.choice(RUBROS),
            "canal": "ecommerce",
            "ciudad": ciudad_por_tarjeta[id_tarjeta],
            "es_fraude": 1,
            "mecanismo": "F4",
            "id_episodio": episodio,
        }))
    return pd.concat(nuevas, ignore_index=True)


def generar(config: ConfigGenerador) -> pd.DataFrame:
    """Punto de entrada unico. Misma semilla, mismos datos."""
    rng = np.random.default_rng(config.semilla)
    perfiles = generar_perfiles(config, rng)
    legitimo = generar_trafico_legitimo(perfiles, config, rng)
    legitimo["id_episodio"] = -1

    n_fraude = int(len(legitimo) * config.tasa_fraude_objetivo)
    n_f1 = max(1, int(n_fraude * config.prop_mecanismos["F1"] / 5))   # ~5 tx por episodio
    n_f2 = max(1, int(n_fraude * config.prop_mecanismos["F2"]))       # 1 tx por episodio
    n_f3 = max(1, int(n_fraude * config.prop_mecanismos["F3"] / 5))   # ~5 tx por episodio
    n_senuelo = max(1, int(legitimo["id_tarjeta"].nunique() * config.prop_senuelo_f1))

    piezas = [
        legitimo,
        _inyectar_episodio_escalado(perfiles, config, rng, n_f1, escalado=True),
        _inyectar_episodio_escalado(perfiles, config, rng, n_senuelo, escalado=False),
        _inyectar_f2(legitimo, config, rng, n_f2),
        _inyectar_f3(legitimo, perfiles, config, rng, n_f3),
    ]

    # F4 se dimensiona contra el fraude que ya cayo en prueba, para poder medirlo
    # aparte sin que se coma el bloque.
    inyectado = pd.concat(piezas[1:], ignore_index=True)
    n_fraude_prueba = int(((inyectado["es_fraude"] == 1)
                           & (inyectado["marca_tiempo"] >= config.dia_inicio_prueba)).sum())
    prop = config.prop_f4_en_prueba
    tx_por_episodio = 5.5  # media de rng.integers(4, 9)
    n_f4 = max(1, round(n_fraude_prueba * prop / (1 - prop) / tx_por_episodio))
    piezas.append(_inyectar_f4(perfiles, config, rng, n_f4))

    df = pd.concat(piezas, ignore_index=True)
    df = df.sort_values(["id_tarjeta", "marca_tiempo"]).reset_index(drop=True)
    df["id_tx"] = np.arange(len(df))
    return df[["id_tx", "id_tarjeta", "marca_tiempo", "monto", "rubro", "canal",
               "ciudad", "es_fraude", "mecanismo", "id_episodio"]]
