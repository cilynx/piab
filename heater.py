from valve import GPIOValve

RED = '\033[31m'
ORANGE = '\033[91m'
YELLOW = '\033[93m'
GREEN = '\033[92m'
CYAN = '\033[36m'
ENDC = '\033[0m'


class Heater():
    """
    Abstract control for a physical heater.

    Attributes:
        is_on (bool): The heater's current state
    """

    def __init__(self, pump, pin, active_low):
        """
        The constructor for the Heater class.

        Parameters:
            pump (Pump): The pump attached to the heater
            pin (int): The address of the GPIO pin that controls the valve
            active_low (bool): Whether the valve is active low
        """
        self.valve = GPIOValve(pin, active_low)
        self.pump = pump

    def turn_on(self):
        """
        Ramp up pump RPM, then open the valve.
        """
        print(f'{RED}Turning heater on{ENDC}')
        self.pump.rpm = 3000
        self.valve.open()
        self.is_on = True

    def turn_off(self):
        """
        Close the valve, then ramp down pump RPM.
        """
        print(f'{CYAN}Turning heater off{ENDC}')
        self.valve.close()
        self.pump.rpm = 1400
        self.is_on = False
