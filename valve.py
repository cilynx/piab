import time

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)
GPIO_PIN = [11, 12, 13, 15, 16, 18, 25]

RED = '\033[31m'
ORANGE = '\033[91m'
YELLOW = '\033[93m'
GREEN = '\033[92m'
CYAN = '\033[36m'
ENDC = '\033[0m'


class GPIOValve():
    """
    Abstract control for a physical valve.

    Attributes:
        pin (int): The GPIO pin that controls the valve
        is_open (bool): The valve's current state
    """

    def __init__(self, pin, active_low):
        """
        The constructor for the GPIOValve class.

        Parameters:
            pin (int): The address of the GPIO pin that controls the valve
            active_low (bool): Whether the valve is active low
        """
        self.pin = GPIO_PIN[pin]
        GPIO.setup(self.pin, GPIO.OUT)
        self.on = not active_low

    def open(self):
        """
        Open the valve.
        """
        print(f'{GREEN}Opening valve{ENDC}')
        GPIO.output(self.pin, self.on)

    def close(self):
        """
        Close the valve.
        """
        print(f'{RED}Closing valve{ENDC}')
        GPIO.output(self.pin, not self.on)
        time.sleep(10)

    def is_open(self):
        return GPIO.input(self.pin) == self.on
