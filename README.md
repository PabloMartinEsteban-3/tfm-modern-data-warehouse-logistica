# Código del TFM — Arquitectura de Modern Data Warehouse para logística urbana

Pablo Martín Esteban · Máster en Análisis de Datos Masivos · Universidad Europea de Madrid

## Puesta en marcha

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # y rellena tus credenciales
java -version                      # necesitas Java 11 o 17 para Spark
```

## Orden de ejecución

| Paso | Comando | Salida | Objetivo |
|---|---|---|---|
| 1 | `python src/01_descarga_datos.py` | `datos/raw/*.parquet` | — |
| 2 | `python src/02_ingesta_bronze.py` | Colección Mongo + `evidencias/informe_ingesta_bronze.json` | OE1 |
| 3 | `python src/03_dimension_zonas.py` | `datos/silver/dim_zona.parquet` | OE2 |
| 4 | `spark-submit --packages org.mongodb.spark:mongo-spark-connector_2.12:10.3.0 --driver-memory 4g src/04_silver_pipeline.py` | `datos/silver/fact_servicio/` + `evidencias/informe_calidad_silver.json` | OE2 |
| 5 | `spark-submit --driver-memory 4g src/05_preparar_gold.py` | `datos/gold/` | OE3 |
| 6 | `aws s3 sync datos/gold/ s3://TU_BUCKET/silver/` | S3 | OE3 |
| 7 | Ejecutar `src/sql/01_ddl_gold.sql` y `02_carga_copy.sql` en Redshift | Tablas cargadas | OE3 |
| 8 | `python src/06_medir_latencia.py` | `evidencias/latencia_consultas.json` | OE3 |
| 9 | Power BI Desktop → conector Amazon Redshift | Cuadro de mando | OE4 |

## Reglas importantes

- **Empieza con UN mes** en `config.MESES`. Cuando todo funcione, amplía.
- **Nunca subas `.env` a Git.** Ya está en `.gitignore`.
- Todo lo que se escribe en `evidencias/` es material para la memoria. No lo borres.
