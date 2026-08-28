# Plan de ejecución del TFM

**Pablo Martín Esteban** — Máster en Análisis de Datos Masivos, UEM

Este documento es la hoja de ruta para completar el TFM: qué hacer, en qué orden,
qué produce cada paso y a qué hueco `[PENDIENTE:]` de la memoria corresponde.

---

## Antes de nada: tres decisiones que condicionan todo lo demás

Tómalas ahora, no a mitad de camino. Cambiarlas después cuesta semanas.

### Decisión 1 — Alcance del conjunto de datos

Este es el punto donde más TFM de Big Data se atascan. El cálculo:

| Alcance | Registros aprox. | Tamaño en MongoDB | ¿Cabe en Atlas M0 gratuito (512 MB)? |
|---|---|---|---|
| 1 mes | ~3 M | ~1,5–2 GB | **No** |
| 3 meses | ~9 M | ~5–6 GB | No — necesitas M10 |
| 12 meses | ~38 M | ~20–25 GB | No — necesitas M20 o superior |

**Recomendación: 3 meses de `yellow` (enero–marzo 2023) sobre un clúster M10.**
Son ~9 millones de registros, suficiente para defender "millones de registros" con
propiedad, y manejable en tiempo y coste. Documenta esta decisión de acotación en la
sección 4.2.3 de la memoria como lo que es: una decisión de ingeniería justificada,
no una limitación que ocultar. Un tribunal valora más un alcance acotado y bien
argumentado que uno inflado y a medio ejecutar.

Si el M10 no es viable económicamente, la alternativa honesta es cargar **1 mes**
en Mongo y dejarlo dicho.

### Decisión 2 — Dónde ejecutas Spark

**Ejecuta Spark en local**, con `pip install pyspark` sobre tu portátil. Para 9 millones
de filas es de sobra, no cuesta nada y es perfectamente defendible. En la memoria lo
justificas: el pipeline está escrito con la API de DataFrames, es idéntico en local y en
clúster, y la elección del entorno de ejecución no altera la lógica.

No montes un clúster EMR salvo que quieras específicamente medir el escalado horizontal.
Si lo haces, enciéndelo un día, toma las medidas y apágalo.

### Decisión 3 — Control de coste en AWS

Antes de crear nada en AWS:

1. Ve a **Billing → Budgets** y crea un presupuesto con alerta por correo (p. ej. 20 €).
2. Usa **Redshift Serverless**, no un clúster provisionado, y configúralo con la capacidad
   base mínima.
3. **Crea Redshift solo cuando llegues a la Fase 4**, toma todas las medidas en una o dos
   sesiones seguidas, y **bórralo después** guardando un snapshot.
4. Consulta la calculadora de precios de AWS antes de crear el recurso: las condiciones y
   los niveles gratuitos cambian, así que no te fíes de lo que leas en foros antiguos.

Lo mismo para MongoDB Atlas: pausa el clúster cuando no lo uses.

---

## Fase 0 — Preparación (2–3 días)

- [ ] Crear repositorio Git y subir el esqueleto de código.
- [ ] Crear entorno virtual e instalar `requirements.txt`.
- [ ] Instalar Java 11 o 17 y comprobar que `pyspark` arranca.
- [ ] Crear cuenta de MongoDB Atlas y de AWS. Configurar la alerta de presupuesto.
- [ ] Crear un **cuaderno de bitácora** (un simple `bitacora.md` en el repo).

> **La bitácora es lo más importante de esta fase.** Apunta cada ejecución con fecha,
> configuración, tiempo que tardó y cualquier cosa que se rompió. Reproducir estas medidas
> dentro de dos meses, cuando estés redactando, cuesta dinero y días. Anotarlas ahora
> cuesta treinta segundos. La mitad de los huecos `[PENDIENTE:]` de tu memoria se rellenan
> desde la bitácora.

---

## Fase 1 — Datos y exploración (1 semana)

- [ ] `python src/01_descarga_datos.py`
- [ ] Análisis exploratorio en un notebook: distribuciones de duración, distancia y
      velocidad implícita; porcentaje de nulos por campo; valores imposibles.
- [ ] **Calibrar los umbrales** de `config.py` con lo que veas. No copies mis valores
      por defecto sin mirarlos: justifícalos con histogramas.
- [ ] Guardar 3–4 gráficas del EDA en `evidencias/`.

**Rellena en la memoria:** sección 4.2.3 (alcance, período, número de registros),
tabla 4.2 (campos), y la justificación de umbrales de la sección 4.2.5.1.

---

## Fase 2 — Capa Bronze (1–2 semanas)

- [ ] Crear clúster M10 en Atlas. Restringir el acceso de red a tu IP.
- [ ] `python src/02_ingesta_bronze.py`
- [ ] Verificar que el conteo en Mongo coincide con el del origen.
- [ ] Capturar pantalla de Atlas: tamaño de colección, índices, métricas.
- [ ] Exportar un documento real de ejemplo para el **Anexo A**.

**Evidencia generada:** `evidencias/informe_ingesta_bronze.json`
**Rellena en la memoria:** sección 4.7.1 (resultados OE1), nivel del clúster en 4.2.4,
Anexo A.

---

## Fase 3 — Capa Silver (2–3 semanas) ← *el corazón del TFM*

- [ ] `python src/03_dimension_zonas.py` (prueba primero con `con_osm=False`, luego con OSM).
- [ ] Ejecutar el pipeline sobre **un solo mes** hasta que funcione limpio.
- [ ] Revisar el informe de calidad: ¿la tasa de rechazo tiene sentido? Si rechazas el 40 %,
      tus umbrales están mal, no los datos.
- [ ] Ejecutar sobre el alcance completo y **cronometrarlo**.
- [ ] Guardar una gráfica de barras con los rechazos por regla.

**Evidencia generada:** `evidencias/informe_calidad_silver.json`
**Rellena en la memoria:** sección 4.7.2, tabla 4.3 (con los conteos reales), Anexo B.

---

## Fase 4 — Capa Gold (1–2 semanas)

- [ ] `spark-submit src/05_preparar_gold.py`
- [ ] Crear bucket S3 y rol IAM con permiso de lectura para Redshift.
- [ ] `aws s3 sync datos/gold/ s3://TU_BUCKET/silver/`
- [ ] Crear Redshift Serverless. Ejecutar `01_ddl_gold.sql` y `02_carga_copy.sql`.
- [ ] Cargar **también** `fact_servicio_control` (la tabla sin diseño físico).
- [ ] `python src/06_medir_latencia.py`

> El experimento optimizada-frente-a-control es el resultado más sólido que vas a poder
> presentar. Es una comparación limpia, con una única variable, sobre los mismos datos y la
> misma máquina. Si el tribunal solo se lleva un número de tu defensa, que sea este.

**Evidencia generada:** `evidencias/latencia_consultas.json`
**Rellena en la memoria:** sección 4.7.3, figura del modelo en estrella, Anexo C y D.

---

## Fase 5 — Visualización (1 semana)

- [ ] Power BI Desktop → Obtener datos → Amazon Redshift → modo **Importación**.
- [ ] Reconstruir el esquema en estrella en el modelo semántico.
- [ ] Tres vistas: panorámica de flota / análisis de corredores / detalle temporal.
- [ ] Medidas DAX: desviación media sobre ETA, factor de rodeo medio, servicios por franja.
- [ ] Capturas a resolución alta de las tres vistas.

> **Ojo a la coherencia:** en la memoria escribí que usas modo híbrido (importación +
> consulta directa). Si acabas usando solo importación —que es lo razonable por coste—,
> corrige ese párrafo de la sección 4.2.7. Que lo escrito coincida con lo hecho.

**Rellena en la memoria:** sección 4.2.7, sección 4.7.4, Anexo E.

---

## Fase 6 — Evaluación comparativa (3–4 días)

- [ ] Levantar PostgreSQL local en Docker como línea base.
- [ ] Cargar el mismo conjunto de hechos.
- [ ] Ejecutar las mismas cinco consultas y cronometrarlas.
- [ ] Calcular el coste mensual real de la infraestructura con la calculadora de AWS.

**Rellena en la memoria:** sección 4.7.5, tabla 4.5 (presupuesto), sección 4.6 (viabilidad).

---

## Fase 7 — Redacción final (2 semanas)

- [ ] `grep -rn "pendiente{" *.tex capitulos/` y cerrar los 39 huecos uno a uno.
- [ ] Sustituir las dos figuras marcador (`logo_ue.png`) por el diagrama de arquitectura y
      el modelo en estrella. Hazlos en draw.io y **expórtalos a PDF**, no a PNG.
- [ ] Escribir la discusión y las conclusiones **con los resultados delante**, no de memoria.
- [ ] Redactar las conclusiones personales. Es la única sección donde se espera tu voz:
      aprovéchala en lugar de rellenarla con fórmulas.
- [ ] Cuando termines: en `datos.tex`, cambiar la macro a `\newcommand{\pendiente}[1]{}`
      para que no quede nada en rojo.
- [ ] Revisar coherencia de fechas: el anteproyecto pone curso 2025-2026 y `datos.tex`
      pone 2026-2027. Decide cuál es y unifícalo.
- [ ] Última pasada: índices de figuras y tablas correctos, referencias sin `[?]`,
      todas las tablas y figuras citadas en el texto.

---

## Orden de prioridad si vas justo de tiempo

Si en algún momento tienes que recortar, recorta en este orden inverso de importancia:

1. **Intocable:** Bronze → Silver → Gold funcionando con datos reales, informe de calidad,
   y la comparativa de latencia optimizada/control.
2. **Muy importante:** cuadro de mando con las tres vistas.
3. **Sacrificable:** el enriquecimiento con OSMnx (puedes quedarte solo con los centroides
   de las zonas y explicar por qué).
4. **Sacrificable:** la línea base con PostgreSQL (OE5 puede reducirse a la comparativa
   optimizada/control dentro de Redshift, que ya es una evaluación válida).

Si sacrificas algo, **dilo en la memoria** en la sección de desviaciones. Un alcance
recortado y declarado es profesional; uno recortado y disimulado se nota en la defensa.

---

## Un consejo sobre el calendario

Tu anteproyecto planificaba Gold para agosto y visualización para septiembre. Estamos a
mediados de agosto. Si aún no has empezado la implementación, siéntate con tu director esta
semana y replanificad, en lugar de intentar recuperar el retraso a base de recortar la fase
Silver, que es la que más peso técnico aporta al trabajo. Es una conversación mucho más
fácil de tener ahora que en octubre.
