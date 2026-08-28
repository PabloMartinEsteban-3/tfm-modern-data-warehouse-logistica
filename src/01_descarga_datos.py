"""
FASE 1 - Descarga de los conjuntos de datos de origen.

Descarga los ficheros mensuales de la NYC TLC y la cartografía de zonas.
Los ficheros de la TLC se publican en formato Parquet desde 2022.

Uso:  python src/01_descarga_datos.py
"""

import sys
import time
import requests
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import config

BASE_TLC = "https://d37ci6vzurychx.cloudfront.net/trip-data"
ZONAS_CSV = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
ZONAS_SHP = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"


def descargar(url: str, destino: Path) -> bool:
    if destino.exists():
        print(f"  [saltado] {destino.name} ya existe ({destino.stat().st_size/1e6:.1f} MB)")
        return True
    print(f"  [descargando] {url}")
    try:
        r = requests.get(url, stream=True, timeout=120)
        r.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
        if destino.exists():
            destino.unlink()
        return False
    print(f"  [ok] {destino.name} ({destino.stat().st_size/1e6:.1f} MB)")
    return True


def main():
    t0 = time.time()
    print(f"Descargando {config.TIPO_SERVICIO} para los meses {config.MESES}\n")

    for mes in config.MESES:
        nombre = f"{config.TIPO_SERVICIO}_tripdata_{mes}.parquet"
        descargar(f"{BASE_TLC}/{nombre}", config.RUTA_RAW / nombre)

    print("\nDescargando cartografia de zonas")
    descargar(ZONAS_CSV, config.RUTA_RAW / "taxi_zone_lookup.csv")
    descargar(ZONAS_SHP, config.RUTA_RAW / "taxi_zones.zip")

    total = sum(f.stat().st_size for f in config.RUTA_RAW.iterdir() if f.is_file())
    print(f"\nVolumen total descargado: {total/1e6:.1f} MB")
    print(f"Tiempo: {time.time()-t0:.1f} s")
    print("\n>>> ANOTA para la memoria: numero de ficheros, volumen total y periodo cubierto.")


if __name__ == "__main__":
    main()
