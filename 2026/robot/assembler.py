#!/usr/bin/env python3
import sys
import os
import hashlib

# CONFIGURATION
SOURCE_DIR = "/Users/mickakawete/Desktop/24h_du_code_2026/2026/test_asm_epreuve2"
REGISTERS = {'R0': 0b00, 'R1': 0b01, 'R2': 0b10, 'R3': 0b11}

def get_md5(data):
    """Calcule le hash MD5 d'un objet bytes."""
    return hashlib.md5(data).hexdigest()

def parse_value(token):
    token = token.strip().replace(',', '')
    if token.startswith("'") and token.endswith("'"):
        char = token[1:-1]
        return ord(char)
    # Supporte décimal (10) et hexa (0x0A)
    return int(token, 0)

def first_pass(lines):
    labels = {}
    address = 0
    for line in lines:
        line = line.strip().split(';')[0]
        if not line: continue
        if line.endswith(':'):
            labels[line[:-1].strip()] = address
            continue
        tokens = line.replace(',', ' ').split()
        instr = tokens[0].upper()
        
        # Tailles mémoire du Nano RISC 8
        if instr in ('RET', 'PUSH', 'POP', 'OUT'): address += 1
        elif instr in ('MOV', 'SUB', 'CMP'):
            if len(tokens) >= 3 and tokens[1].upper() in REGISTERS and tokens[2].upper() in REGISTERS:
                address += 1
            else: address += 2
        elif instr in ('CALL', 'JMP', 'JLT', 'JEQ', 'LDR', 'STR', 'TIM', 'DB'): address += 2
    return labels

def second_pass(lines, labels):
    binary = []
    for line in lines:
        line = line.strip().split(';')[0]
        if not line or line.endswith(':'): continue
        tokens = line.replace(',', ' ').split()
        instr = tokens[0].upper()
        try:
            if instr == 'DB': 
                binary.append(parse_value(tokens[1]) & 0xFF)
            elif instr == 'RET': 
                binary.append(0b10000000)
            elif instr == 'PUSH': 
                binary.append(0b10100000 | REGISTERS[tokens[1].upper()])
            elif instr == 'POP': 
                binary.append(0b01100000 | REGISTERS[tokens[1].upper()])
            elif instr == 'OUT': 
                binary.append(0b11110000 | REGISTERS[tokens[1].upper()])
            elif instr == 'MOV':
                rx = tokens[1].upper()
                ry_val = tokens[2].upper()
                if ry_val in REGISTERS: 
                    binary.append(0b01010000 | (REGISTERS[rx] << 2) | REGISTERS[ry_val])
                else:
                    binary.append(0b11100000 | REGISTERS[rx])
                    binary.append(parse_value(tokens[2]) & 0xFF)
            elif instr == 'SUB':
                rx = tokens[1].upper()
                ry_val = tokens[2].upper()
                if ry_val in REGISTERS: 
                    binary.append(0b11010000 | (REGISTERS[rx] << 2) | REGISTERS[ry_val])
                else:
                    binary.append(0b00010000 | REGISTERS[rx])
                    binary.append(parse_value(tokens[2]) & 0xFF)
            elif instr == 'CMP':
                rx = tokens[1].upper()
                ry_val = tokens[2].upper()
                if ry_val in REGISTERS: 
                    binary.append(0b00110000 | (REGISTERS[rx] << 2) | REGISTERS[ry_val])
                else:
                    binary.append(0b10010000 | REGISTERS[rx])
                    binary.append(parse_value(tokens[2]) & 0xFF)
            elif instr in ('CALL', 'JMP', 'JLT', 'JEQ'):
                codes = {'CALL': 0b00000000, 'JMP': 0b01000000, 'JLT': 0b11000000, 'JEQ': 0b00100000}
                binary.append(codes[instr])
                binary.append(labels[tokens[1]] & 0xFF)
            elif instr in ('LDR', 'STR'):
                code = 0b10110000 if instr == 'LDR' else 0b01110000
                binary.append(code | (REGISTERS[tokens[1].upper()] << 2) | REGISTERS[tokens[2].upper()])
                binary.append(labels[tokens[3]] & 0xFF)
            elif instr == 'TIM':
                binary.append(0b11111000)
                binary.append(parse_value(tokens[1]) & 0xFF)
        except Exception as e:
            print(f"   ❌ Erreur d'encodage '{line}': {e}")
    return bytes(binary)

def compiler_tout_le_dossier():
    if not os.path.exists(SOURCE_DIR):
        print(f"❌ Dossier {SOURCE_DIR} introuvable.")
        return
    
    fichiers = [f for f in sorted(os.listdir(SOURCE_DIR)) if f.endswith('.asm')]
    print(f"🚀 Assemblage de {len(fichiers)} fichiers dans {SOURCE_DIR}")
    print(f"{'-'*85}")
    print(f"{'Fichier':<25} | {'Taille':<8} | {'MD5 Hash'}")
    print(f"{'-'*85}")
    
    for f in fichiers:
        chemin_in = os.path.join(SOURCE_DIR, f)
        chemin_out = os.path.join(SOURCE_DIR, f.replace('.asm', '.bin'))
        
        try:
            with open(chemin_in, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            labels = first_pass(lines)
            binary = second_pass(lines, labels)
            md5_res = get_md5(binary)
            
            with open(chemin_out, 'wb') as file:
                file.write(binary)
            
            print(f"✅ {f:<22} | {len(binary):>3} octets | {md5_res}")
        except Exception as e:
            print(f"❌ Erreur sur {f}: {e}")

if __name__ == '__main__':
    compiler_tout_le_dossier()