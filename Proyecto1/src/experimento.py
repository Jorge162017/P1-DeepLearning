"""Orquestacion completa: A, B, C, falsificaciones y economia."""
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import torch

from src.config import CANALES, CIUDADES, RUBROS, ConfigGenerador
from src.evaluacion import (auc_pr, costo_esperado, desglose_por_mecanismo,
                            elegir_umbral, escalar_a_cartera_mensual,
                            metricas_en_umbral, permutar)
from src.generador import generar
from src.modelos import (ModeloSecuencial, datos_a_tensores, entrenar_a,
                         entrenar_secuencial, puntajes_a, puntajes_secuencial,
                         verificar_senuelo)
from src.ventanas import (COLUMNAS_AGREGADAS, ajustar_escaladores,
                          ajustar_escaladores_agregados, aplicar_escaladores,
                          aplicar_escaladores_agregados, construir_dataset)

MARGEN_EXITO_C = 0.02      # lo fijamos antes de mirar la prueba


@dataclass
class Resultados:
    auc_pr: dict = field(default_factory=dict)
    umbrales: dict = field(default_factory=dict)
    metricas_prueba: dict = field(default_factory=dict)
    permutacion: dict = field(default_factory=dict)
    desglose: dict = field(default_factory=dict)
    desglose_validacion: dict = field(default_factory=dict)
    economia: dict = field(default_factory=dict)
    historial: dict = field(default_factory=dict)
    veredicto_c: dict = field(default_factory=dict)
    puntajes_validacion: dict = field(default_factory=dict)
    puntajes_prueba: dict = field(default_factory=dict)
    go_no_go: float = float("nan")
    go_no_go_cobro: float = float("nan")
    particiones: dict = field(default_factory=dict)
    casos_inferencia: list = field(default_factory=list)


def ejecutar_experimento(config: ConfigGenerador, epocas: int = 12,
                         semilla: int = 42, leer_prueba: bool = False,
                         verbose: bool = False) -> Resultados:
    def log(*a):
        if verbose:
            print(*a, flush=True)

    r = Resultados()
    log("Generando transacciones...")
    df = generar(config)
    log(f"Construyendo ventanas de {len(df):,} transacciones...")
    d = construir_dataset(df, config)
    r.particiones = d.meta.groupby("particion").agg(
        transacciones=("id_tx", "size"), fraudes=("es_fraude", "sum"),
        tasa_fraude=("es_fraude", "mean"),
        dia_min=("marca_tiempo", "min"), dia_max=("marca_tiempo", "max"),
    ).to_dict(orient="index")
    r.go_no_go_cobro = verificar_senuelo(d, semilla=semilla, solo_cobro=True)
    log(f"senuelo en cobro ROC-AUC = {r.go_no_go_cobro:.4f}")
    r.go_no_go = verificar_senuelo(d, semilla=semilla)
    log(f"go/no-go senuelo ROC-AUC = {r.go_no_go:.4f}")

    ent = (d.meta["particion"] == "entrenamiento").to_numpy()
    val = (d.meta["particion"] == "validacion").to_numpy()
    pru = (d.meta["particion"] == "prueba").to_numpy()

    # escaladores ajustados solo con entrenamiento
    esc_seq = ajustar_escaladores(d.seq_num, d.mascara, ent)
    esc_agr = ajustar_escaladores_agregados(d.agregados, ent)
    seq_z = aplicar_escaladores(d.seq_num, d.mascara, esc_seq)
    agr_z = aplicar_escaladores_agregados(d.agregados, esc_agr)

    y = d.meta["es_fraude"].to_numpy()
    peso = float((y[ent] == 0).sum() / max(1, (y[ent] == 1).sum()))

    # --- A ---
    log("Entrenando A (boosting)...")
    modelo_a = entrenar_a(agr_z[ent].to_numpy(), y[ent],
                          agr_z[val].to_numpy(), y[val], semilla=semilla)
    p_a_val = puntajes_a(modelo_a, agr_z[val].to_numpy())
    log(f"A entrenado | AUC-PR val = {auc_pr(y[val], p_a_val):.4f}")

    # --- B y C ---
    t_ent = datos_a_tensores(d, seq_z, agr_z, ent)
    t_val = datos_a_tensores(d, seq_z, agr_z, val)
    n_cat = (len(RUBROS) + 1, len(CANALES) + 1, len(CIUDADES) + 1)

    # sembrar antes de construir, no despues: armar el modelo ya consume el RNG
    # global de torch, y sin esto la misma semilla daba numeros distintos
    torch.manual_seed(semilla)
    modelo_b = ModeloSecuencial(*n_cat, n_agregados=0)
    log("Entrenando B (GRU, CPU)...")
    r.historial["B"] = entrenar_secuencial(modelo_b, t_ent, t_val, peso,
                                           epocas=epocas, semilla=semilla, verbose=verbose)
    p_b_val = puntajes_secuencial(modelo_b, t_val)
    log(f"B entrenado | AUC-PR val = {auc_pr(y[val], p_b_val):.4f}")

    torch.manual_seed(semilla)
    modelo_c = ModeloSecuencial(*n_cat, n_agregados=len(COLUMNAS_AGREGADAS))
    log("Entrenando C (hibrido, CPU)...")
    r.historial["C"] = entrenar_secuencial(modelo_c, t_ent, t_val, peso,
                                           epocas=epocas, semilla=semilla, verbose=verbose)
    p_c_val = puntajes_secuencial(modelo_c, t_val)
    log(f"C entrenado | AUC-PR val = {auc_pr(y[val], p_c_val):.4f}")

    r.puntajes_validacion = {"y": y[val], "A": p_a_val, "B": p_b_val, "C": p_c_val}
    for nombre, p in [("A", p_a_val), ("B", p_b_val), ("C", p_c_val)]:
        r.auc_pr[nombre] = {"validacion": auc_pr(y[val], p)}
        r.umbrales[nombre] = elegir_umbral(y[val], p)
        r.desglose_validacion[nombre] = desglose_por_mecanismo(
            d.meta[val], p, r.umbrales[nombre])

    # permutacion controlada, sobre validacion
    rng = np.random.default_rng(semilla)
    for variante in ["P1", "P2"]:
        cat_p, num_p = permutar(d.seq_cat[val], seq_z[val], d.mascara[val],
                                rng, variante=variante)
        lote = {"cat": torch.from_numpy(cat_p).long(),
                "num": torch.from_numpy(num_p).float(),
                "mascara": torch.from_numpy(d.mascara[val]),
                "agregados": t_val["agregados"],
                "y": t_val["y"]}
        # A ni siquiera lee la secuencia, asi que permutar no puede moverlo
        r.permutacion.setdefault("A", {})[variante] = r.auc_pr["A"]["validacion"]
        r.permutacion.setdefault("B", {})[variante] = auc_pr(
            y[val], puntajes_secuencial(modelo_b, lote))
        r.permutacion.setdefault("C", {})[variante] = auc_pr(
            y[val], puntajes_secuencial(modelo_c, lote))
        log(f"permutacion {variante} | B = {r.permutacion['B'][variante]:.4f}"
            f" | C = {r.permutacion['C'][variante]:.4f}")

    # veredicto de C, con validacion y antes de tocar prueba
    mejor_ab = max(r.auc_pr["A"]["validacion"], r.auc_pr["B"]["validacion"])
    margen = r.auc_pr["C"]["validacion"] - mejor_ab
    dg_c = r.desglose_validacion["C"]["exhaustividad"]
    dg_b = r.desglose_validacion["B"]["exhaustividad"]
    comunes = dg_c.index.intersection(dg_b.index)
    sostenido = bool((dg_c[comunes] >= dg_b[comunes] - 0.02).sum() >= 2)
    r.veredicto_c = {
        "margen": float(margen),
        "supera_umbral": bool(margen >= MARGEN_EXITO_C),
        "sostenido_por_mecanismo": sostenido,
        "util": bool(margen >= MARGEN_EXITO_C and sostenido),
    }

    r._modelos = {"A": modelo_a, "B": modelo_b, "C": modelo_c}
    r._escaladores = {"secuencia": esc_seq, "agregados": esc_agr}

    # Casos pequenos para verificar luego carga en CPU contra la salida original.
    # Se seleccionan por mecanismo en validacion, nunca por puntaje ni por prueba.
    elegidos = [0]
    for mecanismo in ["legitimo", "F1", "F2", "F3", "senuelo_f1"]:
        indices = np.flatnonzero(val & (d.meta["mecanismo"].to_numpy() == mecanismo))
        if len(indices):
            elegidos.append(int(indices[0]))
    for i in elegidos:
        tarjeta = df.iloc[i]["id_tarjeta"]
        eventos = df.iloc[:i + 1]
        eventos = eventos[eventos["id_tarjeta"] == tarjeta].tail(20)
        entrada = eventos[["marca_tiempo", "monto", "rubro", "canal", "ciudad"]]
        lote_caso = {
            "cat": torch.from_numpy(d.seq_cat[i:i+1].copy()).long(),
            "num": torch.from_numpy(seq_z[i:i+1].copy()).float(),
            "mascara": torch.from_numpy(d.mascara[i:i+1].copy()),
            "y": torch.zeros(1),
        }
        r.casos_inferencia.append({
            "id_tx": int(d.meta.iloc[i]["id_tx"]),
            "particion": str(d.meta.iloc[i]["particion"]),
            "mecanismo": str(d.meta.iloc[i]["mecanismo"]),
            "transacciones": entrada.to_dict(orient="records"),
            "puntaje_b_esperado": float(puntajes_secuencial(modelo_b, lote_caso)[0]),
        })

    if not leer_prueba:
        return r

    # de aqui en adelante se lee prueba, una sola vez
    t_pru = datos_a_tensores(d, seq_z, agr_z, pru)
    p_pru = {
        "A": puntajes_a(modelo_a, agr_z[pru].to_numpy()),
        "B": puntajes_secuencial(modelo_b, t_pru),
        "C": puntajes_secuencial(modelo_c, t_pru),
    }
    r.puntajes_prueba = {"y": y[pru], **p_pru}
    n_dias_prueba = config.dia_fin_prueba - config.dia_inicio_prueba + 1

    for nombre, p in p_pru.items():
        u = r.umbrales[nombre]                      # el que ya salio de validacion
        r.auc_pr[nombre]["prueba"] = auc_pr(y[pru], p)
        r.metricas_prueba[nombre] = metricas_en_umbral(y[pru], p, u)
        r.desglose[nombre] = desglose_por_mecanismo(d.meta[pru], p, u)
        costo = costo_esperado(y[pru], p, u)
        r.economia[nombre] = {
            "costo_bloque": costo,
            "costo_mensual": escalar_a_cartera_mensual(
                costo, n_dias_prueba, config.n_tarjetas),
        }
    for nombre in ["B", "C"]:
        r.economia[nombre]["ahorro_mensual_vs_A"] = (
            r.economia["A"]["costo_mensual"] - r.economia[nombre]["costo_mensual"])

    return r


def guardar_artefactos(resultados, config, ruta="artefactos"):
    """Guarda pesos y parametros de preparacion para poder rehacer los puntajes."""
    import pickle

    p = Path(ruta)
    p.mkdir(exist_ok=True)
    (p / "config_generador.json").write_text(json.dumps(asdict(config), indent=2))
    with open(p / "modelo_a_boosting.pkl", "wb") as f:
        pickle.dump(resultados._modelos["A"], f)
    torch.save(resultados._modelos["B"].state_dict(), p / "modelo_b_gru.pt")
    torch.save(resultados._modelos["C"].state_dict(), p / "modelo_c_hibrido.pt")
    esc = {k: {kk: np.asarray(vv).tolist() for kk, vv in v.items()}
           for k, v in resultados._escaladores.items()}
    (p / "escaladores.json").write_text(json.dumps(esc, indent=2))
    (p / "vocabularios.json").write_text(json.dumps(
        {"rubros": RUBROS, "canales": CANALES, "ciudades": CIUDADES,
         "nota": "codigo = indice + 1; 0 reservado a relleno y categorias no vistas"},
        indent=2, ensure_ascii=False))
    return p
