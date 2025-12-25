import socket
import threading
import json
import time

PI_IP = "192.168.1.11" # Replace with your Pi's IP
UDP_PORT_DATA = 5005
UDP_PORT_CMD = 5006

def telemetry_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT_DATA))
    while True:
        data, addr = sock.recvfrom(1024)
        telemetry = json.loads(data.decode())
        print(f"ROV Status: {telemetry}")

def command_sender():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        # Here you would read your joystick or keyboard
        # 1500 is typically 'Neutral' for most ESCs
        pwm_commands = {"t1": 1600, "t2": 1450, "t3": 1500, "t4": 1500}
        sock.sendto(json.dumps(pwm_commands).encode(), (PI_IP, UDP_PORT_CMD))
        time.sleep(0.05) # 20Hz control loop

# Start Threads
threading.Thread(target=telemetry_listener, daemon=True).start()
threading.Thread(target=command_sender, daemon=True).start()

while True:
    time.sleep(1)