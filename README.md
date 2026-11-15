# Análisis de datos y modelo predictivo de demanda para una tienda en línea

**Proyecto integrador · Equipo 4** · Inteligencia de Negocios · Analítica de Datos · Aprendizaje Computacional

> Estado: estructura inicial. Este README se completa con los resultados al cierre del proyecto.

## Problema de negocio

Una tienda en línea del Reino Unido vende artículos de regalo y decoración, sobre todo a mayoristas. El proyecto busca responder:

1. **¿Qué vende, a quién, cuándo y dónde?** → análisis exploratorio y dashboard de Power BI.
2. **¿Cuántas unidades de cada producto venderá la próxima semana?** → modelo supervisado de regresión para planear el inventario.

## Datos

- **Online Retail II** – UCI Machine Learning Repository (id 502): transacciones de dic-2009 a dic-2011.
- **API Nager.Date** – festivos del Reino Unido.
- **API del Banco Mundial** – región y nivel de ingreso de cada país.

## Fases y responsables

| Fase | Responsable | Carpeta |
|---|---|---|
| 1. Recopilación y transformación (ETL) | Víctor | `src/etl.py`, `notebooks/01_etl.ipynb` |
| 2. Análisis exploratorio (EDA) | David | `notebooks/02_eda.ipynb` |
| 4. Modelo predictivo | Samuel | `src/modelado.py`, `notebooks/04_modelo_predictivo.ipynb` |
| 3. Inteligencia de negocios (modelo de datos y dashboard) | Juana | `src/modelo_datos.py`, `dashboard/` |
| 5. Conclusiones, recomendaciones e informe | David (conclusiones del EDA) y Juana (cierre) | `docs/` |

Orden de trabajo: Víctor → David → Samuel → Juana. El modelo de datos de BI (fase 3) se construye después del modelo predictivo porque incluye sus pronósticos.

## Preparar el entorno

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (en Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

Los datos no se suben al repositorio (ver `.gitignore`); se descargan y limpian con el ETL.
