#!/usr/bin/env python3
import binascii
import time

RED    = '\033[31m'
ORANGE = '\033[91m'
YELLOW = '\033[93m'
GREEN  = '\033[92m'
CYAN   = '\033[36m'
ENDC   = '\033[0m'

PACKET_HEADER = [0xff, 0x00, 0xff, 0xa5]

VERSION = 0x00

ADDRESSES = {
        0x10: 'SUNTOUCH',
        0x21: 'REMOTE_CONTROLLER',
        0x48: 'QUICKTOUCH',
        0x60: 'INTELLIFLO_PUMP_0',
        0x0f: 'BROADCAST',
        'SUNTOUCH': 0x10,
        'REMOTE_CONTROLLER': 0x21,
        'QUICKTOUCH': 0x48,
        'INTELLIFLO_PUMP_0': 0x60,
        'BROADCAST': 0x0f
        }

SRC = ADDRESSES['REMOTE_CONTROLLER']

COMMANDS = {
        0x01: 'PUMP_MODE',
        0x04: 'REMOTE_CONTROL',
        0x06: 'PUMP_POWER',
        0x07: 'PUMP_STATUS',
        0xff: 'UNKNOWN',
        'PUMP_MODE': 0x01,
        'REMOTE_CONTROL': 0x04,
        'PUMP_POWER': 0x06,
        'PUMP_STATUS': 0x07
        }

COMMAND_BLOCKS_CONSOLE = {
        COMMANDS['PUMP_MODE']: True,
        COMMANDS['PUMP_POWER']: True,
        COMMANDS['PUMP_STATUS']: False
        }

PACKET_FIELDS = {
        'VERSION': 4,
        'DST': 5,
        'SRC': 6,
        'COMMAND': 7,
        'DATA_LENGTH': 8,
        }

PUMP_STATUS_FIELDS = {
        'RUN': 0,
        'MODE': 1,
        'DRIVE_STATE': 2,
        'WATTS_H': 3,
        'WATTS_L': 4,
        'RPM_H': 5,
        'RPM_L': 6,
        'GPM': 7,
        'PPC': 8,
        'UNKNOWN': 9,
        'ERROR': 10,
        'REMAINING_TIME_H': 11,
        'REMAINING_TIME_M': 12,
        'CLOCK_TIME_H': 13,
        'CLOCK_TIME_M': 14
        }

PUMP_MODES = {
        0x00: 'OFF',
        0x02: 'SET_RPM',
        0x03: 'SET_PROGRAM',
        'OFF': 0x00,
        'SET_RPM': [0x02, 0xc4],
        'SET_PROGRAM': 0x03,
        }

PUMP_POWER = {
        0x04: 'ON',
        0x10: 'OFF',
        'ON': 0x04,
        'OFF': 0x10,
        True: 0x04,
        False: 0x10
        }

PUMP_PROGRAMS = {
        'STOP': 0x00,
        1: 0x08,
        2: 0x10,
        3: 0x18,
        4: 0x20,
        }

REMOTE_CONTROL_MODES = {
        0x00: 'OFF',
        0xff: 'ON',
        'OFF': 0x00,
        'ON': 0xff,
        False: 0x00,
        True: 0xff
        }

import serial
RS485 = serial.Serial(
        port='/dev/ttyUSB0',
        baudrate = 9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
        )

def setPumpPower(state):
    print("Turning Pump", state)
    sendPump(COMMANDS['PUMP_POWER'], [PUMP_POWER[state]])

def setPumpRPM(rpm):
    print("Setting pump RPM to", rpm)
    data = PUMP_MODES['SET_RPM'][:]
    data.extend([int(rpm / 256), int(rpm % 256)])
    response = sendPump(COMMANDS['PUMP_MODE'], data)
    status = None
    actual_rpm = None
    while actual_rpm != rpm:
        while not status:
            status = getPumpStatus()
        actual_rpm = status[2]
        status = None
        print("RPM:",actual_rpm)
    return rpm

def setPumpProgram(program):
    sendPump(COMMANDS['PUMP_MODE'], PUMP_PROGRAMS[program])

def sendPump(command, data=None):
    print(f"{CYAN}sendPump({command}, {data}){ENDC}")

    if(COMMAND_BLOCKS_CONSOLE[command]):
        setPumpRemoteControl(True)

    dst = ADDRESSES['INTELLIFLO_PUMP_0']

    RS485.write(buildPacket(dst, command, data))
    response = getResponsePacket()

    if(COMMAND_BLOCKS_CONSOLE[command]):
        setPumpRemoteControl(False)

    return response

def setPumpRemoteControl(state):
    return
    print(f"{CYAN}setPumpRemoteControl(){ENDC}")
    RS485.write(buildPacket(ADDRESSES['INTELLIFLO_PUMP_0'], COMMANDS['REMOTE_CONTROL'], [REMOTE_CONTROL_MODES[state]]))
    return getResponsePacket()

def getPumpStatus():
    print(f"{CYAN}getPumpStatus(){ENDC}")
    response = sendPump(COMMANDS['PUMP_STATUS'])
    if response[PACKET_FIELDS['COMMAND']] == COMMANDS['PUMP_STATUS']:
        data = response[9:]
        mode = data[PUMP_STATUS_FIELDS['MODE']]
        watts = 256 * data[PUMP_STATUS_FIELDS['WATTS_H']] + data[PUMP_STATUS_FIELDS['WATTS_L']]
        rpm = 256 * data[PUMP_STATUS_FIELDS['RPM_H']] + data[PUMP_STATUS_FIELDS['RPM_L']]
        hour_r, minute_r = data[PUMP_STATUS_FIELDS['REMAINING_TIME_H']], data[PUMP_STATUS_FIELDS['REMAINING_TIME_M']]
        hour_c, minute_c = data[PUMP_STATUS_FIELDS['CLOCK_TIME_H']], data[PUMP_STATUS_FIELDS['CLOCK_TIME_M']]
        return mode, watts, rpm, hour_r, minute_r, hour_c, minute_c

def getResponsePacket():
    print(f"{CYAN}getResponsePacket(){ENDC}")
    packet = []
    while True:
        c = int.from_bytes(RS485.read(), 'big')
        packet.append(c)

        if len(packet) > 4:
            packet.pop(0)
        if packet == PACKET_HEADER:
            packet.extend(RS485.read(4)) # Version, DST, SRC, Command

            data_length = int.from_bytes(RS485.read(), 'big')
            if data_length > 0:
                data = RS485.read(data_length)
                packet.append(data_length)
                packet.extend(data)

            print(f"{GREEN}{packet}{ENDC}")
            print(f"{ORANGE}Version: {packet[4]}{ENDC}")
            print(f"{ORANGE}DST: {packet[5]}{ENDC}")
            print(f"{ORANGE}SRC: {packet[6]}{ENDC}")
            print(f"{ORANGE}Command: {COMMANDS[packet[7]]}{ENDC}")
            print(f"{ORANGE}Data Length: {packet[8]}{ENDC}")
            print(f"{ORANGE}Data: {packet[9:]}{ENDC}")
            payload = packet[3:]

            calc_check_h = int(sum(payload) / 256)
            calc_check_l = int(sum(payload) % 256)

            read_check = list(RS485.read(2))

            if read_check == [calc_check_h, calc_check_l]:
                packet.extend(read_check)
                return bytearray(packet)
            else:
                print(f"{RED}Bad Checksum. Calc: {[calc_check_h, calc_check_l]}, Read: {read_check}{ENDC}")
                return None

def buildPayload(dst, command, data=None):
    payload = bytearray([PACKET_HEADER[3], VERSION, dst, SRC, command])

    if data != None:
        payload.append(len(data))
        payload.extend(data)
    else:
        payload.append(0)

    checkh = int(sum(payload) / 256)
    checkl = int(sum(payload) % 256)
    payload.extend([checkh, checkl])

    return payload

def buildPacket(dst, command, data=None):
    packet = bytearray(PACKET_HEADER[0:3])
    packet.extend(buildPayload(dst, command, data))

    # import binascii
    pack = list(packet)
    print(f"{YELLOW}{list(pack)}")
    print(f"{ORANGE}Version: {pack[4]}{ENDC}")
    print(f"{ORANGE}DST: {pack[5]}{ENDC}")
    print(f"{ORANGE}SRC: {pack[6]}{ENDC}")
    print(f"{ORANGE}Command: {COMMANDS[pack[7]]}{ENDC}")
    print(f"{ORANGE}Data Length: {pack[8]}{ENDC}")
    print(f"{ORANGE}Data: {pack[9:-2]}{ENDC}")
    if pack[7] == COMMANDS['PUMP_MODE']:
        print(f"{ORANGE}Pump Mode: {PUMP_MODES[pack[9]]}{ENDC}")
        if [pack[9],pack[10]] == PUMP_MODES['SET_RPM']:
            print(f"{ORANGE}RPM: {pack[11]*256+pack[12]}{ENDC}")

    return packet
