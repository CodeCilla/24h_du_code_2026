import machine
import utime, sys
import uasyncio as asyncio
import json
from stm32_alphabot_v2 import AlphaBot_v2
import gc
from stm32_ssd1306 import SSD1306, SSD1306_I2C
from stm32_vl53l0x import VL53L0X
from stm32_nec import NEC_8, NEC_16
import neopixel
import os
import RobotBleServer
from nano8_emulator import Nano8Emulator

import buzzer

# ─── Nom BLE de votre équipe ───────────────────────────────────────────────────
robotName = 'Ekod&Commit'  # ← remplacer par le nom de votre équipe

# ─── Variables globales ────────────────────────────────────────────────────────
alphabot = oled = vl53l0x = None
ir_current_remote_code = None
_rx_buffer = bytearray()
bleConnection = None

dict_base=dict([('C-',32.70),('C#',34.65),('D-',36.71),('D#',38.89),('E-',41.20),('E#',43.65),('F-',43.65),('F#',46.35),('G-',49.00),('G#',51.91),('A-',55.00),('A#',58.27),('B-',61.74),('S-',0)])

# ─── NeoPixel ──────────────────────────────────────────────────────────────────
class FoursNeoPixel():
    def __init__(self, pin_number):
        self._pin = pin_number
        self._max_leds = 4
        self._leds = neopixel.NeoPixel(self._pin, 4)

    def set_led(self, addr, red, green, blue):
        if addr >= 0 and addr < self._max_leds:
            self._leds[addr] = (blue, green, red)

    def show(self):
        self._leds.write()

    def clear(self):
        for i in range(self._max_leds):
            self.set_led(i, 0, 0, 0)
        self.show()

async def neo_french_flag(leds):
    while True:
        for color in [(250,0,0),(250,250,250),(0,0,250)]:
            for i in range(4): leds.set_led(i, *color)
            leds.show()
            await asyncio.sleep(1)
        leds.clear()
        await asyncio.sleep(2)

# ─── Télécommande IR ───────────────────────────────────────────────────────────
def remoteNEC_basicBlack_getButton(hexCode):
    mapping = {
        0x0c:"1", 0x18:"2", 0x5e:"3", 0x08:"4", 0x1c:"5", 0x5a:"6",
        0x42:"7", 0x52:"8", 0x4a:"9", 0x16:"0", 0x40:"up", 0x19:"down",
        0x07:"left", 0x09:"right", 0x15:"enter_save", 0x0d:"back",
        0x45:"volMinus", 0x47:"volPlus", 0x46:"play_pause",
        0x44:"setup", 0x43:"stop_mode"
    }
    return mapping.get(hexCode, "NEC remote code error")

def remoteNEC_callback(data, addr, ctrl):
    global ir_current_remote_code
    if data >= 0:
        ir_current_remote_code = remoteNEC_basicBlack_getButton(data)

# ─── Musique ───────────────────────────────────────────────────────────────────
def music_play():
    d = [['C-3',4],['D-3',4],['E-3',4],['F-3',4],['G-3',4],['A-3',4],['B-3',4]]
    freq_list = [dict_base[d[i][0][:2]] * 2**(int(d[i][0][2])-1) for i in range(len(d))]
    duration_list = [int(d[i][1]) * 125 for i in range(len(d))]
    buz = buzzer.Buzzer()
    for i in range(len(freq_list)):
        buz.pitch(alphabot, freq_list[i], duration_list[i], 50)

# ─── Moteurs ───────────────────────────────────────────────────────────────────
_BLACKLIMIT = 650
SPEED_MOTOR = 13

def move_right(t=30):   alphabot.turnRight(20, t)
def move_left(t=30):    alphabot.turnLeft(20, t)
def move_backward(t=200):
    alphabot.moveBackward(20)
    utime.sleep_ms(t)
    alphabot.stop()

def move_forward(t=200):
    if alphabot.readUltrasonicDistance() > 10:
        alphabot.moveForward(20)
        utime.sleep_ms(t)
        alphabot.stop()
    else:
        alphabot.stop()

# ─── Suiveur de ligne ──────────────────────────────────────────────────────────
def line_follower_simple(limit=_BLACKLIMIT):
    oled.fill(0)
    if alphabot.readUltrasonicDistance() <= 5:
        alphabot.stop()
        oled.text('Obstacle', 0, 0)
        oled.text('STOPPED!', 0, 16)
    else:
        line_detection = alphabot.TRSensors_readLine()
        if line_detection[2] < limit:
            alphabot.setMotors(right=22, left=22)
        elif line_detection[1] < limit:
            alphabot.turnLeft(65, duration_ms=50)
        elif line_detection[3] < limit:
            alphabot.turnRight(65, duration_ms=50)
        elif line_detection[2] > limit:
            alphabot.moveBackward(35, duration_ms=50)
    oled.show()

# ─── BLE : réception du binaire nano8 ─────────────────────────────────────────
def onMsgReceived(data):
    """Appelé par RobotBleServer à chaque message reçu"""
    global _rx_buffer

    if isinstance(data, bytes):
        # Données binaires → accumulation
        _rx_buffer += data
        print('BLE recu {} octets, total={}'.format(len(data), len(_rx_buffer)))
        if oled:
            oled.fill(0)
            oled.text('Reception', 0, 0)
            oled.text('{} octets'.format(len(_rx_buffer)), 0, 16)
            oled.show()

    elif isinstance(data, str):
        cmd = data.strip()

        if cmd == 'RUN':
            if len(_rx_buffer) == 0:
                bleConnection.sendMessage('ERROR:empty')
                return
            print('Execution {} octets'.format(len(_rx_buffer)))
            bleConnection.sendMessage('RUNNING:{}'.format(len(_rx_buffer)))
            # Exécuter le binaire
            emulator.execute(bytes(_rx_buffer))
            _rx_buffer = bytearray()
            bleConnection.sendMessage('DONE')

        elif cmd == 'CLEAR':
            _rx_buffer = bytearray()
            bleConnection.sendMessage('CLEARED')

        elif cmd == 'STATUS':
            bleConnection.sendMessage('BUF:{}'.format(len(_rx_buffer)))

# ─── Tâche principale robot ────────────────────────────────────────────────────
async def robotMainTask():
    global ir_current_remote_code
    while True:
        await asyncio.sleep_ms(20)
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
        elif ir_current_remote_code == "9":
            music_play()
        else:
            line_follower_simple()

        ir_current_remote_code = None

# ─── Init matériel ─────────────────────────────────────────────────────────────
try:
    alphabot = AlphaBot_v2()
except Exception as e:
    print('alphabot error: {}'.format(e))

try:
    if alphabot:
        oled = SSD1306_I2C(128, 64, alphabot.i2c)
except Exception as e:
    print('OLED error: {}'.format(e))

try:
    if alphabot:
        vl53l0x = VL53L0X(i2c=alphabot.i2c)
except Exception as e:
    print('vl53l0x error: {}'.format(e))

try:
    if alphabot:
        ir_remote = NEC_8(alphabot.pin_IR, remoteNEC_callback)
except Exception as e:
    print('ir_remote error: {}'.format(e))

neopixel_leds = FoursNeoPixel(alphabot.pin_RGB)
emulator = Nano8Emulator(alphabot, oled)

print()
print('Platform: {}'.format(sys.platform))
print('MicroPython: {}'.format(os.uname().release))
print()

if oled:
    oled.fill(0)
    oled.text('STLION', 0, 0)
    oled.text('Nano8 Ready', 0, 16)
    oled.text(robotName, 0, 32)
    oled.show()

# ─── Main async ────────────────────────────────────────────────────────────────
async def main():
    global bleConnection
    bleConnection = RobotBleServer.RobotBleServer(
        robotName=robotName,
        onMsgReceived=onMsgReceived
    )
    asyncio.create_task(robotMainTask())
    asyncio.create_task(neo_french_flag(neopixel_leds))
    await bleConnection.communicationTask()

asyncio.run(main())
