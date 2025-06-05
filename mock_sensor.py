import random
from abc import ABC, abstractmethod

class ISensor(ABC):
    @abstractmethod
    def read_value(self) -> float:
        pass


class VoltageSensor_res(ISensor):
    def read_value(self) -> float:
        return round(random.uniform(0.0, 100.0), 2)


class VoltageSensor_cap(ISensor):
    def read_value(self) -> float:
        return round(random.uniform(0.0, 100.0), 2)
