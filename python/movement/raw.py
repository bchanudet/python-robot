import gpiozero.pins.pigpio
from gpiozero import Servo

class MovementRaw(object):
    """Class representing the raw orders sent to the servos"""

    def __init__(self, pin_left, pin_right):
        self.factory = gpiozero.pins.pigpio.PiGPIOFactory()
        self.left = Servo(pin=pin_left, pin_factory=self.factory)
        self.right = Servo(pin=pin_right, pin_factory=self.factory)

    def set_value(self, value_left: float = 0.0, value_right: float = 0.0):
        """Sets normalized values for both servos"""
        # Get the current values
        current_values = self.get_values()
        # Normalizes the provided values
        new_values = {
            "left": (max(min(value_left, 1), -1) * -1.0),
            "right": (max(min(value_right, 1), -1) * 1.0)
        }
        # We set the values only if the new values are different
        if current_values["left"] != new_values["left"]:
            self.left.value = new_values["left"]
        if current_values["right"] != new_values["right"]:
            self.right.value = new_values["right"]

    def get_values(self):
        """Return normalized values for both servos"""
        # Normalize the values coming from the servos
        return {
            "left": (self.left.value),
            "right": (self.right.value)
        }

    def set_full_stop(self):
        """Emergency stop"""
        self.left.value = 0
        self.right.value = 0

    def __del__(self):
        self.right.close()
        self.left.close()
