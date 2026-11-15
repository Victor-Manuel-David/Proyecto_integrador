"""Proceso ETL (extracción, transformación y carga) del proyecto.

Integra tres fuentes:
1. Transacciones de la tienda en línea Online Retail II (UCI; archivo Parquet).
2. Festivos del Reino Unido 2009-2011 (API REST Nager.Date, JSON).
3. Catálogo de países con región y nivel de ingreso (API REST Banco Mundial, JSON).

Uso desde la terminal (en la raíz del repositorio):
    python -m src.etl

Las reglas de negocio aplicadas están documentadas en docs/reglas_de_negocio.md.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import requests

from src import config

# ----------------------------------------------------------------------------
# Catálogos usados por las reglas de negocio
# ----------------------------------------------------------------------------

# R7. Nombre del país en el dataset -> código ISO3 del Banco Mundial.
PAIS_A_ISO3 = {
    "United Kingdom": "GBR", "France": "FRA", "USA": "USA", "Belgium": "BEL",
    "Australia": "AUS", "EIRE": "IRL", "Germany": "DEU", "Portugal": "PRT",
    "Japan": "JPN", "Denmark": "DNK", "Nigeria": "NGA", "Netherlands": "NLD",
    "Poland": "POL", "Spain": "ESP", "Channel Islands": "CHI", "Italy": "ITA",
    "Cyprus": "CYP", "Greece": "GRC", "Norway": "NOR", "Austria": "AUT",
    "Sweden": "SWE", "United Arab Emirates": "ARE", "Finland": "FIN",
    "Switzerland": "CHE", "Malta": "MLT", "Bahrain": "BHR", "RSA": "ZAF",
    "Bermuda": "BMU", "Hong Kong": "HKG", "Singapore": "SGP", "Thailand": "THA",
    "Israel": "ISR", "Lithuania": "LTU", "Lebanon": "LBN", "Korea": "KOR",
    "Brazil": "BRA", "Canada": "CAN", "Iceland": "ISL", "Saudi Arabia": "SAU",
    "Czech Republic": "CZE",
}
# Orígenes que no son un país concreto: se les asigna una región a mano.
PAIS_SIN_ISO = {
    "European Community": ("Comunidad Europea (sin país)", "Europa y Asia Central"),
    "West Indies": ("Indias Occidentales (sin país)", "América Latina y el Caribe"),
    "Unspecified": ("No especificado", "No especificado"),
}
REGIONES_ES = {
    "Europe & Central Asia": "Europa y Asia Central",
    "East Asia & Pacific": "Asia Oriental y Pacífico",
    "Latin America & Caribbean": "América Latina y el Caribe",
    "Middle East, North Africa, Afghanistan & Pakistan": "Medio Oriente y Norte de África",
    "Middle East & North Africa": "Medio Oriente y Norte de África",
    "North America": "América del Norte",
    "South Asia": "Asia del Sur",
    "Sub-Saharan Africa": "África Subsahariana",
}
INGRESOS_ES = {
    "High income": "Ingreso alto",
    "Upper middle income": "Ingreso medio alto",
    "Lower middle income": "Ingreso medio bajo",
    "Low income": "Ingreso bajo",
}

# R3. Un código es de producto si empieza por 5 dígitos (p. ej. 85123A)
# o pertenece a las líneas "DCGS" y "SP" de la tienda. Lo demás son cargos o
# ajustes: portes (POST, DOT, C2), manuales (M), descuentos (D), muestras (S),
# comisiones (BANK CHARGES, AMAZONFEE, CRUK), bonos regalo (GIFT_*) y pruebas.
PATRON_PRODUCTO = re.compile(r"^(\d{5}|DCGS|SP\d)", re.IGNORECASE)

# R8. Umbral de cantidad atípica por línea (pedidos anulados de forma masiva).
UMBRAL_CANTIDAD_ATIPICA = 10_000

COLUMNAS = {
    "Invoice": "factura", "StockCode": "codigo_producto", "Description": "descripcion",
    "Quantity": "cantidad", "InvoiceDate": "fecha_hora", "Price": "precio_unitario",
    "Customer ID": "cliente_id", "Country": "pais_origen",
}


# ----------------------------------------------------------------------------
# EXTRACCIÓN
# ----------------------------------------------------------------------------

def descargar(url: str, destino: Path, timeout: int = 120) -> Path:
    """Descarga un archivo si no existe todavía en disco."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        tmp = destino.with_suffix(destino.suffix + ".part")
        with open(tmp, "wb") as f:
            for bloque in r.iter_content(chunk_size=1 << 20):
                f.write(bloque)
        tmp.replace(destino)
    return destino


def extraer_ventas() -> pd.DataFrame:
    """Fuente 1: transacciones Online Retail II (dic-2009 a dic-2011).

    Descarga el archivo Parquet una sola vez a data/raw/ y verifica que traiga
    todas las filas del dataset original de UCI.
    """
    descargar(config.URL_ONLINE_RETAIL, config.PARQUET_ONLINE_RETAIL, timeout=600)
    ventas = pd.read_parquet(config.PARQUET_ONLINE_RETAIL)
    ventas = ventas.rename(columns={"Customer_ID": "Customer ID"})
    if len(ventas) != config.FILAS_ESPERADAS:
        raise ValueError(f"Se esperaban {config.FILAS_ESPERADAS:,} filas y llegaron {len(ventas):,}")
    return ventas


def _leer_o_descargar_json(ruta: Path, descargar_fn) -> object:
    """Usa la copia local del JSON si existe; si no, llama a la API y la guarda."""
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    datos = descargar_fn()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return datos


def extraer_festivos() -> pd.DataFrame:
    """Fuente 2: festivos oficiales del Reino Unido (API Nager.Date)."""
    def _api():
        todos = []
        for anio in config.ANIOS_FESTIVOS:
            r = requests.get(config.URL_FESTIVOS.format(anio=anio), timeout=60)
            r.raise_for_status()
            todos.extend(r.json())
        return todos
    return pd.DataFrame(_leer_o_descargar_json(config.JSON_FESTIVOS, _api))


def extraer_paises() -> pd.DataFrame:
    """Fuente 3: catálogo de países del Banco Mundial (API REST)."""
    def _api():
        r = requests.get(config.URL_PAISES, timeout=60)
        r.raise_for_status()
        return r.json()[1]  # la posición 0 trae metadatos de paginación
    datos = _leer_o_descargar_json(config.JSON_PAISES, _api)
    return pd.json_normalize(datos)


# ----------------------------------------------------------------------------
# TRANSFORMACIÓN
# ----------------------------------------------------------------------------

class Bitacora:
    """Registra cuántas filas elimina cada regla para documentar el ETL."""

    def __init__(self) -> None:
        self.pasos: list[dict] = []

    def registrar(self, regla: str, descripcion: str, antes: int, despues: int) -> None:
        self.pasos.append({"regla": regla, "descripcion": descripcion,
                           "filas_antes": antes, "filas_despues": despues,
                           "filas_eliminadas": antes - despues})

    def tabla(self) -> pd.DataFrame:
        return pd.DataFrame(self.pasos)


def transformar_festivos(festivos: pd.DataFrame) -> pd.DataFrame:
    """Deja una fila por fecha festiva aplicable a Inglaterra (sede de la tienda)."""
    f = festivos.copy()
    f["fecha"] = pd.to_datetime(f["date"])
    aplica_inglaterra = f["counties"].apply(
        lambda c: c is None or (isinstance(c, (list, tuple)) and "GB-ENG" in c)
        or (hasattr(c, "__len__") and "GB-ENG" in list(c)))
    f = f[aplica_inglaterra | f["global"].astype(bool)]
    f = (f.groupby("fecha", as_index=False)["name"].first()
         .rename(columns={"name": "nombre_festivo"}))
    return f


def transformar_paises(paises: pd.DataFrame) -> pd.DataFrame:
    """Catálogo de países con nombres de región y nivel de ingreso en español."""
    p = paises.rename(columns={"id": "iso3", "iso2Code": "iso2", "name": "pais",
                               "region.value": "region_en",
                               "incomeLevel.value": "ingreso_en",
                               "capitalCity": "capital",
                               "latitude": "latitud", "longitude": "longitud"})
    p = p[["iso3", "iso2", "pais", "region_en", "ingreso_en", "capital", "latitud", "longitud"]]
    p["region_en"] = p["region_en"].str.strip()
    p = p[p["region_en"] != "Aggregates"].copy()
    p["region"] = p["region_en"].map(REGIONES_ES).fillna(p["region_en"])
    p["nivel_ingreso"] = p["ingreso_en"].map(INGRESOS_ES).fillna("Sin clasificar")
    for c in ["latitud", "longitud"]:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    return p.drop(columns=["region_en", "ingreso_en"])


def transformar_ventas(crudo: pd.DataFrame, paises: pd.DataFrame,
                       festivos: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aplica las reglas de negocio R1-R10 y devuelve (ventas_limpias, bitacora)."""
    b = Bitacora()
    df = crudo.rename(columns=COLUMNAS).copy()
    n = len(df)
    b.registrar("R0", "Filas extraídas del dataset original", n, n)

    # Tipos y espacios
    df["factura"] = df["factura"].astype(str).str.strip()
    df["codigo_producto"] = df["codigo_producto"].astype(str).str.strip().str.upper()
    df["descripcion"] = df["descripcion"].astype("string").str.strip().str.upper()
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])

    # R9. Descripción única por producto: la más frecuente del código. Se hace
    # antes de buscar duplicados para que dos líneas iguales con descripción
    # escrita distinto cuenten como la misma.
    desc = (df.dropna(subset=["descripcion"])
            .groupby("codigo_producto")["descripcion"]
            .agg(lambda s: s.value_counts().index[0]))
    df["descripcion"] = df["codigo_producto"].map(desc).fillna("SIN DESCRIPCIÓN")

    # R5. Duplicados exactos (misma factura, producto, cantidad, precio, hora...)
    antes = len(df)
    df = df.drop_duplicates(subset=list(COLUMNAS.values()))
    b.registrar("R5", "Duplicados exactos eliminados", antes, len(df))

    # R2. Tipo de transacción: facturas que empiezan por C son devoluciones/anulaciones.
    df["tipo_transaccion"] = df["factura"].str.startswith("C").map(
        {True: "Devolución", False: "Venta"})

    # R2b. Facturas A = ajustes contables de deuda incobrable (no son ventas).
    antes = len(df)
    df = df[~df["factura"].str.startswith("A")]
    b.registrar("R2", "Ajustes contables (facturas A) excluidos", antes, len(df))

    # R3. Solo códigos de producto; se excluyen portes, comisiones, descuentos, etc.
    antes = len(df)
    df = df[df["codigo_producto"].str.match(PATRON_PRODUCTO)]
    b.registrar("R3", "Cargos y ajustes no producto excluidos (POST, M, D, BANK CHARGES...)",
                antes, len(df))

    # R1. Coherencia de valores: precio > 0; ventas con cantidad > 0 y
    # devoluciones con cantidad < 0. Lo demás son ajustes de inventario sin valor.
    antes = len(df)
    venta_ok = (df["tipo_transaccion"] == "Venta") & (df["cantidad"] > 0)
    dev_ok = (df["tipo_transaccion"] == "Devolución") & (df["cantidad"] < 0)
    df = df[(df["precio_unitario"] > 0) & (venta_ok | dev_ok)]
    b.registrar("R1", "Líneas con precio 0 o cantidad incoherente excluidas", antes, len(df))

    # R8. Cantidades atípicas (pedidos masivos que se anularon el mismo día).
    antes = len(df)
    df = df[df["cantidad"].abs() < UMBRAL_CANTIDAD_ATIPICA]
    b.registrar("R8", f"Líneas con |cantidad| >= {UMBRAL_CANTIDAD_ATIPICA:,} excluidas",
                antes, len(df))

    # R6. Clientes sin identificar: se conservan para totales de ventas.
    df["cliente_registrado"] = df["cliente_id"].notna()
    df["cliente_id"] = (df["cliente_id"].astype("Int64").astype("string")
                        .fillna("SIN REGISTRO"))

    # R7. Normalización de país y enriquecimiento con el Banco Mundial.
    df["iso3"] = df["pais_origen"].str.strip().map(PAIS_A_ISO3)
    df = df.merge(paises[["iso3", "pais", "region", "nivel_ingreso"]], on="iso3", how="left")
    for origen, (nombre, region) in PAIS_SIN_ISO.items():
        m = df["pais_origen"] == origen
        df.loc[m, ["pais", "region", "nivel_ingreso"]] = [nombre, region, "Sin clasificar"]
    df["iso3"] = df["iso3"].fillna("ZZZ")

    # R4. Importe de la línea en libras esterlinas (negativo en devoluciones).
    df["importe"] = (df["cantidad"] * df["precio_unitario"]).round(2)

    # R10. Atributos de calendario y festivos (base de la dimensión fecha).
    df["fecha"] = df["fecha_hora"].dt.normalize()
    df["anio"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df["hora"] = df["fecha_hora"].dt.hour
    df["dia_semana"] = df["fecha"].dt.day_of_week  # 0 = lunes
    df["semana_inicio"] = df["fecha"] - pd.to_timedelta(df["dia_semana"], unit="D")
    df["es_festivo"] = df["fecha"].isin(festivos["fecha"])

    columnas = ["factura", "tipo_transaccion", "fecha_hora", "fecha", "anio", "mes",
                "dia_semana", "hora", "semana_inicio", "es_festivo", "codigo_producto",
                "descripcion", "cantidad", "precio_unitario", "importe", "cliente_id",
                "cliente_registrado", "pais_origen", "iso3", "pais", "region",
                "nivel_ingreso"]
    df = df[columnas].sort_values("fecha_hora").reset_index(drop=True)
    b.registrar("FIN", "Filas en la tabla limpia", len(df), len(df))
    return df, b.tabla()


def validar_calidad(df: pd.DataFrame) -> pd.DataFrame:
    """Pruebas de calidad sobre la tabla limpia. Todas deben quedar en 'OK'."""
    claves = ["factura", "codigo_producto", "descripcion", "cantidad", "precio_unitario",
              "fecha_hora", "cliente_id", "pais", "region"]
    pruebas = {
        "Sin nulos en columnas clave": df[claves].notna().all().all(),
        "Precio unitario siempre > 0": (df["precio_unitario"] > 0).all(),
        "Ventas con importe positivo": (df.loc[df["tipo_transaccion"] == "Venta", "importe"] > 0).all(),
        "Devoluciones con importe negativo": (df.loc[df["tipo_transaccion"] == "Devolución", "importe"] < 0).all(),
        "Sin duplicados exactos": not df.duplicated(subset=["factura", "codigo_producto", "cantidad",
                                                            "precio_unitario", "fecha_hora", "cliente_id"]).any(),
        "Todos los países tienen región": (df["region"].notna()).all(),
        "Fechas dentro de dic-2009 a dic-2011": df["fecha"].between("2009-12-01", "2011-12-31").all(),
        "Una descripción por producto": (df.groupby("codigo_producto")["descripcion"].nunique() == 1).all(),
    }
    return pd.DataFrame({"prueba": list(pruebas), "resultado": ["OK" if v else "FALLA" for v in pruebas.values()]})


# ----------------------------------------------------------------------------
# CARGA
# ----------------------------------------------------------------------------

def ejecutar_etl(verbose: bool = True) -> dict[str, pd.DataFrame]:
    """Corre el proceso completo y guarda los resultados en data/processed/."""
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    crudo = extraer_ventas()
    festivos = transformar_festivos(extraer_festivos())
    paises = transformar_paises(extraer_paises())
    ventas, bitacora = transformar_ventas(crudo, paises, festivos)
    calidad = validar_calidad(ventas)

    ventas.to_parquet(config.VENTAS_LIMPIAS, index=False)
    festivos.to_csv(config.FESTIVOS_LIMPIOS, index=False)
    paises.to_csv(config.PAISES_LIMPIOS, index=False)
    bitacora.to_csv(config.REPORTE_CALIDAD, index=False)

    if verbose:
        print(bitacora.to_string(index=False))
        print()
        print(calidad.to_string(index=False))
        print(f"\nTabla limpia: {len(ventas):,} filas -> {config.VENTAS_LIMPIAS}")
    if (calidad["resultado"] != "OK").any():
        raise ValueError("Hay pruebas de calidad en FALLA; revisar antes de continuar.")
    return {"crudo": crudo, "ventas": ventas, "festivos": festivos, "paises": paises,
            "bitacora": bitacora, "calidad": calidad}


if __name__ == "__main__":
    ejecutar_etl()
