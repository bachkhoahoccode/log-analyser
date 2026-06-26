from abc import ABC, abstractmethod

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, event):
        pass
    @abstractmethod
    def generate_alert(self, event):
        pass
        