import time, threading
import Adafruit_ADS1x15

class InfraredSensor(threading.Thread):
    """Thread running to use infrared sensors"""
    def __init__(self,
                 center: int = 0,
                 left: int = 1,
                 right: int = 2,
                 rear: int = 3,
                 interval: float = 0.05):
        """Initializes the instance and their channels"""
        super().__init__()
        self.channels = {
            "center": center,
            "left": left,
            "right": right,
            "rear": rear
        }
        self.values = {
            "center": 0,
            "left": 0,
            "right": 0,
            "rear": 0
        }
        self.interval = interval
        self.front_value = 0.0
        self.rear_value = 0.0
        self.gain = 8
        self.running = False

    def run(self):
        self.running = True
        adc = Adafruit_ADS1x15.ADS1115()

        while self.running:
            self.values["center"] = adc.read_adc(self.channels["center"], gain=self.gain)
            self.values["left"] = adc.read_adc(self.channels["left"], gain=self.gain)
            self.values["right"] = adc.read_adc(self.channels["right"], gain=self.gain)
            self.values["rear"] = adc.read_adc(self.channels["rear"], gain=self.gain)

            self.front_value = (
                -self.values["left"]
                + self.values["center"]
                + self.values["right"]) / 3
            self.rear_value = self.values["rear"]

            time.sleep(self.interval)

        del adc
