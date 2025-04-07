from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["roslinki_monitor"]
plants = db["roslinki"]



plants.insert_one({
    "_id": "3",
    "nazwa": "Papryka",
    "gatunek": "Papricum czerwonum",
    "lokalizacja": "kibel",
    "optymalne_nawodnienie": {
        "min": 30,
        "max": 60
    },
    "notatka": "Podlewać, gdy wilgotność spadnie poniżej 30%."
})

plant = plants.find_one({"_id": "2"})
print("Roślina:", plant["nazwa"], "| Wilgotność min:", plant["optymalne_nawodnienie"]["min"])
