

import sys
import uuid
from flask import Flask, request, jsonify, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.delete_api import DeleteApi
from pymongo import MongoClient
from bson.json_util import dumps
# from bson.objectid import ObjectId
from config_loader import load_config
from datetime import datetime, timezone

# Konfiguracja i Inicjalizacja
config = load_config()
if not config or "influx" not in config or "mongo" not in config:
    print("❌ BŁĄD KRYTYCZNY: Konfiguracja jest pusta lub niekompletna.")
    sys.exit(1)
app = Flask(__name__)
app.config['SECRET_KEY'] = 'bardzo-tajny-klucz-nikomu-nie-mow!'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')
mongo_cfg = config.get("mongo")
mongo_client = MongoClient(mongo_cfg.get("url"))
mongo_db = mongo_client[mongo_cfg.get("db")]
plants = mongo_db[mongo_cfg.get("collection")]
influx_cfg = config.get("influx")
influx_client = InfluxDBClient(url=influx_cfg.get("url"), token=influx_cfg.get("token"), org=influx_cfg.get("org"))
influx_write_api = influx_client.write_api(write_options=SYNCHRONOUS)
influx_delete_api = influx_client.delete_api()


@app.route('/api/rosliny', methods=['POST'])
def add_plant():
    data = request.json
    if not data or 'nazwa' not in data or 'lokalizacja' not in data or 'optymalne_nawodnienie' not in data:
        return jsonify({"error": "Brakuje wymaganych danych"}), 400

    nawodnienie = data['optymalne_nawodnienie']
    if 'min' not in nawodnienie or 'max' not in nawodnienie:
        return jsonify({"error": "Brak danych min/max dla optymalnego nawodnienia"}), 400

    new_plant_doc = {
        "_id": str(uuid.uuid4()),  # <-- KROK 3: Generujemy i przypisujemy ID jako string
        "nazwa": data['nazwa'],
        "lokalizacja": data['lokalizacja'],
        "optymalne_nawodnienie": {
            "min": float(nawodnienie['min']),
            "max": float(nawodnienie['max'])
        },
        "notes": data.get("notes", "")
    }
    plants.insert_one(new_plant_doc)

    # Zwracamy nowo utworzony dokument
    return Response(dumps(new_plant_doc), mimetype='application/json', status=201)


@app.route('/api/rosliny/<plant_id>', methods=['GET'])
def get_plant_details(plant_id):
    # <-- KROK 4: Usuwamy konwersję na ObjectId. Szukamy po prostu po stringu.
    plant = plants.find_one({"_id": plant_id})
    if not plant:
        return jsonify({"error": "Nie znaleziono rośliny"}), 404
    return Response(dumps(plant), mimetype='application/json')


@app.route('/api/rosliny/<plant_id>', methods=['PUT'])
def update_plant(plant_id):
    data = request.json
    if not data:
        return jsonify({"error": "Brak danych do aktualizacji"}), 400
    update_data = {
        "nazwa": data['nazwa'], "lokalizacja": data['lokalizacja'],
        "optymalne_nawodnienie": {"min": float(data['optymalne_nawodnienie']['min']),
                                  "max": float(data['optymalne_nawodnienie']['max'])},
        "notes": data.get("notes", "")
    }
    # <-- KROK 4: Usuwamy konwersję na ObjectId.
    result = plants.update_one({"_id": plant_id}, {"$set": update_data})
    if result.matched_count == 0:
        return jsonify({"error": "Nie znaleziono rośliny do aktualizacji"}), 404
    return jsonify({"success": True, "message": "Dane rośliny zaktualizowane"})


@app.route('/api/rosliny/<plant_id>', methods=['DELETE'])
def delete_plant(plant_id):
    try:

        mongo_result = plants.delete_one({"_id": plant_id})
        if mongo_result.deleted_count == 0:
            return jsonify({"error": "Nie znaleziono rośliny w MongoDB"}), 404
        start = "1970-01-01T00:00:00Z"
        stop = datetime.now(timezone.utc).isoformat()
        predicate = f'_measurement="wilgotnosc" AND id_rosliny="{plant_id}"'
        influx_delete_api.delete(start, stop, predicate, bucket=influx_cfg.get("bucket"), org=influx_cfg.get("org"))
        print(f"INFO: Usunięto roślinę {plant_id} oraz jej historię pomiarów.")
        return jsonify({"success": True, "message": "Roślina i jej historia zostały usunięte"})
    except Exception as e:
        print(f"❌ Błąd podczas usuwania rośliny {plant_id}: {e}")
        return jsonify({"error": "Wystąpił błąd serwera podczas usuwania"}), 500


# Endpoint /api/rosliny
@app.route('/api/rosliny', methods=['GET'])
def get_all_plants():
    all_plants_cursor = plants.find({}, {"_id": 1, "nazwa": 1, "lokalizacja": 1})
    return Response(dumps(all_plants_cursor), mimetype='application/json')


@app.route('/api/rosliny/<plant_id>/pomiary', methods=['GET'])
def get_plant_history(plant_id):
    time_range = request.args.get('zakres', '24h')
    limit = int(request.args.get('limit', 300))
    # <-- KROK 4: Usuwamy konwersję na ObjectId.
    plant = plants.find_one({"_id": plant_id})
    if not plant:
        return jsonify({"error": "Nie znaleziono rośliny"}), 404
    query_api = influx_client.query_api()
    flux_query = f'''
        from(bucket: "{influx_cfg.get("bucket")}")
          |> range(start: -{time_range})
          |> filter(fn: (r) => r["_measurement"] == "wilgotnosc")
          |> filter(fn: (r) => r["id_rosliny"] == "{plant_id}")
          |> sort(columns: ["_time"], desc: false)
          |> limit(n: {limit})
          |> yield(name: "mean")
    '''
    try:
        result = query_api.query(query=flux_query, org=influx_cfg.get("org"))
        data_points = []
        for table in result:
            for record in table.records:
                data_points.append({"time": record.get_time(), "value": record.get_value()})
        response_payload = {
            "history": data_points,
            "metadata": {"nazwa": plant.get("nazwa"), "optymalne_nawodnienie": plant.get("optymalne_nawodnienie", {})}
        }
        return jsonify(response_payload)
    except Exception as e:
        print(f"❌ Błąd przy pobieraniu historii z InfluxDB: {e}")
        return jsonify({"error": "Błąd serwera"}), 500


@app.route('/api/pomiar', methods=['POST'])
def odbierz_pomiar():
    data = request.json
    plant_id, value = data.get("plant_id"), data.get("value")
    if not plant_id or value is None:
        return jsonify({"error": "Brakuje danych"}), 400
    print(f"Odebrano dane: plant_id={plant_id}, value={value}")
    try:
        point = Point("wilgotnosc").tag("id_rosliny", str(plant_id)).field("wartosc", float(value))
        influx_write_api.write(bucket=influx_cfg.get("bucket"), org=influx_cfg.get("org"), record=point)
    except Exception as e:
        print(f"❌ Błąd zapisu do InfluxDB: {e}")
        return jsonify({"error": "Błąd zapisu do InfluxDB"}), 500


    plant = plants.find_one({"_id": plant_id})
    if not plant:

        if plant_id in ["1", "2"]:
            return jsonify({"error": f"Dummy plant ID '{plant_id}' not found in DB. Add it first."}), 404
        return jsonify({"error": "Nie znaleziono rośliny"}), 404

    nawodnienie = plant.get("optymalne_nawodnienie", {})
    wilgotnosc_min, wilgotnosc_max = nawodnienie.get("min"), nawodnienie.get("max")
    if wilgotnosc_min is None or wilgotnosc_max is None:
        status = "nieznany_zakres"
    elif float(value) < wilgotnosc_min:
        status = "za sucho"
    elif float(value) > wilgotnosc_max:
        status = "za mokro"
    else:
        status = "wilgotnosc_ok"
    update_payload = {"status": status, "plant_id": plant_id, "value": value, "nazwa_rosliny": plant.get("nazwa"),
                      "lokalizacja": plant.get("lokalizacja"), "timestamp": datetime.now(timezone.utc).isoformat()}
    socketio.emit('nowy_pomiar', update_payload)
    print(f"📢 Wysłano update przez WebSocket: {update_payload['nazwa_rosliny']} ma status '{status}'")
    return jsonify(update_payload)


@socketio.on('connect')
def handle_connect(): print(f"✅ Klient połączony: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect(): print(f"❌ Klient rozłączony: {request.sid}")


if __name__ == "__main__":
    print("🚀 Serwer startuje na http://0.0.0.0:5001")
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)