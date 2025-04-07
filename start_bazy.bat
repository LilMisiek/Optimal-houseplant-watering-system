@echo off
echo === Uruchamianie MongoDB i InfluxDB ===

REM Sprawdź, czy kontener MongoDB istnieje, jeśli nie — uruchom
docker inspect mongodb >nul 2>&1
if errorlevel 1 (
    echo [MongoDB] Kontener nie istnieje – uruchamiam nowy...
    docker run -d --name=mongodb -p 27017:27017 -v %cd%\mongodb:/data/db mongo:6
) else (
    echo [MongoDB] Kontener istnieje – wznawiam...
    docker start mongodb
)

REM To samo dla InfluxDB
docker inspect influxdb >nul 2>&1
if errorlevel 1 (
    echo [InfluxDB] Kontener nie istnieje – uruchamiam nowy...
    docker run -d --name=influxdb -p 8086:8086 -v %cd%\influxdb:/var/lib/influxdb2 influxdb:2.7
) else (
    echo [InfluxDB] Kontener istnieje – wznawiam...
    docker start influxdb
)

echo === Bazy powinny być już gotowe 🚀 ===
pause
