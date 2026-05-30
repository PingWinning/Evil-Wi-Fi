#!/usr/bin/env bash
# install.sh — install system dependencies for Evil Wi-Fi
# Run once as root: sudo bash install.sh

set -e

if [[ $EUID -ne 0 ]]; then
    echo "[-] Run as root: sudo bash install.sh"
    exit 1
fi

echo "[*] Updating package lists ..."
apt-get update -q

echo "[*] Installing system dependencies ..."
apt-get install -y -q \
    hostapd \
    dnsmasq \
    aircrack-ng \
    wireless-tools \
    iptables \
    python3-flask \
    python3-tk \
    net-tools \
    iw

echo "[+] All dependencies installed."
echo "[+] Usage: sudo python3 main.py -i <AP_interface> -d <deauth_interface>"
echo "    Example: sudo python3 main.py -i wlan0 -d wlan1"
echo ""
echo "    Single-adapter (no deauth): sudo python3 main.py -i wlan0 --no-deauth"
