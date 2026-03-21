# BLE example
Here is an example of driver to send messages using BLE

# Setup on robot (or other BLE advertiser)
Copy following files to robot

- aioble/\*
- RobotBleServer.py
- mainRobotTestBLE.py (to rename as main.py)

You can use script toRobot.sh for that, for example when run from a Windows git bash,
if robot is connected on drive D:, you can run
> ./toRobot.sh /d

# Setup on USB dongle
Copy following files to robot

- aioble/\*
- mainDongle.py (to rename as main.py)

You can use script toDongle.sh for that, for example when run from a Windows git bash,
if dongle is connected on drive E:, you can run
> ./toDongle.sh /e

# Setup on computer
You need pyserial module for python. You can install it using command

> python -m pip install pyserial

or if a proxy is required
> python -m pip install --proxy \<http proxy parameter\> pyserial

Then run following command
> python mainPcTestBLE.py --portcom \<com port used by dongle\>

To know COM port to use as argument, run following command before and after dongle connection:
> python -m serial.tools.list_ports

Port in second result but not in first result is port used by dongle.

# Connect on the good robot
When several robots are started at same time, they shall have a unique identifier so you can connect over BLE on the good robot.
For that, you shall replace "myTeamName" by a unique identifer (for example the name of your team) in following files:
- mainRobotTestBLE.py
- mainPcTestBLE.py

# Note relative to BLE
The Bluetooth is a connection with a limited transfer rate. If you try to send a lot of messages in a short period of time, or transfer long messages, the BLE driver will do it's best to transfer all data but expect delay to receive messages on the other side.
