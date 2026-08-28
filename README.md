# Arquitectura de Modern Data Warehouse para la optimización de logística urbana

Trabajo Fin de Máster · Máster Universitario en Análisis de Datos Masivos
Universidad Europea de Madrid · Pablo Martín Esteban

Integración de telemetría masiva en MongoDB y análisis analítico en AWS Redshift mediante PySpark.

---

## Qué hace

Construye una plataforma analítica completa sobre telemetría de flota, organizada según el
patrón **Medallion** en tres capas de refinamiento progresivo:

| Capa | Tecnología | Función |
|---|---|---|
| **Bronze** | MongoDB | Ingesta del registro crudo en formato documental, con metadatos de linaje |
| **Silver** | PySpark | Validación, deduplicación, enriquecimiento geográfico y cálculo de indicadores |
| **Gold** | AWS Redshift | Modelo dimensional en estrella optimizado para consulta analítica |
| **Consumo** | Power BI | Cuadro de mando de ETA y eficiencia de rutas |

La validación se realiza sobre **9.384.487 registros** del conjunto público de la
[NYC Taxi & Limousine Commission](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page),
correspondientes al primer trimestre de 2023.

## Resultados

- Ciclo completo en **851 segundos** sobre un portátil convencional
- Tasa de rechazo por reglas de calidad del **1,89 %**, con desglose por regla
- El diseño físico del almacén (`DISTKEY` y `SORTKEY`) **no mejora la latencia** a este volumen,
  contrastado frente a un modelo de control
- El cruce entre desviación sobre el ETA y factor de rodeo permite **distinguir la ineficiencia
  por congestión de la derivada de restricciones de la red viaria**

Las métricas completas están en [`evidencias/`](evidencias/), generadas por los propios scripts.

## Estructura

```
src/
  01_descarga_datos.py       Descarga NYC TLC y cartografía de zonas
  02_ingesta_bronze.py       Carga en MongoDB con metadatos de linaje
  03_dimension_zonas.py      Dimensión de zonas y centroides
  04_silver_pipeline.py      Validación, KPI y escritura Parquet
  04b_export_bronze.py       Exportación intermedia (alternativa al conector Spark)
  05_preparar_gold.py        Claves subrogadas y conformación de tipos
  07_redshift_todo.py        DDL, carga COPY y medición en una ejecución
  09_medir_latencia_v2.py    Medición rigurosa optimizada vs. control
  08_generar_tablas_latex.py Genera las tablas de resultados en LaTeX
  sql/                       DDL del esquema en estrella y consultas de referencia
evidencias/                  Informes de ejecución y capturas del cuadro de mando
```

## Puesta en marcha

```bash
python -m venv entorno
source entorno/bin/activate      # Windows: .\entorno\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # rellenar credenciales
docker compose up -d             # MongoDB local
```

Ejecución completa de las capas locales:

```bash
bash run_local.sh                # Windows: .\run_local.ps1
```

Capa Gold sobre Redshift:

```bash
aws s3 sync datos/gold s3://TU_BUCKET/silver/
python src/07_redshift_todo.py
python src/09_medir_latencia_v2.py
```

Requiere Python 3.11, Java 17 y Docker.

## Notas

- El fichero `.pbix` del cuadro de mando no se incluye por tamaño; las capturas de las tres
  vistas están en [`evidencias/`](evidencias/).
- Los conjuntos de datos no se versionan. El script `01_descarga_datos.py` los obtiene del
  origen público.
- `config.py` centraliza los umbrales de las reglas de calidad, de modo que los criterios de
  validación son revisables en un único punto.
