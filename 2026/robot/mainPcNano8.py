# python mainPcNano8.py -p <port_COM> -f <fichier.bin>
# Exemple : python mainPcNano8.py -p COM3 -f fibonacci.bin

import sys
import time
import argparse
import ComWithDongle

robotName = 'Ekod&Commit'  # ← même nom que dans mainRobotNano8.py

def onMsgFromRobot(data):
    if isinstance(data, bytes):
        print('Robot →', data)
    else:
        print('Robot →', data.strip())

parser = argparse.ArgumentParser(description='Envoie un .bin nano8 au robot via BLE')
parser.add_argument('-p', '--portcom', type=str, required=True, help='port COM du dongle')
parser.add_argument('-f', '--file',    type=str, required=True, help='fichier .bin à envoyer')
parser.add_argument('-d', '--debug',   action='store_true',     help='mode debug')
args = parser.parse_args()

# Lire le binaire
with open(args.file, 'rb') as f:
    binary = f.read()
print(f'Fichier: {args.file} ({len(binary)} octets)')

# Connexion BLE
print(f'Connexion à "{robotName}" sur {args.portcom}...')
com = ComWithDongle.ComWithDongle(
    comPort=args.portcom,
    peripheralName=robotName,
    onMsgReceived=onMsgFromRobot,
    debug=args.debug
)
print('Connecté !')

# Envoyer le binaire en bytes (RobotBleServer gère les chunks automatiquement)
print('Envoi du binaire...')
com.sendMsg(binary)
print('Binaire envoyé !')
time.sleep(0.5)

# Lancer l'exécution
print('Lancement...')
com.sendMsg('RUN')
time.sleep(10)  # attendre la fin d'exécution

com.disconnect()
print('Terminé !')
