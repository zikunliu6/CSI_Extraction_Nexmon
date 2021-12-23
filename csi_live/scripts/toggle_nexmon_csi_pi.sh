#!/usr/bin/env bash

echo "Restarting brcmfmac..."
modprobe -r brcmfmac && modprobe brcmfmac;
sleep 1;
modprobe -r brcmfmac && modprobe brcmfmac;
