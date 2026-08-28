"""
PLAN B - Exporta la coleccion Bronze de MongoDB a Parquet usando pymongo.

USA ESTO SI el conector de Spark para MongoDB te da guerra. Evita por completo
el infierno de versiones conector/Spark/Scala a cambio de un paso intermedio.

Es una solucion legitima y hay que declararla en la memoria: la lectura de la
capa Bronze se realiza mediante exportacion intermedia en lugar de conector
nativo, sin que ello altere la logica de transformacion.

Uso:  python src/04b_export_bronze.py
Luego, en config.py:  FUENTE_SILVER = "export"
"""

import sys
import time
from pathlib import Path

import pandas as pd
from pymongo import MongoClient

sys.path.append(str(Path(__file__).parent.parent))
import config

TAM_LOTE = 200_000
DESTINO = config.RUTA_SILVER.parent / "bronze_export"


def main():
    t0 = time.time()
    DESTINO.mkdir(parents=True, exist_ok=True)

    cliente = MongoClient(config.MONGO_URI)
    col = cliente[config.MONGO_DB][config.MONGO_COLLECTION]
    total = col.count_documents({})
    print(f"Documentos a exportar: {total:,}")

    lote, n_fichero, exportados = [], 0, 0
    cursor = col.find({}, {"_id": 0}, batch_size=5000)

    for doc in cursor:
        fila = dict(doc.get("payload", {}))
        ing = doc.get("_ingesta", {})
        fila["_hash_registro"] = ing.get("hash_registro")
        fila["_fichero_origen"] = ing.get("fichero_origen")
        lote.append(fila)

        if len(lote) >= TAM_LOTE:
            pd.DataFrame(lote).to_parquet(
                DESTINO / f"parte_{n_fichero:04d}.parquet", index=False)
            exportados += len(lote)
            print(f"  parte {n_fichero}: {exportados:,}/{total:,}")
            lote, n_fichero = [], n_fichero + 1

    if lote:
        pd.DataFrame(lote).to_parquet(
            DESTINO / f"parte_{n_fichero:04d}.parquet", index=False)
        exportados += len(lote)

    print(f"\nExportados {exportados:,} documentos a {DESTINO}")
    print(f"Tiempo: {time.time()-t0:.1f} s")
    print('\n>>> Ahora pon  FUENTE_SILVER = "export"  en config.py')


if __name__ == "__main__":
    main()
