"""
FASE 4b - Medicion de latencia de las consultas de referencia (OE3).

Ejecuta cada consulta N veces contra fact_servicio y contra
fact_servicio_control, y produce la tabla comparativa de latencia que va
a la seccion 4.7.3 de la memoria.

Uso:  python src/06_medir_latencia.py
"""

import sys
import json
import time
import statistics
from pathlib import Path

import psycopg2

sys.path.append(str(Path(__file__).parent.parent))
import config

REPETICIONES = 3
RUTA_SQL = Path(__file__).parent / "sql" / "03_consultas_referencia.sql"


def cargar_consultas() -> dict:
    """Trocea el fichero SQL por los comentarios -- Qn."""
    texto = RUTA_SQL.read_text(encoding="utf-8")
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


def medir(cur, sql: str, tabla: str) -> list:
    sql = sql.replace("fact_servicio", tabla)
    tiempos = []
    for _ in range(REPETICIONES):
        t0 = time.perf_counter()
        cur.execute(sql)
        cur.fetchall()
        tiempos.append(time.perf_counter() - t0)
    return tiempos


def main():
    consultas = cargar_consultas()
    print(f"Consultas detectadas: {list(consultas.keys())}\n")

    conn = psycopg2.connect(**config.REDSHIFT)
    cur = conn.cursor()

    resultados = []
    for nombre, sql in consultas.items():
        fila = {"consulta": nombre}
        for etiqueta, tabla in [("optimizada", "fact_servicio"),
                                ("control", "fact_servicio_control")]:
            try:
                t = medir(cur, sql, tabla)
                fila[f"mediana_{etiqueta}_s"] = round(statistics.median(t), 3)
                fila[f"min_{etiqueta}_s"] = round(min(t), 3)
            except Exception as e:
                conn.rollback()
                fila[f"mediana_{etiqueta}_s"] = None
                print(f"  [error] {nombre}/{etiqueta}: {e}")
        if fila.get("mediana_control_s") and fila.get("mediana_optimizada_s"):
            fila["mejora_x"] = round(
                fila["mediana_control_s"] / fila["mediana_optimizada_s"], 2)
        resultados.append(fila)
        print(fila)

    destino = config.RUTA_EVIDENCIAS / "latencia_consultas.json"
    destino.write_text(json.dumps(resultados, indent=2, ensure_ascii=False))

    print(f"\n>>> Guardado en {destino}")
    print(">>> Esta tabla va a la seccion 4.7.3. Pasala a LaTeX tal cual.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
