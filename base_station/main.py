import pygame
import numpy as np
import time
import json
import socket
import threading
from config import *
from input_handler import JoystickController
from rov_kinematics import compute_thruster_forces, map_force_to_pwm
from pid import PID
from kf import DepthKalmanFilter

# It takes IMU 10s to start
# for i in range(11):
#     print(f"Starting CountDown: {11 - i}")
#     time.sleep(1) 

shared_data = {
    # Shared from base station to pi
    "pwms": [1500] * 8,
    "running": True,
    # Shared from pi to base station
    "cpu_temp": 0,
    "timestamp": 0, # Heart beat
    "pressure": 0, 
    "depth": 0,
    "water_temp": 0,
    "roll": 0,
    "pitch": 0,   
    "yaw": 0     
}

def command_sender():
    """Sends PWM commands at a steady frequency."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Allows the port to be reused immediately after a crash
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    print("[Thread] Command Sender started.")
    while shared_data["running"]:
        try:
            pwms = shared_data["pwms"]
            pwm_commands = {
                "t1": invert_pwm(pwms[0], I1), "t2": invert_pwm(pwms[1], I2), 
                "t3": invert_pwm(pwms[2], I3), "t4": invert_pwm(pwms[3], I4),
                "t5": invert_pwm(pwms[4], I5), "t6": invert_pwm(pwms[5], I6),
                "t7": invert_pwm(pwms[6], I7), "t8": invert_pwm(pwms[7], I8),
            }
            sock.sendto(json.dumps(pwm_commands).encode(), (PI_IP, UDP_PORT_CMD))
            time.sleep(0.05)  # 20Hz
        except Exception as e:
            print(f"Sender Error: {e}")
            time.sleep(1)

def telemetry_listener():
    """Listens for ROV feedback."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind(("0.0.0.0", UDP_PORT_DATA))
        sock.settimeout(1.0) # Don't block forever if no data comes
    except OSError as e:
        print(f"Binding Error: {e}")
        return

    print("[Thread] Telemetry Listener started.")
    while shared_data["running"]:
        try:
            data, addr = sock.recvfrom(1024)
            telemetry = json.loads(data.decode())
            shared_data['cpu_temp'] = telemetry['cpu_temp']
            shared_data['timestamp'] = telemetry['timestamp']
            shared_data['pressure'] = telemetry['pressure']
            shared_data['depth'] = telemetry['depth']
            shared_data['water_temp'] = telemetry['water_temp']
            shared_data['roll'] = telemetry['roll']
            shared_data['pitch'] = telemetry['pitch']
            shared_data['yaw'] = telemetry['yaw']
            # In a real app, you'd save this to a global for the HUD to draw
            # print(f"ROV Status: {telemetry}") 
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Listener Error: {e}")


def main():
    pygame.init()
    screen = pygame.display.set_mode((400, 300))
    clock = pygame.time.Clock()

    try:
        controller = JoystickController(deadzone=0.1)
    except RuntimeError as e:
        print(e)
        pygame.quit()
        return

    kf = DepthKalmanFilter()

    depth_pid = PID(1.2, 0.1, 0.4, 1, -1)
    target_depth = 0

    target_roll = 0
    target_pitch = 0
    target_yaw = 0

    thread1 = threading.Thread(target=telemetry_listener, daemon=True)
    thread2 = threading.Thread(target=command_sender, daemon=True)
    thread1.start()
    thread2.start()

    running = True
    while running:
        dt = clock.tick(30)/1000

        # Handle quit event
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        p_curr = shared_data["pressure"]
        raw_depth = max(0, (p_curr - 1013.25) * 100 / (1025 * 9.81))
        measured_depth = kf.update(raw_depth, dt)

        # Read joystick input
        raw_inputs = controller.get_input_vector()
        raw_surge, raw_sway, raw_heave, raw_roll, raw_pitch, raw_yaw = raw_inputs

        # --- HEAVE CONTROL LOGIC ---
        target_depth += raw_heave * 0.5 * dt
        heave_command = depth_pid.compute(measured_depth, target_depth, dt)

        # Get thruster force distribution
        thruster_forces = compute_thruster_forces(raw_surge, raw_sway, heave_command, raw_roll, raw_pitch, raw_yaw)

        # Convert forces to PWM
        thruster_pwms = [map_force_to_pwm(f) for f in thruster_forces]
        shared_data['pwms'] = thruster_pwms

        p = shared_data["pwms"]
        pi_temp = shared_data["water_temp"]
        f = thruster_forces
        
        dashboard = (
            f"\033[H"  # Move cursor to top-left (Home)
            f"--- ROV_SEA-6.0 DASHBOARD ---\n"
            f"SYSTEM: Pressure: {p_curr:>7.2f} mb | Pi Temp: {pi_temp:>4.1f}°C\n"
            f"{'-'*60}\n"
            f"THRUSTERS (Forces & PWMs):\n"
            f"  Horizontal: T1:{f[0]:>6.2f}({p[0]}) T2:{f[1]:>6.2f}({p[1]}) T3:{f[2]:>6.2f}({p[2]}) T4:{f[3]:>6.2f}({p[3]})\n"
            f"  Vertical:   T5:{f[4]:>6.2f}({p[4]}) T6:{f[5]:>6.2f}({p[5]}) T7:{f[6]:>6.2f}({p[6]}) T8:{f[7]:>6.2f}({p[7]})\n"
            f"{'-'*60}\n"
            f"NAVIGATION:      {'[SETPOINT]':<15} {'[MEASURED]':<15}\n"
            f"  Depth (m):     {target_depth:>15.2f} {shared_data['depth']:>15.2f}\n"
            f"  Roll  (°):     {target_roll:>15.2f} {shared_data['roll']:>15.2f}\n"
            f"  Pitch (°):     {target_pitch:>15.2f} {shared_data['pitch']:>15.2f}\n"
            f"  Yaw   (°):     {target_yaw:>15.2f} {shared_data['yaw']:>15.2f}\n"
            f"{'-'*60}\n"
            f"Status: RUNNING | Frequency: {clock.get_fps():.1f} FPS"
        )

        # Clear screen once at start or just use the Home cursor trick
        print(dashboard, end='', flush=True)


    # On exit: stop thrusters safely
    pygame.quit()
    shared_data["running"] = False
    print("\nSimulation exited.")

if __name__ == "__main__":
    main()
