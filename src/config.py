"""Configuración central del proyecto: rutas, fuentes de datos y constantes.

Todos los módulos importan desde aquí para que las rutas y parámetros
se cambien en un solo lugar.
"""
from pathlib import Path

# --- Rutas -------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
RAW = DATA / "raw"              # datos originales descargados (no se suben a Git)
EXTERNAL = DATA / "external"    # fuentes complementarias pequeñas (sí se suben)
PROCESSED = DATA / "processed"  # datos limpios generados por el ETL (no se suben)
BI = DATA / "bi"                # tablas del modelo estrella para Power BI (no se suben)
REPORTS = RAIZ / "reports"
FIGURES = REPORTS / "figures"

# --- Fuente 1: transacciones de la tienda en línea (Online Retail II) --------
# Dataset original: UCI Machine Learning Repository, id 502 (Chen, 2019), CC BY 4.0
#   https://archive.ics.uci.edu/dataset/502/online+retail+ii
# Se descarga la copia idéntica publicada en OpenML (id 43368) en formato Parquet
# porque el servidor de UCI entrega el Excel a muy baja velocidad.
URL_ONLINE_RETAIL = "https://data.openml.org/datasets/0004/43368/dataset_43368.pq"
PARQUET_ONLINE_RETAIL = RAW / "online_retail_ii.parquet"
FILAS_ESPERADAS = 1_067_371  # filas que reporta UCI para el dataset completo

# --- Fuente 2: festivos del Reino Unido (API REST Nager.Date, JSON) ---------
URL_FESTIVOS = "https://date.nager.at/api/v3/PublicHolidays/{anio}/GB"
ANIOS_FESTIVOS = [2009, 2010, 2011]
JSON_FESTIVOS = EXTERNAL / "festivos_gb.json"

# --- Fuente 3: países del Banco Mundial (API REST, JSON) --------------------
URL_PAISES = "https://api.worldbank.org/v2/country?format=json&per_page=400"
JSON_PAISES = EXTERNAL / "paises_banco_mundial.json"

# --- Salidas del ETL ----------------------------------------------------------
VENTAS_LIMPIAS = PROCESSED / "ventas_limpias.parquet"
FESTIVOS_LIMPIOS = PROCESSED / "festivos.csv"
PAISES_LIMPIOS = PROCESSED / "paises.csv"
REPORTE_CALIDAD = PROCESSED / "reporte_calidad.csv"

# --- Salidas del modelo predictivo -------------------------------------------
PREDICCIONES = PROCESSED / "predicciones_demanda.csv"
PRONOSTICO_PROXIMA_SEMANA = PROCESSED / "pronostico_proxima_semana.csv"
METRICAS_MODELOS = REPORTS / "metricas_modelos.csv"

# --- Parámetros generales -----------------------------------------------------
SEMILLA = 42
MONEDA = "GBP"
