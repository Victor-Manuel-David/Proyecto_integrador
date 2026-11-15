"""Estilo y funciones de gráficas reutilizables para el EDA y el modelo.

Todas las figuras usan la misma paleta y formato para que el informe y la
presentación se vean coherentes. `guardar` las deja en reports/figures/.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd
import seaborn as sns

from src import config

PALETA = ["#1F4E79", "#E07A1F", "#2E8B57", "#B23A48", "#6C5B7B", "#8C8C8C"]
AZUL, NARANJA, VERDE, ROJO = PALETA[:4]


def aplicar_estilo() -> None:
    sns.set_theme(style="whitegrid", palette=PALETA, font_scale=1.0)
    plt.rcParams.update({
        "figure.figsize": (10, 5), "figure.dpi": 110, "savefig.dpi": 150,
        "axes.titlesize": 13, "axes.titleweight": "bold", "axes.spines.top": False,
        "axes.spines.right": False, "axes.titlelocation": "left",
    })


def guardar(fig, nombre: str) -> None:
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(config.FIGURES / f"{nombre}.png", bbox_inches="tight")


def formato_libras(ax, eje: str = "y", miles: bool = True) -> None:
    """Muestra el eje en libras esterlinas (k = miles)."""
    if miles:
        f = mtick.FuncFormatter(lambda v, _: f"£{v/1000:,.0f}k")
    else:
        f = mtick.FuncFormatter(lambda v, _: f"£{v:,.0f}")
    (ax.yaxis if eje == "y" else ax.xaxis).set_major_formatter(f)


def barras_horizontales(serie: pd.Series, titulo: str, xlabel: str, color: str = AZUL,
                        libras: bool = False, ax=None):
    """Ranking horizontal ordenado de mayor a menor (el mayor arriba)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(10, max(3, 0.38 * len(serie))))
    s = serie.sort_values()
    ax.barh(s.index.astype(str), s.values, color=color)
    ax.set_title(titulo)
    ax.set_xlabel(xlabel)
    if libras:
        formato_libras(ax, "x", miles=s.max() > 10_000)
    return ax


def linea_temporal(df: pd.DataFrame, x: str, y: str, titulo: str, hue: str | None = None,
                   libras: bool = True, ax=None):
    if ax is None:
        _, ax = plt.subplots()
    sns.lineplot(data=df, x=x, y=y, hue=hue, marker="o", ax=ax)
    ax.set_title(titulo)
    ax.set_xlabel("")
    if libras:
        formato_libras(ax)
    return ax


def mapa_calor(tabla: pd.DataFrame, titulo: str, fmt: str = ".0f", cmap: str = "Blues", ax=None,
               **kwargs):
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))
    sns.heatmap(tabla, annot=True, fmt=fmt, cmap=cmap, linewidths=0.5, ax=ax, **kwargs)
    ax.set_title(titulo)
    return ax
