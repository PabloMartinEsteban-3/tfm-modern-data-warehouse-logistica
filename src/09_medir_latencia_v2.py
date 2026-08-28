"""
Medicion rigurosa de latencia: modelo optimizado frente a modelo de control.

Corrige tres problemas de la medicion ingenua:
  1. Desactiva la cache de resultados de Redshift, que devolvia el resultado
     guardado en lugar de reejecutar la consulta.
  2. Descarta una ejecucion de calentamiento antes de medir.
  3. Verifica que ambas tablas contienen datos antes de comparar.

Uso:  python src/09_medir_latencia_v2.py
"""

import sys
import json
import time
import statistics
from pathlib import Path

import psycopg2

sys.path.append(str(Path(__file__).parent.parent))
import config

RUTA_SQL = Path(__file__).parent / "sql" / "03_consultas_referencia.sql"
REPETICIONES = 5


def cargar_consultas() -> dict:
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


def contar(cur, tabla) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {tabla};")
    return cur.fetchone()[0]


def main():
    conn = psycopg2.connect(**config.REDSHIFT)
    conn.autocommit = True
    cur = conn.cursor()

    # --- 1. Desactivar la cache de resultados -------------------------
    cur.execute("SET enable_result_cache_for_session TO off;")
    print("Cache de resultados desactivada para esta sesion.\n")

    # --- 2. Verificar que ambas tablas tienen datos -------------------
    n_opt = contar(cur, "fact_servicio")
    n_ctl = contar(cur, "fact_servicio_control")
    print(f"fact_servicio          : {n_opt:,} filas")
    print(f"fact_servicio_control  : {n_ctl:,} filas")

    if n_ctl == 0:
        print("\n[!] La tabla de control esta vacia. Poblandola ahora...")
        t0 = time.time()
        cur.execute("INSERT INTO fact_servicio_control SELECT * FROM fact_servicio;")
        cur.execute("ANALYZE fact_servicio_control;")
        n_ctl = contar(cur, "fact_servicio_control")
        print(f"    {n_ctl:,} filas insertadas en {time.time()-t0:.1f} s")

    if n_opt != n_ctl:
        print(f"\n[!] AVISO: las tablas no tienen el mismo numero de filas.")
        print(f"    La comparacion no seria valida. Revisalo antes de seguir.")
        return

    # --- 3. Medir -----------------------------------------------------
    consultas = cargar_consultas()
    print(f"\nMidiendo {len(consultas)} consultas x {REPETICIONES} repeticiones")
    print("(se descarta una ejecucion previa de calentamiento)\n")

    resultados = []
    for nombre, sql in consultas.items():
        fila = {"consulta": nombre}
        for etiqueta, tabla in [("optimizada", "fact_servicio"),
                                ("control", "fact_servicio_control")]:
            consulta = sql.replace("fact_servicio ", tabla + " ")
            try:
                cur.execute(consulta)   # calentamiento, no se mide
                cur.fetchall()
                tiempos = []
                for _ in range(REPETICIONES):
                    t0 = time.perf_counter()
                    cur.execute(consulta)
                    cur.fetchall()
                    tiempos.append(time.perf_counter() - t0)
                fila[f"mediana_{etiqueta}_s"] = round(statistics.median(tiempos), 3)
                fila[f"min_{etiqueta}_s"] = round(min(tiempos), 3)
                fila[f"max_{etiqueta}_s"] = round(max(tiempos), 3)
            except Exception as e:
                print(f"    [error] {nombre}/{etiqueta}: {e}")
                fila[f"mediana_{etiqueta}_s"] = None

        o, c = fila.get("mediana_optimizada_s"), fila.get("mediana_control_s")
        if o and c:
            fila["mejora_x"] = round(c / o, 2)
        resultados.append(fila)
        print(f"  {nombre}: optimizada {o}s | control {c}s | mejora {fila.get('mejora_x')}x")

    # --- 4. Guardar, conservando lo ya medido en la fase anterior -----
    destino = config.RUTA_EVIDENCIAS / "resultados_redshift.json"
    previo = {}
    if destino.exists():
        previo = json.loads(destino.read_text(encoding="utf-8"))
    previo["latencia"] = resultados
    previo["filas_fact_servicio"] = n_opt
    previo["cache_desactivada"] = True
    previo["repeticiones"] = REPETICIONES
    destino.write_text(json.dumps(previo, indent=2, ensure_ascii=False),
                       encoding="utf-8")

    print(f"\n>>> Guardado en {destino}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
