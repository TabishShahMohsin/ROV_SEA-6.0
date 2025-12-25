import socket
import threading
import time
import json
import subprocess

# --- Configuration ---
PC_IP = "192.168.1.10"  # Replace with your Base Station IP
PI_IP = "0.0.0.0"       # Listen on all interfaces
UDP_PORT_DATA = 5005    # Pi -> PC (Sensors)
UDP_PORT_CMD = 5006     # PC -> Pi (Thrusters)

# --- Start Video Streams (GStreamer) ---
# This runs in the background. Adjust /dev/video0 and /dev/video1 for your cameras.
subprocess.Popen(f"gst-launch-1.0 v4l2src device=/dev/video0 ! video/x-h264,width=640,height=480 ! rtph264pay ! udpsink host={PC_IP} port=5000", shell=True)
subprocess.Popen(f"gst-launch-1.0 v4l2src device=/dev/video1 ! video/x-h264,width=640,height=480 ! rtph264pay ! udpsink host={PC_IP} port=5001", shell=True)

def sensor_sender():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        # Mocking sensor data - Replace with your actual sensor library (e.g., ms5837)
        telemetry = {
            "pressure": 1013.25,
            "temp": 22.5,
            "depth": 1.2
        }
        message = json.dumps(telemetry).encode()
        sock.sendto(message, (PC_IP, UDP_PORT_DATA))
        time.sleep(0.1) # 10Hz update rate

def command_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((PI_IP, UDP_PORT_CMD))
    while True:
        data, addr = sock.recvfrom(1024)
        commands = json.loads(data.decode())
        # Example: commands = {"t1": 1500, "t2": 1500...}
        # Update your PWM pins here (e.g., using pigpio or RPi.GPIO)
        print(f"Setting Thrusters: {commands}")

# Start Threads
threading.Thread(target=sensor_sender, daemon=True).start()
threading.Thread(target=command_receiver, daemon=True).start()

# Keep main thread alive
while True:
    time.sleep(1)