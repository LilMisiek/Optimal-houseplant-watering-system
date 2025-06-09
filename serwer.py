import sys
from flask import Flask, request, jsonify, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from pymongo import MongoClient
from bson.json_util import dumps
from config_loader import load_config
from datetime import datetime, timezone

# Konfiguracja
print("Próba wczytania konfiguracji")
config = load_config()


if not config or "influx" not in config or "mongo" not in config:
    print("❌ BŁĄD KRYTYCZNY: Konfiguracja jest pusta lub niekompletna.")
    print("   Sprawdź czy plik config.json istnieje i jest poprawny")
    sys.exit(1)  # wylaczenie serwera, zeby uniknac bledow.

print("✅ Konfiguracja pomyślnie załadowana i zweryfikowana.")

# Flask i SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'bardzo-tajny-klucz-nikomu-nie-mow!'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')


# MongoDB
mongo_cfg = config.get("mongo")
mongo_client = MongoClient(mongo_cfg.get("url"))
mongo_db = mongo_client[mongo_cfg.get("db")]
plants = mongo_db[mongo_cfg.get("collection")]

# InfluxDB
influx_cfg = config.get("influx")
influx_client = InfluxDBClient(
    url=influx_cfg.get("url"),
    token=influx_cfg.get("token"),
    org=influx_cfg.get("org")
)
influx_write_api = influx_client.write_api(write_options=SYNCHRONOUS)


# ENDPOINTY DLA FRONTENDU

@app.route('/api/rosliny', methods=['GET'])
def get_all_plants():
    """Zwraca listę wszystkich roślin z Mongo, aby frontend wiedział, co ma wyświetlić."""
    try:
        all_plants_cursor = plants.find({}, {"_id": 1, "nazwa": 1, "lokalizacja": 1})
        return Response(dumps(all_plants_cursor), mimetype='application/json')
    except Exception as e:
        print(f"❌ Błąd przy pobieraniu roślin z MongoDB: {e}")
        return jsonify({"error": "Błąd serwera przy pobieraniu listy roślin"}), 500


@app.route('/api/rosliny/<plant_id>/pomiary', methods=['GET'])
def get_plant_history(plant_id):
    """
    Zwraca historię pomiarów oraz metadane o roślinie.
    """
    time_range = request.args.get('zakres', '24h')
    limit = int(request.args.get('limit', 300))  # Ustawianie limitu punktów wykresu

    # Pobieranie danych o roślinie z MongoDB
    plant = plants.find_one({"_id": str(plant_id)})
    if not plant:
        return jsonify({"error": "Nie znaleziono rośliny"}), 404

    # Pobieranie historii z InfluxDB
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
            "metadata": {
                "nazwa": plant.get("nazwa"),
                "optymalne_nawodnienie": plant.get("optymalne_nawodnienie", {})
            }
        }
        return jsonify(response_payload)

    except Exception as e:
        print(f"❌ Błąd przy pobieraniu historii z InfluxDB: {e}")
        return jsonify({"error": "Błąd serwera"}), 500
    """
    Zwraca historię pomiarów oraz metadane o roślinie,
    aby frontend mógł narysować wykres.
    """
    time_range = request.args.get('zakres', '24h')

    # Dla dłuższych okresów pobieramy mniej szczegółowe dane, żeby wykres był czytelny
    if 'd' in time_range:  # Dla dni
        aggregate_every = '1h'
    elif time_range == '12h':
        aggregate_every = '10m'
    else:  # Dla 1h, 24h
        aggregate_every = '5m'

    # Pobieranie danych o roślinie z MongoDB
    plant = plants.find_one({"_id": str(plant_id)})
    if not plant:
        return jsonify({"error": "Nie znaleziono rośliny"}), 404

    # Pobieranie historii z InfluxDB
    query_api = influx_client.query_api()
    flux_query = f'''
        from(bucket: "{influx_cfg.get("bucket")}")
          |> range(start: -{time_range})
          |> filter(fn: (r) => r["_measurement"] == "wilgotnosc")
          |> filter(fn: (r) => r["id_rosliny"] == "{plant_id}")
          |> aggregateWindow(every: {aggregate_every}, fn: mean, createEmpty: false)
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
            "metadata": {
                "nazwa": plant.get("nazwa"),
                "optymalne_nawodnienie": plant.get("optymalne_nawodnienie", {})
            }
        }
        return jsonify(response_payload)

    except Exception as e:
        print(f"❌ Błąd przy pobieraniu historii z InfluxDB: {e}")
        return jsonify({"error": "Błąd serwera"}), 500


# ENDPOINT ODBIERAJĄCY DANE Z CZUJNIKA

@app.route('/api/pomiar', methods=['POST'])
def odbierz_pomiar():
    """Odbiera dane z czujnika, zapisuje i rozgłasza przez websocket."""
    data = request.json
    plant_id = data.get("plant_id")
    value = data.get("value")

    if not plant_id or value is None:
        return jsonify({"error": "Brakuje danych"}), 400

    print(f"Odebrano dane z czujnika: plant_id={plant_id}, value={value}")

    # Zapis do InfluxDB
    try:
        point = Point("wilgotnosc").tag("id_rosliny", str(plant_id)).field("wartosc", float(value))
        influx_write_api.write(bucket=influx_cfg.get("bucket"), org=influx_cfg.get("org"), record=point)
    except Exception as e:
        print(f"❌ Błąd zapisu do InfluxDB: {e}")
        return jsonify({"error": "Błąd zapisu do InfluxDB"}), 500

    # Dane o roślinie z MongoDB
    plant = plants.find_one({"_id": str(plant_id)})
    if not plant:
        return jsonify({"error": "Nie znaleziono rośliny w bazie danych"}), 404

    # Logika biznesowa
    nawodnienie = plant.get("optymalne_nawodnienie", {})
    wilgotnosc_min = nawodnienie.get("min")
    wilgotnosc_max = nawodnienie.get("max")

    if wilgotnosc_min is None or wilgotnosc_max is None:
        return jsonify({"error": "Brak danych o optymalnym nawodnieniu"}), 500

    if float(value) < wilgotnosc_min:
        status = "za sucho"
    elif float(value) > wilgotnosc_max:
        status = "za mokro"
    else:
        status = "wilgotnosc_ok"

    # Przygotowanie pakietu danych do wysłania
    update_payload = {
        "status": status,
        "plant_id": plant_id,
        "value": value,
        "nazwa_rosliny": plant.get("nazwa"),
        "lokalizacja": plant.get("lokalizacja"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # WYSYŁANIE DANYCH DO FRONTENDU
    socketio.emit('nowy_pomiar', update_payload)
    print(f"📢 Wysłano update przez WebSocket: {update_payload['nazwa_rosliny']} ma status '{status}'")

    return jsonify(update_payload)


# OBSŁUGA ZDARZEŃ WEBSOCKET

@socketio.on('connect')
def handle_connect():
    """Wywoływane, gdy nowy klient połączy się z serwerem."""
    print(f"✅ Klient połączony: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    """Wywoływane, gdy klient się rozłączy."""
    print(f"❌ Klient rozłączony: {request.sid}")



if __name__ == "__main__":
    print("🚀 Serwer startuje na http://0.0.0.0:5001")
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)