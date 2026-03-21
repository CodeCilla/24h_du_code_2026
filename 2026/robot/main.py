import machine
import utime, sys
import json
from stm32_alphabot_v2 import AlphaBot_v2
import gc
from stm32_ssd1306 import SSD1306, SSD1306_I2C
from stm32_vl53l0x import VL53L0X
from stm32_nec import NEC_8, NEC_16
import neopixel
import _thread
import os
#import bluetooth
#from stm32_ble_uart import BLEUART

import buzzer

# variable:
alphabot = oled = vl53l0x = None
ir_current_remote_code = None

dict_base=dict([('C-',32.70),('C#',34.65),('D-',36.71),('D#',38.89),('E-',41.20),('E#',43.65),('F-',43.65),('F#',46.35),('G-',49.00),('G#',51.91),('A-',55.00),('A#',58.27),('B-',61.74),('S-',0)])

# -------------------------------
# neopixel
# -------------------------------
class FoursNeoPixel():
    def __init__(self, pin_number):
        self._pin = pin_number
        self._max_leds = 4
        self._leds = neopixel.NeoPixel(self._pin, 4)

    def set_led(self, addr, red, green, blue):
        if addr >= 0 and addr < self._max_leds:
            # coded on BGR
            self._leds[addr] = (blue,  green, red)

    def set_led2(self, addr, rgb):
        if addr >= 0 and addr < self._max_leds:
            # coded on BGR
            self._leds[addr] = rgb
    def show(self):
        self._leds.write()
    def clear(self):
        for i in range (0, self._max_leds):
            self.set_led(i, 0,0,0)
        self.show()

def neo_french_flag_threaded(leds):
    while True:
        leds.set_led(0, 250, 0, 0)
        leds.set_led(1, 250, 0, 0)
        leds.set_led(2, 250, 0, 0)
        leds.set_led(3, 250, 0, 0)
        leds.show()
        utime.sleep(1)
        leds.set_led(0, 250, 250, 250)
        leds.set_led(1, 250, 250, 250)
        leds.set_led(2, 250, 250, 250)
        leds.set_led(3, 250, 250, 250)
        leds.show()
        utime.sleep(1)
        leds.set_led(0, 0, 0, 250)
        leds.set_led(1, 0, 0, 250)
        leds.set_led(2, 0, 0, 250)
        leds.set_led(3, 0, 0, 250)
        leds.show()
        utime.sleep(1)

        leds.clear()
        utime.sleep(2)


def neo_french_flag(fours_rgb_leds):
    _thread.start_new_thread(neo_french_flag_threaded, ([fours_rgb_leds]))

# ----------------------------
# Remote Control
# ----------------------------
#    Remote control                    Correlation table
# |-----------------|             |----------------------|
# |     |     |     |             |       |       |      |
# | CH- | CH  | CH+ |             | Vol-  | Play  | Vol+ |
# |     |     |     |             |       | Pause |      |
# |     |     |     |             |       |       |      |
# |-----------------|             |----------------------|
# |     |     |     |             |       |       |      |
# | |<< | >>| | >|| |             | Setup | Up    | Stop |
# |     |     |     |             |       |       | Mode |
# |     |     |     |             |       |       |      |
# |-----------------|             |----------------------|
# |     |     |     |             |       |       |      |
# |  -  |  +  | EQ  |             | Left  | Enter | Right|
# |     |     |     |             |       | Save  |      |
# |     |     |     |             |       |       |      |
# |-----------------|             |----------------------|
# |     |     |     |             |       |       |      |
# |  0  |100+ | 200+|   <==>      |   0   | Down  | Back |
# |     |     |     |             |       |       |      |
# |-----------------|             |----------------------|
# |     |     |     |             |       |       |      |
# |  1  |  2  |  3  |             |   1   |   2   |   3  |
# |     |     |     |             |       |       |      |
# |-----------------|             |----------------------|
# |     |     |     |             |       |       |      |
# |  4  |  5  |  6  |             |   4   |   5   |   6  |
# |     |     |     |             |       |       |      |
# |-----------------|             |----------------------|
# |     |     |     |             |       |       |      |
# |  7  |  8  |  9  |             |   7   |   8   |   9  |
# |     |     |     |             |       |       |      |
# |-----------------|             |----------------------|
#
def remoteNEC_basicBlack_getButton(hexCode):
    if hexCode == 0x0c: return "1"
    elif hexCode == 0x18: return "2"
    elif hexCode == 0x5e: return "3"
    elif hexCode == 0x08: return "4"
    elif hexCode == 0x1c: return "5"
    elif hexCode == 0x5a: return "6"
    elif hexCode == 0x42: return "7"
    elif hexCode == 0x52: return "8"
    elif hexCode == 0x4a: return "9"
    elif hexCode == 0x16: return "0"
    elif hexCode == 0x40: return "up"
    elif hexCode == 0x19: return "down"
    elif hexCode == 0x07: return "left"
    elif hexCode == 0x09: return "right"
    elif hexCode == 0x15: return "enter_save"
    elif hexCode == 0x0d: return "back"
    elif hexCode == 0x45: return "volMinus"
    elif hexCode == 0x47: return "volPlus"
    elif hexCode == 0x46: return "play_pause"
    elif hexCode == 0x44: return "setup"
    elif hexCode == 0x43: return "stop_mode"
    else: return "NEC remote code error"

def remoteNEC_callback(data, addr, ctrl):
    global ir_current_remote_code
    print("coucou")
    if data < 0:  # NEC protocol sends repeat codes.
        print('Repeat code.')
    else:
        #print('Data {:02x} Addr {:04x} Ctrl {:02x}'.format(data, addr, ctrl))
        ir_current_remote_code = remoteNEC_basicBlack_getButton(data)
        print('Data {:02x} Addr {:04x} Ctrl {:02x} {}'.format(data, addr, ctrl, ir_current_remote_code))

# ----------------------------
# play music
# ----------------------------
def music_play():
    d= [['C-3', 4 ], ['D-3', 4 ], ['E-3', 4 ], ['F-3', 4 ], ['G-3', 4 ] , ['A-3', 4 ], ['B-3', 4 ]]
    freq_list = [ dict_base[d[i][0][:2] ] * 2**(int(d[i][0][2]) - 1 ) for i in range(0, len(d), 1 ) ]
    duration_list= [int(d[i][1]) * 125 for i in range(0,len(d), 1)]
    buz = buzzer.Buzzer()
    for i in range(len(freq_list)):
        buz.pitch(alphabot, freq_list[i], duration_list[i], 50)

# ----------------------------
# Follow line
# ----------------------------
_BLACKLIMIT = 650

DISPLAY_LINE_TRACKING_INFO = 1
def _motor_left_right(ml, mr):
    alphabot.setMotors(left=ml, right=mr)
    if DISPLAY_LINE_TRACKING_INFO:
        oled.text('L {}'.format(ml),64, 0)
        oled.text('R {}'.format(mr),64, 16)

def show_motor_left_right(ml, mr):
    if DISPLAY_LINE_TRACKING_INFO:
        oled.text('L {}'.format(ml),64, 0)
        oled.text('R {}'.format(mr),64, 16)


def isSensorAboveLine(robot, sensorName, blackLimit = 300):
    sensorsValue = robot.TRSensors_readLine(sensor=0) # all sensors values
    if 'IR' in sensorName:
        if sensorName=='IR1' and sensorsValue[0] < blackLimit: return True
        elif sensorName=='IR2' and sensorsValue[1] < blackLimit: return True
        elif sensorName=='IR3' and sensorsValue[2] < blackLimit: return True
        elif sensorName=='IR4' and sensorsValue[3] < blackLimit: return True
        elif sensorName=='IR5' and sensorsValue[4] < blackLimit: return True
        else: return False
    else:
        raise ValueError("name '" + sensorName + "' is not a sensor option")

SPEED_MOTOR=13
def line_follower(limit=_BLACKLIMIT):
    oled.fill(0)
    if alphabot.readUltrasonicDistance() <= 5:
        alphabot.stop()
        #music_play()
    else:
        if not isSensorAboveLine(alphabot, 'IR2', blackLimit=limit) and not isSensorAboveLine(alphabot, 'IR3', blackLimit=limit) and not isSensorAboveLine(alphabot, 'IR4', blackLimit=limit):
            oled.fill(0)
            oled.show()
            oled.text('En arriere', 0, 0)
            oled.show()
            alphabot.moveBackward(SPEED_MOTOR)
        if not isSensorAboveLine(alphabot, 'IR2', blackLimit=limit) and not isSensorAboveLine(alphabot, 'IR3', blackLimit=limit) and isSensorAboveLine(alphabot, 'IR4', blackLimit=limit):
            oled.fill(0)
            oled.show()
            oled.text('A Gauche', 0, 0)
            oled.show()
            alphabot.setMotorLeft(SPEED_MOTOR)
            alphabot.setMotorRight(0)
        if not isSensorAboveLine(alphabot, 'IR2', blackLimit=limit) and isSensorAboveLine(alphabot, 'IR3', blackLimit=limit) and not isSensorAboveLine(alphabot, 'IR4', blackLimit=limit):
            oled.fill(0)
            oled.show()
            oled.text('Tout Droit', 0, 0)
            oled.show()
            alphabot.setMotorLeft(SPEED_MOTOR)
            alphabot.setMotorRight(SPEED_MOTOR)
        if not isSensorAboveLine(alphabot, 'IR2', blackLimit=limit) and isSensorAboveLine(alphabot, 'IR3', blackLimit=limit) and isSensorAboveLine(alphabot, 'IR4', blackLimit=limit):
            alphabot.setMotorLeft(SPEED_MOTOR)
            alphabot.setMotorRight(5)
        if isSensorAboveLine(alphabot, 'IR2', blackLimit=limit) and not isSensorAboveLine(alphabot, 'IR3', blackLimit=limit) and not isSensorAboveLine(alphabot, 'IR4', blackLimit=limit):
            oled.fill(0)
            oled.show()
            oled.text('A droite', 0, 0)
            oled.show()
            alphabot.setMotorLeft(0)
            alphabot.setMotorRight(SPEED_MOTOR)
        if isSensorAboveLine(alphabot, 'IR2', blackLimit=limit) and not isSensorAboveLine(alphabot, 'IR3', blackLimit=limit) and isSensorAboveLine(alphabot, 'IR4', blackLimit=limit):
            alphabot.moveBackward(SPEED_MOTOR)
        if isSensorAboveLine(alphabot, 'IR2', blackLimit=limit) and isSensorAboveLine(alphabot, 'IR3', blackLimit=limit) and not isSensorAboveLine(alphabot, 'IR4', blackLimit=limit):
            alphabot.setMotorLeft(5)
            alphabot.setMotorLeft(SPEED_MOTOR)
        if isSensorAboveLine(alphabot, 'IR2', blackLimit=limit) and isSensorAboveLine(alphabot, 'IR3', blackLimit=limit) and isSensorAboveLine(alphabot, 'IR4', blackLimit=limit):
            alphabot.moveBackward(SPEED_MOTOR)

def line_follower_simple(limit=_BLACKLIMIT):
    oled.fill(0)
    if alphabot.readUltrasonicDistance() <= 5:
        alphabot.stop()
        oled.text('Obstacle', 4*8, 0)
        oled.text('detected', 4*8, 16)
        oled.text('STOPPED!', 4*8, 32)
        #music_play()
    else:
        # get the light detection measurement on one time
        line_detection = alphabot.TRSensors_readLine()
        if DISPLAY_LINE_TRACKING_INFO:
            print("readline:", line_detection)
            if DISPLAY_LINE_TRACKING_INFO: oled.text('{:.02f}'.format(line_detection[1]), 0, 0)
            if DISPLAY_LINE_TRACKING_INFO: oled.text('{:.02f}'.format(line_detection[2]), 0, 16)
            if DISPLAY_LINE_TRACKING_INFO: oled.text('{:.02f}'.format(line_detection[3]), 0, 32)

        if line_detection[2] < limit:
            # we are on the line
            alphabot.setMotors(right=22, left=22)
            show_motor_left_right(22, 22)
        elif line_detection[1] < limit:
            #alphabot.turnLeft(65, 25)
            alphabot.turnLeft(65, duration_ms=50)
            show_motor_left_right(65, 0)
        elif line_detection[3] < limit:
            #alphabot.turnRight(65, 25)
            alphabot.turnRight(65, duration_ms=50)
            show_motor_left_right(0, 65)
        elif line_detection[2] > limit:
            alphabot.moveBackward(35, duration_ms=50)
            show_motor_left_right(-35, -35)


#         if (line_detection[1] < limit):
#             alphabot.turnLeft(65, 25)
#             show_motor_left_right(65, 0)
#         elif line_detection[3] < limit:
#             alphabot.turnRight(65, 25)
#             show_motor_left_right(0, 65)
#         elif line_detection[2] > limit:
#             alphabot.setMotors(right=22, left=22)
#             show_motor_left_right(22, 22)
#         elif line_detection[2] < limit:
#             alphabot.moveBackward(35, duration_ms=50)
#             show_motor_left_right(-35, -35)

    if vl53l0x is not None:
        oled.text('tof {:4.0f}mm'.format(vl53l0x.getRangeMillimeters()), 0, 48)
    oled.show()


# ------------------------------------------------
last_proportional = 0
integral = 0
maximum = 100
derivative = 0

# Algo from: https://www.waveshare.com/w/upload/7/74/AlphaBot2.tar.gz
def line_follower2():
    oled.fill(0)
    if alphabot.readUltrasonicDistance() <= 5:
        print("Obstacle!!!!!")
        alphabot.stop()
        #music_play()
    else:
        global last_proportional
        global integral
        global derivative
        # get the light detection measurement on one time
        position,sensors_line = alphabot.TRSensors_position_readLine()

        if (sensors_line[0] > 900 and sensors_line[1] > 900 and sensors_line[2] > 900 and sensors_line[3] > 900 and sensors_line[4] > 900):
            _motor_left_right(0, 0)
            return

        if DISPLAY_LINE_TRACKING_INFO:
            print("readline:", position, sensors_line)
            oled.text('{:.02f}'.format(sensors_line[1]), 0, 0)
            oled.text('{:.02f}'.format(sensors_line[2]), 0, 16)
            oled.text('{:.02f}'.format(sensors_line[3]), 0, 32)

        # The "proportional" term should be 0 when we are on the line.
        proportional = position - 2000

        # Compute the derivative (change) and integral (sum) of the position.
        derivative = proportional - last_proportional
        integral += proportional

        # Remember the last position.
        last_proportional = proportional

        '''
        // Compute the difference between the two motor power settings,
        // m1 - m2.  If this is a positive number the robot will turn
        // to the right.  If it is a negative number, the robot will
        // turn to the left, and the magnitude of the number determines
        // the sharpness of the turn.  You can adjust the constants by which
        // the proportional, integral, and derivative terms are multiplied to
        // improve performance.
        '''
        power_difference = proportional/30  + integral/10000 + derivative*2

        if (power_difference > maximum):
            power_difference = maximum
        if (power_difference < - maximum):
            power_difference = - maximum
        print("Line follower: ", position, power_difference)
        if (power_difference < 0):
            _motor_left_right(maximum + power_difference, maximum)
        else:
            _motor_left_right(maximum, maximum - power_difference)
        utime.sleep_ms(100)
        alphabot.stop()
    oled.show()

# ----------------------------
# Motor move
# ----------------------------
def move_right(t=30):
    alphabot.turnRight(20, t)

def move_left(t=30):
    alphabot.turnLeft(20, t)

def move_forward(t=200):
    if alphabot.readUltrasonicDistance() > 10:
        alphabot.moveForward(20)
        utime.sleep_ms(t)
        alphabot.stop()
    else:
        alphabot.stop()

def move_backward(t=200):
    alphabot.moveBackward(20)
    utime.sleep_ms(t)
    alphabot.stop()

def move_circumvention():
    move_left(450)
    move_forward(400)
    move_right(450)
    move_forward(400)
    move_right(450)
    move_forward(400)
    move_left(450)

# ----------------------------
# BLE UART
# ----------------------------
# m: move
# b: move back
# l: left
# r: right
# s: stop
# M: music
# q: quit
def bluetooth_serial_processing(ble_uart):
    while True:
        utime.sleep_ms(200)
        if ble_uart.any():
            bluetoothData = ble_uart.read().decode().strip()
            print(str(bluetoothData));
            if 'r'.find(bluetoothData) + 1 == 1:
                move_right()
            elif 'l'.find(bluetoothData) + 1 == 1:
                move_left()
            elif 'm'.find(bluetoothData) + 1 == 1:
                move_forward()
            elif 'b'.find(bluetoothData) + 1 == 1:
                move_backward()
            elif 's'.find(bluetoothData) + 1 == 1:
                alphabot.stop()
            elif 'M'.find(bluetoothData) + 1 == 1:
                music_play()
            elif 'q'.find(bluetoothData) + 1 == 1:
                break
            else:
                pass

# ----------------------------
# INIT
# ----------------------------

# init Alphabot
try:
    alphabot = AlphaBot_v2()
except Exception as e:
    print('alphabot exception occurred: {}'.format(e))
    alphabot = None

try:
    if alphabot is not None:
        oled = SSD1306_I2C(128, 64, alphabot.i2c)
except Exception as e:
    print('OLED exception occurred: {}'.format(e))
    oled = None

try:
    if alphabot is not None:
        vl53l0x = VL53L0X(i2c=alphabot.i2c)
except Exception as e:
    print('vl53l0x exception occurred: {}'.format(e))
    vl53l0x = None

try:
    classes = (NEC_8, NEC_16)
    if alphabot is not None:
        ir_remote = classes[0](alphabot.pin_IR, remoteNEC_callback)
    else:
        ir_remote = None
except Exception as e:
    print('ir_remote exception occurred: {}'.format(e))
    ir_remote = None

neopixel_leds = FoursNeoPixel(alphabot.pin_RGB)

#ble = bluetooth.BLE()
#uart = BLEUART(ble)

### Print system 
print()
print(f"Platform:           {sys.platform}")
print(f"MicroPython ver:    {os.uname().release} ({os.uname().version})")
print(f"Machine ID:         {os.uname().machine}")
print(f"CPU Frequency:      {machine.freq()} Hz")
print()

oled.text("Martian", 4*8, 0)
oled.show()
print("Ready to drive on Mars")
neo_french_flag(neopixel_leds)
print("We drive on Mars")

while True:
    # IR
    # enter_save    aka     +       : robot stop
    # up            aka     >>      : robot forward
    # down          aka     100+    : robot backward
    # left          aka     -       : robot go to left
    # right         aka     EQ      : robot go to right
    # play_pause    aka     CH      : follow line
    # setup         aka     <<      : bluetooth uart
    # 9             aka     9       : play music
    utime.sleep_ms(20)
    gc.collect()

    if ir_current_remote_code == "enter_save":
        alphabot.stop()
    elif ir_current_remote_code == "up":
        move_forward()
    elif ir_current_remote_code == "down":
        move_backward()
    elif ir_current_remote_code == "left":
        move_left()
    elif ir_current_remote_code == "right":
        move_right()
    elif ir_current_remote_code == "play_pause":
        line_follower_simple()
    elif ir_current_remote_code == "setup":
        bluetooth_serial_processing()
    elif ir_current_remote_code == "9":
        music_play()
    else:
        line_follower_simple()
