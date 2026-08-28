"""
Hace TODO lo de Redshift en un solo comando: crea el esquema, carga desde S3,
mide la latencia de las consultas y guarda las evidencias.

Requisitos previos (ver GUIA_REDSHIFT.md):
  - Workgroup de Redshift Serverless creado
  - Bucket S3 con los datos subidos
  - Rol IAM asociado al namespace
  - .env relleno

Uso:  python src/07_redshift_todo.py
"""

import sys
import json
import time
import statistics
from pathlib import Path

import psycopg2

sys.path.append(str(Path(__file__).parent.parent))
import config

RAIZ_SQL = Path(__file__).parent / "sql"
REPETICIONES = 3


def ejecutar_script(cur, ruta: Path, sustituciones: dict):
    sql = ruta.read_text(encoding="utf-8")
    for k, v in sustituciones.items():
        sql = sql.replace(k, str(v))
    for bruto in sql.split(";"):
        # Elimina las lineas de comentario y conserva solo el SQL.
        limpio = "\n".join(
            l for l in bruto.splitlines() if not l.strip().startswith("--")
        ).strip()
        if not limpio:
            continue
        t0 = time.perf_counter()
        cur.execute(limpio)
        dur = time.perf_counter() - t0
        etiqueta = " ".join(limpio.split()[:4])
        print(f"    [{dur:7.2f}s] {etiqueta}")

def cargar_consultas() -> dict:
    texto = (RAIZ_SQL / "03_consultas_referencia.sql").read_text(encoding="utf-8")
    bloques, actual, nombre = {}, [], None
    for linea in texto.splitlines():
        if linea.strip().startswith("-- Q") and "." in linea:
            if nombre and actual:
                bloques[nombre] = "\n".join(actual)
            nombre = linea.strip()[3:].split(".")[0]
            actual = []
        elif nombre and not linea.strip().startswith("--"):
            actual.append(linea)
    if nombre and actual:
        bloques[nombre] = "\n".join(actual)
    return {k: v.strip().rstrip(";") for k, v in bloques.items() if v.strip()}


def main():
    sustituciones = {
        "s3://tfm-logistica-pablo": f"s3://{config.S3_BUCKET}",
        "arn:aws:iam::<cuenta>:role/RedshiftCopyRole": config.REDSHIFT_IAM_ROLE,
    }

    print("Conectando a Redshift...")
    conn = psycopg2.connect(**config.REDSHIFT)
    conn.autocommit = True
    cur = conn.cursor()

    evidencias = {}

    print("\n[1/4] Creando el esquema en estrella")
    t0 = time.time()
    ejecutar_script(cur, RAIZ_SQL / "01_ddl_gold.sql", sustituciones)
    evidencias["segundos_ddl"] = round(time.time() - t0, 1)

    print("\n[2/4] Cargando datos desde S3 (COPY)")
    t0 = time.time()
    ejecutar_script(cur, RAIZ_SQL / "02_carga_copy.sql", sustituciones)
    evidencias["segundos_copy"] = round(time.time() - t0, 1)

    print("\n[3/4] Duplicando en la tabla de control (sin diseno fisico)")
    t0 = time.time()
    cur.execute("INSERT INTO fact_servicio_control SELECT * FROM fact_servicio;")
    cur.execute("ANALYZE fact_servicio_control;")
    evidencias["segundos_control"] = round(time.time() - t0, 1)

    for tabla in ("fact_servicio", "dim_zona", "dim_tiempo"):
        cur.execute(f"SELECT COUNT(*) FROM {tabla};")
        evidencias[f"filas_{tabla}"] = cur.fetchone()[0]
        print(f"    {tabla}: {evidencias[f'filas_{tabla}']:,} filas")

    print("\n[4/4] Midiendo latencia de las consultas de referencia")
    consultas, resultados = cargar_consultas(), []
    for nombre, sql in consultas.items():
        fila = {"consulta": nombre}
        for etiqueta, tabla in [("optimizada", "fact_servicio"),
                                ("control", "fact_servicio_control")]:
            try:
                tiempos = []
                for _ in range(REPETICIONES):
                    t0 = time.perf_counter()
                    cur.execute(sql.replace("fact_servicio", tabla))
                    cur.fetchall()
                    tiempos.append(time.perf_counter() - t0)
                fila[f"mediana_{etiqueta}_s"] = round(statistics.median(tiempos), 3)
            except Exception as e:
                fila[f"mediana_{etiqueta}_s"] = None
                print(f"    [error] {nombre}/{etiqueta}: {e}")
        o, c = fila.get("mediana_optimizada_s"), fila.get("mediana_control_s")
        if o and c:
            fila["mejora_x"] = round(c / o, 2)
        resultados.append(fila)
        print(f"    {fila}")

    evidencias["latencia"] = resultados
    destino = config.RUTA_EVIDENCIAS / "resultados_redshift.json"
    destino.write_text(json.dumps(evidencias, indent=2, ensure_ascii=False))

    print(f"\n>>> Todo guardado en {destino}")
    print(">>> Ahora ejecuta:  python src/08_generar_tablas_latex.py")
    print(">>> Y NO OLVIDES BORRAR EL WORKGROUP cuando acabes con Power BI.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
