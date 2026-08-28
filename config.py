"""Configuración central del proyecto. Todos los umbrales de las reglas de
calidad se declaran aquí para que sean citables desde la memoria."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Conexiones ---
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "logistica")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "telemetria_raw")

S3_BUCKET = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
REDSHIFT_IAM_ROLE = os.getenv("REDSHIFT_IAM_ROLE")

REDSHIFT = {
    "host": os.getenv("REDSHIFT_HOST"),
    "port": int(os.getenv("REDSHIFT_PORT", 5439)),
    "dbname": os.getenv("REDSHIFT_DB", "dev"),
    "user": os.getenv("REDSHIFT_USER"),
    "password": os.getenv("REDSHIFT_PASSWORD"),
}

# --- Rutas ---
RAIZ = Path(__file__).parent
RUTA_RAW = Path(os.getenv("RUTA_DESCARGAS", RAIZ / "datos/raw"))
RUTA_SILVER = Path(os.getenv("RUTA_SILVER", RAIZ / "datos/silver"))
RUTA_EVIDENCIAS = Path(os.getenv("RUTA_EVIDENCIAS", RAIZ / "evidencias"))

for _p in (RUTA_RAW, RUTA_SILVER, RUTA_EVIDENCIAS):
    _p.mkdir(parents=True, exist_ok=True)

# --- Alcance del conjunto de datos ---
# Ajusta estos meses al alcance que decidas. Empieza con UNO para desarrollar.
MESES = ["2023-01", "2023-02", "2023-03"]
TIPO_SERVICIO = "yellow"   # yellow | green | fhvhv

# --- Umbrales de las reglas de calidad (capa Silver) ---
# Estos valores son los que debes justificar en la memoria, sección 4.2.5.1
MAX_DURACION_MIN = 240.0    # R2: un servicio urbano de más de 4 h es implausible
MIN_DURACION_MIN = 0.5      # R2: menos de 30 s no es un servicio real
MAX_DISTANCIA_KM = 150.0    # R3: fuera del área metropolitana
MIN_DISTANCIA_KM = 0.1      # R3
MAX_VELOCIDAD_KMH = 120.0   # R4: imposible sostenido en entorno urbano
MIN_VELOCIDAD_KMH = 1.0     # R4: por debajo indica error de registro

MILLA_A_KM = 1.609344
RADIO_TIERRA_KM = 6371.0

# --- Fuente de lectura de la capa Silver ---
# "mongo"  -> lectura directa con el conector de Spark (preferido)
# "export" -> lectura de los Parquet generados por 04b_export_bronze.py (plan B)
FUENTE_SILVER = "export"

# --- Lote de escritura en MongoDB ---
TAM_LOTE_INSERCION = 5000

# Vacia la coleccion antes de cargar. Evita duplicar datos si se relanza
# el proceso varias veces, que falsearia el informe de ingesta.
LIMPIAR_COLECCION = True

# --- Muestra ---
# Numero maximo de registros a ingerir. Reduce el tiempo de ejecucion de todo
# el pipeline. Ponlo a None para procesar el mes completo (~3 M registros).
# 500.000 registros bastan para defender el trabajo y tardan minutos, no horas.
MUESTRA = None
