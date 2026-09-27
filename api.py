"""
Paso 6: API geoespacial.
Expone estaciones y viajes de EcoBici via FastAPI + PostGIS, con consultas
espaciales reales (ST_DWithin, ST_Distance) sobre los datos cargados.

Correr con: uvicorn api:app --reload
Documentacion interactiva en: http://127.0.0.1:8000/docs
"""

import json

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://ecobici:ecobici_pass@localhost:5432/ecobici_db"
engine = create_engine(DB_URL)

app = FastAPI(
    title="EcoBici API",
    description="API geoespacial sobre datos reales de bicicletas publicas de Buenos Aires",
)

# Permite que map.html (abierto como archivo local) pueda pedirle datos
# a esta API sin que el navegador lo bloquee por CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _a_geojson(rows, propiedades: list[str]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(row.geom_json),
                "properties": {campo: getattr(row, campo) for campo in propiedades},
            }
            for row in rows
        ],
    }


@app.get("/")
def raiz():
    return {"mensaje": "EcoBici API. Ver /docs para la documentacion interactiva."}


@app.get("/estaciones")
def listar_estaciones():
    """Todas las estaciones, como GeoJSON (puntos)."""
    query = text("""
        SELECT numero_de_estacion, nombre, barrio,
               ST_AsGeoJSON(geometry) AS geom_json
        FROM estaciones
        ORDER BY numero_de_estacion
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return _a_geojson(rows, ["numero_de_estacion", "nombre", "barrio"])


@app.get("/estaciones/cerca")
def estaciones_cerca(
    lat: float = Query(..., description="Latitud del punto de referencia"),
    lon: float = Query(..., description="Longitud del punto de referencia"),
    radio_m: int = Query(500, description="Radio de busqueda en metros"),
):
    """Estaciones dentro de un radio (en metros) de un punto dado."""
    query = text("""
        SELECT numero_de_estacion, nombre, barrio,
               ST_AsGeoJSON(geometry) AS geom_json,
               ROUND(ST_Distance(
                   geometry::geography, ST_MakePoint(:lon, :lat)::geography
               )::numeric, 1) AS distancia_m
        FROM estaciones
        WHERE ST_DWithin(
            geometry::geography, ST_MakePoint(:lon, :lat)::geography, :radio_m
        )
        ORDER BY distancia_m
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"lat": lat, "lon": lon, "radio_m": radio_m}).fetchall()
    return _a_geojson(rows, ["numero_de_estacion", "nombre", "barrio", "distancia_m"])


@app.get("/viajes/top-estaciones")
def top_estaciones(limite: int = Query(10, le=1000)):
    """Estaciones con mas viajes de origen, de mayor a menor."""
    query = text("""
        SELECT e.numero_de_estacion, e.nombre, e.barrio, COUNT(*) AS cantidad_viajes
        FROM viajes v
        JOIN estaciones e ON v.estacion_origen = e.numero_de_estacion
        GROUP BY e.numero_de_estacion, e.nombre, e.barrio
        ORDER BY cantidad_viajes DESC
        LIMIT :limite
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"limite": limite}).fetchall()
    return [dict(row._mapping) for row in rows]


@app.get("/viajes/por-hora")
def viajes_por_hora():
    """Cantidad total de viajes agrupados por hora del dia (0-23)."""
    query = text("""
        SELECT EXTRACT(HOUR FROM fecha_origen)::int AS hora, COUNT(*) AS cantidad_viajes
        FROM viajes
        WHERE fecha_origen IS NOT NULL
        GROUP BY hora
        ORDER BY hora
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(row._mapping) for row in rows]
