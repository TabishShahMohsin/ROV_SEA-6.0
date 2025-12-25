import socket
import threading
import time
import json
import subprocess
import pigpio

# --- Configuration ---
PC_IP = "192.168.1.10"  # Replace with your Base Station IP
PI_IP = "0.0.0.0"        
UDP_PORT_DATA = 5005    
UDP_PORT_CMD = 5006     

# Trying to automate even sudo pigpiod in a single script
try:
    subprocess.run(['sudo', 'pigpiod'], check=True, capture_output=True, text=True)
    print("pigpiod started successfully (or was already running).")
except subprocess.CalledProcessError as e:
    print(f"Error starting pigpiod: {e.stderr}")

# --- Hardware Setup (GPIO Pins) ---
# Adjust these to the physical pins connected to your ESC Signal wires
THRUSTER_PINS = {
    "t1": 17, 
    "t2": 18, 
    "t3": 27, 
    "t4": 22
}

# Initialize PiGPIO
pi = pigpio.pi()
if not pi.connected:
    print("Could not connect to pigpiod. Did you run 'sudo pigpiod'?")
    exit()

# Global state
last_command_time = time.time()
is_running = True

# --- Safety Functions ---
def set_thruster_pwm(commands):
    """Updates the physical PWM signals on the GPIO pins."""
    for key, pin in THRUSTER_PINS.items():
        if key in commands:
            pwm_val = commands[key]
            # Safety clamp to ensure values are within ESC limits
            pwm_val = max(1100, min(1900, pwm_val))
            pi.set_servo_pulsewidth(pin, pwm_val)

def stop_all_thrusters():
    """Immediately sets all thrusters to neutral (1500us)."""
    print("!!! STOPPING ALL THRUSTERS (NEUTRAL) !!!")
    for pin in THRUSTER_PINS.values():
        pi.set_servo_pulsewidth(pin, 1500)

# --- Start Video Streams ---
video_cmd0 = (
    f"gst-launch-1.0 v4l2src device=/dev/video0 ! "
    f"video/x-raw,width=640,height=480,framerate=30/1 ! "
    f"v4l2h264enc ! rtph264pay ! udpsink host={PC_IP} port=5000"
)
# Note: Use separate processes for multiple cameras
subprocess.Popen(video_cmd0, shell=True)

# --- Background Threads ---
def sensor_sender():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while is_running:
        # Replace with real sensor reads (e.g., ms5837 library)
        telemetry = {
            "pressure": 1013.25,
            "temp": 22.5,
            "depth": 1.2,
            "timestamp": time.time()
        }
        try:
            message = json.dumps(telemetry).encode()
            sock.sendto(message, (PC_IP, UDP_PORT_DATA))
        except Exception as e:
            print(f"Sensor error: {e}")
        time.sleep(0.1) 

def command_receiver():
    global last_command_time
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(0.5) # Don't hang if no commands come
    sock.bind((PI_IP, UDP_PORT_CMD))
    
    print("Receiver Ready. Waiting for commands...")
    
    while is_running:
        try:
            data, addr = sock.recvfrom(1024)
            commands = json.loads(data.decode())
            last_command_time = time.time()
            set_thruster_pwm(commands)
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Command error: {e}")

# --- Main Logic / Watchdog ---
try:
    # Initialize thrusters to neutral
    stop_all_thrusters()
    
    t_sender = threading.Thread(target=sensor_sender, daemon=True)
    t_receiver = threading.Thread(target=command_receiver, daemon=True)
    
    t_sender.start()
    t_receiver.start()

    while True:
        # HEARTBEAT WATCHDOG
        # If no command received for more than 1 second, stop for safety
        if time.time() - last_command_time > 1.0:
            stop_all_thrusters()
            print("Warning: Connection lost. Idling thrusters...", end='\r')
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nShutting down script.")
finally:
    is_running = False
    stop_all_thrusters()
    pi.stop() # Close connection to pigpiod