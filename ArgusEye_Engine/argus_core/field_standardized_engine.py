import sys
import os
import socket
import struct
import asyncio
import xml.etree.ElementTree as ET

# International standard for ONVIF WS-Discovery Multicast
MULTICAST_IP = "239.255.255.250"
MULTICAST_PORT = 3702

# Standardized Probe payload to trigger mass responses from cameras
ONVIF_PROBE_PAYLOAD = (
    '<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
    'xmlns:a="http://schemas.xmlsoap.org/ws/2004/08/addressing">'
    '<s:Header><a:Action>http://schemas.xmlsoap.org/ws/2004/08/discovery/Probe</a:Action>'
    '<a:MessageID>urn:uuid:c0396126-7243-41c1-90a6-32ec6a05322c</a:MessageID>'
    '<a:To>urn:schemas-xmlsoap-org:ws:2004:08:discovery</a:To></s:Header>'
    '<s:Body><Probe xmlns="http://schemas.xmlsoap.org/ws/2004/08/discovery">'
    '<Types xmlns:dn="http://www.onvif.org/ver10/network/wsdl">dn:NetworkVideoTransmitter</Types>'
    '</Probe></s:Body></s:Envelope>'
).encode()

class FieldStandardizedEngine:
    def __init__(self):
        self.discovered_cameras = set()

    def get_local_network(self):
        """Automatically detect active IP configuration of the target network"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            local_ip = s.getsockname()[0]
            s.close()
            network_prefix = ".".join(local_ip.split(".")[:3]) + "."
            return local_ip, network_prefix
        except Exception as e:
            print(f"[-] Network detection failed: {e}")
            sys.exit(1)

    async def listen_for_cameras(self, sock, timeout=3):
        """Listen for simultaneous responses from all cameras in the area"""
        loop = asyncio.get_running_loop()
        end_time = loop.time() + timeout
        
        while loop.time() < end_time:
            try:
                data, addr = await loop.sock_recvfrom(sock, 4096)
                ip = addr[0]
                if ip not in self.discovered_cameras:
                    self.discovered_cameras.add(ip)
                    print(f"[+] DETECTION SUCCESS: {ip} verified via WS-Discovery")
            except socket.timeout:
                break
            except Exception:
                pass

    async def trigger_multicast_discovery(self):
        """Broadcast multicast impulse to force target visibility"""
        local_ip, network_prefix = self.get_local_network()
        print(f"[*] Local Deployment Interface IP: {local_ip}")
        print(f"[*] Injecting standardized multicast frames into isolated LAN...")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        sock.sendto(ONVIF_PROBE_PAYLOAD, (MULTICAST_IP, MULTICAST_PORT))
        await self.listen_for_cameras(sock, timeout=4)
        sock.close()

        print(f"\n[!] Discovery sequence terminated. Total identified targets: {len(self.discovered_cameras)}")
        return list(self.discovered_cameras)

if __name__ == "__main__":
    engine = FieldStandardizedEngine()
    asyncio.run(engine.trigger_multicast_discovery())