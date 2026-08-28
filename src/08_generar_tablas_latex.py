"""
Lee las evidencias generadas por el pipeline y escribe las tablas de resultados
en LaTeX, listas para incluir en la memoria.

Salida: evidencias/tablas_resultados.tex

En la memoria, en el capitulo Desarrollo, basta con anadir:
    \\input{tablas_resultados}

Uso:  python src/08_generar_tablas_latex.py
"""

import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import config

EV = config.RUTA_EVIDENCIAS


def leer(nombre):
    ruta = EV / nombre
    if not ruta.exists():
        print(f"  [aviso] falta {nombre}, se omite su tabla")
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def tabla_ingesta(d):
    if not d:
        return ""
    filas = "\n".join(
        f"    {f['fichero'].replace('_', chr(92)+'_')} & {f['registros_insertados']:,} & "
        f"{f['segundos']} & {f['registros_por_segundo']:,.0f} \\\\ \\hline".replace(",", ".")
        for f in d.get("ficheros", [])
    )
    return f"""
\\begin{{table}}[H]
  \\centering
  \\begin{{tabular}}{{|l|r|r|r|}}
    \\hline
    \\textbf{{Fichero}} & \\textbf{{Registros}} & \\textbf{{Segundos}} & \\textbf{{Reg./s}} \\\\ \\hline
{filas}
  \\end{{tabular}}
  \\caption{{Resultados de la ingesta en la capa Bronze}}
  \\label{{tab:res_ingesta}}
\\end{{table}}

\\noindent La coleccion resultante ocupa {d.get('tamano_almacenado_mb', 0)} MB de almacenamiento
y {d.get('tamano_indices_mb', 0)} MB de indices, con un total de
{d.get('documentos_finales', 0):,} documentos ingeridos en
{d.get('segundos_totales', 0)} segundos.
""".replace(",", ".")


def tabla_calidad(d):
    if not d:
        return ""
    filas = "\n".join(
        f"    {k.replace('_', chr(92)+'_')} & {v:,} & {v/d['registros_entrada']*100:.3f} \\\\ \\hline".replace(",", ".")
        for k, v in d.get("rechazos_por_regla", {}).items()
    )
    return f"""
\\begin{{table}}[H]
  \\centering
  \\begin{{tabular}}{{|l|r|r|}}
    \\hline
    \\textbf{{Regla}} & \\textbf{{Rechazados}} & \\textbf{{\\% del total}} \\\\ \\hline
{filas}
  \\end{{tabular}}
  \\caption{{Informe de calidad de la capa Silver: rechazos por regla}}
  \\label{{tab:res_calidad}}
\\end{{table}}

\\noindent De los {d.get('registros_entrada', 0):,} registros de entrada se aceptaron
{d.get('registros_aceptados', 0):,} y se rechazaron {d.get('registros_rechazados', 0):,},
lo que supone una tasa de rechazo del {d.get('tasa_rechazo_pct', 0)}\\%.
El pipeline completo se ejecuto en {d.get('segundos_pipeline', 0)} segundos.
""".replace(",", ".")


def tabla_latencia(d):
    if not d:
        return ""
    filas = "\n".join(
        f"    {f['consulta']} & {f.get('mediana_optimizada_s', '--')} & "
        f"{f.get('mediana_control_s', '--')} & {f.get('mejora_x', '--')} \\\\ \\hline"
        for f in d.get("latencia", [])
    )
    return f"""
\\begin{{table}}[H]
  \\centering
  \\begin{{tabular}}{{|l|r|r|r|}}
    \\hline
    \\textbf{{Consulta}} & \\textbf{{Optimizada (s)}} & \\textbf{{Control (s)}} & \\textbf{{Mejora}} \\\\ \\hline
{filas}
  \\end{{tabular}}
  \\caption{{Latencia de las consultas analiticas de referencia: modelo con claves
  de distribucion y ordenacion frente a modelo de control sin diseno fisico}}
  \\label{{tab:res_latencia}}
\\end{{table}}

\\noindent La carga mediante COPY desde S3 se completo en {d.get('segundos_copy', 0)} segundos
para un total de {d.get('filas_fact_servicio', 0):,} filas en la tabla de hechos.
""".replace(",", ".")


def main():
    partes = [
        "% Generado automaticamente por src/08_generar_tablas_latex.py",
        "% NO editar a mano: se sobrescribe en cada ejecucion.",
        "",
        "\\subsection*{Resultados de la ingesta (OE1)}",
        tabla_ingesta(leer("informe_ingesta_bronze.json")),
        "\\subsection*{Resultados del procesamiento (OE2)}",
        tabla_calidad(leer("informe_calidad_silver.json")),
        "\\subsection*{Resultados del modelado analitico (OE3)}",
        tabla_latencia(leer("resultados_redshift.json")),
    ]
    destino = EV / "tablas_resultados.tex"
    destino.write_text("\n".join(partes), encoding="utf-8")
    print(f"\n>>> Escrito {destino}")
    print(">>> Copialo a la carpeta de Overleaf y anade  \\input{tablas_resultados}")
    print(">>> en la seccion 4.7 de capitulos/Desarrollo.tex")


if __name__ == "__main__":
    main()
