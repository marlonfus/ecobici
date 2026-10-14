# Pronóstico de demanda de EcoBici (Buenos Aires)

Pronóstico de cuántos viajes salen de cada estación, hora por hora, con un día de anticipación. Usa la base geoespacial que arma el pipeline de este repositorio (PostGIS + Prefect) con los viajes de 2025.

## Pregunta

¿Cuántos viajes van a salir de una estación en una hora determinada, sabiendo lo que pasó hasta ayer, el calendario y el clima?

## Datos

- Más de 3,1 millones de viajes de 2025, de los datos abiertos de la Ciudad, ya limpios en PostGIS.
- Se modelan las 20 estaciones con más viajes.
- Tabla final: 20 estaciones x 8.760 horas = 175.200 filas. Las horas sin viajes se completan con 0 (36 % de las filas); si no, el modelo ve una demanda inflada.
- Clima horario (temperatura y precipitación) de Open-Meteo.

## Variables

Calendario (hora, día de la semana, feriado), viajes de hace 24 y 168 horas, promedio móvil de 7 días (con 24 horas de desfase) y clima. Ninguna variable usa información posterior al momento del pronóstico, salvo el clima, que es el real (ver limitaciones).

## Validación

- Entrenamiento: enero a septiembre. Prueba: octubre a diciembre (44.160 predicciones). Nunca se mezclan fechas al azar.
- Para comparar modelos, se entrena con enero a agosto y se evalúa en septiembre. Con eso se elige el modelo; recién después se mira octubre a diciembre.
- Métrica: error absoluto medio (MAE), en viajes por estación y hora.

## Resultados

| Modelo | MAE septiembre | MAE oct-dic |
|---|---|---|
| Siempre 0 | - | 3,006 |
| Lo mismo que la semana pasada | - | 2,227 |
| Promedio histórico (estación, día, hora) | 1,597 | 1,760 |
| Regresión de Poisson | 1,681 | 1,853 |
| KNN (k=30) | 1,592 | 1,730 |
| Random Forest | 1,578 | 1,705 |
| **LightGBM (objetivo Poisson)** | **1,512** | **1,629** |

LightGBM mejora un 7,4 % al promedio histórico en octubre a diciembre y un 5,3 % en septiembre. Sin clima, LightGBM da 1,691. Todos los modelos, salvo el promedio histórico, usan las mismas variables, incluido el clima. Los modelos no tienen ajuste de parámetros.

## Limitaciones

- Un solo año de datos y un solo corte de entrenamiento y prueba.
- El clima es el real, no un pronóstico: la mejora que aporta es un techo.
- El objetivo Poisson y el uso del clima se eligieron mirando octubre a diciembre, así que el 1,629 es algo optimista. La comparación entre modelos sí se decidió con septiembre.
- Lo que se predice son retiros, no faltantes de bicis. Para eso habría que sumar las llegadas (`estacion_destino`).
- El modelo sigue el ritmo del día pero se queda corto en los picos de demanda.
- Con 2 o 3 viajes por estación y hora hay mucho azar que ningún modelo puede eliminar.

## Cómo reproducirlo

1. Levantar la base: `docker compose up -d` y cargar los datos con el pipeline.
2. Instalar: `pip install pandas sqlalchemy psycopg2-binary pyarrow lightgbm holidays scikit-learn requests matplotlib`
3. Ajustar el puerto de conexión en `pronostico/01_extraer_demanda.py` (en `docker-compose.yml` figura el que expone la base).
4. Correr en orden los scripts de `pronostico/`:
   - `01_extraer_demanda.py`: viajes por estación y hora desde PostGIS
   - `02_rellenar_ceros.py`: grilla completa estación x hora
   - `03_modelo_base.py`: referencias simples
   - `04_modelo_lightgbm.py`: primer modelo de Machine Learning
   - `05_analisis_errores.py`: errores por franja, estación y día
   - `06_clima.py`: clima horario
   - `07_modelo_con_clima.py`: modelo con y sin clima
   - `08_comparar_modelos.py`: comparación de cuatro modelos con validación
   - `09_graficos.py`: gráficos

## Próximos pasos

- Sumar las llegadas para calcular el flujo neto por estación.
- Probar con un pronóstico de clima en lugar del clima real.
- Ajustar parámetros con validación temporal y medir la incertidumbre de las predicciones.
