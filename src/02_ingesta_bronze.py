"""
FASE 2 - Capa Bronze: ingesta en MongoDB Atlas.

Lee los ficheros Parquet descargados y los inserta en MongoDB como documentos
BSON, preservando el payload original integro y anadiendo metadatos de linaje.

Genera un informe de ingesta en evidencias/ que alimenta la seccion 4.7.1
de la memoria (objetivo OE1).

Uso:  python src/02_ingesta_bronze.py
"""

import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from pymongo import MongoClient, ASCENDING
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent))
import config

VERSION_ESQUEMA = 1


def hash_registro(d: dict) -> str:
    """Huella estable del contenido, para detectar reingestas duplicadas."""
    canon = json.dumps(d, sort_keys=True, default=str)
    return hashlib.sha256(canon.encode()).hexdigest()[:32]


def crear_indices(col):
    print("Creando indices...")
    col.create_index([("payload.tpep_pickup_datetime", ASCENDING)], name="idx_temporal")
    col.create_index([("_ingesta.hash_registro", ASCENDING)], name="idx_hash")
    col.create_index(
        [("payload.VendorID", ASCENDING), ("payload.tpep_pickup_datetime", ASCENDING)],
        name="idx_operador_fecha",
    )
    print("Indices:", list(col.index_information().keys()))


def ingerir_fichero(col, ruta: Path) -> dict:
    """Ingiere un fichero Parquet y devuelve las metricas de la operacion."""
    t0 = time.time()
    df = pd.read_parquet(ruta)
    if getattr(config, "MUESTRA", None):
        df = df.head(config.MUESTRA)
        print(f"  [muestra] limitando a {config.MUESTRA:,} registros")
    n_origen = len(df)
    ahora = datetime.now(timezone.utc)

    insertados = 0
    lote = []
    for reg in tqdm(df.to_dict(orient="records"), desc=ruta.name, unit="reg"):
        payload = {k: (v.isoformat() if isinstance(v, pd.Timestamp) else v)
                   for k, v in reg.items()}
        doc = {
            "payload": payload,
            "_ingesta": {
                "fecha_carga": ahora,
                "fichero_origen": ruta.name,
                "hash_registro": hash_registro(payload),
                "version_esquema": VERSION_ESQUEMA,
            },
        }
        lote.append(doc)
        if len(lote) >= config.TAM_LOTE_INSERCION:
            col.insert_many(lote, ordered=False)
            insertados += len(lote)
            lote = []
    if lote:
        col.insert_many(lote, ordered=False)
        insertados += len(lote)

    dur = time.time() - t0
    return {
        "fichero": ruta.name,
        "registros_origen": n_origen,
        "registros_insertados": insertados,
        "coincide": n_origen == insertados,
        "segundos": round(dur, 1),
        "registros_por_segundo": round(insertados / dur, 1) if dur else None,
    }


def main():
    cliente = MongoClient(config.MONGO_URI)
    col = cliente[config.MONGO_DB][config.MONGO_COLLECTION]

    print(f"Coleccion destino: {config.MONGO_DB}.{config.MONGO_COLLECTION}")
    existentes = col.estimated_document_count()
    print(f"Documentos existentes: {existentes}")

    if getattr(config, "LIMPIAR_COLECCION", True) and existentes:
        print(f"  [limpieza] vaciando la coleccion ({existentes} documentos)")
        col.drop()
        col = cliente[config.MONGO_DB][config.MONGO_COLLECTION]
    print()

    informe = {"inicio": datetime.now(timezone.utc).isoformat(), "ficheros": []}
    t0 = time.time()

    for ruta in sorted(config.RUTA_RAW.glob(f"{config.TIPO_SERVICIO}_tripdata_*.parquet")):
        informe["ficheros"].append(ingerir_fichero(col, ruta))

    crear_indices(col)

    stats = cliente[config.MONGO_DB].command("collstats", config.MONGO_COLLECTION)
    informe.update({
        "segundos_totales": round(time.time() - t0, 1),
        "documentos_finales": col.count_documents({}),
        "tamano_datos_mb": round(stats.get("size", 0) / 1e6, 1),
        "tamano_almacenado_mb": round(stats.get("storageSize", 0) / 1e6, 1),
        "tamano_indices_mb": round(stats.get("totalIndexSize", 0) / 1e6, 1),
    })

    destino = config.RUTA_EVIDENCIAS / "informe_ingesta_bronze.json"
    destino.write_text(json.dumps(informe, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print(json.dumps(informe, indent=2, ensure_ascii=False))
    print("=" * 60)
    print(f"\n>>> Informe guardado en {destino}")
    print(">>> Evidencia del objetivo OE1. Va a la seccion 4.7.1 de la memoria.")


if __name__ == "__main__":
    main()
