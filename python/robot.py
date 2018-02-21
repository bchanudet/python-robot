#!/usr/bin/env python3

import movement
import sensors
import time
import statistics
import math
from gpiozero import Button


class Robot(object):
    """Main class"""

    def __init__(self):
        # Set status to be retrieved by API if necessary
        self.status = "Initializing..."

        # Bunch of attributes
        self.is_started = False
        self.is_running = False
        self.stop_asked = False

        # Init all the PINS /o/
        self.button_generic = Button(pin=13)
        self.output_movement = movement.MovementRaw(pin_left=17, pin_right=18)
        self.sensor_distance = sensors.DistanceSensor(pin_trigger=4, pin_echo=14)
        self.sensor_infrared = sensors.InfraredSensor(center=0, left=1, right=2, rear=3, interval=0.05)

    def start(self):
        """Starts the robot"""
        self.status = "Initialized !"
        print("Waiting for button")
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
        print(self.status)
        self.sensor_distance.start()
        self.sensor_infrared.start()

        self.button_generic.when_activated = self.ask_for_stop
        self.is_running = True

        factor = 0.0
        turn = 0.0
        way = 1.0
        confidence = 0

        started = 0.0
        framesPerSecond = 10
        sleepTime = 0.0

        #Distance variable
        newValueDistance = 1000

        #Detection variables
        maxValuePossible = pow(2,15) - 1
        minValuePossible = pow(2,15) - 1

        print(maxValuePossible)

        newValueAtCenter = 0
        newValueAtLeft   = 0
        newValueAtRight  = 0
        newValueAtRear   = 0

        oldValuesAtCenter = [0]
        oldValuesAtLeft   = [0]
        oldValuesAtRight  = [0]
        oldValuesAtRear   = [0]

        # Estimate where the line could be
        # -1 : complete left
        #  0 : complete center
        # +1 : complete right
        lineEstimatedPosition = 0.0
        rawLinePosition = 0.0

        # Keep history to avoid jumps ? 
        oldLinePositions = [0.0]

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
                tmpConfidence = confidence + 10
                confidence = min(100, tmpConfidence)
            elif newValueAtLeft == maxValuePossible and newValueAtCenter != maxValuePossible and newValueAtRight != maxValuePossible :
                # max value on left
                lineEstimatedPosition = -1.0
                confidence = min(100, confidence + 10)
            elif newValueAtLeft != maxValuePossible and newValueAtCenter != maxValuePossible and newValueAtRight == maxValuePossible :
                # max value on right
                lineEstimatedPosition = 1.0
                confidence = min(100, confidence + 10)

            ## 2. No value is at maximum, so we do some calculation 
            else:         
                offsetToLeft = (newValueAtLeft - newValueAtCenter)
                offsetToRight = (newValueAtRight - newValueAtCenter)

                lineEstimatedPosition = (-offsetToLeft +offsetToRight)/maxValuePossible
                rawLinePosition = lineEstimatedPosition
                lineEstimatedPosition = min(1,max(-1,lineEstimatedPosition))

                if statistics.median((newValueAtCenter,newValueAtLeft,newValueAtRight))/(maxValuePossible-minValuePossible) > 2.5:
                    confidence = min(100, confidence + 5)
                else:
                    confidence = max(0, confidence - 10)

            
            # Checking history of line position
            # if we detect a jump too big, we decrease the confidence
            if abs(lineEstimatedPosition - oldLinePositions[-1]) > (statistics.pstdev(oldLinePositions) * 100) :
                confidence = max(0, confidence - 5)


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

            # self.output_movement.set_value(value_left=(factor+turn)*way, value_right=(factor-turn)*way)

            # Add new values to history
            oldLinePositions.append(lineEstimatedPosition)

	    # Print values
            print('{1:>+6d} | {0:>+6d} | {2:>+6d} | {3:>+2.6f} | {4:>+4d} | {5:>+2.6f} | {6:>+2.3f} | {7:>+2.3f} | {8:<32} | {9:>+5.3f} | {10:>+4.4f} |'.format(
			newValueAtCenter, 
			newValueAtLeft, 
			newValueAtRight, 
			rawLinePosition, 
			confidence, 
			turn, 
			way, 
			factor, 
			''.join((' '*(15+math.ceil(lineEstimatedPosition*16)),'¤')),
                        newValueDistance,
			statistics.pstdev(oldLinePositions)*100
            ))

            # Sleep until next frame
            sleepTime = (1/framesPerSecond) - (time.perf_counter() - started)
            if sleepTime > 0:
                time.sleep(sleepTime)


ROBOT = Robot()
ROBOT.start()
