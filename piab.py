#!/usr/bin/env python3
from bottle import route, request, run, template

from pypentair import Pump
from heater import Heater

import threading
import datetime
# import pentair
import smbus
import time
import json
# import sms
import sys

PREFIX = '/home/pi/piab'

with open(f'{PREFIX}/json/parts.json', 'r') as file:
    parts = json.load(file)

with open(f'{PREFIX}/json/parts.json', 'w') as file:
    json.dump(parts, file, sort_keys=True, indent=3)

with open(f'{PREFIX}/json/config.json', 'r') as file:
    config = json.load(file)

with open(f'{PREFIX}/json/config.json', 'w') as file:
    json.dump(config, file, sort_keys=True, indent=3)

bus = smbus.SMBus(1)

pump = Pump(1)

RED = '\033[31m'
ORANGE = '\033[91m'
YELLOW = '\033[93m'
GREEN = '\033[92m'
CYAN = '\033[36m'
ENDC = '\033[0m'

colors = {
    'HeatedTemperature': ORANGE,
    'RoofTemperature': RED,
    'PoolTemperature': CYAN
}


class backgroundWorker (threading.Thread):
    # TODO: This whole worker class needs to be configurable, DRYed, etc.
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        sentMessage = False
        lastChange = datetime.datetime.now()
        lastAction = ""

        item = config['heaters']['Solar']
        module = config['relay_modules'][item['module']]
        relay = module['relays'][str(item['relay'])]

        active_low = 'active_low' in module and module['active_low']

        heater = Heater(pump, relay['gpio'], active_low)

        # Start with heater off
        heater.turn_off()

        # Turn heater on
        if len(sys.argv) > 1 and sys.argv[1] == 'heat':
            heater.turn_on()

        while True:
            print(lastAction, (datetime.datetime.now() - lastChange).total_seconds())
            for sensor_name, sensor in config['sensors'].items():
                converter = config['converters'][sensor['converter']]
                addr = converter['address']
                board = parts['converters'][converter['model']]
                cmd = board['adcs'][sensor['adc']]

                # First reading on the PCF8591 is always stale
                bus.read_byte_data(int(addr, 16), int(cmd, 16))

                total = 0
                count = 10  # TODO: This might be better as a config setting
                for _ in range(count):
                    total += bus.read_byte_data(int(addr, 16), int(cmd, 16))

                sensor['value'] = total / count

                x0 = sensor['points'][0][0]
                y0 = sensor['points'][0][1]
                x1 = sensor['points'][1][0]
                y1 = sensor['points'][1][1]

                m = (y1-y0)/(x1-x0)
                b = y0-(m*x0)

                sensor['deg_F'] = m*sensor['value'] + b

                print(f"{colors[sensor_name]}{sensor_name} {str(int(sensor['deg_F']))}F ({str(int(sensor['value']))}) {ENDC}", end='')
            print(f"{YELLOW}RPM: {pump.rpm}{ENDC}")

            if 'value' in config['sensors']['PoolTemperature']:
                if config['sensors']['PoolTemperature']['deg_F'] > 82 and not sentMessage:
                    print("Pool is warm; sending SMS.")
    #                        sms.sendMessage("Pool is warm enough to swim =)")
                    sentMessage = True
                elif config['sensors']['PoolTemperature']['deg_F'] < 80 and sentMessage:
                    sentMessage = False

            if 'value' in config['sensors']['RoofTemperature'] and 'value' in config['sensors']['PoolTemperature'] and 'value' in config['sensors']['HeatedTemperature']:
                with open(f'{PREFIX}/temp.csv', 'a') as csv:
                    csv.write(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') + ", " + str(config['sensors']['RoofTemperature']['deg_F']) + ", " + str(config['sensors']['PoolTemperature']['deg_F']) + ", " + str(config['sensors']['HeatedTemperature']['deg_F']) + "\n")
                if config['sensors']['RoofTemperature']['deg_F'] - config['sensors']['PoolTemperature']['deg_F'] > 5:
                    if lastAction != "turn_on":
                        lastAction = "turn_on"
                        lastChange = datetime.datetime.now()
                    if heater.is_on:
                        print(f"{RED}Solar Heater is on.  Good.{ENDC}")
                    else:
                        print(f"{RED}Turning Solar Heater on and holding 5m for system to settle.{ENDC}")
                        heater.turn_on()
                        for i in range(30):
                            print(f'{RED}{i*10} of 300s{ENDC}')
                            pump.maintain_speed()
                            time.sleep(10)
                elif config['sensors']['HeatedTemperature']['deg_F'] - config['sensors']['PoolTemperature']['deg_F'] < 1:
                    if lastAction != "turn_off":
                        lastAction = "turn_off"
                        lastChange = datetime.datetime.now()
                    if heater.is_on:
                        if (datetime.datetime.now() - lastChange).total_seconds() > 300:
                            heater.turn_off()
                        else:
                            print(f"{CYAN}Heat is waning.{ENDC}")
                    else:
                        print(f"{CYAN}Solar Heater is off.  Good.{ENDC}")
                else:
                    print(f"{GREEN}Avoiding Bounce.{ENDC}")
                    if lastAction != "avoiding_bounce":
                        lastAction = "avoiding_bounce"
                        lastChange = datetime.datetime.now()
                pump.maintain_speed()
            time.sleep(15)


workerThread = backgroundWorker()
workerThread.setDaemon(True)
workerThread.start()


@route('/')
def index():
    return template('html/index.html')


@route('/config')
def configure():
    return template('html/config.html', config=config, parts=parts)


@route('/led')
def led():
    if config['switch']:
        checked = "checked"
    else:
        checked = ""

    return template('html/led.html', checked=checked)


@route('/popup/<type>/<name>')
def popup(type, name):
    sensor = config[type][name]
    converter = config['converters'][sensor['converter']]
    addr = converter['address']
    board = parts['converters'][converter['model']]
    cmd = board['adcs'][sensor['adc']]

    # Throw away the first reading as it's old...on the PCF8591 anyway
    bus.read_byte_data(int(addr, 16), int(cmd, 16))

    total = 0
    count = 100  # TODO: This might be better as a config setting
    for _ in range(count):
        total += bus.read_byte_data(int(addr, 16), int(cmd, 16))

    sensor['value'] = total / count

    x0 = sensor['points'][0][0]
    y0 = sensor['points'][0][1]
    x1 = sensor['points'][1][0]
    y1 = sensor['points'][1][1]

    m = (y1-y0)/(x1-x0)
    b = y0-(m*x0)

    sensor['deg_F'] = m*sensor['value'] + b

    return str(int(sensor['deg_F'])) + " F (" + str(sensor['value']) + ")"


@route('/action', method='POST')
def action():
    item_type = request.forms.get('type')
    item_name = request.forms.get('name')

    item = config[item_type][item_name]
    item['state'] = bool(int(request.forms.get('state')))

    # Item is an abstraction (Pump, Heater, Accessory) connected to a port
    if 'protocol' in item and 'port' in item:
        None
    else:
        # Item is an abstraction (Pump, Heater, Accessory) connected to a relay
        if 'module' in item and 'relay' in item:
            module = config['relay_modules'][item['module']]
            relay = module['relays'][str(item['relay'])]

        else:  # Item is a Relay Module
            module = item
            relay = module['relays'][request.forms.get('relay')]

        relay['state'] = item['state']

        pin = GPIO_PIN[relay['gpio']]
        GPIO.setup(pin, GPIO.OUT)

        if 'active_low' in module and module['active_low']:
            on = False
        else:
            on = True

        if relay['state']:
            GPIO.output(pin, on)
        else:
            GPIO.output(pin, not on)


run(host='0.0.0.0', port=8000, debug=True, reloader=False)
