"""Modelo predictivo de demanda semanal por producto (aprendizaje supervisado).

Pregunta de negocio: ¿cuántas unidades de cada producto se venderán la próxima
semana? Con esa cifra el área de compras e inventario decide cuánto reponer.

Flujo:
1. construir_panel_semanal  -> una fila por producto y semana (con ceros).
2. crear_variables          -> rezagos, medias móviles, precio, calendario y
                               estacionalidad del año anterior.
3. dividir_entrenamiento_prueba -> las últimas 12 semanas quedan para prueba.
4. entrenar_y_comparar      -> líneas base + 4 modelos con ajuste por validación
                               cruzada temporal.
5. pronosticar_proxima_semana -> reentrena el mejor modelo con todo y predice.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RandomizedSearchCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from src import config

SEMANAS_PRUEBA = 12
N_PRODUCTOS = 300

VARIABLES = [
    "lag_1", "lag_2", "lag_3", "lag_4", "media_4", "media_8", "media_12", "desv_4",
    "max_4", "semanas_con_venta_8", "media_historica", "semanas_desde_lanzamiento",
    "precio_lag_1", "clientes_lag_1", "pedidos_lag_1", "demanda_tienda_lag_1",
    "semana_anio", "mes", "festivos_semana",
    "estacional_52", "tiene_historia_anual", "indice_estacional",
]


# ----------------------------------------------------------------------------
# 1. Panel semanal
# ----------------------------------------------------------------------------

def construir_panel_semanal(ventas: pd.DataFrame, festivos: pd.DataFrame,
                            n_productos: int = N_PRODUCTOS) -> pd.DataFrame:
    """Agrega las ventas por producto y semana (lunes a domingo).

    - Se usan solo ventas (no devoluciones): la demanda es lo que el cliente pide.
    - Se descartan la primera y la última semana porque están incompletas.
    - Se eligen los `n_productos` que se vendieron en más semanas (demanda
      recurrente, que es la que conviene planificar).
    - Las semanas sin venta quedan con 0 unidades desde que el producto aparece.
    """
    v = ventas[ventas["tipo_transaccion"] == "Venta"]
    semanas = np.sort(v["semana_inicio"].unique())
    primera_completa = semanas[1]   # la semana del 1-dic-2009 empieza en martes
    ultima_completa = semanas[-2]   # la última semana termina el 9-dic-2011 (viernes)
    v = v[(v["semana_inicio"] >= primera_completa) & (v["semana_inicio"] <= ultima_completa)]

    agg = (v.groupby(["codigo_producto", "semana_inicio"])
           .agg(unidades=("cantidad", "sum"), ingreso=("importe", "sum"),
                clientes=("cliente_id", "nunique"), pedidos=("factura", "nunique"))
           .reset_index())
    tienda = agg.groupby("semana_inicio")["unidades"].sum().rename("demanda_tienda")

    elegidos = (agg.groupby("codigo_producto")["semana_inicio"].nunique()
                .sort_values(ascending=False).head(n_productos).index)
    agg = agg[agg["codigo_producto"].isin(elegidos)]

    todas = pd.date_range(primera_completa, ultima_completa, freq="7D")
    filas = []
    for codigo, g in agg.groupby("codigo_producto"):
        rango = todas[todas >= g["semana_inicio"].min()]
        filas.append(pd.DataFrame({"codigo_producto": codigo, "semana_inicio": rango}))
    panel = pd.concat(filas, ignore_index=True).merge(
        agg, on=["codigo_producto", "semana_inicio"], how="left")
    panel[["unidades", "ingreso", "clientes", "pedidos"]] = (
        panel[["unidades", "ingreso", "clientes", "pedidos"]].fillna(0))
    panel["precio_medio"] = np.where(panel["unidades"] > 0,
                                     panel["ingreso"] / panel["unidades"], np.nan)
    panel["precio_medio"] = panel.groupby("codigo_producto")["precio_medio"].ffill()
    panel = panel.merge(tienda, left_on="semana_inicio", right_index=True, how="left")

    fest = festivos.assign(semana_inicio=festivos["fecha"] - pd.to_timedelta(
        festivos["fecha"].dt.day_of_week, unit="D"))
    n_fest = fest.groupby("semana_inicio").size().rename("festivos_semana")
    panel = panel.merge(n_fest, left_on="semana_inicio", right_index=True, how="left")
    panel["festivos_semana"] = panel["festivos_semana"].fillna(0).astype(int)

    desc = ventas.drop_duplicates("codigo_producto").set_index("codigo_producto")["descripcion"]
    panel["descripcion"] = panel["codigo_producto"].map(desc)
    return panel.sort_values(["codigo_producto", "semana_inicio"]).reset_index(drop=True)


def agregar_semana_futura(panel: pd.DataFrame, festivos: pd.DataFrame) -> pd.DataFrame:
    """Añade una fila vacía por producto para la semana siguiente a la última."""
    siguiente = panel["semana_inicio"].max() + pd.Timedelta(days=7)
    futuro = panel.drop_duplicates("codigo_producto")[["codigo_producto", "descripcion"]].copy()
    futuro["semana_inicio"] = siguiente
    fin = siguiente + pd.Timedelta(days=6)
    futuro["festivos_semana"] = int(festivos["fecha"].between(siguiente, fin).sum())
    return pd.concat([panel, futuro], ignore_index=True).sort_values(
        ["codigo_producto", "semana_inicio"]).reset_index(drop=True)


# ----------------------------------------------------------------------------
# 2. Variables predictoras (solo usan información de semanas anteriores)
# ----------------------------------------------------------------------------

def crear_variables(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    g = df.groupby("codigo_producto", group_keys=False)
    prev = g["unidades"].shift(1)
    for k in (1, 2, 3, 4):
        df[f"lag_{k}"] = g["unidades"].shift(k)
    grp_prev = prev.groupby(df["codigo_producto"])
    for w in (4, 8, 12):
        df[f"media_{w}"] = grp_prev.transform(lambda s: s.rolling(w, min_periods=1).mean())
    df["desv_4"] = grp_prev.transform(lambda s: s.rolling(4, min_periods=2).std()).fillna(0)
    df["max_4"] = grp_prev.transform(lambda s: s.rolling(4, min_periods=1).max())
    df["semanas_con_venta_8"] = grp_prev.transform(
        lambda s: (s > 0).astype(float).rolling(8, min_periods=1).sum())
    df["media_historica"] = grp_prev.transform(lambda s: s.expanding().mean())
    df["semanas_desde_lanzamiento"] = g.cumcount()
    df["precio_lag_1"] = g["precio_medio"].shift(1)
    df["precio_lag_1"] = df.groupby("codigo_producto")["precio_lag_1"].ffill()
    df["clientes_lag_1"] = g["clientes"].shift(1)
    df["pedidos_lag_1"] = g["pedidos"].shift(1)
    tienda = (df.drop_duplicates("semana_inicio").set_index("semana_inicio")["demanda_tienda"]
              .sort_index().shift(1))
    df["demanda_tienda_lag_1"] = df["semana_inicio"].map(tienda)
    df["semana_anio"] = df["semana_inicio"].dt.isocalendar().week.astype(int)
    df["mes"] = df["semana_inicio"].dt.month

    # Estacionalidad anual: lo que se vendió en la misma época del año anterior
    # (semanas 51, 52 y 53 hacia atrás). Si el producto aún no tiene un año de
    # historia se usa su media de 12 semanas y se marca con tiene_historia_anual=0.
    hace_un_anio = pd.concat([g["unidades"].shift(k) for k in (51, 52, 53)], axis=1).mean(axis=1)
    df["tiene_historia_anual"] = hace_un_anio.notna().astype(int)
    df["estacional_52"] = hace_un_anio.fillna(df["media_12"])
    base_anio_anterior = df.groupby("codigo_producto")["media_12"].shift(52)
    df["indice_estacional"] = (hace_un_anio / (base_anio_anterior + 1)).fillna(1.0)
    return df


# ----------------------------------------------------------------------------
# 3. División temporal
# ----------------------------------------------------------------------------

def dividir_entrenamiento_prueba(df: pd.DataFrame, semanas_prueba: int = SEMANAS_PRUEBA):
    """Entrena con el pasado y prueba con las últimas semanas (nunca al revés)."""
    datos = df.dropna(subset=["lag_4", "precio_lag_1", "demanda_tienda_lag_1", "unidades"])
    semanas = np.sort(datos["semana_inicio"].unique())
    corte = semanas[-semanas_prueba]
    train = datos[datos["semana_inicio"] < corte].sort_values("semana_inicio")
    test = datos[datos["semana_inicio"] >= corte].sort_values("semana_inicio")
    return train, test


def particiones_temporales(semanas: pd.Series, n_particiones: int = 4, horizonte: int = 8):
    """Validación cruzada temporal: cada pliegue entrena con el pasado y valida
    con las `horizonte` semanas siguientes (ventana que avanza)."""
    unicas = np.sort(semanas.unique())
    for i in range(n_particiones, 0, -1):
        fin_val = len(unicas) - (i - 1) * horizonte
        ini_val = fin_val - horizonte
        sem_val = unicas[ini_val:fin_val]
        idx_train = np.where(semanas.values < sem_val[0])[0]
        idx_val = np.where(np.isin(semanas.values, sem_val))[0]
        yield idx_train, idx_val


# ----------------------------------------------------------------------------
# 4. Entrenamiento, ajuste de hiperparámetros y evaluación
# ----------------------------------------------------------------------------

def metricas(y_real, y_pred) -> dict:
    y_real = np.asarray(y_real, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "MAE": mean_absolute_error(y_real, y_pred),
        "RMSE": float(np.sqrt(mean_squared_error(y_real, y_pred))),
        "R2": r2_score(y_real, y_pred),
        "WAPE_%": 100 * np.abs(y_real - y_pred).sum() / y_real.sum(),
        "Sesgo_%": 100 * (y_pred - y_real).sum() / y_real.sum(),
    }


def candidatos() -> dict:
    """Modelos supervisados y la grilla de hiperparámetros de cada uno."""
    s = config.SEMILLA
    return {
        "Regresión lineal (Ridge)": (
            make_pipeline(StandardScaler(), Ridge()),
            {"ridge__alpha": [0.1, 1, 10, 100, 1000]}),
        "Árbol de decisión": (
            DecisionTreeRegressor(random_state=s),
            {"max_depth": [3, 5, 8, 12, None], "min_samples_leaf": [5, 20, 50, 100]}),
        "Random Forest": (
            RandomForestRegressor(random_state=s, n_jobs=-1),
            {"n_estimators": [200, 400], "max_depth": [8, 12, 16, None],
             "min_samples_leaf": [2, 5, 10, 20], "max_features": [0.3, 0.5, 0.8]}),
        "Gradient Boosting (HistGB)": (
            HistGradientBoostingRegressor(random_state=s),
            {"learning_rate": [0.03, 0.05, 0.1], "max_iter": [200, 400, 800],
             "max_leaf_nodes": [15, 31, 63], "min_samples_leaf": [10, 20, 50],
             "l2_regularization": [0.0, 0.1, 1.0], "loss": ["squared_error", "poisson"]}),
    }


def entrenar_y_comparar(train: pd.DataFrame, test: pd.DataFrame, n_iter: int = 20,
                        verbose: bool = True):
    """Ajusta cada candidato con búsqueda aleatoria + validación cruzada temporal
    (RMSE como criterio) y lo evalúa en las semanas de prueba.

    Devuelve (tabla_metricas, modelos_ajustados, predicciones_prueba).
    """
    X_tr, y_tr = train[VARIABLES], train["unidades"]
    X_te, y_te = test[VARIABLES], test["unidades"]
    cv = list(particiones_temporales(train["semana_inicio"].reset_index(drop=True)))

    filas, modelos = [], {}
    preds = test[["codigo_producto", "descripcion", "semana_inicio", "unidades"]].copy()

    # Líneas base: si un modelo no les gana, no aporta valor.
    for nombre, pred in {"Base: semana anterior": test["lag_1"],
                         "Base: media 4 semanas": test["media_4"]}.items():
        filas.append({"modelo": nombre, "mejores_parametros": "-",
                      "RMSE_validacion_cruzada": np.nan, **metricas(y_te, pred)})
        preds[nombre] = pred.values

    for nombre, (estimador, grilla) in candidatos().items():
        n = min(n_iter, int(np.prod([len(v) for v in grilla.values()])))
        busqueda = RandomizedSearchCV(estimador, grilla, n_iter=n, cv=cv,
                                      scoring="neg_root_mean_squared_error",
                                      random_state=config.SEMILLA, n_jobs=-1)
        busqueda.fit(X_tr, y_tr)
        mejor = busqueda.best_estimator_
        pred = np.clip(mejor.predict(X_te), 0, None)  # no existe demanda negativa
        modelos[nombre] = mejor
        preds[nombre] = pred
        filas.append({"modelo": nombre, "mejores_parametros": str(busqueda.best_params_),
                      "RMSE_validacion_cruzada": -busqueda.best_score_, **metricas(y_te, pred)})
        if verbose:
            print(f"{nombre:<28} RMSE CV={-busqueda.best_score_:8.2f}  "
                  f"RMSE prueba={filas[-1]['RMSE']:8.2f}")

    tabla = pd.DataFrame(filas).sort_values("RMSE").reset_index(drop=True)
    return tabla, modelos, preds


# ----------------------------------------------------------------------------
# 5. Pronóstico de la próxima semana
# ----------------------------------------------------------------------------

def pronosticar_proxima_semana(modelo, panel: pd.DataFrame, festivos: pd.DataFrame,
                               errores_producto: pd.Series) -> pd.DataFrame:
    """Reentrena el modelo con toda la historia y pronostica la semana siguiente.

    El rango sugerido usa el error absoluto medio de cada producto en prueba,
    para que compras vea un mínimo y un máximo razonables.
    """
    completo = crear_variables(agregar_semana_futura(panel, festivos))
    semana_futura = completo["semana_inicio"].max()
    hist = completo[completo["semana_inicio"] < semana_futura].dropna(
        subset=["lag_4", "precio_lag_1", "demanda_tienda_lag_1"])
    fut = completo[completo["semana_inicio"] == semana_futura].copy()
    fut["demanda_tienda_lag_1"] = fut["demanda_tienda_lag_1"].fillna(
        panel.groupby("semana_inicio")["unidades"].sum().iloc[-1])
    final = clone(modelo).fit(hist[VARIABLES], hist["unidades"])
    fut["unidades_pronosticadas"] = np.clip(final.predict(fut[VARIABLES]), 0, None).round()
    mae = fut["codigo_producto"].map(errores_producto).fillna(errores_producto.median())
    fut["rango_minimo"] = np.clip(fut["unidades_pronosticadas"] - mae, 0, None).round()
    fut["rango_maximo"] = (fut["unidades_pronosticadas"] + mae).round()
    fut["promedio_ultimas_4_semanas"] = fut["media_4"].round(1)
    columnas = ["codigo_producto", "descripcion", "semana_inicio", "unidades_pronosticadas",
                "rango_minimo", "rango_maximo", "promedio_ultimas_4_semanas"]
    return fut[columnas].sort_values("unidades_pronosticadas", ascending=False).reset_index(drop=True)
