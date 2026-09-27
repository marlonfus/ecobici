"""
Paso 3 del pipeline EcoBici: capa de ingesta (raw).
Descarga los datasets crudos desde data.buenosaires.gob.ar y los guarda
sin transformar, versionados por fecha de descarga.
"""

import zipfile
from datetime import date
from pathlib import Path

import requests

# URLs verificadas en el portal de datos abiertos de Buenos Aires.
SOURCES = {
    "estaciones.csv": (
        "https://data.buenosaires.gob.ar/id/dataset/estaciones-bicicletas-publicas"
        "/resource/1d21a28a-bb2b-4ddb-b00b-77f82f3e34fb/download"
    ),
    "recorridos_2025.zip": (
        "https://data.buenosaires.gob.ar/id/dataset/bicicletas-publicas"
        "/resource/d860362d-99f9-49a2-9ea0-1afd65581a97/download"
    ),
}

RAW_DIR = Path("raw") / str(date.today())

# El sitio bloquea pedidos que no parecen venir de un navegador real,
# así que nos identificamos como uno.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Referer": "https://data.buenosaires.gob.ar/",
}


def download(url: str, dest_path: Path) -> None:
    print(f"Descargando {dest_path.name}...")
    session = requests.Session()
    # Primero visitamos el sitio para que nos den las cookies de sesión
    # que el firewall espera ver en el pedido siguiente.
    session.get("https://data.buenosaires.gob.ar/", headers=HEADERS, timeout=30)
    response = session.get(url, headers=HEADERS, timeout=180)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if "text/html" in content_type:
        raise RuntimeError(
            f"El servidor devolvió HTML en vez del archivo esperado "
            f"(posible bloqueo). Primeros 200 caracteres:\n{response.text[:200]}"
        )
    dest_path.write_bytes(response.content)
    size_kb = len(response.content) / 1024
    print(f"  guardado en {dest_path} ({size_kb:.1f} KB)")


def extract_if_zip(path: Path) -> None:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            archive.extractall(path.parent)
        print(f"  descomprimido en {path.parent}")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in SOURCES.items():
        dest = RAW_DIR / filename
        download(url, dest)
        extract_if_zip(dest)
    print(f"\nListo. Archivos crudos disponibles en: {RAW_DIR}")


if __name__ == "__main__":
    main()
