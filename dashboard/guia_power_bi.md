# Guía para construir el dashboard en Power BI

**Responsable:** Juana · Resultado esperado: `dashboard/Dashboard_Equipo4.pbix` y las capturas de cada página en `dashboard/capturas/`.

El dashboard se arma sobre el **modelo estrella** que genera [`src/modelo_datos.py`](../src/modelo_datos.py) (diagrama en `reports/figures/bi_modelo_estrella.png`). Tiene **4 páginas**, una por audiencia, todas con filtros dinámicos.

---

## Paso 0. Preparar los datos

En la raíz del repositorio, con el entorno de Python activo:

```bash
python -m src.etl
jupyter nbconvert --to notebook --execute notebooks/04_modelo_predictivo.ipynb --output 04_modelo_predictivo.ipynb
python -m src.modelo_datos
```

Al final debe aparecer en `data/bi/`:

| Archivo | Filas aprox. | Tipo |
|---|---|---|
| `fact_ventas.csv` | 1.021.239 | Hechos |
| `dim_fecha.csv` | 739 | Dimensión |
| `dim_producto.csv` | 4.737 | Dimensión |
| `dim_cliente.csv` | 5.876 | Dimensión |
| `dim_pais.csv` | 43 | Dimensión |
| `fact_pronostico.csv` | 3.600 | Hechos (modelo) |
| `pronostico_proxima_semana.csv` | 300 | Tabla del modelo |
| `metricas_modelo.csv` | 6 | Tabla del modelo |

## Paso 1. Configuración regional (¡importante en Colombia!)

Los CSV usan **punto decimal** (18.52). Si Power BI está en español puede leer `18.52` como `1852`.

*Archivo → Opciones y configuración → Opciones → **Archivo actual → Configuración regional** → Configuración regional para importación = **Inglés (Estados Unidos)***.

Hazlo **antes** de cargar los datos.

## Paso 2. Cargar las tablas

1. *Inicio → Obtener datos → Texto/CSV* → elegir cada archivo de `data/bi/` → **Transformar datos**.
2. En Power Query revisar los tipos de columna:
   - `fecha`, `semana_inicio`, `primera_compra`, `ultima_compra`, `primera_venta`, `ultima_venta` → **Fecha**.
   - Claves `*_key`, `cantidad`, `unidades`, `R`, `F`, `M` → **Número entero**.
   - `importe`, `precio_unitario`, `monetario`, `pronostico`, `error`, `base_media_4`, `latitud`, `longitud` → **Número decimal**.
   - `factura`, `codigo_producto`, `cliente_id` → **Texto** (si Power BI los convierte en número, se pierden los que empiezan por letra).
3. *Cerrar y aplicar*.

## Paso 3. Modelo (vista de modelo)

1. Borrar las relaciones que Power BI haya detectado solo y crear estas (**uno a varios, filtro en una sola dirección**):

| Desde (1) | Hacia (*) |
|---|---|
| `dim_fecha[fecha_key]` | `fact_ventas[fecha_key]` |
| `dim_producto[producto_key]` | `fact_ventas[producto_key]` |
| `dim_cliente[cliente_key]` | `fact_ventas[cliente_key]` |
| `dim_pais[pais_key]` | `fact_ventas[pais_key]` |
| `dim_producto[producto_key]` | `fact_pronostico[producto_key]` |
| `dim_producto[producto_key]` | `pronostico_proxima_semana[producto_key]` |

2. **Marcar `dim_fecha` como tabla de fechas:** seleccionar la tabla → *Herramientas de tabla → Marcar como tabla de fechas* → columna `fecha`.
3. **Ordenar textos por número:** `dim_fecha[mes]` ordenar por `mes_num`; `dim_fecha[dia_semana]` ordenar por `dia_semana_num` (*Herramientas de columna → Ordenar por columna*).
4. Ocultar en la vista de informe todas las columnas `*_key`.
5. Categorías de datos: `dim_pais[pais]` → *País o región*; `latitud` → *Latitud*; `longitud` → *Longitud*.

## Paso 4. Medidas

*Inicio → Especificar datos* → crear una tabla vacía llamada `_Medidas` → Cargar. Crear dentro de ella todas las medidas de [`medidas_dax.md`](medidas_dax.md). Al final, borrar la columna vacía de `_Medidas` para que la tabla quede arriba con ícono de calculadora.

## Paso 5. Tema

*Vista → Temas → Buscar temas* → elegir `dashboard/tema_equipo4.json`.

## Paso 6. Páginas del dashboard

Lienzo 16:9. En todas las páginas: título arriba a la izquierda, segmentadores en una franja superior y nota de fuente al pie (*Fuente: Online Retail II (UCI), dic-2009 a dic-2011. Cifras en libras esterlinas*).

### Página 1 · Resumen ejecutivo (gerencia)

| Zona | Objeto visual | Campos |
|---|---|---|
| Filtros | Segmentador (mosaico) | `dim_fecha[anio]` |
| Filtros | Segmentador (lista desplegable) | `dim_fecha[mes]`, `dim_pais[region]`, `dim_pais[mercado]` |
| Fila de tarjetas | 6 tarjetas | `Ventas Netas`, `Var % Interanual` (color con `Color Variacion`), `Pedidos`, `Ticket Promedio`, `Clientes Activos`, `Tasa Devolucion %` (color con `Semaforo Devolucion`) |
| Centro | Gráfico de líneas | Eje: `dim_fecha[mes]` · Leyenda: `dim_fecha[anio]` · Valor: `Ventas Netas` |
| Derecha | Gráfico de barras agrupadas | Eje: `dim_fecha[dia_semana]` · Valor: `Pedidos` |
| Abajo | Mapa (burbujas) | Ubicación: `dim_pais[pais]` · Tamaño: `Ventas Netas` · Información sobre herramientas: `Ticket Promedio` |
| Abajo derecha | Tabla | `dim_fecha[temporada]`, `Ventas Netas`, `% Participacion Ventas` |

### Página 2 · Productos (compras y categoría)

| Zona | Objeto visual | Campos |
|---|---|---|
| Filtros | Segmentadores | `dim_fecha[anio]`, `dim_producto[clase_abc]`, `dim_pais[mercado]` |
| Tarjetas | 4 tarjetas | `Unidades Vendidas`, `Productos Clase A`, `Ventas Brutas`, `Tasa Devolucion %` |
| Izquierda | Barras horizontales (Top 10, filtro *N superior* = 10 por `Ventas Brutas`) | Eje: `dim_producto[descripcion]` · Valor: `Ventas Brutas` |
| Derecha | Gráfico de anillo | Leyenda: `dim_producto[clase_abc]` · Valor: `Ventas Brutas` |
| Abajo | Tabla con formato condicional | `dim_producto[descripcion]`, `dim_producto[clase_abc]`, `Ventas Brutas`, `Unidades Vendidas`, `Devoluciones`, `Tasa Devolucion %` (color de fondo con `Semaforo Devolucion`), `Ranking Producto` |

### Página 3 · Clientes y mercados (comercial y marketing)

| Zona | Objeto visual | Campos |
|---|---|---|
| Filtros | Segmentadores | `dim_fecha[anio]`, `dim_cliente[segmento_rfm]`, `dim_pais[region]` |
| Tarjetas | 4 tarjetas | `Clientes Activos`, `Clientes Nuevos`, `Clientes Recurrentes`, `% Internacional` |
| Izquierda | Barras | Eje: `dim_cliente[segmento_rfm]` · Valores: `Clientes Activos` y `% Ventas Segmento` |
| Derecha | Gráfico de columnas apiladas | Eje: `dim_fecha[anio_mes]` · Valores: `Clientes Nuevos`, `Clientes Recurrentes` |
| Abajo izquierda | Barras horizontales (Top 10, excluir United Kingdom con filtro de objeto visual) | Eje: `dim_pais[pais]` · Valor: `Ventas Netas` · Info: `Ticket Promedio` |
| Abajo derecha | Tabla | `dim_cliente[cliente_id]`, `dim_cliente[segmento_rfm]`, `dim_cliente[recencia_dias]`, `Pedidos`, `Ventas Netas` (filtro *N superior* = 15) |

### Página 4 · Pronóstico de demanda (inventario y operaciones)

| Zona | Objeto visual | Campos |
|---|---|---|
| Filtros | Segmentadores | `dim_producto[clase_abc]`, `dim_producto[descripcion]` (con búsqueda) |
| Tarjetas | 5 tarjetas | `Unidades Proxima Semana`, `WAPE Total Semanal %`, `WAPE %`, `RMSE Modelo`, `Sesgo %` |
| Centro | Gráfico de líneas | Eje: `fact_pronostico[semana_inicio]` · Valores: `Demanda Real`, `Demanda Pronosticada`, `Pronostico Base Media 4` (línea punteada) |
| Derecha | Barras | Eje: `metricas_modelo[modelo]` · Valor: `metricas_modelo[RMSE]` (ordenar ascendente) |
| Abajo | Tabla (lista de compras) | `pronostico_proxima_semana[descripcion]`, `unidades_pronosticadas`, `rango_minimo`, `rango_maximo`, `promedio_ultimas_4_semanas`, `Variacion vs Promedio 4 Sem` (iconos ▲▼ con formato condicional) |
| Nota | Cuadro de texto | "El pronóstico de cada producto puede desviarse; planear con el rango mínimo-máximo. Para el total de la bodega el error histórico es ~12,5 %." |

## Paso 7. Interactividad

1. **Sincronizar segmentadores** de año entre las páginas 1 a 3 (*Vista → Sincronizar segmentaciones*).
2. **Obtener detalles (drill-through):** en la página 2, agregar `dim_producto[descripcion]` al panel *Obtener detalles*; así, clic derecho sobre un producto en cualquier página → *Obtener detalles → Productos*.
3. **Información sobre herramientas:** en el gráfico de líneas de la página 1, agregar `Pedidos` y `Ticket Promedio` al campo *Información sobre herramientas*.
4. **Navegación:** botones con forma de pestaña en cada página (*Insertar → Botones → Navegador de páginas*).
5. Dejar activadas las interacciones de filtro cruzado entre objetos visuales (valor predeterminado).

## Paso 8. Verificar con los valores de control

Sin filtros aplicados, las tarjetas deben mostrar lo mismo que la sección 7 del notebook [`03_modelo_datos_bi.ipynb`](../notebooks/03_modelo_datos_bi.ipynb):

| Medida | Valor esperado |
|---|---|
| Ventas Netas | £18.909.854 |
| Ventas Brutas | £19.380.627 |
| Devoluciones | £470.773 |
| Tasa Devolucion % | 2,43 % |
| Pedidos | 39.513 |
| Ticket Promedio | £490 |
| Clientes Activos | 5.852 |
| Unidades Vendidas | 10.922.235 |
| Ventas Netas con año 2011 y meses ene-nov | £8.572.276 |
| Var % Interanual con año 2011 y meses ene-nov | +2,5 % |
| Demanda Real (página 4) | 424.264 |
| WAPE % | 55,4 % |
| WAPE Total Semanal % | 12,5 % |
| RMSE Modelo | 164,85 |
| Sesgo % | −2,6 % |
| Unidades Proxima Semana | 34.963 |

Si una cifra no coincide, revisar en este orden: configuración regional (paso 1), tipos de columna (paso 2), relaciones (paso 3) y la fórmula de la medida.

## Paso 9. Guardar y entregar

1. Guardar como `dashboard/Dashboard_Equipo4.pbix`.
2. Exportar una captura de cada página en PNG a `dashboard/capturas/` con estos nombres: `1_resumen_ejecutivo.png`, `2_productos.png`, `3_clientes_mercados.png`, `4_pronostico_demanda.png`.
3. (Opcional) *Archivo → Exportar → Exportar a PDF* para tener una versión que se abre sin Power BI.
