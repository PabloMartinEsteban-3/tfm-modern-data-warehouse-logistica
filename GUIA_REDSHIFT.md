# Guía de Redshift — clic a clic

Tiempo: ~45 min de configuración + 20 min de ejecución. Coste: ~8 €.
**Haz esto de una sentada.** Todo lo de abajo está en orden; no te saltes pasos.

---

## Paso 1 — Presupuesto (5 min, hazlo primero)

1. Consola AWS → busca **Billing and Cost Management** → **Budgets** → *Create budget*.
2. Tipo *Cost budget*, importe **20 USD**, periodo mensual.
3. Alerta al 50 % y al 80 % con tu correo.

## Paso 2 — Bucket S3 (5 min)

1. Consola → **S3** → *Create bucket*.
2. Nombre: `tfm-logistica-pablo` (si está cogido, añade números).
3. Región: **Europe (Ireland) eu-west-1**. Todo lo demás por defecto.
4. En tu terminal:
   ```
   aws s3 sync datos/gold/ s3://TU_BUCKET/silver/
   ```
   Si no tienes la CLI: `pip install awscli` y luego `aws configure`.

## Paso 3 — Rol IAM (10 min)

1. Consola → **IAM** → *Roles* → *Create role*.
2. Tipo: **AWS service** → **Redshift** → **Redshift - Customizable**.
3. Adjunta la política **AmazonS3ReadOnlyAccess**.
4. Nombre: `RedshiftCopyRole`.
5. **Copia el ARN** (algo como `arn:aws:iam::123456789012:role/RedshiftCopyRole`)
   y pégalo en tu `.env`.

## Paso 4 — Redshift Serverless (10 min)

1. Consola → **Amazon Redshift** → **Serverless dashboard** → *Create workgroup*.
2. Nombre: `tfm-wg`. **Base capacity: 4 RPU** (el mínimo, búscalo en el desplegable).
3. Red: acepta la VPC por defecto y marca **Publicly accessible** (necesitas
   conectarte desde tu portátil y desde Power BI).
4. Namespace: `tfm-ns`. Usuario `admin` y una contraseña que apuntes.
5. En *Associated IAM roles*, asocia `RedshiftCopyRole`.
6. Crear.

## Paso 5 — El límite de gasto (5 min) ⚠️ NO TE LO SALTES

1. Entra en el workgroup `tfm-wg` → pestaña **Limits**.
2. *Add usage limit*: **20 RPU-hours**, periodo **Monthly**,
   acción **Turn off user queries**.
3. Guardar.

Esto es un tope duro. Si algo se descontrola, Redshift deja de aceptar consultas
en vez de seguir facturando. Es tu única protección real.

## Paso 6 — Abrir el puerto (5 min)

1. En el workgroup, pincha en el **VPC security group**.
2. *Edit inbound rules* → *Add rule*: tipo **Custom TCP**, puerto **5439**,
   origen **My IP**.
3. Guardar.

## Paso 7 — Rellenar el .env

Del workgroup copia el **Endpoint** (sin el `:5439/dev` final) y complétalo:

```
REDSHIFT_HOST=tfm-wg.123456789012.eu-west-1.redshift-serverless.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DB=dev
REDSHIFT_USER=admin
REDSHIFT_PASSWORD=lo_que_pusiste
REDSHIFT_IAM_ROLE=arn:aws:iam::...:role/RedshiftCopyRole
S3_BUCKET=tfm-logistica-pablo
```

## Paso 8 — Ejecutar (20 min, desatendido)

```
python src/07_redshift_todo.py
python src/08_generar_tablas_latex.py
```

El primero crea el esquema, carga desde S3, duplica en la tabla de control y mide
las latencias. El segundo convierte todo eso en tablas LaTeX.

## Paso 9 — Power BI y cierre

**No borres el workgroup todavía**: lo necesitas para importar en Power BI
(ver `GUIA_POWERBI.md`). En cuanto termines la importación:

1. Workgroup → *Actions* → **Delete**.
2. El namespace puedes dejarlo; el almacenamiento son céntimos.
3. Al día siguiente mira **Cost Explorer** para anotar el gasto real en la memoria.

---

## Si algo falla

| Error | Causa habitual |
|---|---|
| `timeout` al conectar | Falta la regla de entrada del puerto 5439, o no marcaste *Publicly accessible* |
| `COPY` da error de permisos | El rol IAM no está asociado al namespace, o el ARN del `.env` está mal |
| `relation does not exist` | El DDL falló antes; mira la salida del paso 8 desde arriba |
| Consultas rechazadas | Llegaste al límite de 20 RPU-hours. Súbelo con cuidado o para |
