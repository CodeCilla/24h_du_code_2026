import sys
sys.path.append("")
from micropython import const
import json
import uasyncio as asyncio
import aioble
import bluetooth
import struct

_SERVICE_UUID = bluetooth.UUID(0x1234)
_CHAR_UUID = bluetooth.UUID(0x1235)

MAX_MSG_DATA_LENGTH = const(18)

_COMMAND_DONE = const(0)
_COMMAND_SENDDATA = const(1)
_COMMAND_SENDCHUNK = const(2)  # send chunk of data, use _COMMAND_SENDDATA for last chunk
_COMMAND_SENDBYTESDATA = const(3)
_COMMAND_SENDBYTESCHUNK = const(4)  # send chunk of bytes, use _COMMAND_SENDBYTESDATA for last chunk

class ManageDongle:
	def __init__(self, device):
		self._device = device
		self._connection = None
		self._seq = 1

	async def connect(self):
		try:
			print("Connecting to", self._device)
			self._connection = await self._device.connect()
		except asyncio.TimeoutError:
			print("Timeout during connection")
			return

		try:
			print("Discovering...")
			service = await self._connection.service(_SERVICE_UUID)
			#uuids = []
			#async for char in service.characteristics():
			#	uuids.append(char.uuid)
			#print('uuids', uuids)
			self._characteristic = await service.characteristic(_CHAR_UUID)
		except asyncio.TimeoutError:
			print("Timeout discovering services/characteristics")
			return

		asyncio.create_task(self.readFromBle())
		await asyncio.sleep(0.1)
		self.sendDictToCom({'type':'connected'})

	async def _command(self, cmd, data):
		send_seq = self._seq
		await self._characteristic.write(struct.pack("<BB", cmd, send_seq) + data)
		#print('sent packet num', send_seq)
		self._seq += 1
		return send_seq
	
	async def readFromBle(self):
		msgChunk = ''
		while True:
			read = await self._characteristic.notified()
			# message format is <command><data>
			cmd = read[0]
			#print('received from BLE', read)
			self.sendDictToCom({'type':'debug', 'from':'fromBle','cmd':cmd, 'data':read[1:]})
			if cmd in [_COMMAND_SENDCHUNK, _COMMAND_SENDBYTESCHUNK]:
				#self.sendDictToCom({'type':'debug', 'from':'chunkFromBle','string':msgChunk})
				msgChunk += read[1:].decode()
			elif cmd in [_COMMAND_SENDDATA, _COMMAND_SENDBYTESDATA]:
				# message to send to computer over COM port
				msgFormat = 'base64' if cmd == _COMMAND_SENDBYTESDATA else 'str'
				msg = msgChunk + read[1:].decode()
				self.sendDictToCom({'type':'msgFromBle', 'format':msgFormat, 'string':msg})
				msgChunk = ''

	async def sendData(self, data:str, base64:bool=False):
		"""Send a string or bytes sequence over BLE
		:param data: string to send (plain str or base64 formated)
		:param base64: if True, data is a base64 formated string"""
		sendMsgType = _COMMAND_SENDBYTESCHUNK if base64 else _COMMAND_SENDCHUNK
		while len(data) > MAX_MSG_DATA_LENGTH:
			chunk = data[:MAX_MSG_DATA_LENGTH]
			self.sendDictToCom({'type':'debug', 'from':'sendChunkToBle','string':chunk})
			await self._command(sendMsgType, chunk.encode())
			data = data[MAX_MSG_DATA_LENGTH:]
		sendMsgType = _COMMAND_SENDBYTESDATA if base64 else _COMMAND_SENDDATA
		#self.sendDictToCom({'type':'msgType', 'strOrBase64':sendMsgType, 'sentdata':data})
		await self._command(sendMsgType, data.encode())
		self.sendDictToCom({'type':'sentMessage'})
	
	async def disconnect(self):
		if self._connection:
			await self._connection.disconnect()

	def sendDictToCom(self, data:dict):
		print(json.dumps(data))

async def main():
	print('start dongle')
	while True:
		try:
			line = input()
		except KeyboardInterrupt:
			# when ctrl-C is sent to dongle, we receive a KeyboardInterrupt
			sys.exit(0)
		#print('dongle received:', line)
		receivedMsgDict = json.loads(line)
		if receivedMsgDict['type'] == 'connect':
			# => start BLE scan and connect on this peripheral
			peripheralName = receivedMsgDict['name']
			async with aioble.scan(5000, 30000, 30000, active=True) as scanner:
				async for result in scanner:
					# print('scan', result.name(), result.services())
					print('scan', result.name(), result.rssi, result.services())
					if result.name() == peripheralName and _SERVICE_UUID in result.services():
						device = result.device
						break
				else:
					print("Server not found")
					return

			client = ManageDongle(device)
			await client.connect()
		elif receivedMsgDict['type'] == 'disconnect':
			await client.disconnect()
		elif receivedMsgDict['type'] == 'msg':
			#msgFormat = 'base64' in receivedMsgDict
			if 'format' not in receivedMsgDict or receivedMsgDict['format'] not in ['str', 'base64']:
				client.sendDictToCom({'type':'badMessage', 'error':'invalid format', 'received':receivedMsgDict})
				continue
			msgFormat = True if receivedMsgDict['format'] == 'base64' else False
			await client.sendData(receivedMsgDict['string'], base64=msgFormat)
		else:
			print('unknown message type', receivedMsgDict)
	await client.disconnect()

asyncio.run(main())
