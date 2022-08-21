#!/bin/bash

# This script is used for a simple installation
# of the dashcam application on a e.g. a Raspberry
# PI Zero.
# You will probably asked for sudo password, if you
# did not have the default settings of Raspberry PI
# OS.
# Please feel free to adjust to your needs, e.g.
# adding some mount info like sda1 for external usb sticks

DASHCAM_ROOT="/opt/dashcam"
DASHCAM_ROOT_LEGAL=$DASHCAM_ROOT"/legal"

echo "Install necessary packages (python-venv, pip)"
sudo apt install python3-venv python3-pip pigpio

for DCFile in dashcam.py led.py switch.py;
do
    echo "Copy file "$DCFile" to "$DASHCAM_ROOT/$DCFile
    sudo cp $DCFile $DASHCAM_ROOT/$DCFile
    sudo chmod a+x $DASHCAM_ROOT/$DCFile
done

echo "Setting Python3 virtual env '.venv' at '"$DASHCAM_ROOT"/.venv'"
sudo python3 -m venv $DASHCAM_ROOT/.venv
sudo $DASHCAM_ROOT/.venv/bin/pip3 install --upgrade pip
sudo $DASHCAM_ROOT/.venv/bin/pip3 install picamera RPi.GPIO pigpio

echo "Setup systemd service at /etc/systemd/system/dashcam.service"
sudo cp dashcam.service.example /etc/systemd/system/dashcam.service
echo "Reload systemctl daemon service"
sudo systemctl daemon-reload
echo "Prepare dashcam service to start after reboot"
sudo systemctl enable dashcam.service pigpiod.service
echo "Start dashcam service"
sudo systemctl start pigpiod.service dashcam.service
