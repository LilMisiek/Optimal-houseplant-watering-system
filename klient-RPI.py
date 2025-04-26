import requests
import json
import time
import random

# Adres IP twojego serwera (komputera z Flaskiem)
SERVER_IP = "127.0.0.1"

while True:
    wilgotnosc = round(random.uniform(10, 90), 1)
    payload = {
        "plant_id": "3",
        "value": wilgotnosc
    }

    try:
        response = requests.post(f"http://{SERVER_IP}:5001/api/pomiar", json=payload)
        print("✅ Wysłano:", payload, "| Odpowiedź:", response.json())
    except Exception as e:
        print("❌ Błąd:", e)

    time.sleep(3)
