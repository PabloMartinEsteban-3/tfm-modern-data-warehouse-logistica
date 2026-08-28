# ============================================================
#  Ejecuta TODA la parte local del TFM. Version PowerShell.
#
#  Uso:   .\run_local.ps1
#  Si Windows bloquea el script:
#         Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# ============================================================

$ErrorActionPreference = "Stop"

function Paso($n, $texto) {
    Write-Host ""
    Write-Host "==> [$n] $texto" -ForegroundColor Green
}

if (-not (Test-Path ".env")) {
    Write-Host "!!! No existe .env. Ejecuta:  Copy-Item .env.example .env" -ForegroundColor Red
    exit 1
}

if ($PWD.Path -match "OneDrive" -or $PWD.Path -match " ") {
    Write-Host "!!! AVISO: la ruta contiene espacios u OneDrive." -ForegroundColor Red
    Write-Host "    Spark falla con estas rutas. Mueve el proyecto a C:\tfm" -ForegroundColor Red
    Write-Host ""
    $r = Read-Host "Continuar de todas formas? (s/n)"
    if ($r -ne "s") { exit 1 }
}

Paso "1/6" "Levantando MongoDB en Docker"
docker compose up -d
Start-Sleep -Seconds 10

Paso "2/6" "Descargando datos de la NYC TLC"
python src/01_descarga_datos.py

Paso "3/6" "Cargando la capa Bronze en MongoDB"
python src/02_ingesta_bronze.py

Paso "4/6" "Exportando Bronze a Parquet"
python src/04b_export_bronze.py

Paso "5/6" "Construyendo la dimension de zonas"
python src/03_dimension_zonas.py

Paso "6/6" "Pipeline Silver y preparacion de Gold"
python src/04_silver_pipeline.py
python src/05_preparar_gold.py

Write-Host ""
Write-Host "==> LISTO. Evidencias generadas:" -ForegroundColor Green
Get-ChildItem evidencias
