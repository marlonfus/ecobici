import pandas as pd

df = pd.read_parquet("pronostico/demanda_hora.parquet")

horas = pd.date_range("2025-01-01 00:00", "2025-12-31 23:00", freq="h")
estaciones = df["estacion"].unique()

grilla = pd.MultiIndex.from_product(
    [estaciones, horas], names=["estacion", "hora"]
).to_frame(index=False)

df = grilla.merge(df, on=["estacion", "hora"], how="left")
df["viajes"] = df["viajes"].fillna(0).astype(int)

df.to_parquet("pronostico/demanda_completa.parquet")
print(df.shape)
print(df["viajes"].describe())
print("Proporción de horas con 0 viajes:", round((df["viajes"] == 0).mean(), 3))