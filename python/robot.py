#!/usr/bin/env python3

import movement
import sensors
import time
import statistics
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
        self.sensor_infrared = sensors.InfraredSensor(center=0, left=1, right=2, rear=3, interval=0.05)

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

        #Distance variable
        newValueDistance : int = 1000

        #Detection variables
        maxValuePossible : int = pow(2,15)
        minValuePossible : int = pow(2,15)

        newValueAtCenter : int  = 0
        newValueAtLeft : int    = 0
        newValueAtRight : int   = 0
        newValueAtRear : int    = 0

        oldValuesAtCenter : list   = [0]
        oldValuesAtLeft : list     = [0]
        oldValuesAtRight : list    = [0]
        oldValuesAtRear : list     = [0]

        # Estimate where the line could be
        # -1 : complete left
        #  0 : complete center
        # +1 : complete right
        lineEstimatedPosition : float = 0.0

        # Keep history to avoid jumps ? 
        oldLinePositions : list = [0.0]

        while self.is_running:

            # Log when we start 
            started = time.perf_counter()

            # get all values now 
            newValueAtCenter = self.sensor_infrared.values['center']
            newValueAtLeft = self.sensor_infrared.values['left']
            newValueAtRight = self.sensor_infrared.values['right']
            newValueAtRear = self.sensor_infrared.values['rear']

            newValueDistance = self.sensor_distance.distance

            # set minimum value to have a basis
            minValuePossible = min((minValuePossible,newValueAtCenter,newValueAtLeft,newValueAtRight))

            # If asked for stop, we stop everything
            if self.stop_asked:
                self.output_movement.set_full_stop()
                self.is_running = False
                self.is_started = False
                break

            # Let's check in front of us for an obstacle
            if newValueDistance <= 5 :
                # something is right in front of us, stop all movement
                way = 0 
            elif newValueDistance <= 20 : 
                # there is something coming up in front, maybe slow down ?
                way = (1 - ((20-newValueDistance)/16))
            else:
                # nothing found, let's go!
                way = 1

            # Building or Destroying confidence

            ## 1. If one of the value is at maximum, we know the line position, so we boost confidence
            if   newValueAtLeft != maxValuePossible and newValueAtCenter == maxValuePossible and newValueAtRight != maxValuePossible :
                # max value on center
                lineEstimatedPosition = 0.0
                confidence = max(100, confidence + 10)
            elif newValueAtLeft == maxValuePossible and newValueAtCenter != maxValuePossible and newValueAtRight != maxValuePossible :
                # max value on left
                lineEstimatedPosition = -1.0
                confidence = max(100, confidence + 10)
            elif newValueAtLeft != maxValuePossible and newValueAtCenter != maxValuePossible and newValueAtRight == maxValuePossible :
                # max value on right
                lineEstimatedPosition = 1.0
                confidence = max(100, confidence + 10)

            ## 2. No value is at maximum, so we do some calculation 
            else:         
                lineEstimatedPosition = (-(newValueAtLeft/(maxValuePossible-minValuePossible)) +(newValueAtRight/(maxValuePossible-minValuePossible))) * (newValueAtCenter/(maxValuePossible-minValuePossible))
                lineEstimatedPosition = min(1,max(-1,lineEstimatedPosition))

                if statistics.median((newValueAtCenter,newValueAtLeft,newValueAtRight))/(maxValuePossible-minValuePossible) > 1.5:
                    confidence = max(100, confidence + 5)
                else:
                    confidence = min(0, confidence - 10)

            
            # Checking history of line position
            # if we detect a jump too big, we decrease the confidence
            if abs(lineEstimatedPosition - oldLinePositions[-1]) > (statistics.pstdev(oldLinePositions) * 1.5) :
                confidence = min(0, confidence - 5)


            # finally we affect the position to the turn
            turn = lineEstimatedPosition/2

                

            # Clearing history (keep last 2 seconds)
            if len(oldLinePositions) > (framesPerSecond*2) : 
                oldLinePositions.pop(0)


            # Adjusting confidence to factor
            if confidence > 15:
                factor = 0.25
            if confidence > 50:
                factor = 0.5

            self.output_movement.set_value(value_left=(factor+turn)*way, value_right=(factor-turn)*way)

            # Add new values to history
            oldLinePositions.append(lineEstimatedPosition)


            # Sleep until next frame
            sleepTime = (1/framesPerSecond) - (time.perf_counter() - started)
            if sleepTime > 0:
                time.sleep(sleepTime)


ROBOT = Robot()
ROBOT.start()
