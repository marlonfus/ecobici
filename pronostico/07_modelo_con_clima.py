import pandas as pd
import lightgbm as lgb
import holidays

df = pd.read_parquet("pronostico/demanda_completa.parquet")
clima = pd.read_parquet("pronostico/clima_hora.parquet")
df = df.merge(clima, on="hora", how="left")
df = df.sort_values(["estacion", "hora"]).reset_index(drop=True)

g = df.groupby("estacion")["viajes"]
df["lag_24"] = g.shift(24)
df["lag_168"] = g.shift(168)
df["media_7d"] = g.transform(lambda s: s.shift(24).rolling(168).mean())
df["h"] = df["hora"].dt.hour
df["dow"] = df["hora"].dt.dayofweek
feriados = holidays.Argentina(years=2025)
df["feriado"] = df["hora"].dt.date.map(lambda d: d in feriados).astype(int)
df["estacion_cat"] = df["estacion"].astype("category")

base = ["estacion_cat", "h", "dow", "feriado", "lag_24", "lag_168", "media_7d"]
con_clima = base + ["temp", "lluvia"]

corte = pd.Timestamp("2025-10-01")
train = df[(df["hora"] < corte) & df["lag_168"].notna() & df["media_7d"].notna()]
test = df[df["hora"] >= corte].copy()

print("Referencia: promedio histórico = 1.76")
for nombre, feats in [("sin clima", base), ("con clima", con_clima)]:
    m = lgb.LGBMRegressor(objective="poisson", n_estimators=400,
                          learning_rate=0.05, num_leaves=31, verbose=-1)
    m.fit(train[feats], train["viajes"])
    pred = m.predict(test[feats])
    mae = (test["viajes"] - pred).abs().mean()
    sesgo = (pred - test["viajes"]).mean()
    print(f"LightGBM {nombre}: MAE = {mae:.3f} | sesgo = {sesgo:.3f}")
    if nombre == "con clima":
        test["pred"] = pred
        test.to_parquet("pronostico/predicciones_test_clima.parquet")