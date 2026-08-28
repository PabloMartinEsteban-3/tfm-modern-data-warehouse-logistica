# Ruta mínima para aprobar el TFM

Versión sin florituras: lo imprescindible, en bloques pequeños, con el coste y el
tiempo declarados por adelantado.

---

## Los dos números

### Coste: 10–15 €

| Concepto | Coste |
|---|---|
| MongoDB (Docker local + Atlas M0 gratuito) | 0 € |
| Spark (local) | 0 € |
| S3 (1–2 GB unas semanas) | ~0,20 € |
| Redshift Serverless (4–6 h activas) | 8–13 € |
| Power BI Desktop, Overleaf, datasets | 0 € |
| **Total** | **10–15 €** |

Si te aplica el crédito de prueba de Redshift Serverless, baja a menos de 1 €.
Verifícalo en la página de precios de AWS antes de crear el workgroup.

### Tiempo: 180–220 horas de trabajo real

| Bloque | Horas |
|---|---|
| Preparación del entorno | 6 |
| Datos y exploración | 15 |
| Capa Bronze | 20 |
| Capa Silver | 40 |
| Capa Gold | 25 |
| Power BI | 20 |
| Evaluación | 10 |
| Redacción y figuras | 45 |
| Imprevistos y depuración | 20 |
| **Total** | **~200 h** |

**Lo que eso significa en calendario:**

| Si dedicas | Terminas en | Fecha aproximada |
|---|---|---|
| 8 h/semana | 25 semanas | mediados de febrero 2027 |
| 12 h/semana | 17 semanas | mediados de diciembre 2026 |
| 20 h/semana | 10 semanas | finales de octubre 2026 |

> **Haz esta cuenta hacia atrás desde tu fecha de convocatoria antes de empezar.**
> Si tu defensa es en octubre o noviembre de 2026, necesitas 20 h/semana desde ya y
> conviene que se lo digas a Eduardo esta semana. Si tu convocatoria es del curso
> 2026-2027 y tienes hasta febrero, con 8-10 h/semana vas holgado. Resolver esta
> ambigüedad es lo primero que tienes que hacer: el `datos.tex` pone curso 2026-2027
> y el anteproyecto pone 2025-2026, y esas dos cosas implican planes muy distintos.

---

## Qué es "lo mínimo para aprobar"

**Imprescindible (no se toca):**
- Pipeline Bronze → Silver → Gold funcionando con datos reales.
- Informe de calidad de la capa Silver con números reales.
- Modelo en estrella cargado en Redshift y consultas ejecutándose.
- Un cuadro de mando en Power BI, aunque sea de una sola vista.
- **La memoria completa, sin huecos.**

**Recortable si vas justo, en este orden:**
1. Enriquecimiento con OSMnx (quédate con los centroides de zona y explica por qué).
2. Línea base con PostgreSQL (OE5 se cubre con la comparación optimizada/control).
3. Tercera vista del cuadro de mando.
4. Tabla de control en Redshift (es barata y aporta mucho, sacrifícala la última).

> **El riesgo real no es técnico.** La mayoría de los TFM que suspenden o rozan el
> aprobado no lo hacen por un pipeline flojo, sino por una memoria acabada con prisa
> la última semana. Tienes la memoria ya redactada al 90 %: eso es una ventaja enorme,
> pero solo si cierras los 39 huecos con calma. Reserva las 45 horas de redacción y
> no las canibalices para "mejorar" el código.

---

## Los 20 bloques, en orden

Cada bloque son 8-12 horas. Uno por semana a ritmo tranquilo.

### Bloque 1 — Decidir el calendario (2 h)
- [ ] Confirmar fecha de convocatoria y curso académico.
- [ ] Reunión con Eduardo: replanificación y visto bueno al cambio de Atlas a local.
- [ ] Fijar tu ritmo semanal y bloquearlo en el calendario.

### Bloque 2 — Entorno (6 h)
- [ ] Repositorio Git con el esqueleto de código.
- [ ] Entorno virtual, `requirements.txt`, Java 17.
- [ ] `docker compose up -d` y comprobar que MongoDB responde.
- [ ] Crear `bitacora.md`. **Anota cada ejecución desde el primer día.**

### Bloque 3 — Descarga y primer vistazo (8 h)
- [ ] `python src/01_descarga_datos.py` con **un solo mes** en `config.MESES`.
- [ ] Abrir el Parquet en pandas y mirarlo de verdad.
- [ ] Anotar: número de registros, columnas, rango de fechas.

### Bloque 4 — Exploración y umbrales (10 h)
- [ ] Histogramas de duración, distancia y velocidad implícita.
- [ ] Porcentaje de nulos por columna.
- [ ] **Ajustar los umbrales de `config.py` a lo que veas.** No copies los míos a ciegas.
- [ ] Guardar 3-4 gráficas en `evidencias/`.

### Bloque 5 — Bronze, un mes (10 h)
- [ ] `python src/02_ingesta_bronze.py` contra Mongo local.
- [ ] Verificar que el conteo coincide.
- [ ] Revisar el JSON de evidencias.

### Bloque 6 — Bronze en Atlas M0 (8 h)
- [ ] Crear clúster M0 gratuito.
- [ ] Cargar ~300.000 documentos (subconjunto).
- [ ] Capturas de la consola de Atlas: colección, índices, métricas.
- [ ] Exportar un documento real para el Anexo A.

### Bloque 7 — Ampliar a 3 meses (6 h)
- [ ] Descargar los otros dos meses y reingerir en local.
- [ ] Cronometrar. Anotar en la bitácora.

### Bloque 8 — Dimensión de zonas (10 h)
- [ ] `python src/03_dimension_zonas.py` con `con_osm=False` primero.
- [ ] Si funciona y tienes tiempo, activar OSMnx. Si da guerra, **déjalo en False**
      y anota la decisión. Es el primer recortable de la lista.

### Bloque 9 — Silver, primera pasada (12 h)
- [ ] Levantar Spark con el conector de Mongo. *Aquí es donde se pierde tiempo con
      las versiones del conector: reserva paciencia.*
- [ ] Ejecutar el pipeline sobre un mes.
- [ ] Que no reviente. Todavía no importa que esté fino.

### Bloque 10 — Silver, calidad (12 h)
- [ ] Revisar el informe: ¿la tasa de rechazo tiene sentido?
- [ ] Si rechazas más del 15 %, revisa tus umbrales antes que los datos.
- [ ] Gráfica de rechazos por regla.

### Bloque 11 — Silver, KPIs y volumen completo (12 h)
- [ ] Comprobar que ETA, desviación y factor de rodeo dan valores plausibles.
- [ ] Ejecutar sobre los 3 meses. **Cronometrar.**
- [ ] Guardar el informe definitivo.

### Bloque 12 — Preparar Gold (8 h)
- [ ] `spark-submit src/05_preparar_gold.py`.
- [ ] Verificar filas y claves subrogadas.

### Bloque 13 — Ensayo en PostgreSQL (10 h) ← *el bloque que te ahorra dinero*
- [ ] PostgreSQL local en Docker.
- [ ] Cargar los Parquet y ejecutar el DDL adaptado.
- [ ] Probar las 5 consultas de referencia y `06_medir_latencia.py`.
- [ ] Cazar todas las erratas de SQL aquí, que es gratis.

### Bloque 14 — Redshift: la sesión de carga (6 h, ~4 €)
- [ ] AWS Budget de 20 €. Workgroup 4 RPU. **Usage limit de 20 RPU-horas con acción
      desactivar.** Este paso no es opcional.
- [ ] `aws s3 sync`, DDL, COPY, ANALYZE, VACUUM.
- [ ] Cargar también la tabla de control.
- [ ] `python src/06_medir_latencia.py`.
- [ ] Capturas de consola. **Borrar el workgroup al terminar.**

### Bloque 15 — Power BI, conexión (8 h, ~2 €)
- [ ] Levantar el workgroup. Conectar en **modo Importación**.
- [ ] Importar las tablas. **Desconectar y borrar el workgroup.**
- [ ] A partir de aquí trabajas offline y Redshift no factura.

### Bloque 16 — Power BI, cuadro de mando (12 h)
- [ ] Modelo semántico en estrella.
- [ ] Medidas DAX básicas.
- [ ] Vista panorámica + vista de corredores. La tercera si da tiempo.
- [ ] Capturas a buena resolución.

### Bloque 17 — Rellenar resultados (12 h)
- [ ] Sección 4.7 completa con los números de `evidencias/`.
- [ ] Tablas 4.3 y de latencia en LaTeX.
- [ ] Tabla 4.5 del presupuesto con los importes reales.

### Bloque 18 — Figuras (8 h)
- [ ] Diagrama de arquitectura en draw.io → exportar a **PDF**.
- [ ] Modelo en estrella → PDF.
- [ ] Sustituir los dos marcadores `logo_ue.png`.

### Bloque 19 — Discusión y conclusiones (12 h)
- [ ] Escribir con los resultados delante, no de memoria.
- [ ] Sección de desviaciones: declarar Atlas local, OSMnx si lo recortaste, etc.
- [ ] Conclusiones personales en primera persona. Es tu voz, aprovéchala.

### Bloque 20 — Cierre (12 h)
- [ ] `grep -rn "pendiente{" *.tex capitulos/` → debe dar cero.
- [ ] `\newcommand{\pendiente}[1]{}` en `datos.tex`.
- [ ] Revisar: referencias sin `[?]`, todas las figuras y tablas citadas en el texto,
      fechas y curso coherentes.
- [ ] Leerla entera de una sentada. En papel si puedes.
- [ ] Enviar a Eduardo con margen para que la revise.

---

## Semáforo: cuándo pedir ayuda

- **Bloque 9 se te va de tres sesiones** → el conector de Spark/Mongo te está ganando.
  Escríbeme o pregunta en clase antes de perder dos semanas.
- **Tasa de rechazo por encima del 25 %** → hay algo mal en el aplanado, no en los datos.
- **Llegas al bloque 14 con menos de 4 semanas para la entrega** → recorta ya por la
  lista de recortables y protege las 45 horas de redacción.
- **La factura de AWS pasa de 15 €** → para, mira Cost Explorer y averigua qué está
  encendido antes de seguir.
