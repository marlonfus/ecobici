import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql://ecobici:ecobici_pass@127.0.0.1:5432/ecobici_db")

sql = """
SELECT estacion_origen AS estacion,
       date_trunc('hour', fecha_origen) AS hora,
       COUNT(*) AS viajes
FROM viajes
WHERE estacion_origen IN (
    SELECT estacion_origen FROM viajes
    GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 20
)
GROUP BY 1, 2
ORDER BY 1, 2
"""

df = pd.read_sql(sql, engine)
df.to_parquet("pronostico/demanda_hora.parquet")
print(df.shape)
print(df.head())