import subprocess
from ISensor import ISensor

class VoltageSensor_cap(ISensor):
    def __init__(self, path="/sys/bus/iio/devices/iio:device0/in_voltage0_raw"):
        self.path = path
        self.raw_range = 11000
        self.raw_max = 20000
    def read_value(self) -> int:
        try:
            print("cap:")
            result = subprocess.check_output(["cat", self.path])
            print(result)

            percent = round((self.raw_max- int(result.decode("utf-8").strip()))/self.raw_range *100,2)
            print(percent)
            return percent
        except (subprocess.CalledProcessError, ValueError) as e:
            print(f"❌ Błąd odczytu z czujnika: {e}")
            return 0  # fallback
