"""Modelo A (boosting sobre agregados), B (GRU) y C (hibrido)."""
import numpy as np

from sklearn.ensemble import HistGradientBoostingClassifier

from src.evaluacion import roc_auc


def entrenar_a(X_ent, y_ent, X_val, y_val, semilla: int = 42):
    """Boosting sobre los agregados. Es la linea base y conviene que sea dura.

    Va con sklearn y no con lightgbm porque en macOS ARM lightgbm mas un GRU de
    torch revienta con segfault: los dos cargan su propio OpenMP. El algoritmo es
    el mismo boosting por histogramas, asi que no se pierde nada.
    """
    y_ent = np.asarray(y_ent)
    positivos = max(1, int(y_ent.sum()))
    peso = float((len(y_ent) - positivos) / positivos)
    modelo = HistGradientBoostingClassifier(
        max_iter=400, learning_rate=0.05, random_state=semilla,
        class_weight={0: 1.0, 1: peso},
    )
    modelo.fit(np.asarray(X_ent), y_ent)
    return modelo


def puntajes_a(modelo, X) -> np.ndarray:
    return modelo.predict_proba(np.asarray(X))[:, 1]


def verificar_senuelo(dataset, semilla: int = 42, solo_cobro: bool = False) -> float:
    """Intenta separar F1 del senuelo usando solo los agregados. Devuelve ROC-AUC.

    Cerca de 0.5 quiere decir que el senuelo esta haciendo su trabajo. Con
    solo_cobro=True mide unicamente la ultima transaccion de cada episodio, que es
    donde las dos historias traen los mismos montos y los mismos huecos. Sobre
    todas las anclas sube un poco, porque en las intermedias el prefijo de F1
    siempre trae los montos mas chicos y el del senuelo no.
    """
    meta = dataset.meta
    sel = meta["mecanismo"].isin(["F1", "senuelo_f1"]).to_numpy()
    if solo_cobro:
        ultimo = (meta.loc[sel]
                  .groupby(["mecanismo", "id_tarjeta", "id_episodio"])["marca_tiempo"]
                  .idxmax().to_numpy())
        sel = np.zeros(len(meta), dtype=bool)
        sel[ultimo] = True

    X = dataset.agregados.loc[sel].to_numpy()
    y = (meta.loc[sel, "mecanismo"] == "F1").astype(int).to_numpy()

    corte = int(len(X) * 0.7)
    modelo = entrenar_a(X[:corte], y[:corte], X[corte:], y[corte:], semilla=semilla)
    return roc_auc(y[corte:], puntajes_a(modelo, X[corte:]))


import torch
import torch.nn as nn

from src.evaluacion import auc_pr


class ModeloSecuencial(nn.Module):
    """GRU sobre los eventos en orden. Con n_agregados=0 es B, con 15 es el hibrido C."""

    def __init__(self, n_rubros, n_canales, n_ciudades, n_agregados=0,
                 dim_emb=8, oculto=64, capas=1):
        super().__init__()
        self.emb_rubro = nn.Embedding(n_rubros, dim_emb, padding_idx=0)
        self.emb_canal = nn.Embedding(n_canales, dim_emb, padding_idx=0)
        self.emb_ciudad = nn.Embedding(n_ciudades, dim_emb, padding_idx=0)
        self.gru = nn.GRU(dim_emb * 3 + 7, oculto, num_layers=capas, batch_first=True)
        self.n_agregados = n_agregados
        self.cabeza = nn.Sequential(
            nn.Linear(oculto + n_agregados, 32), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(32, 1),
        )

    def forward(self, cat, num, mascara, agregados=None):
        e = torch.cat([
            self.emb_rubro(cat[..., 0]),
            self.emb_canal(cat[..., 1]),
            self.emb_ciudad(cat[..., 2]),
            num,
        ], dim=-1)
        e = e * mascara.unsqueeze(-1)          # apaga el relleno
        salida, _ = self.gru(e)
        # ultimo paso que existe de verdad en cada secuencia
        ultimo = mascara.float().cumsum(dim=1).argmax(dim=1)
        h = salida[torch.arange(salida.size(0), device=salida.device), ultimo]
        h = h * mascara.any(dim=1, keepdim=True)   # si no hay nada observado, cero
        if self.n_agregados > 0:
            h = torch.cat([h, agregados], dim=-1)
        return self.cabeza(h).squeeze(-1)


def entrenar_secuencial(modelo, datos_ent, datos_val, peso_positivo,
                        epocas=12, semilla=42, dispositivo="cpu", lote=256):
    torch.manual_seed(semilla)
    modelo = modelo.to(dispositivo)
    opt = torch.optim.Adam(modelo.parameters(), lr=1e-3)
    perdida = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor(peso_positivo, device=dispositivo))
    n = len(datos_ent["y"])
    generador = torch.Generator().manual_seed(semilla)
    historial, mejor, mejores_pesos = [], -1.0, None

    for epoca in range(epocas):
        modelo.train()
        orden = torch.randperm(n, generator=generador)
        for i in range(0, n, lote):
            b = orden[i:i + lote]
            agr = datos_ent["agregados"][b].to(dispositivo) if modelo.n_agregados else None
            logits = modelo(datos_ent["cat"][b].to(dispositivo),
                            datos_ent["num"][b].to(dispositivo),
                            datos_ent["mascara"][b].to(dispositivo), agr)
            costo = perdida(logits, datos_ent["y"][b].to(dispositivo))
            opt.zero_grad()
            costo.backward()
            opt.step()

        p_val = puntajes_secuencial(modelo, datos_val, dispositivo)
        metrica = auc_pr(datos_val["y"].numpy(), p_val)
        historial.append({"epoca": epoca, "auc_pr_val": metrica})
        if metrica > mejor:
            mejor = metrica
            mejores_pesos = {k: v.detach().clone() for k, v in modelo.state_dict().items()}

    if mejores_pesos is not None:
        modelo.load_state_dict(mejores_pesos)   # nos quedamos con la mejor epoca en validacion
    return historial


@torch.no_grad()
def puntajes_secuencial(modelo, datos, dispositivo="cpu", lote=512) -> np.ndarray:
    modelo = modelo.to(dispositivo).eval()
    trozos = []
    for i in range(0, len(datos["y"]), lote):
        s = slice(i, i + lote)
        agr = datos["agregados"][s].to(dispositivo) if modelo.n_agregados else None
        logits = modelo(datos["cat"][s].to(dispositivo),
                        datos["num"][s].to(dispositivo),
                        datos["mascara"][s].to(dispositivo), agr)
        trozos.append(torch.sigmoid(logits).cpu().numpy())
    return np.concatenate(trozos)


def datos_a_tensores(dataset, seq_num_escalado, agregados_escalados, sel) -> dict:
    """Pasa el subconjunto que marca `sel` a tensores de torch."""
    sel = np.asarray(sel, dtype=bool)
    return {
        # .copy() porque pandas 3 devuelve arreglos de solo lectura y torch se queja
        "cat": torch.from_numpy(dataset.seq_cat[sel].copy()).long(),
        "num": torch.from_numpy(seq_num_escalado[sel].copy()).float(),
        "mascara": torch.from_numpy(dataset.mascara[sel].copy()),
        "agregados": torch.from_numpy(agregados_escalados.to_numpy()[sel].copy()).float(),
        "y": torch.from_numpy(dataset.meta.loc[sel, "es_fraude"].to_numpy().copy()).float(),
    }
