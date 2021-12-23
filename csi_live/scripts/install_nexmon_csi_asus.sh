#!/usr/bin/env bash

set -e

# Move out of scripts dir
cd ..

helpFunction()
{
   echo ""
   echo -e "\t-i ASUS router IP address."
   exit 1 # Exit script after printing help
}

ASUS_IP=""
while getopts "i:" opt
do
   case "$opt" in
      i ) ASUS_IP="$OPTARG" ;;
      ? ) helpFunction ;; # Print helpFunction in case parameter is non-existent
   esac
done

if [[ -z "$ASUS_IP" ]]; then
    echo "Missing ASUS IP.";
    helpFunction
fi

# 1. Install some dependencies
sudo apt-get install git gawk qpdf flex

# 2. Install i386 libs
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install libc6:i386 libncurses5:i386 libstdc++6:i386

# 3. Clone nexmon base repository
if [[ ! -d nexmon ]]; then
    echo "Cloning nexmon..."
    git clone https://github.com/seemoo-lab/nexmon.git
fi
NEXMON_HOME=$(pwd)/nexmon

# 4. Navigate to dir
cd $NEXMON_HOME
source setup_env.sh

# 5. Run make
make

# 6. Clone nexmon_csi
cd $NEXMON_HOME/patches/bcm4366c0/10_10_122_20/
if [[ ! -d nexmon_csi ]]; then
    echo "Cloning nexmon_csi..."
    git clone https://github.com/seemoo-lab/nexmon_csi.git
fi

# 7. Enter nexmon_csi and make
cd nexmon_csi
make install-firmware REMOTEADDR=${ASUS_IP}


# 8. Clone aarch64
if [[ ! -d am-toolchains ]]; then
    echo "Cloning am-toolchains..."
    git clone https://github.com/RMerl/am-toolchains.git
fi

# 9. Set compile environment
export AMCC=$(pwd)/am-toolchains/brcm-arm-hnd/crosstools-aarch64-gcc-5.3-linux-4.1-glibc-2.22-binutils-2.25/usr/bin/aarch64-buildroot-linux-gnu-
export LD_LIBRARY_PATH=$(pwd)/am-toolchains/brcm-arm-hnd/crosstools-aarch64-gcc-5.3-linux-4.1-glibc-2.22-binutils-2.25/usr/lib

# 10. Go back too root, compile install nexutil

# Install nexutil
cd $NEXMON_HOME
cd utilities/libnexio
${AMCC}gcc -c libnexio.c -o libnexio.o -DBUILD_ON_RPI
${AMCC}ar rcs libnexio.a libnexio.o
cd ../nexutil
echo "typedef uint32_t uint;" > types.h
sed -i 's/argp-extern/argp/' nexutil.c
${AMCC}gcc -static -o nexutil nexutil.c bcmwifi_channels.c b64-encode.c b64-decode.c -DBUILD_ON_RPI -DVERSION=0 -I. -I../libnexio -I../../patches/include -L../libnexio/ -lnexio
scp nexutil admin@${ASUS_IP}:/jffs/nexutil
ssh admin@${ASUS_IP} "/bin/chmod +x /jffs/nexutil"

# Install tcpdump
cd $NEXMON_HOME
cd ../
scp utils/tcpdump admin@${ASUS_IP}:/jffs/tcpdump
ssh admin@${ASUS_IP} "/bin/chmod +x /jffs/tcpdump"

exit 0

