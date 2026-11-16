# Conclusiones y recomendaciones

**Responsable de esta versión:** David · Fase 5 de la guía del proyecto · Primera versión, con las conclusiones del análisis exploratorio ([`02_eda.ipynb`](../notebooks/02_eda.ipynb)).

> **Estado:** borrador. Las conclusiones del modelo de datos (segmentos RFM, clases ABC), del modelo predictivo y la tabla de recomendaciones con su indicador en el dashboard se agregan al cierre del proyecto, cuando esas fases estén terminadas.

## Situación analizada

Una tienda en línea del Reino Unido que vende artículos de regalo y decoración, sobre todo a mayoristas, entre diciembre de 2009 y diciembre de 2011: **£18,9 millones en ventas netas**, 39.513 pedidos, 5.852 clientes identificados y 4.723 productos vendidos en 43 países u orígenes.

## Conclusiones del análisis exploratorio

1. **El negocio es estable pero no crece.** Las ventas de enero a noviembre pasaron de £8,36 M (2010) a £8,57 M (2011): **+2,5 %**. Sin una estrategia nueva, la tendencia es plana.

2. **La estacionalidad manda.** Septiembre, octubre y noviembre concentran el **36,8 %** de las ventas de los meses completos, con pico en noviembre (£1,43 M en 2011). Muchos de los productos más vendidos son de Navidad. Quien no tenga inventario en agosto pierde la temporada.

3. **Pocos productos sostienen el negocio.** Se cumple el principio de Pareto: el **22 % de los productos genera el 80 % del ingreso**.

4. **Pocos clientes sostienen el ingreso, y la mayoría vuelve.** El 10 % de los clientes aporta el **63,4 %** del ingreso identificado y el **72,3 %** de los clientes compra más de una vez.

5. **El mercado internacional es pequeño pero de mayor ticket.** Aporta el 14,6 % del ingreso, pero su **ticket promedio (£851) casi duplica el británico (£457)**. Alemania y Francia ya tienen más de 90 clientes cada una. Irlanda (3,2 % del ingreso) depende de solo 4 clientes.

6. **Las devoluciones están controladas, con focos puntuales.** La tasa global es **2,43 %**, pero algunos productos superan el 15 % (*Fairy Cake Flannel*, 26 %) y Francia llega al 5,7 %.

7. **La operación tiene un calendario fijo.** No hay ventas en festivos ni, prácticamente, en sábados. Los pedidos se concentran de martes a jueves entre las 10 y las 15 h.

## Primeras recomendaciones (a confirmar al cierre)

- Preparar el inventario de temporada desde agosto.
- Priorizar la reposición de los productos que generan el 80 % del ingreso.
- Cuidar a los clientes de mayor valor con un programa de retención.
- Explorar el crecimiento en Alemania y Francia.
- Revisar los productos con devolución superior al 10 %.
