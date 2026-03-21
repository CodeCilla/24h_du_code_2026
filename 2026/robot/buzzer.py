import sys
import utime

class Buzzer:
    def __init__(self):
        pass

    # ------------------------------------
    # Vittascience
    # Example for playing sound
    # ------------------------------------
    def _pitch(self, robot, noteFrequency, noteDuration, silence_ms = 10):
        if noteFrequency is not 0:
            microsecondsPerWave = 1e6 / noteFrequency
            millisecondsPerCycle = 1000 / (microsecondsPerWave * 2)
            loopTime = noteDuration * millisecondsPerCycle
            for x in range(loopTime):
                # Buzzer high: 0
                robot.controlBuzzer(0)
                utime.sleep_us(int(microsecondsPerWave))
                # buzzer low: 1
                robot.controlBuzzer(1)
                utime.sleep_us(int(microsecondsPerWave))
        else:
            utime.sleep_ms(int(noteDuration))
        utime.sleep_ms(silence_ms)

    def pitch(self, robot, noteFrequency, noteDuration, silence_ms = 10):
        #print("[DEBUG][pitch]: Frequency {:5} Hz, Duration {:4} ms, silence {:4} ms".format(noteFrequency, noteDuration, silence_ms))
        self._pitch(robot, noteFrequency, noteDuration, silence_ms)
