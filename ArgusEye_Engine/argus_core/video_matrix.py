import cv2
import threading
import time
import numpy as np
import os

class CameraStreamer(threading.Thread):
    def __init__(self, url, name):
        super().__init__()
        self.url = url
        self.name = name
        self.frame = None
        self.running = True
        # Initialize an empty tactical canvas awaiting transmission input
        self.black_frame = np.zeros((360, 480, 3), dtype=np.uint8)
        cv2.putText(self.black_frame, "SEARCHING SIGNAL...", (90, 180), 
                    cv2.FONT_HERSHEY_COMPLEX, 0.7, (0, 0, 255), 2)

    def run(self):
        while self.running:
            if not self.url:
                time.sleep(1)
                continue
                
            cap = cv2.VideoCapture(self.url)
            # Set hardware buffer size to minimum to eliminate stream lag
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            while cap.isOpened() and self.running:
                ret, frame = cap.read()
                if ret:
                    resized_frame = cv2.resize(frame, (480, 360))
                    
                    # Inject cryptographic signature overlay onto captured lens
                    cv2.putText(resized_frame, f"[HIJACKED - {self.name}]", (10, 30), 
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (0, 0, 255), 2)
                    
                    # Generate real-time telemetry beacon animation
                    if int(time.time()) % 2 == 0:
                        cv2.circle(resized_frame, (450, 25), 8, (0, 0, 255), -1)
                        
                    self.frame = resized_frame
                else:
                    self.frame = None
                    break
                time.sleep(0.03) # Cap system resource usage at ~30 FPS
            cap.release()
            time.sleep(1) # Automated reconnection loop upon packet dropped

    def get_frame(self):
        return self.frame if self.frame is not None else self.black_frame

    def stop(self):
        self.running = False


def get_dynamic_camera_ips():
    """Parse dnsmasq leases dynamically to find hijacked camera targets"""
    leases_file = "/var/lib/misc/dnsmasq.leases"
    ips = []
    if os.path.exists(leases_file):
        try:
            with open(leases_file, "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3:
                        ips.append(parts[2]) # Extract allocated IP
        except Exception:
            pass
    return ips


def main():
    print("[*] Launching Tactical Video Matrix Console (Argus-Matrix)...")
    
    # Initialize 5 threads with placeholder placeholders
    threads = []
    for i in range(5):
        t = CameraStreamer(None, f"CAM_0{i+1}")
        t.start()
        threads.append(t)

    print("[+] Transmission links activated. Output stream routed to HDMI interface...")

    logo_frame = np.zeros((360, 480, 3), dtype=np.uint8)
    cv2.putText(logo_frame, "ARGUS-EYE SYSTEM", (100, 150), cv2.FONT_HERSHEY_COMPLEX, 0.7, (0, 255, 65), 2)
    cv2.putText(logo_frame, "TACTICAL COUNTER-MEASURE", (60, 200), cv2.FONT_HERSHEY_COMPLEX, 0.6, (255, 255, 255), 1)

    window_name = "ARGUS-EYE C2 VIDEO MATRIX"
    cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    try:
        while True:
            # Dynamically discover and update stream destinations
            active_ips = get_dynamic_camera_ips()
            for idx, t in enumerate(threads):
                if idx < len(active_ips) and t.url is None:
                    # Map the found IP into the RTSP routing URL structure
                    t.url = f"rtsp://{active_ips[idx]}/live"

            f1 = threads[0].get_frame()
            f2 = threads[1].get_frame()
            f3 = threads[2].get_frame()
            f4 = threads[3].get_frame()
            f5 = threads[4].get_frame()
            
            row1 = np.hstack((f1, f2, f3))
            row2 = np.hstack((f4, f5, logo_frame))
            matrix = np.vstack((row1, row2))

            cv2.imshow(window_name, matrix)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        pass
    finally:
        print("[*] Revoking network streams and clearing hardware context...")
        for t in threads:
            t.stop()
            t.join()
        cv2.destroyAllWindows()
        print("[+] Environment de-allocated safely.")

if __name__ == "__main__":
    main()