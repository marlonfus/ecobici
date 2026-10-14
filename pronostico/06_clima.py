import requests
import pandas as pd

url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude": -34.61, "longitude": -58.42,
    "start_date": "2025-01-01", "end_date": "2025-12-31",
    "hourly": "temperature_2m,precipitation",
    "timezone": "America/Argentina/Buenos_Aires",
}
r = requests.get(url, params=params, timeout=60)
r.raise_for_status()
h = r.json()["hourly"]

clima = pd.DataFrame({
    "hora": pd.to_datetime(h["time"]),
    "temp": h["temperature_2m"],
    "lluvia": h["precipitation"],
})
clima.to_parquet("pronostico/clima_hora.parquet")
print(clima.shape)
print(clima.describe().round(1))
print("Horas con lluvia:", int((clima["lluvia"] > 0).sum()))