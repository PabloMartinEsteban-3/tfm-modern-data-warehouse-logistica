# Plan de emergencia — del 20 al 30 de agosto

**Coste: 10-13 €. Tiempo: ~95 horas en 10 días (unas 10 h/día).**

Esto solo funciona si tienes los 10 días razonablemente libres. Léete el apartado
final antes de empezar: hay una conversación que tienes que tener hoy.

---

## Recortes (decididos, no negociables)

| Fuera | Por qué se puede |
|---|---|
| **3 meses → 1 mes de datos** | ~3 M registros siguen siendo "millones de registros" |
| **OSMnx entero** | Los centroides salen del shapefile de la TLC. Se declara y ya |
| **Línea base PostgreSQL (OE5)** | La comparación optimizada/control ya es una evaluación válida |
| **Tercera vista del dashboard** | Dos vistas cubren OE4 |
| **Índice geoespacial 2dsphere** | No lo usa ninguna consulta del cuadro de mando |

Todo lo recortado va declarado en la sección de desviaciones. Un alcance acotado y
declarado se lee como criterio; uno disimulado se nota en la defensa.

---

## Día a día

### Día 1 — Miércoles 20 (hoy) · 8 h
- [ ] Escribir a Eduardo (ver apartado final). **Primero esto.**
- [ ] `git init`, entorno virtual, `pip install -r requirements.txt`, Java 17.
- [ ] `docker compose up -d` → MongoDB en local.
- [ ] `config.py`: `MESES = ["2023-01"]` y nada más.
- [ ] `python src/01_descarga_datos.py`
- [ ] Abrir el Parquet en pandas, mirar las columnas, anotar el número de registros.

### Día 2 — Jueves 21 · 10 h
- [ ] Histogramas rápidos de duración, distancia y velocidad. **1 hora, no más.**
- [ ] Ajustar los umbrales de `config.py`. Guardar 3 gráficas en `evidencias/`.
- [ ] `python src/02_ingesta_bronze.py` → Mongo local.
- [ ] Crear Atlas M0 gratuito, cargar ~100.000 documentos, capturas de la consola.
- [ ] Exportar un documento real para el Anexo A.

### Día 3 — Viernes 22 · 10 h ← **el día de riesgo**
- [ ] Levantar Spark con el conector de MongoDB.
- [ ] **PUERTA DE CONTROL: si a las 4 horas el conector no lee, párate.**
      Ejecuta `python src/04b_export_bronze.py`, pon `FUENTE_SILVER = "export"`
      en `config.py` y sigue. Ya está programado el camino alternativo.
- [ ] Que el pipeline llegue al final sin reventar. Fino ya lo pondrás mañana.

### Día 4 — Sábado 23 · 10 h
- [ ] `python src/03_dimension_zonas.py` con **`con_osm=False`**.
- [ ] Revisar el informe de calidad. Si rechazas >20 %, mira el aplanado, no los datos.
- [ ] Comprobar que ETA, desviación y factor de rodeo dan valores plausibles.
- [ ] Ejecutar la versión definitiva. **Cronometrar y guardar el informe.**

### Día 5 — Domingo 24 · 10 h
- [ ] `spark-submit src/05_preparar_gold.py`
- [ ] PostgreSQL local en Docker. Cargar los Parquet, adaptar el DDL, probar las
      5 consultas y `06_medir_latencia.py`.
- [ ] **Cazar aquí todas las erratas de SQL.** Es gratis y te ahorra la mitad de
      la factura de mañana.

### Día 6 — Lunes 25 · 8 h · **~10 €** (único día que gastas)
- [ ] AWS Budget de 20 €. Workgroup Serverless a **4 RPU**.
- [ ] **Usage limit: 20 RPU-horas, acción "desactivar consultas".** No opcional.
- [ ] `aws s3 sync` → DDL → COPY → tabla de control → ANALYZE → VACUUM.
- [ ] `python src/06_medir_latencia.py` → guardar JSON.
- [ ] Capturas de consola. **No borres el workgroup todavía** (lo necesitas mañana).

### Día 7 — Martes 26 · 10 h
- [ ] Power BI, **modo Importación**. Importar las tablas.
- [ ] **Borrar el workgroup de Redshift.** A partir de aquí no gastas más.
- [ ] Modelo en estrella + medidas DAX + dos vistas.
- [ ] Capturas a buena resolución.

### Día 8 — Miércoles 27 · 10 h
- [ ] Sección 4.7 completa con los números reales de `evidencias/`.
- [ ] Tablas de calidad, de latencia y de presupuesto en LaTeX.
- [ ] Anexos A, B, C, D, E con el código y las capturas reales.

### Día 9 — Jueves 28 · 10 h
- [ ] Diagrama de arquitectura y modelo en estrella en draw.io → **exportar a PDF**.
- [ ] Sustituir los dos `logo_ue.png` marcadores.
- [ ] Discusión, conclusiones y **sección de desviaciones** (declara los 5 recortes).
- [ ] Conclusiones personales. En primera persona, es tu voz.

### Día 10 — Viernes 29 · 8 h
- [ ] `grep -rn "pendiente{" *.tex capitulos/` → debe dar **cero**.
- [ ] `\newcommand{\pendiente}[1]{}` en `datos.tex`.
- [ ] Compilar tres veces. Referencias sin `[?]`, figuras y tablas todas citadas.
- [ ] Coherencia de fechas y curso académico.
- [ ] Leerla entera de una sentada.
- [ ] **Enviar.** El día 30 queda de colchón.

---

## Puertas de control

Si a estas alturas no estás donde toca, recorta más o pide prórroga. No sigas
esperando recuperar el tiempo, porque no se recupera.

| Momento | Debes tener | Si no |
|---|---|---|
| Fin día 3 | Silver ejecutándose de principio a fin | Plan B del export, sin dudarlo |
| Fin día 5 | Parquet Gold generado y SQL probado en Postgres | Salta la tabla de control |
| Fin día 7 | Dashboard con 2 vistas y capturas | Deja 1 vista y a redactar |
| Fin día 8 | Sección 4.7 cerrada | Avisa a Eduardo de que llegas justo |

**Los días 8, 9 y 10 son intocables.** Si el día 7 el pipeline no está, entregas
lo que tengas y lo declaras. Una memoria completa sobre un alcance reducido aprueba;
una memoria a medias sobre un alcance ambicioso, no.

---

## La conversación de hoy

Escríbele a Eduardo esta mañana. No para pedir permiso, sino porque necesitas dos
datos que cambian el plan:

1. **¿Qué se entrega exactamente el 30?** ¿La memoria final, un borrador, o la
   memoria con defensa posterior? Si la defensa es en septiembre u octubre, tienes
   más aire del que crees para pulir.
2. **¿Hay convocatoria posterior?** En muchos másteres la hay en diciembre o febrero.
   Saberlo no es rendirse: es tener una red. Entregar algo a medias quema la
   convocatoria igual que no entregar, y con peor sabor.

Dile también los recortes que has decidido. Que los sepa por ti antes de leerlos en
la memoria.

---

## Y lo que no te voy a endulzar

95 horas en 10 días son 10 al día sin fallos, sin imprevistos y sin otras
obligaciones. Si el día 3 el conector se atasca y no aplicas el plan B, o si el
portátil dice que no con 3 millones de filas en Spark, se te va el calendario.

Esto da para un **aprobado digno**: arquitectura completa, datos reales, resultados
medidos y memoria cerrada. No da para brillante, y no pasa nada — dijiste que
querías aprobar.

Y si el día 5 ves que no llegas, la decisión inteligente no es apretar más: es
llamar a Eduardo y hablar de la siguiente convocatoria con el trabajo ya medio hecho.
