# Reglas de negocio de los datos

**Responsable:** Víctor Manuel David Rodríguez · Implementadas en [`src/etl.py`](../src/etl.py) · Ejecutadas y explicadas en [`notebooks/01_etl.ipynb`](../notebooks/01_etl.ipynb)

Estas reglas definen qué es una venta válida para el proyecto. Se aplican en el ETL antes de cualquier análisis, para que el EDA, el modelo predictivo y el dashboard partan de la misma verdad.

## Fuentes integradas

| # | Fuente | Formato | Uso |
|---|---|---|---|
| 1 | **Online Retail II**, UCI Machine Learning Repository, id 502 (Chen, 2019), licencia CC BY 4.0. Se descarga la copia idéntica de OpenML (id 43368) en Parquet | Tabular | Transacciones de dic-2009 a dic-2011 (1.067.371 líneas) |
| 2 | **API Nager.Date**, festivos públicos del Reino Unido 2009-2011 | JSON | Dimensión fecha (festivos) |
| 3 | **API del Banco Mundial**, catálogo de países | JSON | Región y nivel de ingreso de cada país |

Las respuestas de las APIs se guardan en `data/external/` para que el proceso sea reproducible aunque una API cambie o no responda.

## Reglas

| Regla | Nombre | Definición | Justificación | Filas afectadas |
|---|---|---|---|---|
| **R1** | Venta válida | Precio unitario > 0. Las ventas tienen cantidad > 0 y las devoluciones cantidad < 0 | Las líneas con precio 0 o signo incoherente son ajustes de inventario (daños, conteos), no transacciones con clientes | 5.962 excluidas |
| **R2** | Tipo de transacción | Factura que empieza por **C** = devolución o anulación. Factura que empieza por **A** = ajuste contable de deuda incobrable | Las devoluciones se conservan para medir la tasa de devolución; los ajustes contables no son ventas | 6 excluidas (A) |
| **R3** | Solo productos | Se conservan los códigos que empiezan por 5 dígitos o por `DCGS`/`SP` | Portes (POST, DOT, C2), manuales (M), descuentos (D), muestras (S), comisiones (BANK CHARGES, AMAZONFEE, CRUK), bonos regalo y pruebas no son demanda de productos | 5.814 excluidas |
| **R4** | Importe | `importe = cantidad × precio_unitario` en libras esterlinas (GBP). Negativo en devoluciones | Medida base de ventas | — |
| **R5** | Duplicados | Se elimina toda línea idéntica a otra en factura, producto, descripción, cantidad, fecha-hora, precio, cliente y país | Son registros repetidos por el sistema y duplicarían ventas | 34.337 excluidas |
| **R6** | Cliente sin identificar | Si falta el ID del cliente se usa `SIN REGISTRO` | Se conservan para los totales de ventas, pero se excluyen del análisis de clientes y de la segmentación RFM | 22,8 % de las líneas |
| **R7** | País normalizado | El nombre del dataset se lleva a código ISO3 (EIRE → IRL, RSA → ZAF, USA → USA…) y se enriquece con región y nivel de ingreso del Banco Mundial. "European Community", "West Indies" y "Unspecified" reciben región manual | Une la fuente 1 con la fuente 3 | 43 orígenes normalizados |
| **R8** | Cantidades atípicas | Se excluyen las líneas con \|cantidad\| ≥ 10.000 | Incluye los dos pedidos masivos (74.215 y 80.995 unidades) que se anularon a los pocos minutos y pedidos extraordinarios que distorsionan los promedios de demanda | 13 excluidas |
| **R9** | Descripción única | Cada código de producto toma su descripción más frecuente | El mismo producto aparecía escrito de varias formas o sin descripción | 4.474 líneas sin descripción en origen |
| **R10** | Calendario | Se derivan año, mes, día de la semana, hora, semana (lunes a domingo) y marca de festivo | Une la fuente 1 con la fuente 2 y alimenta la dimensión fecha | — |

**Resultado:** de 1.067.371 líneas se conservan **1.021.239 (95,7 %)**.

## Pruebas de calidad automáticas

`validar_calidad()` verifica, después de transformar, que:

1. No hay nulos en las columnas clave.
2. El precio unitario siempre es mayor que 0.
3. Las ventas tienen importe positivo y las devoluciones importe negativo.
4. No quedan duplicados exactos.
5. Todos los países tienen región.
6. Todas las fechas están entre dic-2009 y dic-2011.
7. Cada producto tiene una sola descripción.

Si alguna prueba falla, el ETL se detiene y no guarda datos.

## Consideraciones éticas y de privacidad

- El dataset es **público** y los clientes están **anonimizados** con un número; no contiene nombres, correos ni direcciones.
- No se intenta reidentificar clientes ni cruzar el ID con otras fuentes.
- Los datos crudos y procesados **no se suben al repositorio** (están en `.gitignore`); cada integrante los regenera con `python -m src.etl`.
- Toda exclusión de datos queda documentada con su número de filas en la bitácora (`data/processed/reporte_calidad.csv`), para que cualquier persona pueda auditar el proceso.
