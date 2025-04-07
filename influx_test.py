from pymongo import MongoClient

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import random
import time

# --- KONFIG INFLUXDB ---
influx_token = "1KxV0hegynMaC0nq9Zb6USPXM6VfcofJo6ZW4d5gL4ghQUS09FhNjCsTNjD2cYZVVfOLjfpE-pTT-bM4QpsICQ=="
influx_org = "czworka"
influx_bucket = "dane_wilgotnosci"
influx_url = "http://localhost:8086"

# --- KONFIG MONGODB ---
mongo_url = "mongodb://localhost:27017"
mongo_client = MongoClient(mongo_url)
mongo_db = mongo_client["roslinki_monitor"]
plants = mongo_db["roslinki"]

# zapis danych
def zapis_danych():
    client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    for i in range(100):
        value = random.random() * 100
        point = (
            Point("wilgotnosc")
            .tag("id_rosliny", "1")
            .field("wartosc", value)
        )
        write_api.write(bucket=influx_bucket, org=influx_org, record=point)
        time.sleep(0.1)


# --- POBIERZ ZAKRES WILGOTNOŚCI Z MONGODB ---
def pobierz_zakres(plant_id):
    roslina = plants.find_one({"_id": plant_id})
    return roslina["optymalne_nawodnienie"]["min"], roslina["optymalne_nawodnienie"]["max"]

# --- POBIERZ OSTATNI POMIAR Z INFLUXDB ---
def pobierz_ostatni_pomiar(plant_id):
    client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
    query_api = client.query_api()

    query = f'''
    from(bucket: "{influx_bucket}")
      |> range(start: -1d)
      |> filter(fn: (r) => r._measurement == "wilgotnosc")
      |> filter(fn: (r) => r.id_rosliny == "{plant_id}")
      |> last()
    '''

    result = query_api.query(query, org=influx_org)
    for table in result:
        for record in table.records:
            return record.get_value()
    return None

# --- PORÓWNANIE ---
def sprawdz_wilgotnosc(plant_id):
    min_val, max_val = pobierz_zakres(plant_id)
    pomiar = pobierz_ostatni_pomiar(plant_id)

    if pomiar is None:
        print("❌ Brak pomiaru!")
        return

    print(f"📋 Pomiar: {pomiar:.1f}% | Zakres: {min_val}-{max_val}%")

    if pomiar < min_val:
        print("🔥 ZA SUCHO! PODLEJ!")
    elif pomiar > max_val:
        print("💦 ZA MOKRO! Nie przelewaj.")
    else:
        print("🌿 Wszystko git, roślinka chilluje.")

# --- TEST ---
sprawdz_wilgotnosc("1")
