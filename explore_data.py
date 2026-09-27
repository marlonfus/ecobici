"""
Exploración previa a la transformación (paso 4).
Carga estaciones.csv completo y las primeras filas de Trips.csv para
confirmar columnas, tipos y codificación antes de procesar el archivo
completo (que pesa varios cientos de MB).
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd


def read_csv_robust(path: Path, **kwargs) -> pd.DataFrame:
    """Prueba varias codificaciones comunes en datasets del gobierno argentino."""
    last_error = None
    for encoding in ("utf-8", "utf-8-sig", "latin1"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    raise RuntimeError(f"No se pudo leer {path} con ninguna codificación probada") from last_error


def explore_estaciones(path: Path) -> gpd.GeoDataFrame:
    print(f"\n=== Estaciones: {path} ===")
    df = read_csv_robust(path)
    print("Columnas:", list(df.columns))
    print(df.head(3))

    lat_col = next(c for c in df.columns if "lat" in c.lower())
    lon_col = next(c for c in df.columns if c.lower().startswith("lon"))
    print(f"Detectado -> latitud: '{lat_col}', longitud: '{lon_col}'")

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs="EPSG:4326",
    )
    print("Total de estaciones:", len(gdf))
    print("Geometría de ejemplo:", gdf.geometry.iloc[0])
    return gdf


def explore_trips(path: Path, nrows: int = 2000) -> pd.DataFrame:
    print(f"\n=== Viajes (primeras {nrows} filas): {path} ===")
    df = read_csv_robust(path, nrows=nrows, on_bad_lines="warn", engine="python")
    print("Columnas:", list(df.columns))
    print(df.head(3))
    print("\nTipos de dato:")
    print(df.dtypes)
    if "genero" in "".join(df.columns).lower() or any("nero" in c.lower() for c in df.columns):
        genero_col = next(c for c in df.columns if "nero" in c.lower())
        print(f"\nValores únicos en '{genero_col}':", df[genero_col].unique())
    return df


def main() -> None:
    raw_root = Path("raw")
    latest_dir = max(raw_root.iterdir(), key=lambda p: p.name)
    print(f"Usando carpeta más reciente: {latest_dir}")

    explore_estaciones(latest_dir / "estaciones.csv")
    explore_trips(latest_dir / "Trips.csv")


if __name__ == "__main__":
    main()
