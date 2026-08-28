"""
FASE 3b - Capa Silver: pipeline de transformacion en PySpark.

Lee la coleccion Bronze de MongoDB, aplica las reglas de calidad, enriquece
con la dimension de zonas, calcula los KPI y escribe Parquet particionado.

Genera el informe de calidad que sustenta el objetivo OE2 (seccion 4.7.2).

Ejecucion (Spark local, con el conector de MongoDB):

  spark-submit \
    --packages org.mongodb.spark:mongo-spark-connector_2.12:10.3.0 \
    --driver-memory 4g \
    src/04_silver_pipeline.py

Comprueba en la documentacion del conector la version compatible con tu Spark.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone

from pyspark.sql import SparkSession, functions as F, Window

sys.path.append(str(Path(__file__).parent.parent))
import config


def crear_sesion() -> SparkSession:
    return (SparkSession.builder
            .appName("silver_telemetria_logistica")
            .master("local[*]")
            .config("spark.driver.memory", "4g")
            .config("spark.mongodb.read.connection.uri", config.MONGO_URI)
            .config("spark.mongodb.read.database", config.MONGO_DB)
            .config("spark.mongodb.read.collection", config.MONGO_COLLECTION)
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.sql.shuffle.partitions", "64")
            .getOrCreate())


def leer_bronze(spark):
    """Lee la capa Bronze. Dos caminos segun config.FUENTE_SILVER.

    "mongo"  -> conector nativo de Spark (preferido)
    "export" -> Parquet intermedio generado por 04b_export_bronze.py (plan B)
    """
    if getattr(config, "FUENTE_SILVER", "mongo") == "export":
        ruta = config.RUTA_SILVER.parent / "bronze_export"
        print(f"[bronze] leyendo export intermedio en {ruta}")
        plano = spark.read.parquet(str(ruta))
        # Reconstruye la estructura anidada que espera aplanar()
        campos = [c for c in plano.columns if not c.startswith("_")]
        return plano.select(
            F.struct(*[F.col(c) for c in campos]).alias("payload"),
            F.struct(
                F.col("_hash_registro").alias("hash_registro"),
                F.col("_fichero_origen").alias("fichero_origen"),
            ).alias("_ingesta"),
        )
    print("[bronze] leyendo con el conector nativo de MongoDB")
    return spark.read.format("mongodb").load()


def aplanar(df):
    """Aplana el documento y conforma tipos. Grano: un servicio."""
    return df.select(
        F.col("payload.VendorID").cast("int").alias("id_operador"),
        F.to_timestamp("payload.tpep_pickup_datetime").alias("ts_inicio"),
        F.to_timestamp("payload.tpep_dropoff_datetime").alias("ts_fin"),
        F.col("payload.trip_distance").cast("double").alias("distancia_millas"),
        F.col("payload.PULocationID").cast("int").alias("id_zona_origen"),
        F.col("payload.DOLocationID").cast("int").alias("id_zona_destino"),
        F.col("payload.passenger_count").cast("int").alias("n_pasajeros"),
        F.col("payload.total_amount").cast("double").alias("importe_total"),
        F.col("_ingesta.hash_registro").alias("hash_registro"),
        F.col("_ingesta.fichero_origen").alias("fichero_origen"),
    )


def derivar_metricas(df):
    """Metricas base necesarias para evaluar las reglas de calidad."""
    return (df
        .withColumn("distancia_km", F.col("distancia_millas") * config.MILLA_A_KM)
        .withColumn("duracion_min",
                    (F.col("ts_fin").cast("long") - F.col("ts_inicio").cast("long")) / 60.0)
        .withColumn("velocidad_kmh",
                    F.when(F.col("duracion_min") > 0,
                           F.col("distancia_km") / (F.col("duracion_min") / 60.0)))
    )


def marcar_calidad(df):
    """Asigna a cada registro el codigo de la PRIMERA regla que incumple.

    Se marca en lugar de descartar: los rechazados van a cuarentena, que es
    lo que permite construir el informe de calidad exigido por OE2.
    """
    motivo = (
        F.when(F.col("ts_inicio").isNull() | F.col("ts_fin").isNull(), "R1_temporal_nulo")
         .when(F.col("ts_fin") <= F.col("ts_inicio"), "R1_temporal_incoherente")
         .when((F.col("duracion_min") < config.MIN_DURACION_MIN) |
               (F.col("duracion_min") > config.MAX_DURACION_MIN), "R2_duracion")
         .when((F.col("distancia_km") < config.MIN_DISTANCIA_KM) |
               (F.col("distancia_km") > config.MAX_DISTANCIA_KM), "R3_distancia")
         .when((F.col("velocidad_kmh") < config.MIN_VELOCIDAD_KMH) |
               (F.col("velocidad_kmh") > config.MAX_VELOCIDAD_KMH), "R4_velocidad")
         .when(F.col("id_zona_origen").isNull() |
               F.col("id_zona_destino").isNull(), "R7_zona_nula")
         .otherwise(F.lit(None))
    )
    return df.withColumn("motivo_rechazo", motivo)


def calcular_kpis(df):
    """KPI de la tabla 4.4 de la memoria.

    El ETA de referencia es el percentil 50 historico del tiempo de trayecto
    para el par origen-destino en la misma franja horaria y tipo de dia.
    """
    df = (df
        .withColumn("fecha", F.to_date("ts_inicio"))
        .withColumn("hora", F.hour("ts_inicio"))
        .withColumn("dia_semana", F.dayofweek("ts_inicio"))
        .withColumn("es_laborable", F.col("dia_semana").between(2, 6))
        .withColumn("franja_horaria",
            F.when(F.col("hora").between(0, 5), "madrugada")
             .when(F.col("hora").between(6, 9), "punta_manana")
             .when(F.col("hora").between(10, 15), "valle")
             .when(F.col("hora").between(16, 19), "punta_tarde")
             .otherwise("noche"))
    )

    # Percentiles por corredor: define el ETA de referencia y la fiabilidad
    corredor = (df.groupBy("id_zona_origen", "id_zona_destino",
                           "franja_horaria", "es_laborable")
                  .agg(
                      F.expr("percentile_approx(duracion_min, 0.5)").alias("eta_referencia_min"),
                      F.expr("percentile_approx(duracion_min, 0.9)").alias("p90_min"),
                      F.count("*").alias("n_servicios_corredor"),
                  )
                  .withColumn("fiabilidad_corredor",
                              F.when(F.col("eta_referencia_min") > 0,
                                     F.col("p90_min") / F.col("eta_referencia_min"))))

    df = df.join(corredor,
                 ["id_zona_origen", "id_zona_destino", "franja_horaria", "es_laborable"],
                 "left")

    return (df
        .withColumn("desviacion_eta_pct",
                    F.when(F.col("eta_referencia_min") > 0,
                           (F.col("duracion_min") - F.col("eta_referencia_min"))
                           / F.col("eta_referencia_min") * 100))
    )


def enriquecer_zonas(df, spark):
    """Une la dimension de zonas por origen y destino. Difusion: tabla pequena."""
    zonas = spark.read.parquet(str(config.RUTA_SILVER / "dim_zona.parquet"))

    org = zonas.select(
        F.col("id_zona").alias("id_zona_origen"),
        F.col("sk_zona").alias("sk_zona_origen"),
        F.col("lat").alias("lat_origen"), F.col("lon").alias("lon_origen"))
    dst = zonas.select(
        F.col("id_zona").alias("id_zona_destino"),
        F.col("sk_zona").alias("sk_zona_destino"),
        F.col("lat").alias("lat_destino"), F.col("lon").alias("lon_destino"))

    df = (df.join(F.broadcast(org), "id_zona_origen", "left")
            .join(F.broadcast(dst), "id_zona_destino", "left"))

    # Distancia geodesica por la formula del semiverseno (ecuacion 4.1)
    dlat = F.radians(F.col("lat_destino") - F.col("lat_origen"))
    dlon = F.radians(F.col("lon_destino") - F.col("lon_origen"))
    a = (F.sin(dlat / 2) ** 2 +
         F.cos(F.radians("lat_origen")) * F.cos(F.radians("lat_destino")) *
         F.sin(dlon / 2) ** 2)

    return (df
        .withColumn("distancia_geodesica_km", 2 * config.RADIO_TIERRA_KM * F.asin(F.sqrt(a)))
        .withColumn("factor_rodeo",
                    F.when(F.col("distancia_geodesica_km") > 0,
                           F.col("distancia_km") / F.col("distancia_geodesica_km")))
    )


def informe_calidad(marcado, limpio, cuarentena, segundos) -> dict:
    total = marcado.count()
    por_regla = (cuarentena.groupBy("motivo_rechazo").count()
                 .orderBy(F.desc("count")).collect())
    n_limpio = limpio.count()
    return {
        "generado": datetime.now(timezone.utc).isoformat(),
        "registros_entrada": total,
        "registros_aceptados": n_limpio,
        "registros_rechazados": total - n_limpio,
        "tasa_rechazo_pct": round((total - n_limpio) / total * 100, 3) if total else 0,
        "rechazos_por_regla": {r["motivo_rechazo"]: r["count"] for r in por_regla},
        "umbrales": {
            "MAX_DURACION_MIN": config.MAX_DURACION_MIN,
            "MIN_DURACION_MIN": config.MIN_DURACION_MIN,
            "MAX_DISTANCIA_KM": config.MAX_DISTANCIA_KM,
            "MAX_VELOCIDAD_KMH": config.MAX_VELOCIDAD_KMH,
        },
        "segundos_pipeline": round(segundos, 1),
    }


def main():
    t0 = time.time()
    spark = crear_sesion()
    print("Configuracion Spark:", spark.sparkContext.getConf().get("spark.master"))

    bronze = leer_bronze(spark)
    plano = aplanar(bronze)
    derivado = derivar_metricas(plano)
    marcado = marcar_calidad(derivado).cache()

    cuarentena = marcado.filter(F.col("motivo_rechazo").isNotNull())
    limpio = (marcado.filter(F.col("motivo_rechazo").isNull())
                     .dropDuplicates(["hash_registro"]))

    silver = enriquecer_zonas(calcular_kpis(limpio), spark)

    # Escritura particionada por fecha: evita el problema de ficheros pequenos
    (silver.repartition("fecha")
           .write.mode("overwrite").partitionBy("fecha")
           .parquet(str(config.RUTA_SILVER / "fact_servicio")))

    (cuarentena.write.mode("overwrite")
               .parquet(str(config.RUTA_SILVER / "cuarentena")))

    inf = informe_calidad(marcado, limpio, cuarentena, time.time() - t0)
    destino = config.RUTA_EVIDENCIAS / "informe_calidad_silver.json"
    destino.write_text(json.dumps(inf, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print(json.dumps(inf, indent=2, ensure_ascii=False))
    print("=" * 60)
    print(f"\n>>> Informe guardado en {destino}")
    print(">>> Evidencia del objetivo OE2. Va a la seccion 4.7.2 y a la tabla 4.3.")

    spark.stop()


if __name__ == "__main__":
    main()
