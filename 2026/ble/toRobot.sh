#!/bin/bash

drive=$1
if [[($drive == "")]]; then
  echo missing drive
  exit 1
fi

cp -r aioble "$drive/"
cp RobotBleServer.py "$drive"
cp mainRobotTestBLE.py "$drive/main.py"
sync
