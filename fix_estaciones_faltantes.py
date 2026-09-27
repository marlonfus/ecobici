"""
Corrige estaciones faltantes: algunas estaciones referenciadas en los
viajes de 2025 no están en el listado oficial de estaciones activas
(probablemente dadas de baja o renumeradas desde entonces). Las
reconstruimos usando el nombre y las coordenadas que vienen embebidos
en el propio archivo de viajes.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine

DB_URL = "postgresql+psycopg2://ecobici:ecobici_pass@localhost:5432/ecobici_db"
CHUNK_SIZE = 200_000


def extract_station_number(series: pd.Series) -> pd.Series:
    return series.astype(str).str.extract(r"(\d+)")[0].astype("Int64")


def main() -> None:
    engine = create_engine(DB_URL)
    raw_root = Path("raw")
    latest_dir = max(raw_root.iterdir(), key=lambda p: p.name)
    trips_path = latest_dir / "Trips.csv"

    with engine.connect() as conn:
        existing = pd.read_sql("SELECT numero_de_estacion FROM estaciones", conn)
    known_ids = set(existing["numero_de_estacion"].dropna().astype(int))
    print(f"Estaciones oficiales conocidas: {len(known_ids)}")

    missing: dict[int, tuple[str, float, float]] = {}

    for chunk in pd.read_csv(
        trips_path, encoding="utf-8", chunksize=CHUNK_SIZE, low_memory=False
    ):
        for prefix in ("origen", "destino"):
            nums = extract_station_number(chunk[f"id_estacion_{prefix}"])
            sub = pd.DataFrame({
                "numero": nums,
                "nombre": chunk[f"nombre_estacion_{prefix}"],
                "lat": chunk[f"lat_estacion_{prefix}"],
                "lon": chunk[f"long_estacion_{prefix}"],
            }).dropna(subset=["numero", "lat", "lon"])
            nuevas = sub[~sub["numero"].isin(known_ids)].drop_duplicates("numero")
            for _, row in nuevas.iterrows():
                num = int(row["numero"])
                missing.setdefault(num, (row["nombre"], row["lat"], row["lon"]))
        print(f"  ... estaciones faltantes detectadas hasta ahora: {len(missing)}")

    print(f"Total de estaciones faltantes a agregar: {len(missing)}")

    if missing:
        df = pd.DataFrame([
            {
                "numero_de_estacion": num,
                "nombre": nombre,
                "direccion": None,
                "barrio": None,
                "comuna": None,
                "emplazamiento": "inferida_de_viajes",
                "lat": lat,
                "lon": lon,
            }
            for num, (nombre, lat, lon) in missing.items()
        ])
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df["lon"], df["lat"]),
            crs="EPSG:4326",
        ).drop(columns=["lat", "lon"])
        gdf.to_postgis("estaciones", engine, if_exists="append", index=False)
        print(f"  {len(gdf)} estaciones agregadas a la tabla 'estaciones'.")

    print("Listo.")


if __name__ == "__main__":
    main()
