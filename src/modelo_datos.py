"""Modelo de datos en estrella para Power BI.

Tablas que genera en data/bi/ (CSV con separador coma y punto decimal):

    dim_fecha        una fila por día (dic-2009 a dic-2011) con festivos
    dim_producto     catálogo de productos con su clase ABC (Pareto)
    dim_cliente      clientes con su segmento RFM
    dim_pais         países con región y nivel de ingreso (Banco Mundial)
    fact_ventas      una fila por línea de factura (ventas y devoluciones)
    fact_pronostico  demanda real vs. pronosticada (semanas de prueba)
    pronostico_proxima_semana  pronóstico por producto para la semana siguiente
    metricas_modelo  métricas de los modelos comparados

Relaciones (uno a muchos, filtro en una dirección):
    dim_fecha[fecha_key]       -> fact_ventas[fecha_key]
    dim_producto[producto_key] -> fact_ventas[producto_key]
    dim_cliente[cliente_key]   -> fact_ventas[cliente_key]
    dim_pais[pais_key]         -> fact_ventas[pais_key]
    dim_producto[producto_key] -> fact_pronostico[producto_key]
    dim_producto[producto_key] -> pronostico_proxima_semana[producto_key]

Uso:
    python -m src.modelo_datos
"""
from __future__ import annotations

import pandas as pd

from src import config

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def construir_dim_fecha(ventas: pd.DataFrame, festivos: pd.DataFrame) -> pd.DataFrame:
    fechas = pd.date_range(ventas["fecha"].min(), ventas["fecha"].max(), freq="D")
    d = pd.DataFrame({"fecha": fechas})
    d["fecha_key"] = d["fecha"].dt.strftime("%Y%m%d").astype(int)
    d["anio"] = d["fecha"].dt.year
    d["trimestre"] = "T" + d["fecha"].dt.quarter.astype(str)
    d["mes_num"] = d["fecha"].dt.month
    d["mes"] = d["mes_num"].map(lambda m: MESES[m - 1])
    d["anio_mes"] = d["fecha"].dt.strftime("%Y-%m")
    d["semana_inicio"] = d["fecha"] - pd.to_timedelta(d["fecha"].dt.day_of_week, unit="D")
    d["dia_semana_num"] = d["fecha"].dt.day_of_week + 1
    d["dia_semana"] = d["fecha"].dt.day_of_week.map(lambda x: DIAS[x])
    d = d.merge(festivos, on="fecha", how="left")
    d["es_festivo"] = d["nombre_festivo"].notna()
    d["nombre_festivo"] = d["nombre_festivo"].fillna("")
    d["temporada"] = d["mes_num"].map(lambda m: "Alta (sep-nov)" if m in (9, 10, 11) else
                                      ("Navidad (dic)" if m == 12 else "Regular"))
    cols = ["fecha_key", "fecha", "anio", "trimestre", "mes_num", "mes", "anio_mes",
            "semana_inicio", "dia_semana_num", "dia_semana", "es_festivo",
            "nombre_festivo", "temporada"]
    return d[cols]


def construir_dim_producto(ventas: pd.DataFrame) -> pd.DataFrame:
    """Catálogo con clasificación ABC: A = productos que suman el 80 % del ingreso."""
    v = ventas[ventas["tipo_transaccion"] == "Venta"]
    resumen = (v.groupby("codigo_producto")
               .agg(ingreso=("importe", "sum"), precio_mediano=("precio_unitario", "median"),
                    primera_venta=("fecha", "min"), ultima_venta=("fecha", "max"))
               .sort_values("ingreso", ascending=False))
    acumulado = resumen["ingreso"].cumsum() / resumen["ingreso"].sum()
    resumen["clase_abc"] = pd.cut(acumulado, [0, 0.8, 0.95, 1.0001], labels=["A", "B", "C"]).astype(str)
    catalogo = ventas.drop_duplicates("codigo_producto")[["codigo_producto", "descripcion"]]
    p = catalogo.merge(resumen.drop(columns="ingreso"), left_on="codigo_producto",
                       right_index=True, how="left")
    p["clase_abc"] = p["clase_abc"].fillna("Sin ventas")
    p = p.sort_values("codigo_producto").reset_index(drop=True)
    p.insert(0, "producto_key", range(1, len(p) + 1))
    return p


def segmentar_rfm(ventas: pd.DataFrame) -> pd.DataFrame:
    """Segmentación RFM (Recencia, Frecuencia, valor Monetario) por cliente.

    Cada dimensión se puntúa de 1 a 5 por quintiles y se combina en segmentos
    con nombre de negocio.
    """
    v = ventas[(ventas["tipo_transaccion"] == "Venta") & ventas["cliente_registrado"]]
    corte = ventas["fecha"].max() + pd.Timedelta(days=1)
    rfm = v.groupby("cliente_id").agg(
        ultima_compra=("fecha", "max"), primera_compra=("fecha", "min"),
        frecuencia=("factura", "nunique"), monetario=("importe", "sum"))
    rfm["recencia_dias"] = (corte - rfm["ultima_compra"]).dt.days
    rfm["R"] = pd.qcut(rfm["recencia_dias"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F"] = pd.qcut(rfm["frecuencia"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M"] = pd.qcut(rfm["monetario"], 5, labels=[1, 2, 3, 4, 5]).astype(int)

    def nombre(r, f):
        if r >= 4 and f >= 4:
            return "Campeones"
        if r >= 3 and f >= 3:
            return "Leales"
        if r >= 4 and f <= 2:
            return "Nuevos o recientes"
        if r == 3 and f <= 2:
            return "Necesitan atención"
        if r <= 2 and f >= 3:
            return "En riesgo"
        return "Perdidos"
    rfm["segmento_rfm"] = [nombre(r, f) for r, f in zip(rfm["R"], rfm["F"])]
    return rfm.reset_index()


def construir_dim_cliente(ventas: pd.DataFrame) -> pd.DataFrame:
    rfm = segmentar_rfm(ventas)
    pais = (ventas[ventas["cliente_registrado"]].groupby("cliente_id")["pais"]
            .agg(lambda s: s.value_counts().index[0]))
    c = rfm.merge(pais.rename("pais_principal"), left_on="cliente_id", right_index=True)
    # Clientes que en el periodo solo registran devoluciones (compraron antes de dic-2009)
    solo_dev = sorted(set(pais.index) - set(c["cliente_id"]))
    otros = pd.DataFrame({"cliente_id": solo_dev, "segmento_rfm": "Solo devoluciones",
                          "pais_principal": pais.reindex(solo_dev).values})
    sin = pd.DataFrame([{"cliente_id": "SIN REGISTRO", "segmento_rfm": "Sin registro",
                         "pais_principal": "Varios"}])
    c = pd.concat([c, otros, sin], ignore_index=True)
    c.insert(0, "cliente_key", range(1, len(c) + 1))
    cols = ["cliente_key", "cliente_id", "pais_principal", "primera_compra", "ultima_compra",
            "recencia_dias", "frecuencia", "monetario", "R", "F", "M", "segmento_rfm"]
    return c[cols]


def construir_dim_pais(ventas: pd.DataFrame, paises: pd.DataFrame) -> pd.DataFrame:
    usados = ventas.drop_duplicates("pais")[["pais", "iso3", "region", "nivel_ingreso"]]
    d = usados.merge(paises[["iso3", "iso2", "capital", "latitud", "longitud"]],
                     on="iso3", how="left").sort_values("pais").reset_index(drop=True)
    d["mercado"] = (d["pais"] == "United Kingdom").map({True: "Nacional (Reino Unido)",
                                                         False: "Internacional"})
    d.insert(0, "pais_key", range(1, len(d) + 1))
    return d


def construir_fact_ventas(ventas, dim_producto, dim_cliente, dim_pais) -> pd.DataFrame:
    f = ventas.merge(dim_producto[["producto_key", "codigo_producto"]], on="codigo_producto")
    f = f.merge(dim_cliente[["cliente_key", "cliente_id"]], on="cliente_id")
    f = f.merge(dim_pais[["pais_key", "pais"]], on="pais")
    f["fecha_key"] = f["fecha"].dt.strftime("%Y%m%d").astype(int)
    f["es_devolucion"] = (f["tipo_transaccion"] == "Devolución").astype(int)
    cols = ["factura", "fecha_key", "hora", "producto_key", "cliente_key", "pais_key",
            "tipo_transaccion", "es_devolucion", "cantidad", "precio_unitario", "importe"]
    assert len(f) == len(ventas), "Se perdieron filas al unir con las dimensiones"
    return f[cols]


def construir_tablas_pronostico(dim_producto):
    """Prepara las salidas del modelo predictivo (si ya se ejecutó) para Power BI."""
    tablas = {}
    claves = dim_producto[["producto_key", "codigo_producto"]]
    if config.PREDICCIONES.exists():
        p = pd.read_csv(config.PREDICCIONES, parse_dates=["semana_inicio"], dtype={"codigo_producto": str})
        tablas["fact_pronostico"] = p.merge(claves, on="codigo_producto").drop(columns=["descripcion"], errors="ignore")
    if config.PRONOSTICO_PROXIMA_SEMANA.exists():
        p = pd.read_csv(config.PRONOSTICO_PROXIMA_SEMANA, parse_dates=["semana_inicio"], dtype={"codigo_producto": str})
        tablas["pronostico_proxima_semana"] = p.merge(claves, on="codigo_producto")
    if config.METRICAS_MODELOS.exists():
        tablas["metricas_modelo"] = pd.read_csv(config.METRICAS_MODELOS)
    return tablas


def construir_modelo_estrella(guardar: bool = True) -> dict[str, pd.DataFrame]:
    ventas = pd.read_parquet(config.VENTAS_LIMPIAS)
    festivos = pd.read_csv(config.FESTIVOS_LIMPIOS, parse_dates=["fecha"])
    paises = pd.read_csv(config.PAISES_LIMPIOS)

    dim_fecha = construir_dim_fecha(ventas, festivos)
    dim_producto = construir_dim_producto(ventas)
    dim_cliente = construir_dim_cliente(ventas)
    dim_pais = construir_dim_pais(ventas, paises)
    fact = construir_fact_ventas(ventas, dim_producto, dim_cliente, dim_pais)
    tablas = {"dim_fecha": dim_fecha, "dim_producto": dim_producto, "dim_cliente": dim_cliente,
              "dim_pais": dim_pais, "fact_ventas": fact, **construir_tablas_pronostico(dim_producto)}

    if guardar:
        config.BI.mkdir(parents=True, exist_ok=True)
        for nombre, t in tablas.items():
            t.to_csv(config.BI / f"{nombre}.csv", index=False, date_format="%Y-%m-%d")
            print(f"{nombre:<28} {len(t):>9,} filas")
    return tablas


def validar_modelo(tablas: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Integridad referencial y unicidad de claves del modelo estrella."""
    f = tablas["fact_ventas"]
    pruebas = {
        "Claves únicas en dim_fecha": tablas["dim_fecha"]["fecha_key"].is_unique,
        "Claves únicas en dim_producto": tablas["dim_producto"]["producto_key"].is_unique,
        "Claves únicas en dim_cliente": tablas["dim_cliente"]["cliente_key"].is_unique,
        "Claves únicas en dim_pais": tablas["dim_pais"]["pais_key"].is_unique,
        "Toda venta tiene fecha": f["fecha_key"].isin(tablas["dim_fecha"]["fecha_key"]).all(),
        "Toda venta tiene producto": f["producto_key"].isin(tablas["dim_producto"]["producto_key"]).all(),
        "Toda venta tiene cliente": f["cliente_key"].isin(tablas["dim_cliente"]["cliente_key"]).all(),
        "Toda venta tiene país": f["pais_key"].isin(tablas["dim_pais"]["pais_key"]).all(),
    }
    return pd.DataFrame({"prueba": list(pruebas),
                         "resultado": ["OK" if v else "FALLA" for v in pruebas.values()]})


if __name__ == "__main__":
    t = construir_modelo_estrella()
    print(validar_modelo(t).to_string(index=False))
