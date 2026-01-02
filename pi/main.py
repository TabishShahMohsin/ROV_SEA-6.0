import socket
import threading
import time
import json
import subprocess
from gpiozero import CPUTemperature
import pigpio

cpu = CPUTemperature()

# --- Configuration ---
# PC_IP = "192.168.137.1"  # Replace with your Base Station IP
PC_IP = "10.51.148.179"  
# PC_IP = "10.38.254.107"
PI_IP = "0.0.0.0"        
UDP_PORT_DATA = 5005    
UDP_PORT_CMD = 5006     

# --- Ramping Constants ---
RAMP_STEP = 15        # How many µs to change per loop iteration
LOOP_FREQ = 0.05      # 20Hz update (50ms)

# Global PWM States
# target_pwms: what the base station is asking for
# current_pwms: what is actually being sent to the ESCs right now
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

def sensor_sender():
    sock = None
    while is_running:
        try:
            if sock is None:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            telemetry_data = {
                "pressure": 1013.25,
                "temp": cpu.temperature,
                "timestamp": time.time()
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
    
    t_sender.start()
    t_receiver.start()
    t_ramper.start()

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