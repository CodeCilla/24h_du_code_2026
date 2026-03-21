import utime

class StlionVM:
    def __init__(self, oled,leds):
        self.RAM_SIZE = 256
        self.memory = bytearray(self.RAM_SIZE)
        self.regs= [0, 0, 0, 0]
        self.stack = []
        self.pc = 0
        self.flag_lt = False
        self.flag_eq = False
        self.oled = oled
        self.leds = leds
    
    def load(self, binary_data):
        self.memory = bytearray(binary_data) + bytearray(self.RAM_SIZE - len(binary_data))
        self.regs =[0, 0, 0, 0]
        self.stack = []
        self.sp = 255
        self.pc = 0
        self.flag_lt = False
        self.flag_eq = False

    def run(self, max_cycles=1000):
        if self.oled:
            self.oled.fill(0)
            self.oled.text("Running...", 0, 0)
            self.oled.show()
        cycle = 0
        while cycle < max_cycles:
            if self.pc >= len(self.memory):
                break
            b0 = self.memory[self.pc]
            b1 = self.memory[self.pc + 1] if self.pc + 1 < len(self.memory) else 0

            #-----bytecode instructions-----

            if b0 == 0b10000000:  # RET
                if not self.stack:
                    break # stack empty -> stop
                self.pc = self.stack.pop()
                self.sp = min(self.sp + 1, 255)
                cycle += 1
                continue

            if(b0 & 0b11111100) == 0b10100000: # PUSH Rx
                rx = b0 & 0b11
                self.stack.append(self.regs[rx])
                self.sp = max(self.sp - 1, 0)
                self.pc += 1
                cycle += 1
                continue

            if(b0 & 0b11111100) == 0b01100000: # POP Rx
                rx = b0 & 0b11
                if self.stack:
                    self.regs[rx] = self.stack.pop()
                    self.sp = min(self.sp + 1, 255)
                self.pc += 1
                cycle += 1
                continue

            if(b0 & 0b11111100) == 0b11110000: # OUT Rx
                rx = b0 & 0b11
                val = self.regs[rx]
                print("OUT:", val)
                if self.oled:
                    self.oled.fill(0)
                    self.oled.text("VM Output:", 0, 0)
                    self.oled.text(str(val), 0, 16)
                    self.oled.show()
                if self.leds:
                    self.leds.set_color(0, 0, 255 if val & 1 else 0, 0)
                    self.leds.show()
                utime.sleep_ms(500)
                self.pc += 1
                cycle += 1
                continue

            if (b0 & 0b11110000) == 0b01010000: # MOV Rx Ry
                rx = (b0 >> 2) & 0b11
                ry = b0 & 0b11
                self.regs[rx] = self.regs[ry]
                self.pc += 1
                cycle += 1
                continue

            if (b0 & 0b11110000) == 0b11010000: # SUB Rx Ry
                rx = (b0 >> 2) & 0b11
                ry = b0 & 0b11
                self.regs[rx] = (self.regs[rx] - self.regs[ry]) % 256
                self.pc += 1
                cycle += 1
                continue

            if (b0 & 0b11110000) == 0b00110000: # CMP Rx Ry
                rx = (b0 >> 2) & 0b11
                ry = b0 & 0b11
                self.flag_lt = self.regs[rx] < self.regs[ry]
                self.flag_eq = self.regs[rx] == self.regs[ry]
                self.pc += 1
                cycle += 1
                continue

            # --- 2 bytes instructions ---

            if b0 == 0b00000000: # CALL
                self.stack.append(self.pc + 2)
                self.sp = max(self.sp - 1, 0)
                self.pc = b1
                cycle += 2
                continue

            if b0 == 0b01000000: # JMP
                self.pc = b1
                cycle += 2
                continue

            if b0 == 0b11000000: # JLT
                if self.flag_lt: self.pc = b1
                else: self.pc += 2
                cycle += 2
                continue

            if b0 == 0b00100000: #JEQ
                if self.flag_eq: self.pc = b1
                else: self.pc += 2
                cycle += 2
                continue

            if (b0 & 0b11111100) == 0b11100000: # MOV Rx valeur
                rx = b0 & 0b11
                self.regs[rx] = b1
                self.pc += 2
                cycle += 2
                continue
                
            if (b0 & 0b11111100) == 0b00010000: # SUB Rx valeur
                rx = b0 & 0b11
                self.regs[rx] = (self.regs[rx] - b1) & 0xFF
                self.pc += 2
                cycle += 2
                continue
                
            if (b0 & 0b11111100) == 0b10010000: # CMP Rx valeur
                rx = b0 & 0b11
                self.flag_lt = self.regs[rx] < b1
                self.flag_eq = self.regs[rx] == b1
                self.pc += 2
                cycle += 2
                continue
                
            if (b0 & 0b11110000) == 0b10110000: # LDR Rx Ry addr
                rx = (b0 >> 2) & 0b11
                ry = b0 & 0b11
                addr = (b1 + self.regs[ry]) & 0xFF
                self.regs[rx] = self.memory[addr]
                self.pc += 2
                cycle += 3
                continue
                
            if (b0 & 0b11110000) == 0b01110000: # STR Rx Ry addr
                rx = (b0 >> 2) & 0b11
                ry = b0 & 0b11
                addr = (b1 + self.regs[ry]) & 0xFF
                self.memory[addr] = self.regs[rx]
                self.pc += 2
                cycle += 3
                continue
                
            if b0 == 0b11111000: # TIM valeur
                m = (b1 >> 7) & 1
                v = b1 & 0x7F
                mult = 100 if m else 1
                ms = mult * (v + 1)
                utime.sleep_ms(ms)
                self.pc += 2
                cycle += 2
                continue

            # Invalid OP code
            print("Invalid opcode at PC", self.pc)
            break
            
        print("VM Stopped after", cycle, "cycles.")
        if self.oled:
            self.oled.fill(0)
            self.oled.text("VM Stopped", 0, 0)
            self.oled.text("Cycles: "+str(cycle), 0, 16)
            self.oled.show()