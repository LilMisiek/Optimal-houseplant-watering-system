import requests
import time

from ConfigLoader import load_config
from VoltageSensor_res import VoltageSensor_res
from VoltageSensor_cap import VoltageSensor_cap
# from mock_sensor import MockSensor

config = load_config()
SERVER_IP = config.get("server_ip", "127.0.0.1")
PLANT_ID = config.get("plant1_id", "0")
PLANT2_ID = config.get("plant2_id", "1")

sensor1 = VoltageSensor_res()
sensor2 = VoltageSensor_cap()
# sensor = MockSensor()

while True:
    value = sensor1.read_value()
    value2 = sensor2.read_value()
    payload = {
        "plant_id": PLANT_ID,
        "value": value
    }
    payload2 = {
        "plant_id": PLANT2_ID,
        "value": value2
    }
    try:
        response = requests.post(f"http://{SERVER_IP}:5001/api/pomiar", json=payload, timeout=5)
        print("✅ Wysłano:", payload, "| Odpowiedź:", response.json())
    except requests.RequestException as e:
        print("❌ Błąd połączenia:", e)

    try:
        response = requests.post(f"http://{SERVER_IP}:5001/api/pomiar", json=payload2, timeout=5)
        print("✅ Wysłano:", payload2, "| Odpowiedź:", response.json())
    except requests.RequestException as e:
        print("❌ Błąd połączenia:", e)

    time.sleep(10)
