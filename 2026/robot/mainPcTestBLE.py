# python -m serial.tools.list_ports
# python mainPcTestBLE.py -p <port com>

# In this example, PC will send some messages to robot,
# and verify it receives checksum of these messages from robot
# Note: if message from PC to robot exceeds 18 characters, it will be split in
# several BLE messages, then merged at robot side to get original message

import sys
import binascii
import time
import argparse
import random
import ComWithDongle

robotName = 'myTeamName'

randCharRange = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

expectedToReceive = []

def onMsgFromRobot(data:str):
	"""Function to call when a message sent by robot is received
	:param data: message"""
	print('received msg', data, flush=True)
	print('compair to', expectedToReceive, flush=True)
	if data in expectedToReceive:
		expectedToReceive.remove(data)
		print('-not received yet', len(expectedToReceive), expectedToReceive, flush=True)
	else:
		print('bad message received', data)
		print('expected to receive')
		for s in expectedToReceive:
			print('  ', s)
		exit(1)

parser = argparse.ArgumentParser(
	description='Script to communicate with STM32WB55 dongle connected on computer')
parser.add_argument('-p', '--portcom', type=str, help='id of com port used')
parser.add_argument('-d', '--debug', action='store_true', help='display debug messages')
parser.add_argument('-l', '--length', type=int, default=16,
	help='number of characters to send over BLE, in each message')
parser.add_argument('-n', '--number', type=int, default=5 , help='number of messages to send over BLE')
parser.add_argument('-b', '--bytes', action='store_true', help='send bytes instead of string')
args = parser.parse_args()


try:
	print('start main')
	# wait BLE connection is established
	com = ComWithDongle.ComWithDongle(comPort=args.portcom, peripheralName=robotName,
		onMsgReceived=onMsgFromRobot, debug=args.debug)
	print('connected to', robotName)
	msgId = 0
	while True:
		if args.bytes:
			data = random.randbytes(args.length)
		else:
			data = ''.join([random.choice(randCharRange) for _ in range(args.length)])
		print('send data', len(data), msgId, data, flush=True)
		checksum = binascii.crc32(data)
		expectedToReceive.append(str(checksum))
		com.sendMsg(data)
		print('+not received yet', len(expectedToReceive), expectedToReceive, flush=True)
		msgId += 1
		if msgId >= args.number: break
		#time.sleep(0.01)
		time.sleep(0.2)
	#all messages sent, wait while we receive some messages
	com.sendMsg('END')
	nbMissing = len(expectedToReceive)
	lastNbMissing = 0
	while not nbMissing == lastNbMissing:
		if nbMissing == 0:
			print('all messages received')
			exit(0)
		print('missing', expectedToReceive, flush=True)
		lastNbMissing = nbMissing
		com.sendMsg('END')
		time.sleep(2)
		nbMissing = len(expectedToReceive)
except KeyboardInterrupt:
	pass
com.disconnect()
exit(0)