"""
Paso 5: orquestación del pipeline con Prefect.
Encadena ingesta -> carga a PostGIS -> corrección de estaciones faltantes,
con reintentos automáticos y logging centralizado.
"""

import fix_estaciones_faltantes
import ingest
import load_to_postgis
from prefect import flow, get_run_logger, task


@task(retries=2, retry_delay_seconds=30, name="ingesta")
def tarea_ingesta() -> None:
    logger = get_run_logger()
    logger.info("Descargando datos crudos de EcoBici...")
    ingest.main()
    logger.info("Ingesta completada.")


@task(retries=1, retry_delay_seconds=15, name="carga-postgis")
def tarea_carga() -> None:
    logger = get_run_logger()
    logger.info("Cargando estaciones y viajes a PostGIS...")
    load_to_postgis.main()
    logger.info("Carga completada.")


@task(retries=1, retry_delay_seconds=15, name="completar-estaciones")
def tarea_completar_estaciones() -> None:
    logger = get_run_logger()
    logger.info("Completando estaciones faltantes a partir de los viajes...")
    fix_estaciones_faltantes.main()
    logger.info("Estaciones completadas.")


@flow(name="pipeline-ecobici")
def pipeline_ecobici() -> None:
    tarea_ingesta()
    tarea_carga()
    tarea_completar_estaciones()


if __name__ == "__main__":
    pipeline_ecobici()
