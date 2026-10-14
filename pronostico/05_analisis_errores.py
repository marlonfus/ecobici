import pandas as pd

df = pd.read_parquet("pronostico/demanda_completa.parquet")
df["dow"] = df["hora"].dt.dayofweek
df["h"] = df["hora"].dt.hour
corte = pd.Timestamp("2025-10-01")
train = df[df["hora"] < corte]
prom = (train.groupby(["estacion", "dow", "h"])["viajes"]
        .mean().rename("base").reset_index())

t = pd.read_parquet("pronostico/predicciones_test.parquet")[["estacion", "hora", "viajes", "pred"]]
t["dow"] = t["hora"].dt.dayofweek
t["h"] = t["hora"].dt.hour
t = t.merge(prom, on=["estacion", "dow", "h"], how="left")
t["err_modelo"] = (t["viajes"] - t["pred"]).abs()
t["err_base"] = (t["viajes"] - t["base"]).abs()
t["sesgo"] = t["pred"] - t["viajes"]

print("MAE modelo:", round(t["err_modelo"].mean(), 3), "| MAE base:", round(t["err_base"].mean(), 3))

# 1) ¿En cuántos días gana el modelo?
dia = t.groupby(t["hora"].dt.date)[["err_modelo", "err_base"]].mean()
print("\nDías de prueba:", len(dia))
print("Días en que el modelo gana:", int((dia.err_modelo < dia.err_base).sum()))

# 2) Por franja horaria
t["franja"] = pd.cut(t["h"], [-1, 5, 11, 17, 23],
                     labels=["madrugada 0-5", "mañana 6-11", "tarde 12-17", "noche 18-23"])
print("\nPor franja horaria:")
print(t.groupby("franja", observed=True)[["viajes", "err_modelo", "err_base", "sesgo"]].mean().round(3))

# 3) Fin de semana vs semana
t["tipo"] = t["dow"].map(lambda d: "fin de semana" if d >= 5 else "semana")
print("\nSemana vs fin de semana:")
print(t.groupby("tipo")[["viajes", "err_modelo", "err_base", "sesgo"]].mean().round(3))

# 4) Por estación
est = t.groupby("estacion")[["viajes", "err_modelo", "err_base"]].mean().round(3)
est["mejora"] = (est["err_base"] - est["err_modelo"]).round(3)
print("\nPor estación:")
print(est.sort_values("mejora"))