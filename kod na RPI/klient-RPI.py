import requests
import json
import time
import random

import subprocess

def read_voltage():
	# Uruchamiamy komendę `cat` i pobieramy wynik
	try:
		result = subprocess.check_output(["cat", "/sys/bus/iio/devices/iio:device0/in_voltage0-voltage1_raw"])
        # Zwracamy wynik jako string, usuwając ewentualne białe znaki na końcu
		return result.decode("utf-8").strip()
	except subprocess.CalledProcessError as e:
        	print(f"Blad podczas wykonywania komendy: {e}")
	return None

# Adres IP twojego serwera (komputera z Flaskiem)
SERVER_IP = "192.168.0.105"

while True:
    voltage = read_voltage()
    if voltage:
        wilgotnosc =voltage
    else:
        wilgotnosc =0



   # wilgotnosc = round(random.uniform(30, 60), 1)
    payload = {
        "plant_id": "3",
        "value": wilgotnosc
    }

    try:
        response = requests.post(f"http://{SERVER_IP}:5001/api/pomiar", json=payload)
        print("✅ Wysłano:", payload, "| Odpowiedź:", response.json())
    except Exception as e:
        print("❌ Błąd:", e)

    time.sleep(10)
