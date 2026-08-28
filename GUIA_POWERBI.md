# Guía de Power BI — lo mínimo para cubrir OE4

Tiempo: 2-3 h. Coste: 0 € (Power BI Desktop es gratuito, solo Windows).

> Si no tienes Windows: usa una máquina virtual, o sustituye Power BI por
> **Metabase en Docker** (gratis, multiplataforma) y declara el cambio en la
> memoria. Un cuadro de mando es un cuadro de mando; la herramienta es secundaria.

---

## 1. Conectar (15 min) — con el workgroup aún encendido

1. Power BI Desktop → **Obtener datos** → busca **Amazon Redshift**.
2. Servidor: tu endpoint con el puerto, `tfm-wg.xxxxx.eu-west-1.redshift-serverless.amazonaws.com:5439`
3. Base de datos: `dev`
4. **Modo: Importar.** No DirectQuery, que factura con cada clic.
5. Usuario `admin` y tu contraseña.
6. Selecciona `fact_servicio`, `dim_zona`, `dim_tiempo`, `dim_operador` → **Cargar**.
7. Cuando termine de importar: **vete a AWS y borra el workgroup.** Ya no lo necesitas.

## 2. Modelo (20 min)

Vista *Modelo*. Crea estas relaciones (arrastrando de la dimensión al hecho):

- `dim_tiempo[sk_tiempo]` → `fact_servicio[sk_tiempo]`
- `dim_zona[sk_zona]` → `fact_servicio[sk_zona_origen]`
- `dim_operador[sk_operador]` → `fact_servicio[sk_operador]`

Todas de **uno a varios**, dirección **simple**.

## 3. Medidas DAX (15 min)

Botón *Nueva medida*, una por una:

```
N Servicios = COUNTROWS(fact_servicio)

Duracion Media = AVERAGE(fact_servicio[duracion_min])

Velocidad Media = AVERAGE(fact_servicio[velocidad_kmh])

Desviacion ETA Media = AVERAGE(fact_servicio[desviacion_eta_pct])

Factor Rodeo Medio = AVERAGE(fact_servicio[factor_rodeo])

Servicios Retrasados = 
CALCULATE(COUNTROWS(fact_servicio), fact_servicio[desviacion_eta_pct] > 20)

Pct Retrasados = DIVIDE([Servicios Retrasados], [N Servicios], 0)
```

## 4. Vista 1 — Panorámica de flota (45 min)

- Cuatro **tarjetas** arriba: `N Servicios`, `Duracion Media`, `Velocidad Media`, `Pct Retrasados`.
- **Gráfico de líneas**: eje `dim_tiempo[fecha]`, valor `Duracion Media`.
- **Gráfico de barras**: eje `fact_servicio[franja_horaria]`, valor `N Servicios`.
- **Segmentación** por `dim_zona[distrito]`.

## 5. Vista 2 — Corredores (45 min)

- **Tabla**: filas `dim_zona[nombre_zona]` y `fact_servicio[franja_horaria]`;
  valores `N Servicios`, `Duracion Media`, `Desviacion ETA Media`, `Factor Rodeo Medio`.
- Ordena por `Desviacion ETA Media` descendente: arriba salen tus peores corredores.
- **Gráfico de dispersión**: eje X `Duracion Media`, eje Y `Factor Rodeo Medio`,
  detalle `dim_zona[nombre_zona]`, tamaño `N Servicios`.

## 6. Capturas (15 min)

Pantalla completa, tecla Windows + Shift + S. Guarda en `evidencias/`
como `powerbi_vista1.png` y `powerbi_vista2.png`.

En Overleaf van al Anexo E, sustituyendo el `[PENDIENTE]` correspondiente:

```latex
\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{imagenes/powerbi_vista1.png}
\caption{Vista panorámica de flota del cuadro de mando.}
\end{figure}
```

## 7. Qué escribir en la memoria

Con la tabla de la vista 2 delante, mira los tres peores corredores y escribe dos
párrafos en la sección 4.7.4: qué zonas y franjas concentran la mayor desviación
sobre el ETA de referencia, y si el factor de rodeo apunta a un problema de ruta
o de congestión. **Ese es el hallazgo analítico del trabajo**, y es lo que un
tribunal te va a preguntar.
