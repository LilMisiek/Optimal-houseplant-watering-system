from flask import Flask, request, jsonify
from influxdb_client import InfluxDBClient, Point, WritePrecision
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# --- MongoDB ---
mongo_client = MongoClient("mongodb://localhost:27017")
mongo_db = mongo_client["roslinki_monitor"]
plants = mongo_db["roslinki"]

# --- InfluxDB ---
influx_token = "TWÓJ_TOKEN"
influx_org = "czworka"
influx_bucket = "dane_wilgotnosci"
influx_url = "http://localhost:8086"

influx_client = InfluxDBClient(
    url=influx_url,
    token=influx_token,
    org=influx_org
)
#write_api = influx_client.write_api(write_options=WritePrecision.S)

@app.route('/api/pomiar', methods=['POST'])
def odbierz_pomiar():
    data = request.json
    plant_id = data.get("plant_id")
    value = data.get("value")

    if not plant_id or value is None:
        return jsonify({"error": "Brakuje danych"}), 400
    else:
        print(plant_id,value)
        return jsonify({"status": "ok", "plant_id": plant_id, "value": value})
    '''
    # --- Zapis do InfluxDB ---
    point = (
        Point("wilgotnosc")
        .tag("id_rosliny", str(plant_id))
        .field("wartosc", float(value))
    )
    write_api.write(bucket=influx_bucket, org=influx_org, record=point)

    # --- Zapis do MongoDB (ostatni pomiar) ---
    plants.update_one(
        {"_id": str(plant_id)},
        {"$set": {
            "ostatni_pomiar": value,
            "timestamp": datetime.utcnow()
        }},
        upsert=True
    )

    return jsonify({"status": "ok", "plant_id": plant_id, "value": value})
    '''
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
