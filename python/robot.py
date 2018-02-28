#!/usr/bin/env python3

import movement
import sensors
import time
import statistics
import math
import sys
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

        # Set a complete factor for test
        self.generalCoefficient = 0.1
        self.framesPerSecond = 120

        self.confidenceIncrement = 200
        self.confidenceDecrement = -200

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
        print("General Coefficient: {0}".format(self.generalCoefficient))
        print("Confidence Increment: {0}".format(self.confidenceIncrement))
        print("Confidence Decrement: {0}".format(self.confidenceDecrement))
        print("Frames per second: {0}".format(self.framesPerSecond))
        self.sensor_distance.start()
        self.sensor_infrared.start()
        time.sleep(2)

        # Init here
        print("")
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
                print("=",end="",flush=True)
            time.sleep(0.02)
        print(" 100%!")

        lowestValueOnLeft = int(statistics.mean(initValuesLeft))
        lowestValueOnRight = int(statistics.mean(initValuesRight))
        lowestValueOnCenter = int(statistics.mean(initValuesCenter))

        initValuesCenter.clear()
        initValuesLeft.clear()
        initValuesRight.clear()
        
        print("Left base : {0:d}".format(lowestValueOnLeft))
        print("Center base : {0:d}".format(lowestValueOnCenter))
        print("Right base : {0:d}".format(lowestValueOnRight))
        print("Initialization done! Press the button to start mode")
        self.button_generic.wait_for_active()

        self.button_generic.when_activated = self.ask_for_stop
        self.is_running = True

        fd = open("test.log",mode="a")

        # Final values initialiazed here
        confidence = 0.0

        confidenceFactor = 0.0
        turnFactor = 0.0
        distanceCoefficient = 1.0
        newValueToLeftMotor = 0.0
        newValueToRightMotor = 0.0

        started = 0.0
        sleepTime = 0.0

        #Distance variable
        newValueDistance = 1000

        #Detection variables
        maxValuePossible = pow(2,15) - 1

        newValueAtCenter = 0
        newValueAtLeft   = 0
        newValueAtRight  = 0

        linearValueOfCenter = 0.0
        linearValueOfLeft = 0.0
        linearValueOfRight = 0.0

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
                distanceCoefficient = 0 
            elif newValueDistance <= 20 : 
                # there is something coming up in front, maybe slow down ?
                distanceCoefficient = (1 - ((20-newValueDistance)/16))
            else:
                # nothing found, let's go!
                distanceCoefficient = 1

            # Building or Destroying confidence
            linearValueOfLeft = (max(lowestValueOnLeft, newValueAtLeft) - lowestValueOnLeft) / (maxValuePossible - lowestValueOnLeft)
            linearValueOfRight = (max(lowestValueOnRight, newValueAtRight) - lowestValueOnRight) / (maxValuePossible - lowestValueOnRight)
            linearValueOfCenter = (max(lowestValueOnCenter, newValueAtCenter) - lowestValueOnCenter) / (maxValuePossible - lowestValueOnCenter)
            sumOfValues = (linearValueOfLeft + linearValueOfCenter + linearValueOfRight)

            if sumOfValues == 0 :
                lineEstimatedPosition = -1 if (lineEstimatedPosition < 0) else 1
            else :
                lineEstimatedPosition = ((linearValueOfLeft * -1) + (linearValueOfCenter * 0) + (linearValueOfRight * 1)) / sumOfValues
            
            if max(newValueAtLeft,newValueAtCenter,newValueAtRight)/maxValuePossible > .25:
                confidence = confidence + (self.confidenceIncrement/self.framesPerSecond)
            else:
                confidence = confidence + (self.confidenceDecrement/self.framesPerSecond)

            
            # Checking history of line position
            # if we detect a jump too big, we decrease the confidence
            if abs(lineEstimatedPosition - oldLinePositions[-1]) > 0.25 :
                confidence = confidence + (self.confidenceDecrement/self.framesPerSecond)

            # finally we affect the position to the turn
            turnFactor = math.pow(lineEstimatedPosition,3) # * (-1 if lineEstimatedPosition > 0 else 1)

            # Clearing history (keep last 2 seconds)
            if len(oldLinePositions) > (self.framesPerSecond*2) : 
                oldLinePositions.pop(0)

            # Clamp confidence and apply it to factor
            confidence = max(0,min(100,confidence))
            confidenceFactor = pow(confidence,2) / 10000


            # Assign new values to motor
            newValueToLeftMotor = (confidenceFactor - turnFactor) * distanceCoefficient * self.generalCoefficient
            newValueToRightMotor = (confidenceFactor + turnFactor) * distanceCoefficient * self.generalCoefficient
            
            # Add new values to history
            oldLinePositions.append(lineEstimatedPosition)

            # Calculate remaining time to next frame
            sleepTime = (1/self.framesPerSecond) - (time.perf_counter() - started)

	        # Print values
            print('L:{1:>+6d} | C:{0:>+6d} | R:{2:>+6d} | P:{3:>+2.6f} | C:{4:>8.2f} | tF:{5:>+2.5f} | dC:{6:>+2.3f} | cF:{7:>+2.3f} | {8:<32} | Dt:{9:>+8.2f} || sl:{10:>1.4f} || Val: | {12:>2.4f} | {11:>+2.4f} | {13:>+2.4f} || Mot: | {14:>+2.4f} | {15:>+2.4f} |'.format(
                newValueAtCenter, 
                newValueAtLeft, 
                newValueAtRight, 
                lineEstimatedPosition, 
                confidence, 
                turnFactor, 
                distanceCoefficient, 
                confidenceFactor, 
                ''.join((' '*(15+math.ceil(lineEstimatedPosition*16)),'¤')),
                newValueDistance,
                sleepTime,
                linearValueOfCenter,
                linearValueOfLeft,
                linearValueOfRight,
                newValueToLeftMotor, 
                newValueToRightMotor
            ))

            print('{1:d},{0:d},{2:d},{3:f},{4:f},{5:f},{6:f},{7:f},[{8:<32}],{9:f},{10:f},{11:f},{12:f},{13:d},{14:f},{15:f},{16:f},{17:f},{18:f}'.format(
                newValueAtCenter, 
                newValueAtLeft, 
                newValueAtRight, 
                lineEstimatedPosition, 
                confidence, 
                turnFactor, 
                distanceCoefficient, 
                confidenceFactor, 
                ''.join((' '*(15+math.ceil(lineEstimatedPosition*16)),'|')),
                newValueDistance,
                statistics.pstdev(oldLinePositions)*100,
                abs(lineEstimatedPosition - oldLinePositions[-1]),
                sleepTime,
                maxValuePossible,
                linearValueOfCenter,
                linearValueOfLeft,
                linearValueOfRight,
                newValueToLeftMotor,
                newValueToRightMotor
            ), file=fd)

            # send values to motor
            self.output_movement.set_value(
                value_left = newValueToLeftMotor,
                value_right= newValueToRightMotor
            )

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

if len(sys.argv) > 1:
    ROBOT.generalCoefficient = float(sys.argv[1])
if len(sys.argv) > 2:
    ROBOT.confidenceIncrement = int(sys.argv[2])
if len(sys.argv) > 3:
    ROBOT.confidenceDecrement = int(sys.argv[3])
if len(sys.argv) > 4:
    ROBOT.framesPerSecond = int(sys.argv[4])

ROBOT.start()
