import os
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("pronostico/graficos", exist_ok=True)

# Gráfico 1: error por modelo (valores de la tabla, octubre a diciembre)
modelos = ["Regresión de Poisson", "Promedio histórico", "KNN", "Random Forest", "LightGBM"]
mae = [1.853, 1.760, 1.730, 1.705, 1.629]
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.barh(modelos, mae, color=["#9aa5b1"] * 4 + ["#0E7490"])
for i, v in enumerate(mae):
    ax.text(v + 0.02, i, f"{v:.3f}", va="center")
ax.set_xlim(0, 2.2)
ax.set_title("Error medio por modelo (viajes por estación y hora, menor es mejor)")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig("pronostico/graficos/error_por_modelo.png", dpi=200)

# Gráfico 2: real contra predicción, estación 14, semana del 6 al 12 de octubre
t = pd.read_parquet("pronostico/predicciones_test_clima.parquet")
s = t[(t["estacion"] == 14) & (t["hora"] >= "2025-10-06") & (t["hora"] < "2025-10-13")]
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(s["hora"], s["viajes"], label="Real", color="#14213D", lw=1.2)
ax.plot(s["hora"], s["pred"], label="Predicción", color="#0E7490", lw=1.2, ls="--")
ax.set_title("Estación 14 (Pacífico): viajes por hora, semana del 6 al 12 de octubre")
ax.legend()
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig("pronostico/graficos/real_vs_prediccion.png", dpi=200)

print("MAE de esa semana y estación:", round((s["viajes"] - s["pred"]).abs().mean(), 3))