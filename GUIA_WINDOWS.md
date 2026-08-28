# Guía de Windows — los tres bloqueos y cómo saltarlos

Tu entorno está bien: Python 3.12, Java 11 (vale, Spark lo soporta) y Docker 27.
Pero hay tres cosas que van a fallar si no las arreglas antes.

---

## Bloqueo 1 — La carpeta está en OneDrive ⚠️ *el más grave*

Tu ruta actual:

```
C:\Users\pablo\OneDrive - UNICAN - Estudiantes\Escritorio\Master BIG DATA UEM\TFM
```

Tiene **espacios, guiones y sincronización de OneDrive**. Spark en Windows falla
con rutas así: unas veces no encuentra los ficheros, otras OneDrive bloquea un
Parquet a medio escribir y el job se cae sin explicación clara.

**Solución (2 minutos):**

```powershell
mkdir C:\tfm
# copia ahí el contenido del proyecto
cd C:\tfm
```

Trabaja siempre desde `C:\tfm`. Cuando termines, copias los resultados de vuelta
a OneDrive para tenerlos guardados. No trabajes dentro de OneDrive.

---

## Bloqueo 2 — Spark en Windows necesita winutils

Spark usa librerías de Hadoop que en Windows requieren dos ficheros que no vienen
incluidos. Sin ellos verás errores tipo `HADOOP_HOME and hadoop.home.dir are unset`
o fallos al escribir Parquet.

**Solución:**

1. Descarga `winutils.exe` y `hadoop.dll` para **Hadoop 3.3.x**. El repositorio
   más usado es `cdarlint/winutils` en GitHub (carpeta `hadoop-3.3.x/bin`).
   Verifica tú el repositorio antes de descargar nada ejecutable.
2. Créate `C:\hadoop\bin` y mete ahí los dos ficheros.
3. En PowerShell, como administrador:

```powershell
[Environment]::SetEnvironmentVariable("HADOOP_HOME", "C:\hadoop", "User")
$env:Path += ";C:\hadoop\bin"
```

4. **Cierra y reabre PowerShell.**

### Alternativa sin winutils: Spark dentro de Docker

Si lo anterior te da guerra más de media hora, salta a esto. Ya tienes Docker.

```powershell
docker run --rm -it `
  -v C:\tfm:/proyecto `
  --network tfm_default `
  apache/spark-py:v3.5.0 `
  /opt/spark/bin/spark-submit --driver-memory 4g /proyecto/src/04_silver_pipeline.py
```

Antes de usarlo, en tu `.env` cambia el host de Mongo de `localhost` a `mongo`,
que es el nombre del servicio dentro de la red de Docker:

```
MONGO_URI=mongodb://tfm:tfm@mongo:27017/?authSource=admin
```

---

## Bloqueo 3 — Python 3.12 con PySpark

PySpark 3.5.1 puede dar problemas con Python 3.12 (por la retirada de `distutils`).
Puede que funcione, pero si al lanzar `spark-submit` ves errores raros de importación:

**Opción A (rápida):** actualiza a la última 3.5.x

```powershell
pip install --upgrade "pyspark==3.5.6"
```

**Opción B (segura):** instala Python 3.11 y crea el entorno con él

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Orden de ejecución en PowerShell

```powershell
cd C:\tfm
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `config.py` y pon `MUESTRA = 250_000`.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run_local.ps1
```

> `bash run_local.sh` **no funciona en PowerShell**. Usa el `.ps1`.

---

## Si geopandas no instala

Es la dependencia más frágil en Windows. Si `pip install` falla en geopandas o
en osmnx, no pierdas tiempo:

```powershell
pip install pandas pyarrow pymongo python-dotenv tqdm requests pyspark
```

Y en `src/03_dimension_zonas.py` no uses el shapefile: la dimensión se queda con
el `taxi_zone_lookup.csv` (id, nombre, distrito) y sin coordenadas. Pierdes el
factor de rodeo y la distancia geodésica, que son dos de los seis KPI.

Se declara en la memoria en la sección de desviaciones y no pasa nada: te quedan
cuatro KPI, que es de sobra para el cuadro de mando y para OE2.
