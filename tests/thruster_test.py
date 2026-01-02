import pigpio
import time

# --- 1. CONFIGURATION ---
# List all 8 GPIO pins for your thrusters
THRUSTER_PINS = [6, 5, 16, 26, 22, 23, 27, 17]

# PWM Values
NEUTRAL = 1500
FORWARD = 1650  # 150ms above neutral
REVERSE = 1350  # 150ms below neutral

# Timing
MOVE_TIME = 2.0
BREAK_TIME = 1.0

# --- 2. INITIALIZATION & SAFETY ---
pi = pigpio.pi()
if not pi.connected:
    print("❌ pigpiod not running! Run: sudo pigpiod")
    exit()

def safe_stop():
    """Immediately sets all pins to neutral and stops the script."""
    print("\n🛑 Emergency Stop: Neutralizing all thrusters...")
    for pin in THRUSTER_PINS:
        pi.set_servo_pulsewidth(pin, NEUTRAL)
    pi.stop()

def arm_system():
    print("⚙️  Step 1: Arming ESCs (Sending Neutral for 3s)...")
    for pin in THRUSTER_PINS:
        pi.set_servo_pulsewidth(pin, NEUTRAL)
    time.sleep(3)
    print("✅ System Armed and Ready.")

# --- 3. EXECUTION LOOP ---
try:
    arm_system()

    for i, pin in enumerate(THRUSTER_PINS):
        print(f"\n🚀 Testing Thruster {i+1} (GPIO {pin})")

        # 2 Seconds Forward
        print("  ↑ Forward")
        pi.set_servo_pulsewidth(pin, FORWARD)
        time.sleep(MOVE_TIME)

        # 1 Second Break
        print("  ⏸️ Break")
        pi.set_servo_pulsewidth(pin, NEUTRAL)
        time.sleep(BREAK_TIME)

        # 2 Seconds Back
        print("  ↓ Backward")
        pi.set_servo_pulsewidth(pin, REVERSE)
        time.sleep(MOVE_TIME)

        # Neutralize before moving to next pin
        pi.set_servo_pulsewidth(pin, NEUTRAL)
        print(f"✅ Thruster {i+1} complete.")
        time.sleep(0.5)

    print("\n✨ Sequence finished successfully.")

except KeyboardInterrupt:
    pass # Handled by 'finally'

finally:
    safe_stop()