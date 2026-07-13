#!/usr/bin/env python3
"""
VIDEO MATRIX  - Tactical C2 Dashboard
Real-time Multi-Camera Surveillance Matrix

Copyright (c) 2024 F1REW0LF
License: MIT - For authorized security testing only
"""

import cv2
import threading
import time
import numpy as np
import os
import json
import socket
from datetime import datetime
from collections import deque
import subprocess

# ==================== COLOR CODES ====================
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

# ==================== CAMERA STREAM ====================
class CameraStreamer(threading.Thread):
    """Individual camera stream handler"""
    
    def __init__(self, url, name, index, stealth=False):
        super().__init__()
        self.url = url
        self.name = name
        self.index = index
        self.stealth = stealth
        self.frame = None
        self.running = True
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect = 5
        self.frame_count = 0
        self.fps = 0
        self.last_fps_update = time.time()
        self.status = "Connecting..."
        self.error_message = ""
        
        # Create black frame for "No Signal"
        self.black_frame = np.zeros((360, 480, 3), dtype=np.uint8)
        self._draw_no_signal()
        
        cprint(f"[*] Camera {name} initialized (URL: {url})", Colors.DIM)
    
    def _draw_no_signal(self):
        """Draw 'No Signal' on black frame"""
        cv2.putText(
            self.black_frame, 
            "NO SIGNAL", 
            (150, 180), 
            cv2.FONT_HERSHEY_COMPLEX, 
            0.8, 
            (0, 0, 255), 
            2
        )
        cv2.putText(
            self.black_frame, 
            f"CAM_{self.index+1}", 
            (170, 220), 
            cv2.FONT_HERSHEY_COMPLEX, 
            0.5, 
            (255, 255, 255), 
            1
        )
    
    def _get_frame(self):
        """Get current frame or black frame"""
        return self.frame if self.frame is not None else self.black_frame
    
    def run(self):
        """Main stream loop"""
        while self.running:
            if not self.url:
                self.status = "No URL"
                time.sleep(1)
                continue
            
            try:
                # Open video capture
                cap = cv2.VideoCapture(self.url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
                cap.set(cv2.CAP_PROP_FPS, 30)
                
                self.connected = True
                self.status = "Connected"
                self.reconnect_attempts = 0
                cprint(f"[+] Camera {self.name} connected", Colors.GREEN)
                
                while cap.isOpened() and self.running:
                    ret, frame = cap.read()
                    
                    if ret:
                        # Resize frame
                        resized_frame = cv2.resize(frame, (480, 360))
                        
                        # Add overlay (if not stealth mode)
                        if not self.stealth:
                            self._add_overlay(resized_frame)
                        
                        self.frame = resized_frame
                        self.frame_count += 1
                        self.connected = True
                        self.status = "Streaming"
                        
                        # Update FPS
                        if time.time() - self.last_fps_update >= 1:
                            self.fps = self.frame_count
                            self.frame_count = 0
                            self.last_fps_update = time.time()
                        
                    else:
                        self.frame = None
                        self.connected = False
                        self.status = "Reconnecting..."
                        break
                    
                    time.sleep(0.03)  # ~30 FPS
                
                cap.release()
                
                # Handle disconnect
                if self.running:
                    self.reconnect_attempts += 1
                    if self.reconnect_attempts <= self.max_reconnect:
                        cprint(f"[*] Camera {self.name} reconnecting... ({self.reconnect_attempts}/{self.max_reconnect})", Colors.YELLOW)
                        time.sleep(2)
                    else:
                        self.status = "Failed"
                        cprint(f"[-] Camera {self.name} connection failed", Colors.RED)
                        time.sleep(10)  # Longer cooldown
                    
            except Exception as e:
                self.error_message = str(e)
                self.status = "Error"
                cprint(f"[-] Camera {self.name} error: {e}", Colors.RED)
                time.sleep(5)
    
    def _add_overlay(self, frame):
        """Add overlay to frame"""
        # Camera name overlay
        cv2.putText(
            frame, 
            f"[{self.name}]", 
            (10, 30), 
            cv2.FONT_HERSHEY_COMPLEX, 
            0.6, 
            (0, 255, 255), 
            2
        )
        
        # Status indicator (blinking dot)
        if int(time.time()) % 2 == 0:
            cv2.circle(frame, (450, 25), 8, (0, 255, 0), -1)
        else:
            cv2.circle(frame, (450, 25), 8, (0, 0, 255), -1)
        
        # Timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(
            frame, 
            timestamp, 
            (10, 340), 
            cv2.FONT_HERSHEY_COMPLEX, 
            0.5, 
            (255, 255, 255), 
            1
        )
        
        # FPS
        cv2.putText(
            frame, 
            f"{self.fps} FPS", 
            (400, 340), 
            cv2.FONT_HERSHEY_COMPLEX, 
            0.5, 
            (0, 255, 0), 
            1
        )
    
    def get_frame(self):
        """Get current frame for display"""
        if self.frame is not None:
            return self.frame
        else:
            # Update no signal frame with status
            status_frame = self.black_frame.copy()
            cv2.putText(
                status_frame, 
                self.status, 
                (150, 260), 
                cv2.FONT_HERSHEY_COMPLEX, 
                0.5, 
                (0, 255, 255), 
                1
            )
            return status_frame
    
    def stop(self):
        """Stop the stream"""
        self.running = False

# ==================== VIDEO MATRIX ====================
class VideoMatrix:
    """Multi-camera surveillance matrix dashboard"""
    
    def __init__(self, camera_urls=None, stealth=False):
        self.camera_urls = camera_urls or []
        self.stealth = stealth
        self.threads = []
        self.running = True
        self.matrix_window = "ARGUS-EYE C2 MATRIX"
        
        # Initialize cameras
        self._init_cameras()
        
        # Start matrix display
        self._start_display()
    
    def _init_cameras(self):
        """Initialize camera streams"""
        if not self.camera_urls:
            # Try to get cameras from network discovery
            self._discover_cameras()
        
        for idx, url in enumerate(self.camera_urls):
            if isinstance(url, dict):
                name = url.get('name', f'CAM_{idx+1}')
                url = url.get('url', '')
            else:
                name = f'CAM_{idx+1}'
            
            stream = CameraStreamer(url, name, idx, self.stealth)
            stream.daemon = True
            stream.start()
            self.threads.append(stream)
            time.sleep(0.5)  # Stagger startup
    
    def _discover_cameras(self):
        """Discover cameras via ONVIF or RTSP scan"""
        cprint("[*] Discovering cameras via ONVIF...", Colors.YELLOW)
        
        try:
            # Try ONVIF discovery
            from field_standardized import FieldStandardizedEngine
            import asyncio
            
            engine = FieldStandardizedEngine()
            cameras = asyncio.run(engine.scan_cameras())
            
            for ip in cameras:
                rtsp_url = f"rtsp://{ip}/live"
                self.camera_urls.append(rtsp_url)
                cprint(f"[+] Camera discovered: {ip}", Colors.GREEN)
                
        except Exception as e:
            cprint(f"[!] ONVIF discovery failed: {e}", Colors.YELLOW)
            
            # Fallback: try common RTSP URLs
            fallback_urls = [
                "rtsp://192.168.1.100/live",
                "rtsp://192.168.1.101/live",
                "rtsp://192.168.1.102/live",
                "rtsp://192.168.1.103/live",
                "rtsp://192.168.1.104/live",
            ]
            self.camera_urls.extend(fallback_urls)
            cprint("[*] Using fallback RTSP URLs", Colors.DIM)
    
    def _start_display(self):
        """Start the matrix display"""
        cprint("\n[+] Matrix display started. Press 'q' to quit.", Colors.GREEN)
        cprint("[*] Camera feeds loading...", Colors.DIM)
        
        # Create window
        cv2.namedWindow(self.matrix_window, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(
            self.matrix_window,
            cv2.WND_PROP_FULLSCREEN,
            cv2.WINDOW_FULLSCREEN
        )
        
        try:
            while self.running:
                # Get frames from all cameras
                frames = []
                for stream in self.threads:
                    frames.append(stream.get_frame())
                
                # Build matrix grid
                matrix = self._build_matrix(frames)
                
                # Display
                cv2.imshow(self.matrix_window, matrix)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == ord('Q'):
                    break
                elif key == ord('f') or key == ord('F'):
                    self._toggle_fullscreen()
                elif key == ord('s') or key == ord('S'):
                    self._save_screenshot(matrix)
                
                time.sleep(0.03)  # ~30 FPS
                
        except KeyboardInterrupt:
            cprint("\n[!] Interrupted by user", Colors.YELLOW)
        finally:
            self.cleanup()
    
    def _build_matrix(self, frames):
        """Build 2x3 matrix grid"""
        # Ensure we have 6 frames (pad with black if needed)
        while len(frames) < 6:
            black = np.zeros((360, 480, 3), dtype=np.uint8)
            cv2.putText(black, "NO CAMERA", (150, 180), cv2.FONT_HERSHEY_COMPLEX, 0.7, (255, 255, 255), 2)
            frames.append(black)
        
        # Trim to 6
        frames = frames[:6]
        
        # Build grid: 2 rows x 3 columns
        row1 = np.hstack(frames[:3])
        row2 = np.hstack(frames[3:6])
        
        # Add status bar
        status_bar = np.zeros((40, row1.shape[1], 3), dtype=np.uint8)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            status_bar, 
            f"ARGUS-EYE v2.0 | {timestamp} | Cameras: {len(self.threads)} | Press 'q' to quit", 
            (10, 25), 
            cv2.FONT_HERSHEY_COMPLEX, 
            0.5, 
            (0, 255, 0), 
            1
        )
        
        # Combine
        matrix = np.vstack([status_bar, row1, row2])
        return matrix
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        try:
            fullscreen = cv2.getWindowProperty(
                self.matrix_window,
                cv2.WND_PROP_FULLSCREEN
            )
            
            if fullscreen == cv2.WINDOW_FULLSCREEN:
                cv2.setWindowProperty(
                    self.matrix_window,
                    cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_NORMAL
                )
            else:
                cv2.setWindowProperty(
                    self.matrix_window,
                    cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_FULLSCREEN
                )
        except:
            pass
    
    def _save_screenshot(self, frame):
        """Save screenshot of matrix"""
        filename = f"matrix_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        cv2.imwrite(filename, frame)
        cprint(f"[+] Screenshot saved: {filename}", Colors.GREEN)
    
    def cleanup(self):
        """Cleanup resources"""
        cprint("\n[*] Cleaning up camera streams...", Colors.YELLOW)
        
        for stream in self.threads:
            stream.stop()
            stream.join(timeout=2)
        
        cv2.destroyAllWindows()
        cprint("[+] Cleanup complete", Colors.GREEN)

# ==================== MAIN ====================
def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Video Matrix v2.0")
    parser.add_argument("-c", "--cameras", help="Camera URLs (comma separated)")
    parser.add_argument("-f", "--file", help="Camera config file (JSON)")
    parser.add_argument("-s", "--stealth", action="store_true", help="Stealth mode")
    parser.add_argument("-d", "--discover", action="store_true", help="Auto-discover cameras")
    
    args = parser.parse_args()
    
    # Show banner
    print("="*60)
    cprint(" VIDEO MATRIX v2.0", Colors.PURPLE, bold=True)
    cprint(" Tactical C2 Surveillance Dashboard", Colors.CYAN)
    print("="*60)
    
    # Get camera URLs
    camera_urls = []
    
    if args.file and os.path.exists(args.file):
        with open(args.file, 'r') as f:
            data = json.load(f)
            camera_urls = data.get('cameras', [])
        cprint(f"[*] Loaded {len(camera_urls)} cameras from {args.file}", Colors.GREEN)
    
    elif args.cameras:
        camera_urls = [url.strip() for url in args.cameras.split(',')]
        cprint(f"[*] Using {len(camera_urls)} cameras", Colors.GREEN)
    
    elif args.discover:
        # Will auto-discover
        pass
    
    else:
        # Default: try to discover
        cprint("[*] No cameras specified. Attempting discovery...", Colors.YELLOW)
    
    # Start matrix
    matrix = VideoMatrix(camera_urls, stealth=args.stealth)

if __name__ == "__main__":
    main()
