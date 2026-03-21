#!/usr/bin/bash

drive=$1
if [[($drive == "")]]; then
  echo missing drive
  exit 1
fi

cp -r aioble $drive/
cp mainDongle.py $drive/main.py
sync
