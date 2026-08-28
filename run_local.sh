#!/usr/bin/env bash
# ============================================================
#  Ejecuta TODA la parte local del TFM con un solo comando.
#  Bronze -> export -> Silver -> Gold. Sin AWS, sin coste.
#
#  Uso:   bash run_local.sh
# ============================================================
set -e

verde() { printf "\n\033[1;32m==> %s\033[0m\n" "$1"; }
rojo()  { printf "\n\033[1;31m!!! %s\033[0m\n" "$1"; }

if [ ! -f .env ]; then
  rojo "No existe .env. Ejecuta:  cp .env.example .env"
  exit 1
fi

verde "1/6  Levantando MongoDB en Docker"
docker compose up -d
sleep 8

verde "2/6  Descargando datos de la NYC TLC"
python src/01_descarga_datos.py

verde "3/6  Cargando la capa Bronze en MongoDB"
python src/02_ingesta_bronze.py

verde "4/6  Exportando Bronze a Parquet (evita el conector de Spark)"
python src/04b_export_bronze.py

verde "5/6  Construyendo la dimension de zonas"
python src/03_dimension_zonas.py

verde "6/6  Ejecutando el pipeline Silver y preparando Gold"
spark-submit --driver-memory 4g src/04_silver_pipeline.py
spark-submit --driver-memory 4g src/05_preparar_gold.py

verde "LISTO. Evidencias generadas:"
ls -la evidencias/

echo ""
echo "Siguiente paso: sigue GUIA_REDSHIFT.md"
