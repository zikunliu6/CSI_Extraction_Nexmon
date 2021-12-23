#!/usr/bin/env bash

set -e

# Move out of scripts dir
cd ..

# helpFunction()
# {
#    echo ""
#    echo -e "\t-s to patch driver for CSI collection, restores normal driver otherwise."
#    exit 1 # Exit script after printing help
# }

# START="0"
# while getopts "s" opt
# do
#    case "$opt" in
#       s ) START="1" ;;
#       ? ) helpFunction ;; # Print helpFunction in case parameter is non-existent
#    esac
# done

# 0. Make sure platform-tools exists.
if [[ ! -d platform-tools ]]; then
    echo "Downloading platform-tools..."
    wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip
    unzip platform-tools-latest-linux.zip
    rm -f platform-tools-latest-linux.zip
fi
PATH=$PATH:$(pwd)/platform-tools

# 1. 2. Install some dependencies
sudo apt-get install git gawk qpdf adb flex bison
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install libc6:i386 libncurses5:i386 libstdc++6:i386

# 3. Clone nexmon base repository
if [[ ! -d nexmon ]]; then
    echo "Cloning nexmon..."
    git clone https://github.com/seemoo-lab/nexmon.git
fi
NEXMON_HOME=$(pwd)/nexmon

# 4. Get Android NDK
if [[ ! -d android-ndk-r11c ]]; then
    echo "Downloading android-ndk-r11c..."
    curl http://dl.google.com/android/repository/android-ndk-r11c-linux-x86_64.zip > android-ndk-r11c.zip
    unzip android-ndk-r11c.zip
    rm -f android-ndk-r11c.zip
fi
export NDK_ROOT=$(pwd)/android-ndk-r11c

# 6. Setup nexmon environment
cd $NEXMON_HOME
source setup_env.sh

# 7. Extract ucode, templateram, flashpatches
make

# 8. Build utilities
cd $NEXMON_HOME/utilities
make

# 9. Check if phone is connected
if [[ ! $(adb devices | tail -n +2) == *"device"* ]]; then
    echo "No device connected."
    exit 1
fi

# 10. Install utilities onto phone.
make install

# 11. Install nexmon_csi.
cd $NEXMON_HOME/patches/bcm4358/7_112_300_14_sta/
if [[ ! -d nexmon_csi ]]; then
    echo "Cloning nexmon_csi..."
    git clone https://github.com/seemoo-lab/nexmon_csi.git
fi

# 12. Install firwmare onto phone.
cd nexmon_csi
if [[ ! -e fw_bcmdhd.orig.bin ]]; then
    echo "Backing up original firmware..."
    make backup-firmware
fi

make install-firmware

exit 0

