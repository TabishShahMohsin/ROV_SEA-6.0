import socket
import threading
import time
import json
import subprocess
from gpiozero import CPUTemperature
import pigpio
import os
import cv2
import imagezmq
import numpy as np
import pyrealsense2 as rs
from picamera2 import Picamera2
import simplejpeg

cpu = CPUTemperature()

# --- Configuration ---
PC_IP = "10.51.148.179"  
PI_IP = "0.0.0.0"        
UDP_PORT_DATA = 5005    
UDP_PORT_CMD = 5006
CAMERA_PORT = 5555
JPEG_QUALITY = 95

# Silence camera logs
os.environ["LIBCAMERA_LOG_LEVELS"] = "3"

# --- Ramping Constants --- (To Edit)
RAMP_STEP = 15        
LOOP_FREQ = 0.05      

# Global PWM States
target_pwms = {f"t{i}": 1500 for i in range(1, 9)}
current_pwms = {f"t{i}": 1500 for i in range(1, 9)}

telemetry = {
    "pressure": 1013.25,
    "temp": cpu.temperature,
    "timestamp": time.time()
}

try:
    subprocess.run(['sudo', 'pigpiod'], check=True, capture_output=True, text=True)
    print("pigpiod started successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error starting pigpiod: {e.stderr}")

THRUSTER_PINS = {
    "t1": 17, "t2": 18, "t3": 27, "t4": 22, 
    "t5": 23, "t6": 24, "t7": 25, "t8": 8  
}

pi = pigpio.pi()
if not pi.connected:
    exit()

last_command_time = time.time()
is_running = True

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

# --- Background Threads ---
def sensor_sender():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while is_running:
        telemetry_data = {
            "pressure": 1013.25,
            "temp": cpu.temperature,
            "timestamp": time.time()
        }
        try:
            message = json.dumps(telemetry_data).encode()
            sock.sendto(message, (PC_IP, UDP_PORT_DATA))
        except Exception as e:
            print(f"Sensor error: {e}")
        time.sleep(0.1) 

def command_receiver():
    global last_command_time, target_pwms
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(0.5)
    sock.bind((PI_IP, UDP_PORT_CMD))
    
    while is_running:
        try:
            data, addr = sock.recvfrom(1024)
            new_cmds = json.loads(data.decode())
            for key, val in new_cmds.items():
                if key in target_pwms:
                    target_pwms[key] = val
            last_command_time = time.time()
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Command error: {e}")

def camera_streamer():
    """thread for camera streaming using the second script's logic."""
    print(f"Camera Thread: Connecting to Base Station at {PC_IP}:{CAMERA_PORT}...")
    
    try:
        sender = imagezmq.ImageSender(connect_to=f"tcp://{PC_IP}:{CAMERA_PORT}")
        print("  [SUCCESS] Camera connected.")
    except Exception as e:
        print(f"  [FAILURE] Camera Network Error: {e}")
        return
    
    # Setup Pi Camera
    print("Camera Thread: Initializing Pi Camera...")
    picam2 = None
    try:
        picam2 = Picamera2()
        config = picam2.create_video_configuration(
            main={"size": (640, 480), "format": "BGR888"}
        )
        picam2.configure(config)
        picam2.start()
        print("  [SUCCESS] Pi Camera initialized.")
    except Exception as e:
        print(f"  [FAILURE] Pi Cam Error: {e}")
        picam2 = None
    
    # Setup RealSense
    print("Camera Thread: Initializing RealSense...")
    rs_pipeline = None
    try:
        rs_pipeline = rs.pipeline()
        rs_config = rs.config()
        rs_config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        rs_pipeline.start(rs_config)
        print("  [SUCCESS] RealSense initialized.")
    except Exception as e:
        print(f"  [FAILURE] RealSense Error: {e}")
        rs_pipeline = None
    
    if picam2 is None and rs_pipeline is None:
        print("Camera Thread: CRITICAL - Both cameras failed. Thread exiting.")
        return
    
    print("Camera Thread: Starting stream...")
    
    try:
        while is_running:
            # Pi Camera
            if picam2:
                try:
                    pi_frame = picam2.capture_array()
                    jpg_buffer = simplejpeg.encode_jpeg(
                        pi_frame, 
                        quality=JPEG_QUALITY, 
                        colorspace='RGB', 
                        fastdct=True
                    )
                    sender.send_jpg("PiCam_Feed", jpg_buffer)
                except Exception as e:
                    print(f"Camera Thread: PiCam error - {e}")
            
            # RealSense
            if rs_pipeline:
                try:
                    frames = rs_pipeline.poll_for_frames()
                    if frames:
                        color_frame = frames.get_color_frame()
                        if color_frame:
                            rs_image = np.asanyarray(color_frame.get_data())
                            rs_jpg = simplejpeg.encode_jpeg(
                                rs_image, 
                                quality=JPEG_QUALITY, 
                                colorspace='BGR', 
                                fastdct=True
                            )
                            sender.send_jpg("RealSense_Feed", rs_jpg)
                except Exception as e:
                    print(f"Camera Thread: RealSense error - {e}")
                    
    except Exception as e:
        print(f"Camera Thread: Fatal error - {e}")
    finally:
        print("Camera Thread: Cleaning up...")
        if picam2: 
            picam2.stop()
        if rs_pipeline: 
            rs_pipeline.stop()

# --- Main Logic ---
try:
    stop_all_thrusters()
    
    t_sender = threading.Thread(target=sensor_sender, daemon=True)
    t_receiver = threading.Thread(target=command_receiver, daemon=True)
    t_ramper = threading.Thread(target=ramping_loop, daemon=True)
    t_camera = threading.Thread(target=camera_streamer, daemon=True)
    
    t_sender.start()
    t_receiver.start()
    t_ramper.start()
    t_camera.start()
    
    print("\n--- All threads started ---")

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