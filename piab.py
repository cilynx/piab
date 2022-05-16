#!/usr/bin/env python3

import pentair
#import sms
import datetime

import json

with open('json/parts.json', 'r') as file:
    parts = json.load(file)

with open('json/config.json', 'r') as file:
    config = json.load(file)

# Keeping this around in case I need it later.
with open('json/config.json', 'w') as file:
    json.dump(config, file, sort_keys=True, indent=3)

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)
GPIO_PIN = [11,12,13,15,16,18,25]

import smbus

bus = smbus.SMBus(1)

import threading
import time

RED    = '\033[31m'
ORANGE = '\033[91m'
YELLOW = '\033[93m'
GREEN  = '\033[92m'
CYAN   = '\033[36m'
ENDC   = '\033[0m'

class backgroundWorker (threading.Thread):
    # TODO: This whole worker class is a goat rodeo.  It needs to be configurable, DRYed, etc.
    def __init__(self):
         threading.Thread.__init__(self)
    def run(self):
        sentMessage = False
        while True:
            for sensor_name,sensor in config['sensors'].items():
                time.sleep(1)

                converter = config['converters'][sensor['converter']]
                addr = converter['address']
                board = parts['converters'][converter['model']]
                cmd = board['adcs'][sensor['adc']]

                # Throw away the first reading as it's old...on the PCF8591 anyway
                bus.read_byte_data(int(addr,16), int(cmd,16))

                total = 0
                count = 10 # TODO: This might be better as a config setting
                for _ in range(count):
                    total += bus.read_byte_data(int(addr,16), int(cmd,16))

                sensor['value'] = total / count

                x0 = sensor['points'][0][0]
                y0 = sensor['points'][0][1]
                x1 = sensor['points'][1][0]
                y1 = sensor['points'][1][1]

                m = (y1-y0)/(x1-x0)
                b = y0-(m*x0)

                sensor['deg_F'] = m*sensor['value'] + b
                print(f"{sensor_name} {str(int(sensor['deg_F']))}F ({str(int(sensor['value']))})")

                item = config['heaters']['Solar']
                module = config['relay_modules'][item['module']]
                relay = module['relays'][str(item['relay'])]
                pin = GPIO_PIN[relay['gpio']]
                GPIO.setup(pin, GPIO.OUT)

                if 'active_low' in module and module['active_low']:
                    on = False
                else:
                    on = True

                if 'value' in config['sensors']['PoolTemperature']:
                    if config['sensors']['PoolTemperature']['deg_F'] > 82 and not sentMessage:
                        print("Pool is warm; sending SMS.")
#                        sms.sendMessage("Pool is warm enough to swim =)")
                        sentMessage = True
                    elif config['sensors']['PoolTemperature']['deg_F'] < 80 and sentMessage:
                        sentMessage = False

                if 'value' in config['sensors']['RoofTemperature'] and 'value' in config['sensors']['PoolTemperature'] and 'value' in config['sensors']['HeatedTemperature']:
                    csv=open('./temp.csv', 'a')
                    csv.write(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') + ", " + str(config['sensors']['RoofTemperature']['deg_F']) + ", " + str(config['sensors']['PoolTemperature']['deg_F']) + ", " + str(config['sensors']['HeatedTemperature']['deg_F']) + "\n")
                    csv.close()
                    if config['sensors']['RoofTemperature']['deg_F'] - config['sensors']['PoolTemperature']['deg_F'] > 15:
                        if 'state' in config['heaters']['Solar'] and config['heaters']['Solar']['state'] == True:
                            print(f"{RED}Solar Heater is on.  Good.{ENDC}")
                            pentair.setPumpRPM(3000)
                        else:
                            print(f"{RED}Turning Solar Heater on and holding 5m for system to settle.{ENDC}")
                            config['heaters']['Solar']['state'] = True
                            pentair.setPumpRPM(3000)
                            print(f'{RED}Reached RPM.  Opening valve.{ENDC}')
                            GPIO.output(pin, on)
                            for i in range(30):
                                print(f'{RED}{i*10} of 300s{ENDC}')
                                time.sleep(10)
                                pentair.setPumpRPM(3000)
                    elif config['sensors']['HeatedTemperature']['deg_F'] - config['sensors']['PoolTemperature']['deg_F'] < 1:
                        if 'state' in config['heaters']['Solar'] and config['heaters']['Solar']['state'] == True:
                            print(f"{CYAN}Turning Solar Heater off.{ENDC}")
                            config['heaters']['Solar']['state'] = False
                            GPIO.output(pin, not on)
                            time.sleep(10)  # Give valve time to close before slowing the pump
                        else:
                            print(f"{CYAN}Solar Heater is off.  Good.{ENDC}")
                        pentair.setPumpRPM(1400)

                    else:
                        print(f"{GREEN}Avoiding Bounce.{ENDC}")
                        if 'state' in config['heaters']['Solar'] and config['heaters']['Solar']['state'] == True:
                            pentair.setPumpRPM(3000)
                        else:
                            pentair.setPumpRPM(1400)

workerThread = backgroundWorker()
workerThread.setDaemon(True)
workerThread.start()

from bottle import route, request, run, static_file, template

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
    bus.read_byte_data(int(addr,16), int(cmd,16))

    total = 0
    count = 100 # TODO: This might be better as a config setting
    for _ in range(count):
        total += bus.read_byte_data(int(addr,16), int(cmd,16))

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

    if 'protocol' in item and 'port' in item: # Item is an abstraction (Pump, Heater, Accessory) connected to a Serial Port
        None
    else:
        if 'module' in item and 'relay' in item: # Item is an abstraction (Pump, Heater, Accessory) connected to a Relay Module
            module = config['relay_modules'][item['module']]
            relay = module['relays'][str(item['relay'])]

        else: # Item is a Relay Module
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
