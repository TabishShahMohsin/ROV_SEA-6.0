import socket
import threading
import time
import json
import subprocess
from gpiozero import CPUTemperature
import pigpio
import cv2
import imagezmq
import pyrealsense2 as rs
import numpy as np
import ms5837
from picamera2 import Picamera2
from imu import IMU

# Initialize IMU
imu_sensor = IMU(port='/dev/ttyUSB0') # Check your port with v4l2-ctl or dmesg
imu_sensor.start()

sensor = ms5837.MS5837_30BA()
sensor.init()

cpu = CPUTemperature()

# --- Configuration ---
# PC_IP = "192.168.137.1"  # Replace with your Base Station IP
# PC_IP = socket.gethostbyname("laptop.local")
# PC_IP = "192.168.0.113"
PC_IP = socket.gethostbyname('mba.local')
PI_IP = "0.0.0.0"        
UDP_PORT_DATA = 5005    
UDP_PORT_CMD = 5006     

# --- Ramping Constants ---
RAMP_STEP = 15        # How many Âµs to change per loop iteration
LOOP_FREQ = 0.05      # 20Hz update (50ms)

# Global PWM States
# target_pwms: what the base station is asking for
# current_pwms: what is actually being sent to the ESCs right now
target_pwms = {f"t{i}": 1500 for i in range(1, 9)}
current_pwms = {f"t{i}": 1500 for i in range(1, 9)}

telemetry = {
    "pressure": 1013.25,
    "depth": 0,
    "cpu_temp": cpu.temperature,
    "ps_temp": 0,
    "timestamp":0,
    "roll": 0,
    "pitch": 0,   
    "yaw": 0     
}

try:
    subprocess.run(['sudo', 'pigpiod'], check=True, capture_output=True, text=True)
    print("pigpiod started successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error starting pigpiod: {e.stderr}")

THRUSTER_PINS = {
    "t1": 18, "t2": 23, "t3": 17, "t4": 27, 
    "t5": 20, "t6": 13, "t7": 19, "t8": 6  
}

pi = pigpio.pi()
if not pi.connected:
    exit()

last_command_time = time.time()
is_running = True

SENDER = imagezmq.ImageSender(connect_to=f'tcp://{PC_IP}:5555')
HOSTNAME = socket.gethostname()

def video_stream_loop():
    """Thread to capture from RealSense and PiCam using native Picamera2."""
    # 1. Initialize RealSense
    pipeline = rs.pipeline()
    rs_config = rs.config()
    rs_config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    # 2. Initialize PiCam via native Picamera2 (The working way!)
    picam2 = Picamera2()
    pc_config = picam2.create_preview_configuration(main={"size": (640, 480)})
    picam2.configure(pc_config)
    picam2.start()

    try:
        pipeline.start(rs_config)
        print("RealSense and PiCam (Native) streams started.")
    except Exception as e:
        print(f"Camera Startup Error: {e}")

    while is_running:
        try:
            # --- Handle RealSense ---
            frames = pipeline.wait_for_frames(timeout_ms=50) # Lower timeout
            color_frame = frames.get_color_frame()
            if color_frame:
                realsense_img = np.asanyarray(color_frame.get_data())
                SENDER.send_image(f"{HOSTNAME}_realsense", realsense_img)

            # --- Handle PiCam (Native Capture) ---
            # capture_array() returns RGB, so we convert to BGR for the Base Station
            frame_rgb = picam2.capture_array()
            picam_img = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            
            if picam_img is not None:
                SENDER.send_image(f"{HOSTNAME}_picam", picam_img)

        except Exception as e:
            # print(f"Streaming Error: {e}")
            time.sleep(0.01)
            continue

    pipeline.stop()
    picam2.stop()

# --- Ramping Functions ---

def ramping_loop():
    """Background thread that smoothly transitions current_pwms to target_pwms."""
    global current_pwms
    while is_running:
        for key in target_pwms:
            target = target_pwms[key]
            current = current_pwms[key]
            
            if current < target:
                current_pwms[key] = min(current + RAMP_STEP, target)
            elif current > target:
                current_pwms[key] = max(current - RAMP_STEP, target)
            
            # Apply the current (ramped) value to the GPIO
            pwm_val = max(1100, min(1900, current_pwms[key]))
            pi.set_servo_pulsewidth(THRUSTER_PINS[key], pwm_val)
            
        time.sleep(LOOP_FREQ)

def stop_all_thrusters():
    """Sets targets and current values back to neutral immediately."""
    print("!!! STOPPING ALL THRUSTERS (NEUTRAL) !!!")
    for key in target_pwms:
        target_pwms[key] = 1500
        current_pwms[key] = 1500
        pi.set_servo_pulsewidth(THRUSTER_PINS[key], 1500)

def sensor_sender():
    sock = None
    while is_running:
        try:
            if sock is None:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sensor.read()
            roll, pitch, yaw = imu_sensor.get_angles()
            telemetry_data = {
                "pressure": sensor.pressure(),
                "cpu_temp": cpu.temperature,
                "timestamp": time.time(),
                "depth": sensor.depth(),
                "water_temp": sensor.temperature(),
                "roll": roll,
                "pitch": pitch,   
                "yaw": yaw     
            }
            
            message = json.dumps(telemetry_data).encode()
            sock.sendto(message, (PC_IP, UDP_PORT_DATA))
        except Exception as e:
            print(f"Sensor Socket Error: {e}. Retrying...")
            if sock: sock.close()
            sock = None # Force recreation
        time.sleep(0.1)

def command_receiver():
    global last_command_time, target_pwms
    sock = None
    
    while is_running:
        try:
            if sock is None:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((PI_IP, UDP_PORT_CMD))
                sock.settimeout(0.5)
            
            data, addr = sock.recvfrom(1024)
            new_cmds = json.loads(data.decode())
            for key, val in new_cmds.items():
                if key in target_pwms:
                    target_pwms[key] = val
            last_command_time = time.time()

        except socket.timeout:
            continue
        except Exception as e:
            print(f"Command Socket Error: {e}. Re-binding...")
            if sock: sock.close()
            sock = None
            time.sleep(1) # Wait before trying to re-bind

# --- Main Logic ---
try:
    stop_all_thrusters()
    
    t_sender = threading.Thread(target=sensor_sender, daemon=True)
    t_receiver = threading.Thread(target=command_receiver, daemon=True)
    t_ramper = threading.Thread(target=ramping_loop, daemon=True)
    t_video = threading.Thread(target=video_stream_loop, daemon=True)

    t_sender.start()
    t_receiver.start()
    t_ramper.start()
    t_video.start()

    while True:
        # Get actual hardware PWM values for display
        p = [pi.get_servo_pulsewidth(THRUSTER_PINS[f"t{i}"]) for i in range(1, 9)]
        p_curr = 1013.25 # Placeholder
        depth = 0.0      # Placeholder

        if time.time() - last_command_time > 1.0:
            stop_all_thrusters()
            print("Warning: Connection lost. Idling thrusters...", end='\r')
        else:
            status_msg = f"D:{depth:>5.2f}m | CPU:{cpu.temperature:>4.1f}C"
            dashboard = (
                f"CURR_PWM:[{p[0]:>4} {p[1]:>4} {p[2]:>4} {p[3]:>4}] | "
                f"V_PWM:[{p[4]:>4} {p[5]:>4} {p[6]:>4} {p[7]:>4}] | {status_msg}"
            )
            print(f"{dashboard:<150}", end='\r', flush=True)
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nShutting down script.")
finally:
    is_running = False
    stop_all_thrusters()
    pi.stop()
