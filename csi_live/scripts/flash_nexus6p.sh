#!/usr/bin/env bash

set -e

# Move out of scripts dir
cd ..

# 0. Make sure platform-tools exists.
if [[ ! -d platform-tools ]]; then
    echo "Downloading platform-tools..."
    wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip
    unzip platform-tools-latest-linux.zip
    rm -f platform-tools-latest-linux.zip
fi
PATH=$PATH:$(pwd)/platform-tools

SAVE=$PWD

# Get stock image.
if [[ ! -d android ]]; then
    mkdir android
fi
cd android/

if [[ ! -d angler-opm7.181205.001 ]]; then
    wget https://dl.google.com/dl/android/aosp/angler-opm7.181205.001-factory-b75ce068.zip
    unzip angler-opm7.181205.001-factory-b75ce068.zip
    rm -f angler-opm7.181205.001-factory-b75ce068.zip
fi
cd angler-opm7.181205.001

if [[ ! -e system.img ]]; then
    unzip image-angler-opm7.181205.001.zip
fi

# Check if phone is connected in bootloader
if [[ ! $(fastboot devices) == *"fastboot"* ]]; then
    echo "No device connected."
    exit 1
fi

fastboot flash bootloader bootloader-angler-angler-03.84.img
fastboot reboot bootloader
sleep 3

fastboot flash radio radio-angler-angler-03.88.img 
fastboot reboot bootloader
sleep 3

fastboot flash:raw boot boot.img
fastboot flash recovery recovery.img
fastboot flash system system.img
fastboot flash vendor vendor.img
fastboot reboot bootloader
sleep 3

# cd ..
# if [[ ! -e twrp-3.4.0-0-angler.img ]]; then
#     wget --referer https://dl.twrp.me/twrp/twrp-3.4.0-0-twrp.img https://dl.twrp.me/twrp/twrp-3.4.0-0-twrp.img
# fi
# fastboot flash recovery twrp-3.4.0-0-twrp.img
# fastboot reboot bootloader
# sleep 3

# fastboot reboot recovery
# cd $SAVE

echo "Remember to wipe cache+Dalvik."
