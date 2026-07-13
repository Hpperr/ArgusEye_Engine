#!/usr/bin/env python3
"""
FIELD STANDARDIZED ENGINE - ONVIF Camera Discovery
Enhanced with stealth and comprehensive device fingerprinting
"""

import sys
import os
import socket
import struct
import asyncio
import xml.etree.ElementTree as ET
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
import aiohttp
import async_timeout

# ==================== CONFIG ====================
MULTICAST_IP = "239.255.255.250"
MULTICAST_PORT = 3702
DISCOVERY_TIMEOUT = 5
DEVICE_TIMEOUT = 3

# ONVIF Probe payload
ONVIF_PROBE_PAYLOAD = (
    '<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
    'xmlns:a="http://schemas.xmlsoap.org/ws/2004/08/addressing">'
    '<s:Header><a:Action>http://schemas.xmlsoap.org/ws/2004/08/discovery/Probe</a:Action>'
    '<a:MessageID>urn:uuid:{uuid}</a:MessageID>'
    '<a:To>urn:schemas-xmlsoap-org:ws:2004:08:discovery</a:To></s:Header>'
    '<s:Body><Probe xmlns="http://schemas.xmlsoap.org/ws/2004/08/discovery">'
    '<Types xmlns:dn="http://www.onvif.org/ver10/network/wsdl">dn:NetworkVideoTransmitter</Types>'
    '</Probe></s:Body></s:Envelope>'
)

# ==================== COLORS ====================
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

def cprint(text, color=Colors.WHITE, bold=False):
    if bold:
        print(f"{Colors.BOLD}{color}{text}{Colors.WHITE}")
    else:
        print(f"{color}{text}{Colors.WHITE}")

# ==================== FIELD STANDARDIZED ENGINE ====================
class FieldStandardizedEngine:
    """ONVIF camera discovery engine"""
    
    def __init__(self, stealth_mode=True):
        self.stealth_mode = stealth_mode
        self.discovered_cameras = {}
        self.network_info = {}
        self._init_network()
    
    def _init_network(self):
        """Initialize network detection"""
        try:
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            self.network_info['local_ip'] = local_ip
            self.network_info['subnet'] = ".".join(local_ip.split(".")[:3]) + ".0/24"
            
            cprint(f"[*] Local IP: {local_ip}", Colors.DIM)
            cprint(f"[*] Subnet: {self.network_info['subnet']}", Colors.DIM)
            
        except Exception as e:
            cprint(f"[-] Network init failed: {e}", Colors.RED)
            sys.exit(1)
    
    def _generate_uuid(self):
        """Generate UUID for probe"""
        import uuid
        return str(uuid.uuid4())
    
    def _parse_discovery_response(self, data, addr):
        """Parse ONVIF discovery response"""
        try:
            root = ET.fromstring(data)
            
            # Extract device info
            device_info = {
                'ip': addr[0],
                'port': addr[1],
                'raw_data': data[:200] + '...'
            }
            
            # Try to extract XAddrs
            for elem in root.iter():
                if 'XAddrs' in elem.tag:
                    device_info['xaddrs'] = elem.text
                    break
                if 'Types' in elem.tag:
                    device_info['types'] = elem.text
                    break
            
            return device_info
        except Exception as e:
            return None
    
    async def listen_for_cameras(self, sock, timeout=DISCOVERY_TIMEOUT):
        """Listen for discovery responses"""
        loop = asyncio.get_running_loop()
        end_time = loop.time() + timeout
        
        while loop.time() < end_time:
            try:
                data, addr = await loop.sock_recvfrom(sock, 4096)
                ip = addr[0]
                
                if ip not in self.discovered_cameras:
                    device_info = self._parse_discovery_response(data, addr)
                    if device_info:
                        self.discovered_cameras[ip] = device_info
                        cprint(f"[+] Camera discovered: {ip}", Colors.GREEN)
                        
                        # Additional device info
                        if device_info.get('xaddrs'):
                            cprint(f"    Service: {device_info['xaddrs'][:50]}...", Colors.DIM)
                        
            except socket.timeout:
                break
            except Exception as e:
                if not self.stealth_mode:
                    cprint(f"[-] Listen error: {e}", Colors.RED)
                continue
    
    async def trigger_multicast_discovery(self):
        """Broadcast discovery probe"""
        cprint(f"\n[*] Broadcasting ONVIF discovery probe...", Colors.YELLOW)
        cprint(f"[*] Multicast: {MULTICAST_IP}:{MULTICAST_PORT}", Colors.DIM)
        
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1)
        
        # Send probe
        probe_payload = ONVIF_PROBE_PAYLOAD.format(uuid=self._generate_uuid())
        
        try:
            sock.sendto(probe_payload.encode(), (MULTICAST_IP, MULTICAST_PORT))
            cprint("[+] Probe sent", Colors.GREEN)
        except Exception as e:
            cprint(f"[-] Send failed: {e}", Colors.RED)
            sock.close()
            return []
        
        # Listen for responses
        await self.listen_for_cameras(sock, timeout=DISCOVERY_TIMEOUT)
        sock.close()
        
        cprint(f"\n[!] Discovery complete. Found {len(self.discovered_cameras)} cameras", Colors.GREEN)
        return self.discovered_cameras
    
    async def probe_device_details(self, ip, port=80):
        """Get detailed device information"""
        try:
            # ONVIF GetDeviceInformation request
            device_info_payload = (
                '<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">'
                '<s:Body>'
                '<GetDeviceInformation xmlns="http://www.onvif.org/ver10/device/wsdl"/>'
                '</s:Body>'
                '</s:Envelope>'
            )
            
            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
                'User-Agent': 'ONVIF/1.0'
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"http://{ip}:{port}/onvif/device_service"
                async with session.post(url, data=device_info_payload, headers=headers, timeout=DEVICE_TIMEOUT) as resp:
                    if resp.status == 200:
                        data = await resp.text()
                        # Parse response
                        return {
                            'status': 'success',
                            'data': data[:500]
                        }
            return None
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def scan_cameras(self):
        """Main scan function"""
        cameras = await self.trigger_multicast_discovery()
        
        # Probe each camera for details
        cprint(f"\n[*] Probing device details...", Colors.YELLOW)
        
        for ip in list(cameras.keys()):
            details = await self.probe_device_details(ip)
            if details:
                self.discovered_cameras[ip]['details'] = details
                cprint(f"[+] Details retrieved for {ip}", Colors.DIM)
        
        return self.discovered_cameras
    
    def export_results(self, filename="camera_discovery.json"):
        """Export discovery results"""
        data = {
            'network': self.network_info,
            'cameras': self.discovered_cameras,
            'timestamp': datetime.now().isoformat()
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        cprint(f"[+] Results exported to {filename}", Colors.GREEN)

# ==================== MAIN ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Field Standardized Engine v2.0")
    parser.add_argument("-s", "--stealth", action="store_true", help="Stealth mode")
    parser.add_argument("-o", "--output", default="camera_discovery.json", help="Output file")
    
    args = parser.parse_args()
    
    engine = FieldStandardizedEngine(args.stealth)
    
    try:
        asyncio.run(engine.scan_cameras())
        engine.export_results(args.output)
    except KeyboardInterrupt:
        cprint("\n[!] Interrupted by user", Colors.RED)
    
    cprint("\n[+] Field Standardized Engine finished", Colors.GREEN)
