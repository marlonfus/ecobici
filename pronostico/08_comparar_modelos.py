import time
import pandas as pd
import lightgbm as lgb
import holidays
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import PoissonRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import RandomForestRegressor

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

full = df.copy()  # para el promedio histórico, con todas las filas
df = df.dropna(subset=["lag_168", "media_7d"]).reset_index(drop=True)

etapas = {
    "val": (pd.Timestamp("2025-09-01"), pd.Timestamp("2025-09-01"), pd.Timestamp("2025-10-01")),
    "test": (pd.Timestamp("2025-10-01"), pd.Timestamp("2025-10-01"), pd.Timestamp("2026-01-01")),
}

cat = ["estacion", "h", "dow"]
num = ["feriado", "lag_24", "lag_168", "media_7d", "temp", "lluvia"]
cols = cat + num
cols_lgb = ["estacion_cat", "h", "dow"] + num

def prep():
    return ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), cat),
                              ("n", StandardScaler(), num)])

modelos = {
    "Regresión de Poisson": (lambda: make_pipeline(prep(), PoissonRegressor(alpha=1e-4, max_iter=500)), cols),
    "KNN (k=30)": (lambda: make_pipeline(prep(), KNeighborsRegressor(n_neighbors=30, n_jobs=-1)), cols),
    "Random Forest": (lambda: RandomForestRegressor(n_estimators=150, min_samples_leaf=10, n_jobs=-1, random_state=0), cols),
    "LightGBM (poisson)": (lambda: lgb.LGBMRegressor(objective="poisson", n_estimators=400, learning_rate=0.05, num_leaves=31, verbose=-1), cols_lgb),
}

filas = []

# Referencia: promedio histórico por estación, día de la semana y hora
fila = {"modelo": "Promedio histórico"}
for etapa, (corte, ini, fin) in etapas.items():
    tr = full[full["hora"] < corte]
    ev = full[(full["hora"] >= ini) & (full["hora"] < fin)]
    p = tr.groupby(["estacion", "dow", "h"])["viajes"].mean().rename("b").reset_index()
    e = ev.merge(p, on=["estacion", "dow", "h"], how="left")
    fila[f"MAE {etapa}"] = round((e["viajes"] - e["b"]).abs().mean(), 3)
filas.append(fila)

for nombre, (fabrica, columnas) in modelos.items():
    t0 = time.time()
    fila = {"modelo": nombre}
    for etapa, (corte, ini, fin) in etapas.items():
        tr = df[df["hora"] < corte]
        ev = df[(df["hora"] >= ini) & (df["hora"] < fin)]
        m = fabrica()
        m.fit(tr[columnas], tr["viajes"])
        p = m.predict(ev[columnas])
        fila[f"MAE {etapa}"] = round((ev["viajes"] - p).abs().mean(), 3)
        if etapa == "test":
            fila["sesgo test"] = round((p - ev["viajes"]).mean(), 3)
    filas.append(fila)
    print(f"{nombre} listo ({time.time() - t0:.0f} s)", flush=True)

print()
print(pd.DataFrame(filas).to_string(index=False))