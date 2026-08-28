"""
FASE 3a - Construccion de la dimension de zonas enriquecida con OpenStreetMap.

Cruza la tabla de zonas de la TLC con su geometria (shapefile) y anade
atributos de red viaria obtenidos de OSM mediante OSMnx.

Salida: datos/silver/dim_zona.parquet

Uso:  python src/03_dimension_zonas.py
"""

import sys
import time
from pathlib import Path

import pandas as pd
import geopandas as gpd

sys.path.append(str(Path(__file__).parent.parent))
import config


def cargar_zonas():
    """Carga el shapefile de zonas y lo reproyecta a WGS84.

    Descomprime primero a disco: la lectura directa del ZIP falla en Windows.
    Si el fichero esta corrupto o incompleto, devuelve None y el proceso
    continua sin coordenadas.
    """
    import zipfile

    ruta_zip = config.RUTA_RAW / "taxi_zones.zip"
    destino = config.RUTA_RAW / "taxi_zones"

    if not ruta_zip.exists():
        print("  [aviso] no existe taxi_zones.zip")
        return None

    try:
        with zipfile.ZipFile(ruta_zip) as z:
            z.extractall(destino)
    except zipfile.BadZipFile:
        print("  [aviso] taxi_zones.zip esta corrupto. Borralo y vuelve a")
        print("          ejecutar 01_descarga_datos.py para descargarlo de nuevo.")
        return None

    shp = list(destino.rglob("*.shp"))
    if not shp:
        print("  [aviso] no se encontro ningun .shp dentro del zip")
        return None

    print(f"  [ok] leyendo {shp[0].name}")
    gdf = gpd.read_file(shp[0])
    return gdf.to_crs(epsg=4326)


def enriquecer_con_osm(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Anade metricas de red viaria por zona.

    OJO: descargar el grafo de las 260+ zonas tarda. Para la primera
    ejecucion, prueba con las 10 primeras (parametro limite).
    """
    import osmnx as ox

    filas = []
    for _, z in gdf.iterrows():
        try:
            g = ox.graph_from_polygon(z.geometry, network_type="drive", simplify=True)
            stats = ox.basic_stats(g)
            filas.append({
                "id_zona": int(z["LocationID"]),
                "long_via_km": round(stats["edge_length_total"] / 1000, 2),
                "n_intersecciones": stats["n"],
                "densidad_interseccion": round(stats["n"] / z.geometry.area, 2)
                if z.geometry.area else None,
            })
        except Exception as e:
            print(f"  [aviso] zona {z['LocationID']} sin grafo OSM: {e}")
            filas.append({"id_zona": int(z["LocationID"]), "long_via_km": None,
                          "n_intersecciones": None, "densidad_interseccion": None})
    return pd.DataFrame(filas)


def main(con_osm: bool = True):
    t0 = time.time()

    lookup = pd.read_csv(config.RUTA_RAW / "taxi_zone_lookup.csv")
    gdf = cargar_zonas()

    if gdf is None:
        # Sin geometria: la dimension se queda sin coordenadas. Se pierden el
        # factor de rodeo y la distancia geodesica; los demas KPI no se ven
        # afectados. Declarar esta limitacion en la memoria.
        print("  [degradado] dimension sin coordenadas geograficas")
        con_osm = False
        lookup["lat"] = None
        lookup["lon"] = None
        cent = None
    else:
        proj = gdf.to_crs(epsg=2263)
        gdf["lat"] = proj.geometry.centroid.to_crs(epsg=4326).y
        gdf["lon"] = proj.geometry.centroid.to_crs(epsg=4326).x
        cent = gdf

    if cent is not None:
        dim = lookup.merge(
            cent[["LocationID", "lat", "lon"]], on="LocationID", how="left")
    else:
        dim = lookup
    dim = dim.rename(columns={
        "LocationID": "id_zona",
        "Borough": "distrito",
        "Zone": "nombre_zona",
        "service_zone": "zona_servicio",
    })

    if con_osm:
        print("Descargando red viaria de OSM por zona (esto tarda)...")
        osm = enriquecer_con_osm(gdf)
        dim = dim.merge(osm, on="id_zona", how="left")
    else:
        dim["long_via_km"] = None
        dim["n_intersecciones"] = None
        dim["densidad_interseccion"] = None

    # Clave subrogada, requisito del modelo dimensional de Kimball
    dim = dim.sort_values("id_zona").reset_index(drop=True)
    dim.insert(0, "sk_zona", range(1, len(dim) + 1))

    destino = config.RUTA_SILVER / "dim_zona.parquet"
    dim.to_parquet(destino, index=False)

    print(f"\nDimension de zonas: {len(dim)} filas -> {destino}")
    print(dim.head(10).to_string())
    print(f"Tiempo: {time.time()-t0:.1f} s")


if __name__ == "__main__":
    # Cambia a False si quieres saltarte el enriquecimiento OSM en pruebas
    # OSM desactivado por defecto: anade horas y es lo primero recortable.
    main(con_osm=False)
