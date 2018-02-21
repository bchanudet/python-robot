import threading
import time

import RPi.GPIO as GPIO

class DistanceSensor(threading.Thread):
    """Reprensents the distance sensor, allows it to run periodically"""

    def __init__(self, pin_trigger:int, pin_echo:int, interval:int = 1):
        """initializes the instance"""
        super().__init__()
        self.pin_trigger = pin_trigger
        self.pin_echo = pin_echo
        self.interval = interval

        self.running = False
        self.distance = 0

    def run(self):
        """Infinite loop, set .running=False to stop it"""
        self.running = True
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin_trigger, GPIO.OUT)
        GPIO.setup(self.pin_echo, GPIO.IN)

        while self.running:
            GPIO.output(self.pin_trigger, False)
            time.sleep(1)
            GPIO.output(self.pin_trigger, True)
            time.sleep(0.00001)
            GPIO.output(self.pin_trigger, False)

            while GPIO.input(self.pin_echo) == 0:
                pulse_start = time.time()

            while GPIO.input(self.pin_echo) == 1:
                pulse_end = time.time()

            pulse_duration = pulse_end - pulse_start

            # Multiply pulse_duration by speed of sound (34 300 cm/s), divided by 2.
            self.distance = round(pulse_duration * 34300 / 2, 1)
            
            time.sleep(self.interval)

        GPIO.cleanup()

        return True
