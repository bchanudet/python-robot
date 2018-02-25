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
        self.is_started = True
        self.follow_line()

    def ask_for_stop(self):
        """Ask for stopping the current script"""
        self.stop_asked = True

    def follow_line(self):
        """Follow a line detected by infrared sensors"""
        self.status = "Starting follow line mode"
        print(self.status)
        self.sensor_distance.start()
        self.sensor_infrared.start()
        time.sleep(2)

        # Init here
        print("Initialization phase. Press button to start")
        initValuesLeft = []
        initValuesRight = []
        initValuesCenter = []

        self.button_generic.wait_for_active()
        i = 0
        while i < 100:
            if min([self.sensor_infrared.values["left"],self.sensor_infrared.values["right"],self.sensor_infrared.values["center"]]) > 0 :
                initValuesLeft.append(self.sensor_infrared.values["left"])
                initValuesRight.append(self.sensor_infrared.values["right"])
                initValuesCenter.append(self.sensor_infrared.values["center"])
                i = i+1
            time.sleep(0.02)

        lowestValueOnLeft = statistics.mean(initValuesLeft)
        lowestValueOnRight = statistics.mean(initValuesRight)
        lowestValueOnCenter = statistics.mean(initValuesCenter)

        print("Initialization done! Press the button to start mode")
        self.button_generic.wait_for_active()

        self.button_generic.when_activated = self.ask_for_stop
        self.is_running = True

        fd = open("test.log",mode="a")

        factor = 0.0
        turn = 0.0
        way = 1.0
        confidence = 0

        started = 0.0
        framesPerSecond = 20
        sleepTime = 0.0

        #Distance variable
        newValueDistance = 1000

        #Detection variables
        maxValuePossible = pow(2,15) - 1

        newValueAtCenter = 0
        newValueAtLeft   = 0
        newValueAtRight  = 0

        # Estimate where the line could be
        # -1 : complete left
        #  0 : complete center
        # +1 : complete right
        lineEstimatedPosition = 0.0

        # Keep history to avoid jumps ? 
        oldLinePositions = [0.0]

        while self.is_running:

            # Log when we start 
            started = time.perf_counter()

            # get all values now 
            newValueAtCenter = self.sensor_infrared.values['center']
            newValueAtLeft = self.sensor_infrared.values['left']
            newValueAtRight = self.sensor_infrared.values['right']

            newValueDistance = self.sensor_distance.distance

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
                confidence = confidence + 10
            elif newValueAtLeft == maxValuePossible and newValueAtCenter != maxValuePossible and newValueAtRight != maxValuePossible :
                # max value on left
                lineEstimatedPosition = -1.0
                confidence = confidence + 10
            elif newValueAtLeft != maxValuePossible and newValueAtCenter != maxValuePossible and newValueAtRight == maxValuePossible :
                # max value on right
                lineEstimatedPosition = 1.0
                confidence = confidence + 10

            ## 2. No value is at maximum, so we do some calculation 
            else:         
                # values
                linearValueOfLeft = (max(lowestValueOnLeft, newValueAtLeft) - lowestValueOnLeft) / (maxValuePossible - lowestValueOnLeft)
                linearValueOfRight = (max(lowestValueOnRight, newValueAtRight) - lowestValueOnRight) / (maxValuePossible - lowestValueOnRight)
                linearValueOfCenter = (max(lowestValueOnCenter, newValueAtCenter) - lowestValueOnCenter) / (maxValuePossible - lowestValueOnCenter)

                lineEstimatedPosition = ((linearValueOfLeft * -1) + (linearValueOfCenter * 0) + (linearValueOfRight * 1)) / (linearValueOfLeft + linearValueOfCenter + linearValueOfRight)
                
                if statistics.mean((linearValueOfLeft,linearValueOfCenter,linearValueOfRight)) > .5:
                    confidence = confidence + 5
                else:
                    confidence = confidence - 10

            
            # Checking history of line position
            # if we detect a jump too big, we decrease the confidence
            if abs(lineEstimatedPosition - oldLinePositions[-1]) > 0.25 :
                confidence = confidence - 3

            # finally we affect the position to the turn
            turn = lineEstimatedPosition/2

            # Clearing history (keep last 2 seconds)
            if len(oldLinePositions) > (framesPerSecond*2) : 
                oldLinePositions.pop(0)

            # Clamp confidence and apply it to factor
            confidence = max(0,min(100,confidence))
            factor = pow(confidence,2) / 10000

            # self.output_movement.set_value(value_left=(factor+turn)*way, value_right=(factor-turn)*way)

            # Add new values to history
            oldLinePositions.append(lineEstimatedPosition)

            # Calculate remaining time to next frame
            sleepTime = (1/framesPerSecond) - (time.perf_counter() - started)

	        # Print values
            print('{1:>+6d} | {0:>+6d} | {2:>+6d} | {3:>+2.6f} | {4:>+4d} | {5:>+2.6f} | {6:>+2.3f} | {7:>+2.3f} | {8:<32} | {9:>+8.2f} || {10:>1.6f} || {11:>+6d} ||'.format(
                newValueAtCenter, 
                newValueAtLeft, 
                newValueAtRight, 
                lineEstimatedPosition, 
                confidence, 
                turn, 
                way, 
                factor, 
                ''.join((' '*(15+math.ceil(lineEstimatedPosition*16)),'¤')),
                newValueDistance,
                sleepTime,
                maxValuePossible
            ))

            print('{1:d},{0:d},{2:d},{3:f},{4:d},{5:f},{6:f},{7:f},[{8:<32}],{9:f},{10:f},{11:f},{12:f},{13:d}'.format(
                newValueAtCenter, 
                newValueAtLeft, 
                newValueAtRight, 
                lineEstimatedPosition, 
                confidence, 
                turn, 
                way, 
                factor, 
                ''.join((' '*(16+math.ceil(lineEstimatedPosition*15)),'|')),
                newValueDistance,
                statistics.pstdev(oldLinePositions)*100,
                abs(lineEstimatedPosition - oldLinePositions[-1]),
                sleepTime,
                maxValuePossible
            ), file=fd)

            # Sleep until next frame
            if sleepTime > 0:
                time.sleep(sleepTime)

        
        fd.close()

        self.output_movement.set_full_stop()
        self.sensor_distance.running = False
        self.sensor_infrared.running = False
        self.sensor_distance.join()
        self.sensor_infrared.join()

        print("Finished!")


ROBOT = Robot()
ROBOT.start()
