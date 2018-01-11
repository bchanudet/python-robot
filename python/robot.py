import movement
import sensors
from gpiozero import Button

MOVE = movement.MovementRaw(pin_left=17, pin_right=18)
DISTANCE = sensors.DistanceSensor(pin_trigger=4, pin_echo=14)
INFRARED = sensors.InfraredSensor(center=0, left=1, right=2, rear=3)

START_BUTTON = Button(pin=13)

