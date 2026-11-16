# Ficha del modelo predictivo

**Responsable:** Samuel · Código: [`src/modelado.py`](../src/modelado.py) · Experimento completo: [`notebooks/04_modelo_predictivo.ipynb`](../notebooks/04_modelo_predictivo.ipynb) · Métricas: [`reports/metricas_modelos.csv`](../reports/metricas_modelos.csv)

Una ficha de modelo (*model card*) resume en una página qué hace el modelo, con qué datos se entrenó, qué tan bien funciona, para qué sirve y para qué **no** debe usarse.

## 1. Descripción

| Campo | Detalle |
|---|---|
| Objetivo | Pronosticar las **unidades vendidas por producto en la semana siguiente** |
| Usuarios | Compras e inventario (reposición), operaciones (capacidad de bodega y despacho) |
| Tipo | Aprendizaje supervisado de **regresión** |
| Algoritmo elegido | **Random Forest** (`n_estimators=400`, `max_depth=12`, `min_samples_leaf=20`, `max_features=0.3`) |
| Alternativas evaluadas | Regresión lineal Ridge, árbol de decisión, Gradient Boosting (HistGB) y dos líneas base sin modelo |
| Criterio de selección | Menor RMSE en **validación cruzada temporal** (4 pliegues de 8 semanas) |
| Salida | Unidades pronosticadas, con un rango mínimo y máximo por producto |

## 2. Datos

- **Fuente:** tabla limpia del ETL (Online Retail II, UCI), solo líneas de **venta** (sin devoluciones).
- **Unidad de análisis:** producto × semana (lunes a domingo). Las semanas sin venta cuentan como 0.
- **Alcance:** los **300 productos con demanda más recurrente**, que representan el 30,3 % del ingreso. Son 31.147 filas, de dic-2009 a nov-2011.
- **Entrenamiento:** 25.759 filas (11-ene-2010 a 5-sep-2011). **Prueba:** 3.600 filas, las últimas 12 semanas (12-sep a 4-dic-2011, temporada alta).
- **Variables (22):** rezagos de 1 a 4 semanas, promedios móviles de 4, 8 y 12 semanas, variabilidad reciente, regularidad de venta, media histórica, antigüedad, precio, clientes y pedidos de la semana anterior, demanda total de la tienda, calendario, festivos y estacionalidad del año anterior. **Todas usan solo información del pasado** para evitar fuga de datos.

## 3. Desempeño (12 semanas de prueba)

| Modelo | RMSE (validación cruzada) | RMSE prueba | MAE | R² | WAPE | Sesgo |
|---|---|---|---|---|---|---|
| **Random Forest (elegido)** | **138,8** | **164,8** | **65,3** | **0,52** | **55,4 %** | **−2,6 %** |
| Regresión lineal (Ridge) | 139,8 | 161,6 | 66,3 | 0,54 | 56,3 % | +1,0 % |
| Gradient Boosting (HistGB) | 142,0 | 166,8 | 67,4 | 0,51 | 57,2 % | +0,6 % |
| Base: promedio 4 semanas | — | 169,0 | 69,0 | 0,50 | 58,5 % | −6,3 % |
| Árbol de decisión | 144,7 | 170,9 | 66,4 | 0,49 | 56,3 % | −6,4 % |
| Base: semana anterior | — | 202,7 | 81,0 | 0,28 | 68,8 % | −1,0 % |

- **Total semanal de los 300 productos:** WAPE **12,5 %**.
- **Por volumen del producto:** WAPE de 50 % en los de alto volumen y de 89 % en los de bajo volumen.
- **Mejora frente a líneas base:** −18,7 % de RMSE frente a "semana anterior" y −2,5 % frente a "promedio 4 semanas".
- **Variables más influyentes** (importancia por permutación): promedios de 8 y 12 semanas, estacionalidad del año anterior y promedio de 4 semanas.

## 4. Usos recomendados y no recomendados

**Sí usarlo para:**
- Planear el **volumen total semanal** de bodega, transporte y personal.
- Sugerir reposición de productos de **alta rotación**, usando el **rango mínimo-máximo**.
- Detectar productos cuyo pronóstico se aleja mucho de su promedio reciente (alerta para revisar).

**No usarlo para:**
- Decidir pedidos de productos fuera de los 300 modelados o recién lanzados (sin historia).
- Prometer cantidades exactas a un cliente: el error por producto es alto.
- Anticipar pedidos mayoristas extraordinarios: el modelo no tiene esa información.
- Tomar decisiones sobre personas (empleados o clientes individuales): el modelo predice demanda de productos, no comportamiento de personas.

## 5. Limitaciones

1. Solo hay **dos años de historia**, es decir, un único ciclo anual completo para aprender la estacionalidad.
2. La demanda es **mayorista e irregular** (coeficiente de variación mediano 1,54): ninguna variable histórica anticipa un pedido grande puntual.
3. Los **precios casi no cambiaron**, así que el modelo no aprendió cómo responde la demanda a promociones o cambios de precio.
4. Los datos llegan a **dic-2011**; para usarlo hoy habría que reentrenarlo con datos recientes.

## 6. Consideraciones éticas

- **Privacidad:** el modelo trabaja con datos **agregados por producto y semana**; no usa ni expone información individual de clientes. Los IDs de cliente del dataset ya vienen anonimizados.
- **Transparencia:** se reportan las métricas reales, incluida la mejora modesta frente al promedio móvil, y se compara siempre contra líneas base, sin exagerar el desempeño.
- **Uso responsable:** el pronóstico **apoya** la decisión de compras, no la reemplaza. Una persona debe revisar los casos donde el pronóstico se aleja mucho de la tendencia.
- **Impacto:** un pronóstico demasiado alto genera sobreinventario y desperdicio; uno demasiado bajo genera quiebres de stock. Por eso se entrega un **rango** y se recomienda revisarlo cada semana.
- **Reproducibilidad:** semilla fija (`SEMILLA = 42`), división temporal documentada y código abierto en el repositorio.

## 7. Mantenimiento

- Reentrenar **cada semana** con los datos nuevos (`modelado.pronosticar_proxima_semana`).
- Vigilar el `WAPE Total Semanal %` en el dashboard. Si supera el 20 % durante 3 semanas seguidas, revisar variables y datos.
