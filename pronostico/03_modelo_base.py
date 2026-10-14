import pandas as pd

df = pd.read_parquet("pronostico/demanda_completa.parquet")
df = df.sort_values(["estacion", "hora"]).reset_index(drop=True)

# Lo que pasó hace una semana (168 horas) en la misma estación
df["lag_168"] = df.groupby("estacion")["viajes"].shift(168)
df["dow"] = df["hora"].dt.dayofweek
df["h"] = df["hora"].dt.hour

# Pasado para entrenar, futuro para probar
corte = pd.Timestamp("2025-10-01")
train = df[df["hora"] < corte]
test = df[df["hora"] >= corte].copy()

# Promedio histórico por estación, día de la semana y hora (solo con el pasado)
prom = (train.groupby(["estacion", "dow", "h"])["viajes"]
        .mean().rename("prom_hist").reset_index())
test = test.merge(prom, on=["estacion", "dow", "h"], how="left")

mae_cero = test["viajes"].abs().mean()
mae_semana = (test["viajes"] - test["lag_168"]).abs().mean()
mae_prom = (test["viajes"] - test["prom_hist"]).abs().mean()

print("Filas de prueba:", len(test))
print("MAE siempre 0:           ", round(mae_cero, 3))
print("MAE semana pasada:       ", round(mae_semana, 3))
print("MAE promedio histórico:  ", round(mae_prom, 3))