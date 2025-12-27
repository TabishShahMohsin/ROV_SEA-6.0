import pygame
import numpy as np
import time
import json
import socket
import threading
from config import *
from input_handler import JoystickController
from rov_kinematics import compute_thruster_forces, map_force_to_pwm
from drawing_utils import draw_rov, draw_thruster_vectors, draw_hud, draw_resultant_vector

shared_data = {
    "pwms": [1500] * 8,
    "running": True,
    "pressure": 1013.25, 
    "temp": 24.5,
    "timestamp": None
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
                "t1": pwms[0], "t2": pwms[1], 
                "t3": pwms[2], "t4": pwms[3],
                "t5": pwms[4], "t6": pwms[5],
                "t7": pwms[6], "t8": pwms[7],
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
            shared_data['pressure'] = telemetry['pressure']
            shared_data['temp'] = telemetry['temp']
            shared_data['timstamp'] = telemetry['timestamp']
            # In a real app, you'd save this to a global for the HUD to draw
            # print(f"ROV Status: {telemetry}") 
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Listener Error: {e}")


def main():
    pygame.init()

    # Initialize input
    try:
        controller = JoystickController(deadzone=0.1)
    except RuntimeError as e:
        print(e)
        pygame.quit()
        return


    # Initialize simulation window
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("ROV Thruster Allocation Simulation")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, FONT_SIZE)
    rov_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

    thread1 = threading.Thread(target=telemetry_listener, daemon=True)
    thread2 = threading.Thread(target=command_sender, daemon=True)
    thread1.start()
    thread2.start()

    running = True
    while running:
        # Handle quit event
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Read joystick input
        raw_inputs = controller.get_input_vector()
        raw_surge, raw_sway, raw_heave, raw_roll, raw_pitch, raw_yaw = raw_inputs

        # Get thruster force distribution
        thruster_forces = compute_thruster_forces(raw_surge, raw_sway, raw_heave, raw_roll, raw_pitch, raw_yaw)

        # Convert forces to PWM
        thruster_pwms = [map_force_to_pwm(f) for f in thruster_forces]
        shared_data['pwms'] = thruster_pwms

        telemetry_str = f"P:{shared_data['pressure']:.2f} T:{shared_data['temp']:.1f}"
        p_curr = shared_data["pressure"]
        depth = max(0, (p_curr - 1013.25) * 100 / (1025 * 9.81))
        p = shared_data["pwms"]
        pi_temp = shared_data["temp"]
        f = thruster_forces

        dashboard = (
            f"F_HOR:[{f[0]:>5.1f} {f[1]:>5.1f} {f[2]:>5.1f} {f[3]:>5.1f}] "
            f"PWM_H:[{p[0]:>4} {p[1]:>4} {p[2]:>4} {p[3]:>4}] | "
            f"F_VER:[{f[4]:>5.1f} {f[5]:>5.1f} {f[6]:>5.1f} {f[7]:>5.1f}] "
            f"PWM_V:[{p[4]:>4} {p[5]:>4} {p[6]:>4} {p[7]:>4}] | "
            f"D:{depth:>5.2f}m P:{p_curr:>7.2f}mb PI:{pi_temp:>4.1f}C"
        )

        # Debug output
        print(f"{dashboard:<180}", end='\r', flush=True)

        # Draw visuals
        screen.fill(BLACK)
        # draw_rov(screen, rov_center)
        # draw_thruster_vectors(screen, font, rov_center, thruster_forces)
        # draw_resultant_vector(screen, rov_center, thruster_forces)
        # draw_hud(screen, font, raw_inputs)
        pygame.display.flip()
        clock.tick(30)

    # On exit: stop thrusters safely
    pygame.quit()
    shared_data["running"] = False
    print("\nSimulation exited.")

if __name__ == "__main__":
    main()
