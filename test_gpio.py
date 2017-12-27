from gpiozero import LED
from time import sleep

red = LED(4)
time = 0.5

while True:
    red.on()
    sleep(time)
    red.off()
    sleep(time)
    print('One Cycle done!')