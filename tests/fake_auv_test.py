import pigpio
import time
import threading
import numpy as np
import subprocess

# --- 1. HARDCODED CONFIGURATION ---
THRUSTER_PINS = {
    "t1": 17, "t2": 18, "t3": 27, "t4": 22, 
    "t5": 23, "t6": 24, "t7": 25, "t8": 8  
}

RAMP_STEP = 15
LOOP_FREQ = 0.05
# Constant Heave value (0.0 to 1.0). Adjust this to keep your ROV at depth.
CONST_HEAVE = -0.3 

target_pwms = {f"t{i}": 1500 for i in range(1, 9)}
current_pwms = {f"t{i}": 1500 for i in range(1, 9)}
is_running = True

# --- 2. KINEMATICS ENGINE (From your code) ---
def map_force_to_pwm(f):
    if abs(f) < 1e-2: return 1500
    if f < 0:
        return int(np.array([f**3, f**2, f, 1]) @ [4.58, 35.21, 169.73, 1464.33])
    else:
        return int(np.array([f**3, f**2, f, 1]) @ [2.22, -22.41, 135.44, 1535.90])

def get_pwms(surge, sway, yaw, heave, roll=0, pitch=0):
    """Calculates PWMs based on your allocation matrix logic."""
    # Horizontal (Simplified for your V-config)
    t1 = surge + sway + yaw
    t2 = surge - sway - yaw
    t3 = surge - sway + yaw
    t4 = surge + sway - yaw
    
    # Vertical (Simplified for Heave/Pitch/Roll)
    t5 = heave - pitch - roll
    t6 = heave - pitch + roll
    t7 = heave + pitch - roll
    t8 = heave + pitch + roll
    
    forces = [t1, t2, t3, t4, t5, t6, t7, t8]
    # Normalize
    max_f = max(np.abs(forces))
    if max_f > 1.0: forces = [f/max_f for f in forces]
    
    return [map_force_to_pwm(f) for f in forces]

# --- 3. HARDWARE & RAMPING ---
try:
    subprocess.run(['sudo', 'pigpiod'], capture_output=True)
except: pass

pi = pigpio.pi()

def ramping_loop():
    while is_running:
        for i, key in enumerate(target_pwms):
            target = target_pwms[key]
            curr = current_pwms[key]
            if curr < target: current_pwms[key] = min(curr + RAMP_STEP, target)
            elif curr > target: current_pwms[key] = max(curr - RAMP_STEP, target)
            pi.set_servo_pulsewidth(THRUSTER_PINS[key], current_pwms[key])
        time.sleep(LOOP_FREQ)

def update_motion(surge, sway, yaw, heave):
    pwms = get_pwms(surge, sway, yaw, heave)
    for i in range(8):
        target_pwms[f"t{i+1}"] = pwms[i]

# --- 4. MISSION CONTROL (The "AUV" Logic) ---
def mission_logic():
    global is_running
    print("🚀 Mission Starting in 5 seconds...")
    time.sleep(5)

    print("➡️ Phase 1: Moving Forward")
    # Surge=0.4, Sway=0, Yaw=0, Heave=CONST
    update_motion(0.4, 0, 0, CONST_HEAVE)
    time.sleep(5)

    print("🛑 Phase 2: Braking/Waiting")
    update_motion(0, 0, 0, CONST_HEAVE)
    time.sleep(2)

    print("🔄 Phase 3: Moving Right (Sway)")
    update_motion(0, 0.4, 0, CONST_HEAVE)
    time.sleep(4)

    print("🏁 Phase 4: Mission Complete. Stopping.")
    update_motion(0, 0, 0, 0)
    time.sleep(2)
    is_running = False

# --- 5. MAIN EXECUTION ---
try:
    t_ramp = threading.Thread(target=ramping_loop, daemon=True)
    t_ramp.start()
    
    mission_logic()

except KeyboardInterrupt:
    print("\nEmergency Stop!")
finally:
    is_running = False
    for pin in THRUSTER_PINS.values():
        pi.set_servo_pulsewidth(pin, 1500)
    pi.stop()