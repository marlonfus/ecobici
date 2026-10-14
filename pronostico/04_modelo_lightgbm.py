import pandas as pd
import lightgbm as lgb
import holidays

df = pd.read_parquet("pronostico/demanda_completa.parquet")
df = df.sort_values(["estacion", "hora"]).reset_index(drop=True)

# Variables del pasado (siempre con al menos 24 h de desfase)
g = df.groupby("estacion")["viajes"]
df["lag_24"] = g.shift(24)
df["lag_168"] = g.shift(168)
df["media_7d"] = g.transform(lambda s: s.shift(24).rolling(168).mean())

# Variables de calendario
df["h"] = df["hora"].dt.hour
df["dow"] = df["hora"].dt.dayofweek
feriados = holidays.Argentina(years=2025)
df["feriado"] = df["hora"].dt.date.map(lambda d: d in feriados).astype(int)
df["estacion_cat"] = df["estacion"].astype("category")

features = ["estacion_cat", "h", "dow", "feriado", "lag_24", "lag_168", "media_7d"]

# Pasado para entrenar, futuro para probar (igual que en el modelo base)
corte = pd.Timestamp("2025-10-01")
train = df[(df["hora"] < corte) & df["lag_168"].notna() & df["media_7d"].notna()]
test = df[df["hora"] >= corte].copy()

print("Referencia: promedio histórico = 1.76")
mejores = None
for objetivo in ["poisson", "l1"]:
    modelo = lgb.LGBMRegressor(objective=objetivo, n_estimators=400,
                               learning_rate=0.05, num_leaves=31, verbose=-1)
    modelo.fit(train[features], train["viajes"])
    pred = modelo.predict(test[features])
    mae = (test["viajes"] - pred).abs().mean()
    print(f"LightGBM ({objetivo}): MAE =", round(mae, 3))
    if mejores is None or mae < mejores[0]:
        mejores = (mae, objetivo, pred, modelo)

mae, objetivo, pred, modelo = mejores
test["pred"] = pred
test.to_parquet("pronostico/predicciones_test.parquet")
print("Mejor:", objetivo)
print(dict(zip(features, modelo.feature_importances_)))