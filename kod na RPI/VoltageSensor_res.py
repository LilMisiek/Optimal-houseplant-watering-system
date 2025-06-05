import subprocess
from ISensor import ISensor

class VoltageSensor_res(ISensor):
    def __init__(self, path="/sys/bus/iio/devices/iio:device0/in_voltage1_raw"):
        self.path = path
        self.raw_min = 0
        self.raw_max = 17000
    def read_value(self) -> int:
        try:
            print("res")
            result = subprocess.check_output(["cat", self.path])
            print(result)

            percent = round((int(result.decode("utf-8").strip())-self.raw_min)/self.raw_max *100,2)
            print(percent)
            return percent
        except (subprocess.CalledProcessError, ValueError) as e:
            print(f"❌ Błąd odczytu z czujnika: {e}")
            return 0  # fallback
