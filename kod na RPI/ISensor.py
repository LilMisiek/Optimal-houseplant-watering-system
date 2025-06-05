from abc import ABC, abstractmethod

class ISensor(ABC):
    @abstractmethod
    def read_value(self) -> int:
        """Odczytuje wartość z sensora"""
        pass
