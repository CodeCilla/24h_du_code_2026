# python -m serial.tools.list_ports

import sys
import time
#import binascii
import base64
import serial
import threading
import json

ctrlC = bytes.fromhex("03")
ctrlD = bytes.fromhex("04")

class ComWithDongle:
	"""Class to manage communication with dongle, over virtual COM port"""
	def __init__(self, comPort:str, peripheralName:str, onMsgReceived, debug=False):
		""":param comPort: name of COM port used by dongle
		:param peripheralName: name of BLE peripheral
		:param onMsgReceived: function to call when a message from peripheral is received
		:param debug: when True, print debug messages received from dongle"""
		try:
			self.ser = serial.Serial(port=comPort, baudrate=115200, timeout=2)
		except serial.SerialException:
			exit(f"no device on port {comPort}")
		self.bleConnected = threading.Semaphore(0)
		self.messageSent = threading.Semaphore(0)
		self.onMsgReceived = onMsgReceived
		self.debug = debug
		self.resetDongle()
		threading.Thread(name='readComPort', target=self.readFromComPort, daemon=True).start()
		# first message over COM port to dongle is to define BLE peripheral to connect on
		self.sendDict({'type':'connect','name':peripheralName})
		timeoutNotReached = self.bleConnected.acquire(timeout=5)
		if not timeoutNotReached:
			exit(f'unable to connect to peripheral "{peripheralName}"')

	def resetDongle(self):
		self.ser.write(ctrlC)
		self.ser.write(ctrlD)
		self.ser.flush()
		time.sleep(2)

	def sendDict(self, msg:dict):
		self.ser.write(json.dumps(msg).encode("utf-8") + b'\r')

	def sendMsg(self, msg:str|bytes):
		if isinstance(msg, str):
			self.sendDict({'type':'msg', 'format':'str', 'string':msg})
		else:
			#self.sendDict({'type':'msg', 'base64':binascii.b2a_base64(msg).decode("utf-8")})
			#b = binascii.b2a_base64(msg).decode("utf-8").rstrip()
			#b = base64.b64encode(msg).decode("utf-8").rstrip()
			b = base64.b64encode(msg).decode("utf-8").rstrip()
			if self.debug: print('sendMsg', msg, '=>', b, flush=True)
			self.sendDict({'type':'msg', 'format':'base64', 'string':b})
		self.messageSent.acquire(timeout=2)

	def disconnect(self):
		self.sendDict({'type': 'disconnect'})

	def readFromComPort(self):
		while True:
			line = self.ser.readline().rstrip()
			# valid message can't be empty
			if type(line) is not bytes or line == b'':
				# empty message received after a timeout on serial connection, to ignore
				continue
			line = line.decode("utf-8")
			try:
				receivedMsgDict = json.loads(line)
			except json.decoder.JSONDecodeError:
				# this is not a dictionnary, just a debug message
				if self.debug: print('from COM:', line, flush=True)
				continue
			msgType = receivedMsgDict['type']
			if msgType == 'connected':
				self.bleConnected.release()
			elif msgType == 'sentMessage':
				self.messageSent.release()
			elif msgType == 'msgFromBle':
				if receivedMsgDict['format'] == 'str':
					self.onMsgReceived(receivedMsgDict['string'])
				else:
					if self.debug: print('base64 msg from BLE:', len(receivedMsgDict['string']), receivedMsgDict['string'])
					#self.onMsgReceived(binascii.a2b_base64(receivedMsgDict['string']))
					self.onMsgReceived(base64.b64decode(receivedMsgDict['string']))

			elif msgType == 'debug':
				if self.debug:
					del(receivedMsgDict['type'])
					print('debug COM:', receivedMsgDict)
			elif msgType in ['connect', 'msg']:
				pass
			else:
				print('unknown msg type', receivedMsgDict)
