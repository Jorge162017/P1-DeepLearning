"""Figuras del informe. Cada funcion guarda un PNG y devuelve la ruta."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import precision_recall_curve

from src.config import COSTO_FN, COSTO_FP
from src.evaluacion import barrer_umbrales

RUTA = Path("figuras")
COLOR = {"A": "#8c8c8c", "B": "#1f6feb", "C": "#d1791f"}


def _guardar(fig, nombre):
    RUTA.mkdir(exist_ok=True)
    destino = RUTA / nombre
    fig.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return destino


def fig_particion(config):
    """Linea de tiempo con los tres bloques y los dos embargos."""
    fig, ax = plt.subplots(figsize=(9, 1.8))
    bloques = [
        (0, config.dia_fin_entrenamiento + 1, "Entrenamiento", "#2f6f4f"),
        (config.dia_fin_entrenamiento + 1, config.dia_inicio_validacion, "", "#cccccc"),
        (config.dia_inicio_validacion, config.dia_fin_validacion + 1, "Validación", "#1f6feb"),
        (config.dia_fin_validacion + 1, config.dia_inicio_prueba, "", "#cccccc"),
        (config.dia_inicio_prueba, config.dia_fin_prueba + 1, "Prueba", "#b03030"),
    ]
    for inicio, fin, etiqueta, color in bloques:
        ax.barh(0, fin - inicio, left=inicio, height=0.5, color=color,
                edgecolor="white", linewidth=1.5)
        if etiqueta:
            ax.text((inicio + fin) / 2, 0, f"{etiqueta}\ndías {inicio} a {fin - 1}",
                    ha="center", va="center", color="white", fontsize=9, weight="bold")
    ax.text(120.5, -0.42, "embargo", ha="center", fontsize=7, color="#666")
    ax.text(150.5, -0.42, "embargo", ha="center", fontsize=7, color="#666")
    ax.set_xlim(0, config.n_dias)
    ax.set_ylim(-0.6, 0.4)
    ax.set_yticks([])
    ax.set_xlabel("día de la simulación")
    ax.set_title("Partición temporal", loc="left")
    for lado in ["top", "right", "left"]:
        ax.spines[lado].set_visible(False)
    return _guardar(fig, "fig1_particion.png")


def fig_curvas_pr(y, puntajes_por_modelo, auc_por_modelo, titulo):
    fig, ax = plt.subplots(figsize=(6, 4.5))
    for nombre, p in puntajes_por_modelo.items():
        prec, exh, _ = precision_recall_curve(y, p)
        ax.plot(exh, prec, color=COLOR[nombre], linewidth=2,
                label=f"{nombre}  (AUC-PR {auc_por_modelo[nombre]:.3f})")
    ax.axhline(float(np.mean(y)), color="#999", linestyle=":", linewidth=1,
               label=f"azar ({np.mean(y):.4f})")
    ax.set_xlabel("exhaustividad")
    ax.set_ylabel("precisión")
    ax.set_title(titulo, loc="left")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25)
    return _guardar(fig, "fig2_curvas_pr.png")


def fig_permutacion(auc_original, permutacion):
    """Barras de original contra P1 y P2, por modelo."""
    fig, ax = plt.subplots(figsize=(7, 4.2))
    modelos = ["A", "B", "C"]
    x = np.arange(len(modelos))
    ancho = 0.26
    series = [
        ("original", [auc_original[m] for m in modelos], "#2f6f4f"),
        ("P1: historia barajada", [permutacion[m]["P1"] for m in modelos], "#d1791f"),
        ("P2: orden destruido", [permutacion[m]["P2"] for m in modelos], "#b03030"),
    ]
    for i, (etiqueta, valores, color) in enumerate(series):
        barras = ax.bar(x + (i - 1) * ancho, valores, ancho, label=etiqueta, color=color)
        ax.bar_label(barras, fmt="%.3f", fontsize=8, padding=2)
    ax.set_xticks(x, modelos)
    ax.set_ylabel("AUC-PR en validación")
    ax.set_title("AUC-PR antes y después de barajar el orden", loc="left")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, max(auc_original.values()) * 1.25)
    return _guardar(fig, "fig3_permutacion.png")


def fig_desglose(desglose_por_modelo):
    """Exhaustividad por mecanismo. F4 es el que nadie entreno."""
    mecanismos = ["F1", "F2", "F3", "F4"]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    x = np.arange(len(mecanismos))
    ancho = 0.26
    for i, (nombre, d) in enumerate(desglose_por_modelo.items()):
        valores = [d["exhaustividad"].get(m, 0.0) for m in mecanismos]
        barras = ax.bar(x + (i - 1) * ancho, valores, ancho, label=nombre, color=COLOR[nombre])
        ax.bar_label(barras, fmt="%.2f", fontsize=8, padding=2)
    ax.set_xticks(x, ["F1\nprueba y cobro\n(orden)", "F2\nviaje imposible\n(mixto)",
                      "F3\ntoma de cuenta\n(agregados)", "F4\ngoteo lento\n(no entrenado)"])
    ax.set_ylabel("exhaustividad en prueba")
    ax.set_title("Exhaustividad por mecanismo de fraude", loc="left")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, 1.15)
    return _guardar(fig, "fig4_desglose.png")


def fig_costo(y_val, puntajes_val, umbrales):
    """Costo esperado contra umbral, con el punto elegido marcado."""
    fig, ax = plt.subplots(figsize=(7, 4.2))
    minimos = []
    for nombre, p in puntajes_val.items():
        tabla = barrer_umbrales(y_val, p)
        ax.plot(tabla["umbral"], tabla["costo"] / 1000, color=COLOR[nombre],
                linewidth=2, label=nombre)
        u = umbrales[nombre]
        costo_u = float(tabla.loc[(tabla["umbral"] - u).abs().idxmin(), "costo"]) / 1000
        minimos.append(costo_u)
        ax.plot([u], [costo_u], "o", color=COLOR[nombre], markersize=8,
                markeredgecolor="white")
        ax.annotate(f"{u:.2f}", (u, costo_u), textcoords="offset points",
                    xytext=(6, 10), fontsize=9, color=COLOR[nombre], weight="bold")
    # sin recortar el eje, los extremos aplastan el minimo y la curva se ve plana
    ax.set_ylim(0, max(minimos) * 2.6)
    ax.set_xlabel(f"umbral de bloqueo   (FN = Q{COSTO_FN:,.0f} · FP = Q{COSTO_FP:,.0f})")
    ax.set_ylabel("costo esperado en validación (miles de Q)")
    ax.set_title("Costo esperado según el umbral", loc="left")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25)
    return _guardar(fig, "fig5_costo.png")
