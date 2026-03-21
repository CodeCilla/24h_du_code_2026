# to know COM port used when connected on PC:
# python -m serial.tools.list_ports

# in this example, robot will send back to PC the checksum of each message received

import binascii
import uasyncio as asyncio
import RobotBleServer

robotName = 'myTeamName'

toSend = []

def onMsgToRobot(data:str|bytes):
	"""Function to call when a message sent by PC is received
	:param data: message received"""
	checksum = binascii.crc32(data)
	print('received', data, '=>', checksum)
	toSend.append(str(checksum))

async def robotMainTask(bleConnection):
	"""Main function for robot activities
	:param bleConnection: object to check BLE connection and send messages"""
	while True:
		await asyncio.sleep(0.1)
		#print('connection', bleConnection.connection)
		if not bleConnection.connection: continue
		if toSend == []: continue
		while not toSend == []:
			data = toSend.pop(0)
			bleConnection.sendMessage(data)
			print('sent', data)

# Run tasks
async def main():
	print('Start main')
	bleConnection = RobotBleServer.RobotBleServer(robotName=robotName, onMsgReceived=onMsgToRobot)
	asyncio.create_task(robotMainTask(bleConnection))
	await bleConnection.communicationTask()

asyncio.run(main())
