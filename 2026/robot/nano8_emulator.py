"""
Émulateur Nano RISC 8 — MicroPython pour AlphaBot2 / NUCLEO-WB55
Reçoit un fichier .bin via BLE et l'exécute sur le robot.

Intégration dans main.py :
    from nano8_emulator import Nano8Emulator
    emulator = Nano8Emulator(alphabot, oled)
    emulator.execute(binary_data)
"""

import utime

# ─── Décodage ──────────────────────────────────────────────────────────────────

def _decode(memory, pc):
    b0 = memory[pc]

    # RET : 10000000
    if b0 == 0x80:
        return ("RET", [], 1, 1)

    # PUSH Rx : 101000xx
    if (b0 & 0xFC) == 0xA0:
        return ("PUSH", [b0 & 0x03], 1, 1)

    # POP Rx : 011000xx
    if (b0 & 0xFC) == 0x60:
        return ("POP", [b0 & 0x03], 1, 1)

    # OUT Rx : 111100xx
    if (b0 & 0xFC) == 0xF0:
        return ("OUT", [b0 & 0x03], 1, 1)

    # MOV Rx Ry : 0101xxyy
    if (b0 & 0xF0) == 0x50:
        return ("MOV_RR", [(b0 >> 2) & 0x03, b0 & 0x03], 1, 1)

    # SUB Rx Ry : 1101xxyy
    if (b0 & 0xF0) == 0xD0:
        return ("SUB_RR", [(b0 >> 2) & 0x03, b0 & 0x03], 1, 1)

    # CMP Rx Ry : 0011xxyy
    if (b0 & 0xF0) == 0x30:
        return ("CMP_RR", [(b0 >> 2) & 0x03, b0 & 0x03], 1, 1)

    # Instructions 2 octets
    b1 = memory[pc + 1] if pc + 1 < len(memory) else 0

    # CALL : 00000000 aaaaaaaa
    if b0 == 0x00:
        return ("CALL", [b1], 2, 2)

    # JMP : 01000000 aaaaaaaa
    if b0 == 0x40:
        return ("JMP", [b1], 2, 2)

    # JLT : 11000000 aaaaaaaa
    if b0 == 0xC0:
        return ("JLT", [b1], 2, 2)

    # JEQ : 00100000 aaaaaaaa
    if b0 == 0x20:
        return ("JEQ", [b1], 2, 2)

    # MOV Rx val : 111000xx vvvvvvvv
    if (b0 & 0xFC) == 0xE0:
        return ("MOV_RV", [b0 & 0x03, b1], 2, 2)

    # SUB Rx val : 000100xx vvvvvvvv
    if (b0 & 0xFC) == 0x10:
        return ("SUB_RV", [b0 & 0x03, b1], 2, 2)

    # CMP Rx val : 100100xx vvvvvvvv
    if (b0 & 0xFC) == 0x90:
        return ("CMP_RV", [b0 & 0x03, b1], 2, 2)

    # LDR Rx Ry addr : 1011xxyy aaaaaaaa
    if (b0 & 0xF0) == 0xB0:
        return ("LDR", [(b0 >> 2) & 0x03, b0 & 0x03, b1], 2, 3)

    # STR Rx Ry addr : 0111xxyy aaaaaaaa
    if (b0 & 0xF0) == 0x70:
        return ("STR", [(b0 >> 2) & 0x03, b0 & 0x03, b1], 2, 3)

    # TIM : 11111000 mvvvvvvv
    if b0 == 0xF8:
        return ("TIM", [b1], 2, 2)

    return None  # octet inconnu


# ─── Décodage vitesse moteur ────────────────────────────────────────────────────

def _decode_motor_speed(nibble_4bit):
    """
    Convertit un nibble 4 bits en complément à 2 en vitesse moteur.
    svvv : -8..7
    Retourne une valeur entre -100 et 100 pour setMotors()
    """
    if nibble_4bit >= 8:
        val = nibble_4bit - 16  # complément à 2 : -8..-1
    else:
        val = nibble_4bit       # 0..7
    # Normaliser sur -100..100 (max robot = 100, max nano8 = 7)
    return int(val * 100 / 7)


# ─── Émulateur principal ────────────────────────────────────────────────────────

class Nano8Emulator:
    MAX_CYCLES = 100000

    def __init__(self, alphabot=None, oled=None):
        self.alphabot = alphabot
        self.oled = oled

    def _oled_print(self, line1="", line2="", line3=""):
        """Affiche jusqu'à 3 lignes sur l'OLED"""
        if self.oled is None:
            return
        try:
            self.oled.fill(0)
            if line1:
                self.oled.text(line1[:16], 0, 0)
            if line2:
                self.oled.text(line2[:16], 0, 16)
            if line3:
                self.oled.text(line3[:16], 0, 32)
            self.oled.show()
        except Exception:
            pass

    def _apply_motors(self, val):
        """
        Applique la valeur OUT aux moteurs.
        val = svvvsvvv (8 bits) : nibble haut = gauche, nibble bas = droit
        """
        left_nibble  = (val >> 4) & 0x0F
        right_nibble =  val       & 0x0F
        left_speed  = _decode_motor_speed(left_nibble)
        right_speed = _decode_motor_speed(right_nibble)

        print("OUT: val={} gauche={} droit={}".format(val, left_speed, right_speed))

        if self.alphabot is not None:
            try:
                self.alphabot.setMotors(left=left_speed, right=right_speed)
            except Exception as e:
                print("Motor error:", e)

        self._oled_print(
            "OUT={}".format(val),
            "G={}".format(left_speed),
            "D={}".format(right_speed)
        )

    def execute(self, binary_data):
        """
        Exécute un programme binaire nano8.
        binary_data : bytes ou bytearray
        """
        RAM_SIZE = 256
        memory = list(binary_data) + [0] * (RAM_SIZE - len(binary_data))

        regs    = [0, 0, 0, 0]
        stack   = []
        pc      = 0
        flag_lt = False
        flag_eq = False

        self._oled_print("Nano8", "Demarrage...", "")
        print("Nano8: démarrage, {} octets".format(len(binary_data)))

        for cycle in range(self.MAX_CYCLES):
            if pc >= len(binary_data):
                break

            result = _decode(memory, pc)
            if result is None:
                print("Nano8: octet inconnu PC={} 0x{:02X}".format(pc, memory[pc]))
                break

            mn, ops, size, _ = result
            next_pc = pc + size
            stop = False

            if mn == "RET":
                if not stack:
                    print("Nano8: RET pile vide → arrêt")
                    stop = True
                else:
                    next_pc = stack.pop()

            elif mn == "PUSH":
                stack.append(regs[ops[0]])

            elif mn == "POP":
                if stack:
                    regs[ops[0]] = stack.pop()
                else:
                    stop = True

            elif mn == "OUT":
                self._apply_motors(regs[ops[0]])

            elif mn == "MOV_RR":
                regs[ops[0]] = regs[ops[1]]

            elif mn == "MOV_RV":
                regs[ops[0]] = ops[1]

            elif mn == "SUB_RR":
                regs[ops[0]] = (regs[ops[0]] - regs[ops[1]]) & 0xFF

            elif mn == "SUB_RV":
                regs[ops[0]] = (regs[ops[0]] - ops[1]) & 0xFF

            elif mn == "CMP_RR":
                flag_lt = regs[ops[0]] < regs[ops[1]]
                flag_eq = regs[ops[0]] == regs[ops[1]]

            elif mn == "CMP_RV":
                flag_lt = regs[ops[0]] < ops[1]
                flag_eq = regs[ops[0]] == ops[1]

            elif mn == "JMP":
                next_pc = ops[0]

            elif mn == "JEQ":
                if flag_eq:
                    next_pc = ops[0]

            elif mn == "JLT":
                if flag_lt:
                    next_pc = ops[0]

            elif mn == "CALL":
                stack.append(next_pc)
                next_pc = ops[0]

            elif mn == "LDR":
                addr = (ops[2] + regs[ops[1]]) & 0xFF
                regs[ops[0]] = memory[addr]

            elif mn == "STR":
                addr = (ops[2] + regs[ops[1]]) & 0xFF
                memory[addr] = regs[ops[0]]

            elif mn == "TIM":
                val = ops[0]
                m   = (val >> 7) & 1
                v   =  val & 0x7F
                mult = 100 if m else 1
                ms  = mult * (v + 1)
                print("Nano8: TIM {}ms".format(ms))
                utime.sleep_ms(ms)

            pc = next_pc
            if stop:
                break

        # Arrêt des moteurs à la fin
        if self.alphabot is not None:
            try:
                self.alphabot.stop()
            except Exception:
                pass

        self._oled_print("Nano8", "Termine!", "")
        print("Nano8: fin après {} cycles".format(cycle + 1))
