
from abc import ABC, abstractmethod
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
plants_collection = mongo_db["roslinki"]

# --- Interfejsy ---
class SensorDataSource(ABC):
    @abstractmethod
    def get_latest_reading(self, plant_id: str) -> float:
        pass

    @abstractmethod
    def record_random_data(self, plant_id: str, count: int = 100):
        pass


class PlantRepository(ABC):
    @abstractmethod
    def get_optimal_range(self, plant_id: str) -> tuple:
        pass

# --- Implementacja: InfluxDB jako źródło danych ---
class InfluxSensorDataSource(SensorDataSource):
    def __init__(self):
        self.client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)

    def get_latest_reading(self, plant_id: str) -> float:
        query_api = self.client.query_api()
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

    def record_random_data(self, plant_id: str, count: int = 100):
        write_api = self.client.write_api(write_options=SYNCHRONOUS)
        for _ in range(count):
            value = random.random() * 100
            point = (
                Point("wilgotnosc")
                .tag("id_rosliny", plant_id)
                .field("wartosc", value)
            )
            write_api.write(bucket=influx_bucket, org=influx_org, record=point)
            time.sleep(0.1)

# --- Implementacja: MongoDB jako repozytorium roślin ---
class MongoPlantRepository(PlantRepository):
    def __init__(self, collection):
        self.collection = collection

    def get_optimal_range(self, plant_id: str) -> tuple:
        roslina = self.collection.find_one({"_id": plant_id})
        return roslina["optymalne_nawodnienie"]["min"], roslina["optymalne_nawodnienie"]["max"]

# --- Logika porównawcza ---
class WilgotnoscChecker:
    def __init__(self, sensor: SensorDataSource, repository: PlantRepository):
        self.sensor = sensor
        self.repository = repository

    def sprawdz_wilgotnosc(self, plant_id: str):
        min_val, max_val = self.repository.get_optimal_range(plant_id)
        pomiar = self.sensor.get_latest_reading(plant_id)

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
sensor = InfluxSensorDataSource()
repo = MongoPlantRepository(plants_collection)
checker = WilgotnoscChecker(sensor, repo)
checker.sprawdz_wilgotnosc("1")
