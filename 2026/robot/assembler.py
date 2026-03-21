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
    """Premier passage : collecter les labels et leurs adresses.
    Les DB sont toujours placés après le RET dans le binaire final.
    """
    labels = {}
    # Passe 1a : adresses des instructions (sans DB, sans RET)
    address = 0
    for line in lines:
        line = line.strip()
        if ';' in line:
            line = line[:line.index(';')].strip()
        if not line:
            continue
        if line.endswith(':'):
            label = line[:-1].strip()
            labels[label] = address
            continue
        tokens = line.split()
        instr = tokens[0].upper()
        if instr in ('DB', 'RET'):
            pass  # traités séparément
        elif instr in ('PUSH', 'POP', 'OUT'):
            address += 1
        elif instr in ('MOV', 'SUB', 'CMP'):
            if len(tokens) >= 3 and tokens[1].upper() in REGISTERS and tokens[2].upper() in REGISTERS:
                address += 1
            else:
                address += 2
        elif instr in ('CALL', 'JMP', 'JLT', 'JEQ'):
            address += 2
        elif instr in ('LDR', 'STR'):
            address += 2
        elif instr == 'TIM':
            address += 2
        else:
            raise ValueError(f"Instruction inconnue: {instr}")

    # Passe 1b : labels devant des DB → adresses après le RET
    db_address = address + 1  # +1 pour le RET implicite
    db_label_pending = None
    for line in lines:
        line = line.strip()
        if ';' in line:
            line = line[:line.index(';')].strip()
        if not line:
            continue
        if line.endswith(':'):
            db_label_pending = line[:-1].strip()
            continue
        tokens = line.split()
        instr = tokens[0].upper()
        if instr == 'DB':
            if db_label_pending:
                labels[db_label_pending] = db_address
                db_label_pending = None
            db_address += 1
        else:
            db_label_pending = None

    return labels


def second_pass(lines, labels):
    """Deuxième passage : générer le binaire.
    Ordre de sortie : [instructions] + RET (0x80) + [données DB]
    Peu importe l'ordre dans le .asm source.
    """
    code = []
    db_bytes = []

    for line in lines:
        line = line.strip()
        if ';' in line:
            line = line[:line.index(';')].strip()
        if not line:
            continue
        if line.endswith(':'):
            continue

        tokens = line.split()
        instr = tokens[0].upper()

        if instr == 'DB':
            db_bytes.append(parse_value(tokens[1]))

        elif instr == 'RET':
            pass  # RET implicite ajouté à la fin

        elif instr == 'PUSH':
            rx = REGISTERS[tokens[1].upper()]
            code.append(0b10100000 | rx)

        elif instr == 'POP':
            rx = REGISTERS[tokens[1].upper()]
            code.append(0b01100000 | rx)

        elif instr == 'OUT':
            rx = REGISTERS[tokens[1].upper()]
            code.append(0b11110000 | rx)

        elif instr == 'MOV':
            rx = tokens[1].upper()
            ry_or_val = tokens[2].upper()
            if ry_or_val in REGISTERS:
                code.append(0b01010000 | (REGISTERS[rx] << 2) | REGISTERS[ry_or_val])
            else:
                val = parse_value(tokens[2])
                code.append(0b11100000 | REGISTERS[rx])
                code.append(val)

        elif instr == 'SUB':
            rx = tokens[1].upper()
            ry_or_val = tokens[2].upper()
            if ry_or_val in REGISTERS:
                code.append(0b11010000 | (REGISTERS[rx] << 2) | REGISTERS[ry_or_val])
            else:
                val = parse_value(tokens[2])
                code.append(0b00010000 | REGISTERS[rx])
                code.append(val)

        elif instr == 'CMP':
            rx = tokens[1].upper()
            ry_or_val = tokens[2].upper()
            if ry_or_val in REGISTERS:
                code.append(0b00110000 | (REGISTERS[rx] << 2) | REGISTERS[ry_or_val])
            else:
                val = parse_value(tokens[2])
                code.append(0b10010000 | REGISTERS[rx])
                code.append(val)

        elif instr == 'CALL':
            addr = labels[tokens[1]]
            code.append(0b00000000)
            code.append(addr)

        elif instr == 'JMP':
            addr = labels[tokens[1]]
            code.append(0b01000000)
            code.append(addr)

        elif instr == 'JLT':
            addr = labels[tokens[1]]
            code.append(0b11000000)
            code.append(addr)

        elif instr == 'JEQ':
            addr = labels[tokens[1]]
            code.append(0b00100000)
            code.append(addr)

        elif instr == 'LDR':
            rx = REGISTERS[tokens[1].upper()]
            ry = REGISTERS[tokens[2].upper()]
            addr = labels[tokens[3]]
            code.append(0b10110000 | (rx << 2) | ry)
            code.append(addr)

        elif instr == 'STR':
            rx = REGISTERS[tokens[1].upper()]
            ry = REGISTERS[tokens[2].upper()]
            addr = labels[tokens[3]]
            code.append(0b01110000 | (rx << 2) | ry)
            code.append(addr)

        elif instr == 'TIM':
            val = parse_value(tokens[1])
            code.append(0b11111000)
            code.append(val)

        else:
            raise ValueError(f"Instruction inconnue: {instr}")

    return bytes(code + [0x80] + db_bytes)


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
