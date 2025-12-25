import math

PI_IP = "192.168.1.11" # Replace with your Pi's IP
UDP_PORT_DATA = 1345
UDP_PORT_CMD = 1346

# --- Screen Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
BLUE = (0, 170, 255)
RED = (255, 50, 50)
GREEN = (0, 200, 100)
YELLOW = (255, 255, 0) # <-- ADDED THIS
VECTOR_SCALE = 80
RESULTANT_VECTOR_SCALE = 50 # <-- ADDED THIS
FONT_SIZE = 30

# --- ROV Physical Configuration (for Allocation Logic) ---
ROV_WIDTH_MM = 262.629
ROV_LENGTH_MM = 195.311

# --- Simulation Drawing Configuration ---
SIM_ROV_WIDTH = 150
SIM_ROV_LENGTH = int(SIM_ROV_WIDTH * (ROV_LENGTH_MM / ROV_WIDTH_MM))
THRUSTER_POSITIONS = [
    (-SIM_ROV_WIDTH/2, -SIM_ROV_LENGTH/2), # T1 (Front-Left)
    ( SIM_ROV_WIDTH/2, -SIM_ROV_LENGTH/2), # T2 (Front-Right)
    (-SIM_ROV_WIDTH/2,  SIM_ROV_LENGTH/2), # T3 (Rear-Left)
    ( SIM_ROV_WIDTH/2,  SIM_ROV_LENGTH/2)  # T4 (Rear-Right)
]

# --- Thruster Angles ---
# "V" Configuration: T1(45), T2(135), T3(-45), T4(-135)
THRUSTER_ANGLES_DEG = [45, 135, -45, -135] 

# --- Thruster Control & Scaling ---

SIN_45 = math.sin(math.radians(45)) # approx 0.7071

# Maximum theoretical force/torque for "V" configuration

# Max axial (Surge/Sway) force = 4 * sin(45) * 1.0_thruster_force
# (All 4 thrusters contribute, same as "X" config)
MAX_AXIAL_FORCE = 4 * SIN_45  # approx 2.828

# Max yaw torque = 2 * sin(45) * (L + W) * 1.0_thruster_force
# (All 4 thrusters contribute)
MAX_YAW_TORQUE = 2 * SIN_45 * (ROV_LENGTH_MM + ROV_WIDTH_MM) # approx 647.6

# PWM Mapping Constants (T200)
PWM_NEUTRAL = 1500

# MAX thrust offered by an individual thruster
MAX_THRUST = 2.35 # This change was made due to problems in cancelling moments: from fixing PWM ranges to thrust ranges

# Controller Type
XBOX = "XBOX"
PS = "PS"
KEYBAORD = "KEYBOARD"

CONTROLLER_TYPE = KEYBAORD

# Found mechanical team messing up the connections, as exchanging 2 would invert the direction of thrust
# Fixing that in code
I1 = False
I2 = False
I3 = False
I4 = False
I5 = False
I6 = False
I7 = False
I8 = False

invert_thrusters = [I1, I2, I3, I4, I5, I6, I7, I8]

def invert_pwm(PWM, invert=False):
    """
    Docstring for invert_pwm
    
    :param PWM: PWM
    :param invert: Bool denoting if to invert
    """
    if invert == True:
        return PWM_NEUTRAL - (PWM - PWM_NEUTRAL)
    return PWM