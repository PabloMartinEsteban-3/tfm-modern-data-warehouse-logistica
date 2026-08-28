"""
FASE 4 - Preparacion de la capa Gold: claves subrogadas y dimension de tiempo.

Lee la salida Silver, genera dim_tiempo y dim_operador, asigna claves
subrogadas a la tabla de hechos y escribe el Parquet listo para COPY a S3.

IMPORTANTE: Redshift exige coincidencia EXACTA de tipos al cargar Parquet
mediante COPY. No aplica conversiones implicitas. Por eso cada columna se
castea aqui al tipo declarado en src/sql/01_ddl_gold.sql. El diccionario
ESQUEMAS de mas abajo es la unica fuente de verdad: si cambias el DDL,
cambialo tambien aqui.

Uso:  python src/05_preparar_gold.py
Despues:  aws s3 sync datos/gold s3://TU_BUCKET/silver/
"""

import sys
import time
from pathlib import Path

from pyspark.sql import SparkSession, functions as F, Window

sys.path.append(str(Path(__file__).parent.parent))
import config

RUTA_GOLD = config.RUTA_SILVER.parent / "gold"
RUTA_GOLD.mkdir(parents=True, exist_ok=True)

# Correspondencia con los tipos declarados en 01_ddl_gold.sql
ESQUEMAS = {
    "dim_zona": {
        "sk_zona": "int",
        "id_zona": "int",
        "nombre_zona": "string",
        "distrito": "string",
        "zona_servicio": "string",
        "lat": "decimal(9,6)",
        "lon": "decimal(9,6)",
        "long_via_km": "decimal(10,2)",
        "n_intersecciones": "int",
        "densidad_interseccion": "decimal(12,4)",
    },
    "dim_tiempo": {
        "sk_tiempo": "int",
        "fecha": "date",
        "anio": "smallint",
        "trimestre": "smallint",
        "mes": "smallint",
        "dia": "smallint",
        "dia_semana": "smallint",
        "nombre_dia": "string",
        "semana_anio": "smallint",
        "es_laborable": "boolean",
    },
    "dim_operador": {
        "sk_operador": "int",
        "id_operador": "int",
        "nombre_operador": "string",
    },
    "fact_servicio": {
        "sk_servicio": "bigint",
        "sk_tiempo": "int",
        "sk_zona_origen": "int",
        "sk_zona_destino": "int",
        "sk_operador": "int",
        "hora": "smallint",
        "franja_horaria": "string",
        "duracion_min": "decimal(10,2)",
        "distancia_km": "decimal(10,3)",
        "distancia_geodesica_km": "decimal(10,3)",
        "velocidad_kmh": "decimal(10,2)",
        "eta_referencia_min": "decimal(10,2)",
        "desviacion_eta_pct": "decimal(10,2)",
        "factor_rodeo": "decimal(10,4)",
        "fiabilidad_corredor": "decimal(10,4)",
        "importe_total": "decimal(10,2)",
        "n_pasajeros": "smallint",
    },
}


def conformar(df, esquema: dict):
    """Proyecta y castea el DataFrame al esquema exacto de la tabla destino.

    Las columnas ausentes se crean a nulo y las sobrantes se descartan, de
    modo que el Parquet resultante coincide columna a columna con el DDL.
    """
    columnas = []
    for nombre, tipo in esquema.items():
        if nombre in df.columns:
            columnas.append(F.col(nombre).cast(tipo).alias(nombre))
        else:
            print(f"    [aviso] columna ausente, se crea a nulo: {nombre}")
            columnas.append(F.lit(None).cast(tipo).alias(nombre))
    return df.select(*columnas)


def limpiar_ficheros_control(ruta: Path):
    """Elimina _SUCCESS y .crc, que Redshift no sabe interpretar como Parquet."""
    borrados = 0
    for f in ruta.rglob("*"):
        if f.is_file() and (f.name.startswith("_") or f.suffix == ".crc"
                            or f.name.startswith(".")):
            f.unlink()
            borrados += 1
    print(f"  [limpieza] {borrados} ficheros de control eliminados")


def construir_dim_tiempo(df):
    return (df.select("fecha").distinct()
        .withColumn("anio", F.year("fecha"))
        .withColumn("trimestre", F.quarter("fecha"))
        .withColumn("mes", F.month("fecha"))
        .withColumn("dia", F.dayofmonth("fecha"))
        .withColumn("dia_semana", F.dayofweek("fecha"))
        .withColumn("nombre_dia", F.date_format("fecha", "EEEE"))
        .withColumn("semana_anio", F.weekofyear("fecha"))
        .withColumn("es_laborable", F.col("dia_semana").between(2, 6))
        .withColumn("sk_tiempo", F.row_number().over(Window.orderBy("fecha"))))


def construir_dim_operador(df):
    nombres = {1: "Creative Mobile Technologies", 2: "Curb Mobility",
               6: "Myle Technologies", 7: "Helix"}
    mapa = F.create_map([F.lit(x) for kv in nombres.items() for x in kv])
    return (df.select("id_operador").distinct()
              .filter(F.col("id_operador").isNotNull())
              .withColumn("nombre_operador",
                          F.coalesce(mapa[F.col("id_operador")], F.lit("Desconocido")))
              .withColumn("sk_operador",
                          F.row_number().over(Window.orderBy("id_operador"))))


def main():
    t0 = time.time()
    spark = (SparkSession.builder.appName("preparar_gold")
             .master("local[*]")
             .config("spark.driver.memory", "4g")
             .config("spark.sql.shuffle.partitions", "64")
             .getOrCreate())

    silver = spark.read.parquet(str(config.RUTA_SILVER / "fact_servicio"))
    print(f"Filas Silver: {silver.count():,}")

    dim_tiempo = construir_dim_tiempo(silver)
    dim_operador = construir_dim_operador(silver)
    dim_zona = spark.read.parquet(str(config.RUTA_SILVER / "dim_zona.parquet"))

    hechos = (silver
        .join(F.broadcast(dim_tiempo.select("fecha", "sk_tiempo")), "fecha", "left")
        .join(F.broadcast(dim_operador.select("id_operador", "sk_operador")),
              "id_operador", "left")
        .withColumn("sk_servicio", F.monotonically_increasing_id()))

    tablas = {
        "dim_tiempo": dim_tiempo,
        "dim_operador": dim_operador,
        "dim_zona": dim_zona,
        "fact_servicio": hechos,
    }

    for nombre, df in tablas.items():
        print(f"\n  {nombre}")
        conformado = conformar(df, ESQUEMAS[nombre])
        destino = RUTA_GOLD / nombre
        # Las dimensiones caben en un solo fichero: menos objetos en S3.
        if nombre.startswith("dim_"):
            conformado = conformado.coalesce(1)
        conformado.write.mode("overwrite").parquet(str(destino))
        print(f"    {conformado.count():,} filas -> {destino}")

    limpiar_ficheros_control(RUTA_GOLD)

    print(f"\nTiempo total: {time.time()-t0:.1f} s")
    print(f"\n>>> Ahora sube a S3:")
    print(f"    aws s3 rm s3://{config.S3_BUCKET}/silver/ --recursive")
    print(f"    aws s3 sync datos\\gold s3://{config.S3_BUCKET}/silver/")
    spark.stop()


if __name__ == "__main__":
    main()