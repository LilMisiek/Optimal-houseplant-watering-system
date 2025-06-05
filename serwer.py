from flask import Flask, request, jsonify
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from pymongo import MongoClient
from config_loader import load_config

# Wczytaj konfigurację
config = load_config()

# --- Flask ---
app = Flask(__name__)

# --- MongoDB ---
mongo_cfg = config.get("mongo", {})
mongo_client = MongoClient(mongo_cfg.get("url", "mongodb://localhost:27017"))
mongo_db = mongo_client[mongo_cfg.get("db", "roslinki_monitor")]
plants = mongo_db[mongo_cfg.get("collection", "roslinki")]

# --- InfluxDB ---
influx_cfg = config.get("influx", {})
influx_client = InfluxDBClient(
    url=influx_cfg.get("url"),
    token=influx_cfg.get("token"),
    org=influx_cfg.get("org")
)
influx_write_api = influx_client.write_api(write_options=SYNCHRONOUS)

@app.route('/api/pomiar', methods=['POST'])
def odbierz_pomiar():
    data = request.json
    plant_id = data.get("plant_id")
    value = data.get("value")

    if not plant_id or value is None:
        return jsonify({"error": "Brakuje danych"}), 400
    print(f"Odebrano dane: plant_id={plant_id}, value={value}")

    # --- Zapis do InfluxDB ---
    try:
        point = (
            Point("wilgotnosc")
            .tag("id_rosliny", str(plant_id))
            .field("wartosc", float(value))
        )
        influx_write_api.write(
            bucket=influx_cfg.get("bucket"),
            org=influx_cfg.get("org"),
            record=point
        )
    except Exception as e:
        print(f"❌ Błąd zapisu do InfluxDB: {e}")
        return jsonify({"error": "Błąd zapisu do InfluxDB"}), 500

    # --- Dane o roślinie z MongoDB ---
    plant = plants.find_one({"_id": str(plant_id)})

    if not plant:
        return jsonify({"error": "Nie znaleziono rośliny w bazie danych"}), 404

    nawodnienie = plant.get("optymalne_nawodnienie", {})
    wilgotnosc_min = nawodnienie.get("min")
    wilgotnosc_max = nawodnienie.get("max")

    if wilgotnosc_min is None or wilgotnosc_max is None:
        return jsonify({"error": "Brak danych o optymalnym nawodnieniu"}), 500

    # Porównanie wilgotności
    if value < wilgotnosc_min:
        status = "za sucho"
    elif value > wilgotnosc_max:
        status = "za mokro"
    else:
        status = "wilgotnosc_ok"

    print(status)

    return jsonify({
        "status": status,
        "plant_id": plant_id,
        "value": value,
        "wilgotnosc_min": wilgotnosc_min,
        "wilgotnosc_max": wilgotnosc_max,
        "nazwa_rosliny": plant.get("nazwa"),
        "lokalizacja": plant.get("lokalizacja"),
        "notes": plant.get("notes")
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
