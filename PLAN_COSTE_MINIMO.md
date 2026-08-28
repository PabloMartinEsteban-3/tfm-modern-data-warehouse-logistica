# Plan de coste mínimo — techo de 30 €

Objetivo: completar el TFM sin que la factura pase de 30 €, manteniendo Redshift
(que está en el título del trabajo y no se puede quitar sin hablar con el director).

**Coste esperado: 10–15 €.** El margen sobra a propósito.

---

## Arquitectura ajustada al presupuesto

| Capa | Antes | Ahora | Coste |
|---|---|---|---|
| Bronze | MongoDB Atlas M10 | **MongoDB local en Docker** (volumen completo) + **Atlas M0 gratuito** (subconjunto de demostración) | **0 €** |
| Silver | Spark local | Spark local (sin cambios) | **0 €** |
| Staging | S3 | S3, 1–2 GB durante unas semanas | **~0,20 €** |
| Gold | Redshift Serverless | Redshift Serverless 4 RPU, sesiones acotadas | **8–15 €** |
| Visualización | Power BI Desktop | Power BI Desktop, **modo Importación** | **0 €** |
| Memoria | Overleaf | Overleaf plan gratuito | **0 €** |

El único grifo abierto es Redshift. Todo lo que sigue va de cerrarlo bien.

---

## Por qué MongoDB local no debilita el trabajo

Tu objetivo OE1 dice literalmente "desplegar un clúster de MongoDB Atlas". La solución
que preserva ese objetivo al pie de la letra y cuesta cero:

1. **Despliega un clúster M0 gratuito en Atlas** y carga en él un subconjunto de unos
   300.000 documentos. Es gratis para siempre y te da capturas reales de la consola de
   Atlas, índices operativos y un documento auténtico para el Anexo A.
2. **Ejecuta el volumen completo contra la instancia local en Docker**, con configuración
   equivalente y el mismo código.

En la memoria lo declaras tal cual, en la sección 4.2.4 y en la de desviaciones: el
despliegue en Atlas valida funcionalmente la capa Bronze, y la ejecución a volumen
completo se realiza sobre una instancia local por restricción presupuestaria del
proyecto académico, sin que ello altere el modelo documental ni la lógica de ingesta.

Eso es una decisión de ingeniería justificada y declarada. Lo que no puedes hacer es
ejecutarlo en local y escribir que lo hiciste en Atlas.

**Habla esto con Eduardo antes de ejecutarlo.** Es un cambio sobre un objetivo del
anteproyecto y conviene que quede acordado, no explicado a posteriori.

---

## El protocolo de Redshift: prepara todo antes de crear nada

Redshift Serverless cobra por tiempo activo. Cada minuto que pasas pensando delante de la
consola con el workgroup levantado cuesta dinero. La regla es sencilla: **llega con todo
escrito y ensayado, ejecuta, y borra.**

### Antes de tocar AWS (una tarde entera, coste 0 €)

- [ ] Pipeline Silver terminado y ejecutado. `datos/gold/` generado y verificado.
- [ ] `01_ddl_gold.sql` revisado línea a línea.
- [ ] `02_carga_copy.sql` con tu bucket y tu ARN ya sustituidos.
- [ ] `03_consultas_referencia.sql` probado **contra PostgreSQL local en Docker**, para
      cazar erratas de SQL sin pagarlas. Es el mismo dialecto en lo esencial.
- [ ] `06_medir_latencia.py` probado contra ese mismo PostgreSQL.
- [ ] Informe Silver y evidencias Bronze ya guardados.

Depurar SQL en Redshift a 1,50 $/hora es la forma más tonta de gastarse el presupuesto.

### Configuración de seguridad (hazlo en este orden, sin saltarte nada)

1. **AWS Budgets** → presupuesto de 20 € con alerta por correo al 50 % y al 80 %.
2. Crea el workgroup de **Redshift Serverless** con **capacidad base 4 RPU** (el mínimo).
   No 8, no 16. Cuatro.
3. **Usage limits del workgroup** → límite de **20 RPU-horas al mes** con acción
   **desactivar consultas**. Esto es un tope duro: 20 × 0,375 $ ≈ 7,50 $ y Redshift
   deja de aceptar consultas. Es tu red de seguridad real, mucho más fiable que la
   alerta de presupuesto, que solo avisa cuando ya has gastado.
4. Región **eu-west-1 (Irlanda)**, que soporta la base de 4 RPU.

> Si te saltas el punto 3 y algo se queda haciendo consultas en bucle, no hay nada que
> te pare hasta que llegue la factura. Es literalmente el paso más importante de esta
> lista.

### Sesión 1 — Carga y medición (2–3 horas activas, ~4 $)

- [ ] `aws s3 sync datos/gold/ s3://TU_BUCKET/silver/`
- [ ] Ejecutar `01_ddl_gold.sql` (crea las dos tablas: optimizada y control).
- [ ] Ejecutar `02_carga_copy.sql`. Anotar el tiempo de cada COPY.
- [ ] Cargar también `fact_servicio_control`.
- [ ] `ANALYZE` y `VACUUM`.
- [ ] `python src/06_medir_latencia.py` → guarda el JSON.
- [ ] Capturas de la consola: tamaño de tablas, plan de una consulta, uso de RPU.

### Sesión 2 — Power BI (1–2 horas activas, ~2 $)

- [ ] Conectar en **modo Importación**, nunca DirectQuery.
- [ ] Cargar las tablas una sola vez.
- [ ] **Desconectar.** A partir de aquí Power BI trabaja sobre datos importados y
      Redshift ya no factura nada.
- [ ] Construir las tres vistas y las medidas DAX offline.

> DirectQuery lanza consultas cada vez que mueves un filtro. Una tarde diseñando el
> cuadro de mando en DirectQuery puede costar más que todo el resto del proyecto junto.

### Al terminar

- [ ] Snapshot manual del namespace (por si necesitas rehacer una medida).
- [ ] **Borrar el workgroup.** El namespace con el snapshot puede quedarse: el
      almacenamiento gestionado son céntimos.
- [ ] Vaciar el bucket S3 o dejar solo lo mínimo.
- [ ] Comprobar la factura en Billing → Cost Explorer al día siguiente.

---

## Verifica el crédito de prueba antes de empezar

Hay indicios de que AWS ofrece un crédito de prueba para Redshift Serverless (una fuente
menciona 300 $ durante 90 días). Si aplica a tu cuenta, tu gasto en Redshift sería cero.

**Compruébalo tú en la página oficial de precios de AWS antes de crear el workgroup**,
porque las condiciones cambian y suelen requerir cuenta nueva o no haber usado el
servicio antes. No lo des por hecho.

---

## Si aun así te pasas de 30 €

Plan de contención, en este orden:

1. **Reduce el alcance a 1 mes** (~3 M registros en vez de 9 M). Menos tiempo de COPY,
   consultas más rápidas, menos RPU-horas. Sigues pudiendo decir "millones de registros".
2. **Renuncia a la tabla de control.** Pierdes el experimento optimizada-frente-a-control,
   que es una pena porque es tu mejor resultado, pero se puede sustituir por una
   comparación contra PostgreSQL local, que es gratis.
3. **Último recurso: PostgreSQL local con columnstore como capa Gold.** Esto sí cambia el
   título del TFM y exige acuerdo explícito con el director. No lo hagas por tu cuenta.

---

## Qué tienes que cambiar en la memoria

- **Sección 4.2.4**: sustituir el nivel de clúster de Atlas por la configuración real
  (M0 para validación funcional + instancia local para volumen completo), con su
  justificación.
- **Sección 4.2.7**: quitar la mención al modo híbrido de Power BI. Es solo importación.
- **Sección 4.4 (tabla 4.5, presupuesto)**: con los importes reales, que ahora serán casi
  todos cero. Es un dato interesante en sí mismo y merece un comentario en el texto: la
  barrera de entrada de una arquitectura así ya no es el capital, es el conocimiento.
- **Sección 4.6 (viabilidad)**: el coste medido en Redshift es tu dato real para
  extrapolar el coste de una implantación productiva.
- **Sección 4.7.6 (desviaciones)**: declarar el cambio de alcance en la capa Bronze y su
  motivo. Un tribunal lo lee como criterio; ocultarlo se nota.
