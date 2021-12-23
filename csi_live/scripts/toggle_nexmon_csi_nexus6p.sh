#!/usr/bin/env bash

set -e

helpFunction()
{
   echo ""
   echo -e "\t-s to patch driver for CSI collection, restores normal driver otherwise."
   exit 1 # Exit script after printing help
}

START="0"
while getopts "s" opt
do
   case "$opt" in
      s ) START="1" ;;
      ? ) helpFunction ;; # Print helpFunction in case parameter is non-existent
   esac
done
 
# 9. Check if phone is connected
if [[ ! $(adb devices | tail -n +2) == *"device"* ]]; then
    echo "No device connected."
    exit 1
fi

adb shell 'su -c "mount -o rw,remount /system"'
adb shell 'su -c "mount -o rw,remount /vendor"'

if [[ $START=="1" ]]; then
    adb shell 'su -c "cp /sdcard/fw_bcmdhd.bin /vendor/firmware/fw_bcmdhd.bin"'
else
    adb shell 'su -c "cp /sdcard/fw_bcmdhd.orig.bin /vendor/firmware/fw_bcmdhd.bin"'
fi

sleep 2
adb shell 'su -c "ifconfig wlan0 down"'
sleep 2
adb shell 'su -c "ifconfig wlan0 up"'

exit 0
