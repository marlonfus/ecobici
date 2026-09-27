"""
Paso 4: modelado y carga a PostGIS.
Carga 'estaciones' (dimensión, con geometría) y 'viajes' (hechos) desde
los CSV crudos hacia la base ecobici_db.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://ecobici:ecobici_pass@localhost:5432/ecobici_db"
CHUNK_SIZE = 200_000  # filas leídas por lote desde el CSV de viajes
SQL_BATCH = 5_000     # filas por INSERT al escribir en Postgres


def read_csv_robust(path: Path, **kwargs) -> pd.DataFrame:
    for encoding in ("utf-8", "utf-8-sig", "latin1"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"No se pudo leer {path} con ninguna codificación probada")


def extract_station_number(series: pd.Series) -> pd.Series:
    """Convierte '146BAEcobici' o '26' en el entero 146 o 26."""
    return series.astype(str).str.extract(r"(\d+)")[0].astype("Int64")


def load_estaciones(engine, path: Path) -> None:
    print("Cargando estaciones...")
    df = read_csv_robust(path)

    # Si alguna de estas columnas viene vacía en todas las filas, pandas
    # infiere el tipo como numérico (double precision) en vez de texto.
    # Forzamos texto explícitamente para que el tipo de columna sea estable
    # entre corridas, incluso si la tabla se recrea desde cero.
    for col in ("nombre", "direccion", "barrio", "comuna", "emplazamiento"):
        if col in df.columns:
            df[col] = df[col].astype("string")

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitud"], df["latitud"]),
        crs="EPSG:4326",
    )
    gdf = gdf.drop(columns=["latitud", "longitud"])
    gdf.to_postgis("estaciones", engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_estaciones_geom "
            "ON estaciones USING GIST (geometry)"
        ))
    print(f"  {len(gdf)} estaciones cargadas.")


def load_viajes(engine, path: Path) -> None:
    print("Cargando viajes (por lotes, puede tardar varios minutos)...")
    first_chunk = True
    total = 0
    for chunk in pd.read_csv(
        path, encoding="utf-8", chunksize=CHUNK_SIZE, low_memory=False
    ):
        clean = pd.DataFrame({
            "id_recorrido": chunk["Id_recorrido"],
            "duracion_seg": pd.to_numeric(chunk["duracion_recorrido"], errors="coerce"),
            "fecha_origen": pd.to_datetime(chunk["fecha_origen_recorrido"], errors="coerce"),
            "fecha_destino": pd.to_datetime(chunk["fecha_destino_recorrido"], errors="coerce"),
            "estacion_origen": extract_station_number(chunk["id_estacion_origen"]),
            "estacion_destino": extract_station_number(chunk["id_estacion_destino"]),
            "id_usuario": chunk["id_usuario"],
            "modelo_bicicleta": chunk["modelo_bicicleta"],
            "genero": chunk["género"],
        })
        clean.to_sql(
            "viajes",
            engine,
            if_exists="replace" if first_chunk else "append",
            index=False,
            method="multi",
            chunksize=SQL_BATCH,
        )
        first_chunk = False
        total += len(clean)
        print(f"  ... {total:,} viajes cargados")
    print(f"Total final: {total:,} viajes.")


def main() -> None:
    engine = create_engine(DB_URL)
    raw_root = Path("raw")
    latest_dir = max(raw_root.iterdir(), key=lambda p: p.name)
    print(f"Usando carpeta: {latest_dir}")

    load_estaciones(engine, latest_dir / "estaciones.csv")
    load_viajes(engine, latest_dir / "Trips.csv")

    with engine.begin() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_viajes_origen ON viajes (estacion_origen)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_viajes_destino ON viajes (estacion_destino)"
        ))
    print("Listo. Índices creados sobre estaciones y viajes.")


if __name__ == "__main__":
    main()
