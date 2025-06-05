import requests
import time
from mock_sensor import VoltageSensor_res, VoltageSensor_cap

# Stałe testowe zamiast config.json
SERVER_IP = "127.0.0.1"
PLANT1_ID = "1"
PLANT2_ID = "2"

sensor1 = VoltageSensor_res()
sensor2 = VoltageSensor_cap()

while True:
    value1 = sensor1.read_value()
    value2 = sensor2.read_value()

    payload1 = {"plant_id": PLANT1_ID, "value": value1}
    payload2 = {"plant_id": PLANT2_ID, "value": value2}

    try:
        response1 = requests.post(f"http://{SERVER_IP}:5001/api/pomiar", json=payload1, timeout=5)
        print("✅ Wysłano:", payload1, "| Odpowiedź:", response1.json())
    except requests.RequestException as e:
        print("❌ Błąd połączenia (czujnik 1):", e)

    try:
        response2 = requests.post(f"http://{SERVER_IP}:5001/api/pomiar", json=payload2, timeout=5)
        print("✅ Wysłano:", payload2, "| Odpowiedź:", response2.json())
    except requests.RequestException as e:
        print("❌ Błąd połączenia (czujnik 2):", e)

    time.sleep(10)
