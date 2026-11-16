# Medidas DAX del dashboard

**Responsable:** Juana · Se crean en una tabla vacía llamada `_Medidas` (ver paso 4 de la [guía](guia_power_bi.md)).

Cada medida implementa una regla de negocio del notebook [`03_modelo_datos_bi.ipynb`](../notebooks/03_modelo_datos_bi.ipynb). Los nombres van sin tildes para evitar errores al escribirlos en otras fórmulas.

> **Cómo crear una medida:** clic derecho sobre la tabla `_Medidas` → *Nueva medida* → pegar el bloque completo → Enter. Luego, en *Herramientas de medición*, aplicar el formato indicado.

---

## 1. Ventas (página Resumen ejecutivo)

```DAX
Ventas Netas = SUM ( fact_ventas[importe] )
```
Formato: moneda £, 0 decimales.

```DAX
Ventas Brutas =
CALCULATE ( SUM ( fact_ventas[importe] ), fact_ventas[es_devolucion] = 0 )
```
Formato: moneda £, 0 decimales.

```DAX
Devoluciones =
- CALCULATE ( SUM ( fact_ventas[importe] ), fact_ventas[es_devolucion] = 1 )
```
Formato: moneda £, 0 decimales. Se cambia el signo para mostrarla en positivo.

```DAX
Tasa Devolucion % = DIVIDE ( [Devoluciones], [Ventas Brutas] )
```
Formato: porcentaje, 2 decimales.

```DAX
Pedidos =
CALCULATE ( DISTINCTCOUNT ( fact_ventas[factura] ), fact_ventas[es_devolucion] = 0 )
```
Formato: número entero con separador de miles.

```DAX
Ticket Promedio = DIVIDE ( [Ventas Brutas], [Pedidos] )
```
Formato: moneda £, 0 decimales.

```DAX
Unidades Vendidas =
CALCULATE ( SUM ( fact_ventas[cantidad] ), fact_ventas[es_devolucion] = 0 )
```

```DAX
Clientes Activos =
CALCULATE (
    DISTINCTCOUNT ( fact_ventas[cliente_key] ),
    fact_ventas[es_devolucion] = 0,
    dim_cliente[segmento_rfm] <> "Sin registro"
)
```

## 2. Comparación con el año anterior

Requiere que `dim_fecha` esté **marcada como tabla de fechas** (paso 3 de la guía).

```DAX
Ventas Netas AA =
CALCULATE ( [Ventas Netas], SAMEPERIODLASTYEAR ( dim_fecha[fecha] ) )
```

```DAX
Var % Interanual =
DIVIDE ( [Ventas Netas] - [Ventas Netas AA], [Ventas Netas AA] )
```
Formato: porcentaje, 1 decimal. Formato condicional: verde si > 0, rojo si < 0.

```DAX
Pedidos AA =
CALCULATE ( [Pedidos], SAMEPERIODLASTYEAR ( dim_fecha[fecha] ) )
```

```DAX
Color Variacion =
IF ( [Var % Interanual] >= 0, "#2E8B57", "#B23A48" )
```
Se usa en *Formato condicional → Color de fuente → Valor del campo*.

## 3. Productos

```DAX
% Participacion Ventas =
DIVIDE ( [Ventas Brutas], CALCULATE ( [Ventas Brutas], ALLSELECTED ( dim_producto ) ) )
```
Formato: porcentaje, 1 decimal.

```DAX
Ranking Producto =
IF (
    HASONEVALUE ( dim_producto[descripcion] ),
    RANKX ( ALLSELECTED ( dim_producto[descripcion] ), [Ventas Brutas], , DESC, DENSE )
)
```

```DAX
Productos Clase A =
CALCULATE ( DISTINCTCOUNT ( dim_producto[producto_key] ), dim_producto[clase_abc] = "A" )
```

```DAX
Semaforo Devolucion =
SWITCH ( TRUE (),
    [Tasa Devolucion %] >= 0.10, "#B23A48",
    [Tasa Devolucion %] >= 0.03, "#E07A1F",
    "#2E8B57"
)
```
Rojo ≥ 10 %, naranja entre 3 % y 10 %, verde < 3 % (meta de referencia de la regla de negocio).

## 4. Clientes y mercados

```DAX
Clientes Nuevos =
VAR inicio = MIN ( dim_fecha[fecha] )
VAR fin = MAX ( dim_fecha[fecha] )
RETURN
    CALCULATE (
        DISTINCTCOUNT ( fact_ventas[cliente_key] ),
        fact_ventas[es_devolucion] = 0,
        FILTER (
            dim_cliente,
            dim_cliente[primera_compra] >= inicio
                && dim_cliente[primera_compra] <= fin
        )
    )
```
Clientes cuya primera compra cae dentro del periodo filtrado.

```DAX
Clientes Recurrentes = [Clientes Activos] - [Clientes Nuevos]
```

```DAX
% Ventas Segmento =
DIVIDE ( [Ventas Netas], CALCULATE ( [Ventas Netas], ALL ( dim_cliente[segmento_rfm] ) ) )
```

```DAX
Ventas Internacionales =
CALCULATE ( [Ventas Netas], dim_pais[mercado] = "Internacional" )
```

```DAX
% Internacional = DIVIDE ( [Ventas Internacionales], [Ventas Netas] )
```

## 5. Pronóstico de demanda

`fact_pronostico` contiene las 12 semanas de prueba del modelo (real vs. pronóstico) y `pronostico_proxima_semana` el pronóstico de la semana del 5-dic-2011.

```DAX
Demanda Real = SUM ( fact_pronostico[unidades] )
```

```DAX
Demanda Pronosticada = SUM ( fact_pronostico[pronostico] )
```

```DAX
Pronostico Base Media 4 = SUM ( fact_pronostico[base_media_4] )
```

```DAX
Error Absoluto = SUMX ( fact_pronostico, ABS ( fact_pronostico[error] ) )
```

```DAX
WAPE % = DIVIDE ( [Error Absoluto], [Demanda Real] )
```
Error por producto-semana como % de lo vendido. Formato: porcentaje, 1 decimal.

```DAX
WAPE Total Semanal % =
VAR semanas =
    ADDCOLUMNS (
        VALUES ( fact_pronostico[semana_inicio] ),
        "@real", CALCULATE ( SUM ( fact_pronostico[unidades] ) ),
        "@pron", CALCULATE ( SUM ( fact_pronostico[pronostico] ) )
    )
RETURN
    DIVIDE ( SUMX ( semanas, ABS ( [@pron] - [@real] ) ), SUMX ( semanas, [@real] ) )
```
Error del total semanal (los errores de los productos se compensan entre sí).

```DAX
RMSE Modelo = SQRT ( AVERAGEX ( fact_pronostico, fact_pronostico[error] ^ 2 ) )
```

```DAX
Sesgo % = DIVIDE ( [Demanda Pronosticada] - [Demanda Real], [Demanda Real] )
```

```DAX
Unidades Proxima Semana = SUM ( pronostico_proxima_semana[unidades_pronosticadas] )
```

```DAX
Variacion vs Promedio 4 Sem =
DIVIDE (
    SUM ( pronostico_proxima_semana[unidades_pronosticadas] )
        - SUM ( pronostico_proxima_semana[promedio_ultimas_4_semanas] ),
    SUM ( pronostico_proxima_semana[promedio_ultimas_4_semanas] )
)
```
Indica a compras si debe pedir más (+) o menos (−) que el ritmo reciente.
