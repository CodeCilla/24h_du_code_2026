# to know COM port used when connected on PC:
# python -m serial.tools.list_ports

import binascii
import sys
sys.path.append("")
from micropython import const
import aioble
import bluetooth
import struct

_SERVICE_UUID = bluetooth.UUID(0x1234)
_CHAR_UUID = bluetooth.UUID(0x1235)

# How frequently to send advertising beacons.
_ADV_INTERVAL_MS = 250_000

MAX_MSG_DATA_LENGTH = const(18)

_COMMAND_DONE = const(0)
_COMMAND_SENDDATA = const(1)
_COMMAND_SENDCHUNK = const(2)  # send chunk of string, use _COMMAND_SENDDATA for last chunk
_COMMAND_SENDBYTESDATA = const(3)
_COMMAND_SENDBYTESCHUNK = const(4)  # send chunk of string base64 formatted, use _COMMAND_SENDBYTESDATA for last chunk

class RobotBleServer:
	"""Class to manage connection with BLE"""
	def __init__(self, robotName:str, onMsgReceived):
		""":param robotName: name to use in advertising
		:param onMsgReceived: function to call when a message is received"""
		self.robotName = robotName
		self.onMsgReceived = onMsgReceived
		# Register GATT server.
		service = aioble.Service(_SERVICE_UUID)
		self.characteristic = aioble.Characteristic(service, _CHAR_UUID, write=True, notify=True)
		aioble.register_services(service)
		self.connection = None

	def sendMessage(self, msg:str|bytes):
		"""Send a message over BLE
		Message can be a string or a bytes sequence (maximum 18 charaters/bytes per message)
		:param msg: message to send"""
		if type(msg) == str:
			encodedMsg = msg.encode()
			sendMsgType, sendChunkMsgType = _COMMAND_SENDDATA, _COMMAND_SENDCHUNK
		elif type(msg) == bytes:
			#msg = binascii.b2a_base64(msg).encode()
			encodedMsg = binascii.b2a_base64(msg).rstrip()
			sendMsgType, sendChunkMsgType = _COMMAND_SENDBYTESDATA, _COMMAND_SENDBYTESCHUNK
		else:
			raise Exception('unsupported message type', type(msg))
		print('encode', type(msg), msg, '=>', encodedMsg)
		while len(encodedMsg) > MAX_MSG_DATA_LENGTH:
			chunk = encodedMsg[:MAX_MSG_DATA_LENGTH]
			self.characteristic.notify(self.connection, struct.pack("<B", sendChunkMsgType) + chunk)
			encodedMsg = encodedMsg[MAX_MSG_DATA_LENGTH:]
			print('sent chunk', chunk)
		self.characteristic.notify(self.connection, struct.pack("<B", sendMsgType) + encodedMsg)
		print('sent last', encodedMsg)

	async def bleTask(self):
		"""Loop to wait for incoming messages over BLE.
		When a received message is complete, call function defined in self.onMsgReceived
		When BLE connection is closed, stop this function"""
		try:
			with self.connection.timeout(None):
				dataChunk = ''
				msgId = 0
				while True:
					await self.characteristic.written()
					msg = self.characteristic.read()
					#self.characteristic.write(b"")

					if len(msg) < 3:
						continue

					# Message is <command><seq><data>.
					command = msg[0]
					op_seq = int(msg[1])
					msgData = msg[2:].decode()
					#print('MSG=', msg)

					if command in (_COMMAND_SENDCHUNK, _COMMAND_SENDBYTESCHUNK):
						dataChunk += msgData
						print('received chunk', msgData, '=>', dataChunk)
					elif command in (_COMMAND_SENDDATA, _COMMAND_SENDBYTESDATA):
						data = dataChunk + msgData
						dataChunk = ''
						if command == _COMMAND_SENDBYTESDATA:
							data = binascii.a2b_base64(data)
							#print('received data:', data)
						print('received:', len(data), msgId, type(data), data)
						self.onMsgReceived(data)
						msgId += 1
		except aioble.DeviceDisconnectedError:
			print('disconnected BLE')
			return

	async def communicationTask(self):
		"""Loop to advertise and wait for connection.
		When connection is established, start task to read incoming messages"""
		while True:
			print("Waiting for connection")
			self.connection = await aioble.advertise(
				_ADV_INTERVAL_MS,
				name=self.robotName,
				services=[_SERVICE_UUID],
			)
			print("Connection from", self.connection.device)
			await self.bleTask()
			await self.connection.disconnected()
			self.connection = None
	
