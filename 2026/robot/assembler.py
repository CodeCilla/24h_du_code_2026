#!/usr/bin/env python3
"""
Assembleur pour le processeur Nano RISC 8
Compile un fichier .asm en fichier .bin
Usage: python3 assembler.py input.asm output.bin
"""

import sys
import re

# Mapping des registres vers leurs bits (2 bits)
REGISTERS = {'R0': 0b00, 'R1': 0b01, 'R2': 0b10, 'R3': 0b11}

def parse_value(token):
    """Parse une valeur décimale ou ASCII (ex: 65 ou 'A')"""
    token = token.strip()
    if token.startswith("'") and token.endswith("'"):
        char = token[1:-1]
        if len(char) == 1:
            return ord(char)
        raise ValueError(f"Caractère ASCII invalide: {token}")
    val = int(token)
    if not (0 <= val <= 255):
        raise ValueError(f"Valeur hors plage [0..255]: {val}")
    return val

def first_pass(lines):
    """Premier passage : collecter les labels et leurs adresses"""
    labels = {}
    address = 0
    for line in lines:
        line = line.strip()
        # Supprimer commentaires
        if ';' in line:
            line = line[:line.index(';')].strip()
        if not line:
            continue
        # Label seul sur sa ligne
        if line.endswith(':'):
            label = line[:-1].strip()
            labels[label] = address
            continue
        # Calculer la taille de l'instruction
        tokens = line.split()
        instr = tokens[0].upper()
        if instr == 'DB':
            address += 1
        elif instr in ('RET',):
            address += 1
        elif instr in ('PUSH', 'POP', 'OUT'):
            address += 1
        elif instr in ('MOV', 'SUB', 'CMP'):
            if len(tokens) >= 3 and tokens[1].upper() in REGISTERS and tokens[2].upper() in REGISTERS:
                address += 1  # Rx Ry -> 1 octet
            else:
                address += 2  # Rx valeur -> 2 octets
        elif instr in ('CALL', 'JMP', 'JLT', 'JEQ'):
            address += 2
        elif instr in ('LDR', 'STR'):
            address += 2
        elif instr == 'TIM':
            address += 2
        else:
            raise ValueError(f"Instruction inconnue: {instr}")
    return labels

def second_pass(lines, labels):
    """Deuxième passage : générer le binaire"""
    binary = []
    for line in lines:
        line = line.strip()
        if ';' in line:
            line = line[:line.index(';')].strip()
        if not line:
            continue
        if line.endswith(':'):
            continue  # Label, pas d'instruction

        tokens = line.split()
        instr = tokens[0].upper()

        if instr == 'DB':
            binary.append(parse_value(tokens[1]))

        elif instr == 'RET':
            # 10000000
            binary.append(0b10000000)

        elif instr == 'PUSH':
            # 101000xx
            rx = REGISTERS[tokens[1].upper()]
            binary.append(0b10100000 | rx)

        elif instr == 'POP':
            # 011000xx
            rx = REGISTERS[tokens[1].upper()]
            binary.append(0b01100000 | rx)

        elif instr == 'OUT':
            # 111100xx
            rx = REGISTERS[tokens[1].upper()]
            binary.append(0b11110000 | rx)

        elif instr == 'MOV':
            rx = tokens[1].upper()
            ry_or_val = tokens[2].upper()
            if ry_or_val in REGISTERS:
                # MOV Rx Ry -> 0101xxyy
                binary.append(0b01010000 | (REGISTERS[rx] << 2) | REGISTERS[ry_or_val])
            else:
                # MOV Rx valeur -> 111000xx vvvvvvvv
                val = parse_value(tokens[2])
                binary.append(0b11100000 | REGISTERS[rx])
                binary.append(val)

        elif instr == 'SUB':
            rx = tokens[1].upper()
            ry_or_val = tokens[2].upper()
            if ry_or_val in REGISTERS:
                # SUB Rx Ry -> 1101xxyy
                binary.append(0b11010000 | (REGISTERS[rx] << 2) | REGISTERS[ry_or_val])
            else:
                # SUB Rx valeur -> 000100xx vvvvvvvv
                val = parse_value(tokens[2])
                binary.append(0b00010000 | REGISTERS[rx])
                binary.append(val)

        elif instr == 'CMP':
            rx = tokens[1].upper()
            ry_or_val = tokens[2].upper()
            if ry_or_val in REGISTERS:
                # CMP Rx Ry -> 0011xxyy
                binary.append(0b00110000 | (REGISTERS[rx] << 2) | REGISTERS[ry_or_val])
            else:
                # CMP Rx valeur -> 100100xx vvvvvvvv
                val = parse_value(tokens[2])
                binary.append(0b10010000 | REGISTERS[rx])
                binary.append(val)

        elif instr == 'CALL':
            # 00000000 aaaaaaaa
            label = tokens[1]
            addr = labels[label]
            binary.append(0b00000000)
            binary.append(addr)

        elif instr == 'JMP':
            # 01000000 aaaaaaaa
            label = tokens[1]
            addr = labels[label]
            binary.append(0b01000000)
            binary.append(addr)

        elif instr == 'JLT':
            # 11000000 aaaaaaaa
            label = tokens[1]
            addr = labels[label]
            binary.append(0b11000000)
            binary.append(addr)

        elif instr == 'JEQ':
            # 00100000 aaaaaaaa
            label = tokens[1]
            addr = labels[label]
            binary.append(0b00100000)
            binary.append(addr)

        elif instr == 'LDR':
            # 1011xxyy aaaaaaaa
            rx = REGISTERS[tokens[1].upper()]
            ry = REGISTERS[tokens[2].upper()]
            label = tokens[3]
            addr = labels[label]
            binary.append(0b10110000 | (rx << 2) | ry)
            binary.append(addr)

        elif instr == 'STR':
            # 0111xxyy aaaaaaaa
            rx = REGISTERS[tokens[1].upper()]
            ry = REGISTERS[tokens[2].upper()]
            label = tokens[3]
            addr = labels[label]
            binary.append(0b01110000 | (rx << 2) | ry)
            binary.append(addr)

        elif instr == 'TIM':
            # 11111000 mvvvvvvv
            val = parse_value(tokens[1])
            binary.append(0b11111000)
            binary.append(val)

        else:
            raise ValueError(f"Instruction inconnue: {instr}")

    return bytes(binary)

def assemble(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print(f"[1/2] Premier passage (collecte des labels)...")
    labels = first_pass(lines)
    print(f"      Labels trouvés: {labels}")

    print(f"[2/2] Deuxième passage (génération binaire)...")
    binary = second_pass(lines, labels)

    with open(output_path, 'wb') as f:
        f.write(binary)

    print(f"\n✅ Assemblage réussi !")
    print(f"   Entrée : {input_path}")
    print(f"   Sortie : {output_path}")
    print(f"   Taille : {len(binary)} octets")
    print(f"   Binaire (hex) : {binary.hex(' ').upper()}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 assembler.py input.asm output.bin")
        sys.exit(1)
    try:
        assemble(sys.argv[1], sys.argv[2])
    except Exception as e:
        print(f"❌ Erreur : {e}")
        sys.exit(1)
