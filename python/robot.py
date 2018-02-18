#!/usr/bin/env python3

import movement
import sensors
import time
from gpiozero import Button


class Robot(object):
    """Main class"""

    def __init__(self):
        # Set status to be retrieved by API if necessary
        self.status = "Initializing..."

        # Bunch of attributes
        self.is_started: bool = False
        self.is_running: bool = False
        self.stop_asked = False

        # Init all the PINS /o/
        self.button_generic = Button(pin=13)
        self.output_movement = movement.MovementRaw(pin_left=17, pin_right=18)
        self.sensor_distance = sensors.DistanceSensor(pin_trigger=4, pin_echo=14)
        self.sensor_infrared = sensors.InfraredSensor(center=0, left=1, right=2, rear=3)

    def start(self):
        """Starts the robot"""
        self.status = "Initialized !"
        self.button_generic.wait_for_active()
        time.sleep(2)
        self.is_started = True
        self.follow_line()

    def ask_for_stop(self):
        """Ask for stopping the current script"""
        self.stop_asked = True

    def follow_line(self):
        """Follow a line detected by infrared sensors"""
        self.status = "Following line mode started"
        self.button_generic.when_activated = self.ask_for_stop
        self.is_running = True

        factor: float = 0.0
        turn: float = 0.0
        way: float = 1.0
        confidence: int = 0

        started : float = 0.0
        framesPerSecond : float = 10
        sleepTime : float = 0.0

        while self.is_running:

            # Log when we start 
            started = time.perf_counter()

            # If asked for stop, we stop everything
            if self.stop_asked:
                self.output_movement.set_full_stop()
                self.is_running = False
                self.is_started = False
                break

            # Let's check in front of us for an obstacle
            if self.sensor_distance.distance <= 5 :
                # something is right in front of us, stop all movement
                way = 0 
            else if self.sensor_distance.distance <= 20 : 
                # there is something coming up in front, maybe slow down ?
                way = (1 - ((20-self.sensor_distance.distance)/16))
            else:
                # nothing found, let's go!
                way = 1

            # Building or Destroying confidence



            # Adjusting confidence to factor
            if confidence > 15:
                factor = 0.25
            if confidence > 30:
                factor = 0.5

            self.output_movement.set_value(value_left=(factor+turn)*way, value_right=(factor-turn)*way)


            # Sleep until next frame
            sleepTime = (1/framesPerSecond) - (time.perf_counter() - started)
            if sleepTime > 0:
                time.sleep(sleepTime)


ROBOT = Robot()
ROBOT.start()
