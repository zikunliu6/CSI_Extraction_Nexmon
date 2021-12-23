#!/usr/bin/env bash

set -e

# Get out of scripts dir
cd ..

# 1. Make sure you are su
# sudo su

# 2. 3. Get prereqs

if [[ $(uname -a) == *"kali"* ]]; then
	echo "deb http://http.kali.org/kali kali-rolling main non-free contrib" | sudo tee /etc/apt/source.list
	apt-get update && apt-get upgrade
	apt install kalipi-kernel-headers git libgmp3-dev gawk qpdf bison flex autoconf automake libtool texinfo

else
	apt-get update && apt-get upgrade
	apt install raspberrypi-kernel-headers git libgmp3-dev gawk qpdf bison flex makeautoconf automake libtool
fi

# 4. Clone nexmon base repository
if [[ ! -d nexmon ]]; then
	echo "Cloning nexmon..."
	git clone https://github/com/seemoo-lab/nexmon.git nexmon
fi

# 5. Go to nexmon directory
cd nexmon
NEXMON_HOME=$(pwd)

# 6. Build isl if doesn't exist.
if [[ ! -e /usr/lib/arm-linux-gnueabihf/libisl.so.10 ]]; then
	cd buildtools/isl-0.10
	autoreconf -f -i
	./configure
	make
	make install
	ln -s /usr/local/lib/libisl.so /usr/lib/arm-linux-gnueabihf/libisl.so.10
	cd $NEXMON_HOME
fi

# 7. Build mpfr if doesn't exist.
if [[ ! -e /usr/lib/arm-linux-gnueabihf/libmpfr.so.4 ]]; then
	cd buildtools/mpfr-3.1.4
	autoreconf -f -i
	./configure
	make
	make install
	ln -s /usr/local/lib/libmpfr.so /usr/lib/arm-linux-gnueabihf/libmpfr.so.4
	cd $NEXMON_HOME
fi

# 8. Compile build tools, extract ucode, flashpatches from original firwmare
source setup_env.sh
make

# 9. Clone the nexmon_csi repo
cd patches/bcm43455c0/7_45_189/
if [[ ! -d nexmon_csi ]]; then
	git clone https://github.com/seemoo-lab/nexmon_csi.git
fi
# 10. Enter subdirectory and install-firmware
cd nexmon_csi
make

# Make backups first
if [[ ! -e brcmfmac43455-sdio.bin.orig ]]; then
	make backup-firmware
fi
MODULE_PATH=$(modinfo brcmfmac | head -n 1 | awk '{print $2}')
if [[ ! -e brcmfmac.ko.orig ]]; then

	mv $MODULE_PATH brcmfmac.ko.orig
fi

# Install the firmware
make install-firmware

# To load modified driver after reboot
if [[ $(uname -r) == *"4.9"* ]]; then
	cp brcmfmac_4.9.y-nexmon/brcmfmac.ko $MODULE_PATH
elif [[ $(uname -r) == *"4.14"* ]]; then
	cp brcmfmac_4.14.y-nexmon/brcmfmac.ko $MODULE_PATH
elif [[ $(uname -r) == *"4.19"* ]]; then
	cp brcmfmac_4.19.y-nexmon/brcmfmac.ko $MODULE_PATH	
elif [[ $(uname -r) == *"5.4"* ]]; then
	cp brcmfmac_5.4.y-nexmon/brcmfmac.ko $MODULE_PATH
fi
depmod -a

# 11. Install nexutil
cd $NEXMON_HOME
cd utilities/nexutil
make && make install
apt-get install tcpdump wireshark iperf

# 12. Optional: remove wpa_supplicant
apt-get remove wpasupplicant
