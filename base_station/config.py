import math
import socket
import numpy as np

'''
        ---------------width-----------------
    |    T1 (CW)                       T2 (CW)
    |
    |
    |           T5 (CCW)      T6 (CW)
  length
    |           T7 (CW)       T8 (CCW)
    |
    |
    |   T3 (CCW)                      T4 (CCW)
'''

PI_IP = "192.168.137.2"
#PI_IP = socket.gethostbyname("auv.local")
UDP_PORT_DATA = 5005
UDP_PORT_CMD = 5006

ROV_WIDTH_MM = 262.629
ROV_LENGTH_MM = 195.311

# "V" Configuration: T1(45), T2(135), T3(-45), T4(-135)
THRUSTER_ANGLES_DEG = [45, 135, -45, -135] # From +ve x-axis

SIN_45 = math.sin(math.radians(45))


# MAX thrust offered by an individual thruster
# This change was made due to problems in cancelling moments: from fixing PWM ranges to thrust ranges
MAX_THRUST = 2.35 

MAX_AXIAL_FORCE = 4 * SIN_45 * MAX_THRUST
MAX_YAW_TORQUE = 2 * SIN_45 * (ROV_LENGTH_MM + ROV_WIDTH_MM) * MAX_THRUST
MAX_HEAVE_FORCE = 4 * MAX_THRUST
MAX_ROLL_TORQUE = 4 * (ROV_WIDTH_MM / 2) * MAX_THRUST
MAX_PITCH_TORQUE = 4 * (ROV_LENGTH_MM / 2) * MAX_THRUST

PWM_NEUTRAL = 1500

XBOX = "XBOX"
PS = "PS"
KEYBAORD = "KEYBOARD"
CONTROLLER_TYPE = KEYBAORD

# Found mechanical team messing up the connections, as exchanging 2 would invert the direction of thrust
# Also 4 propellers must in be in one sense and the other 4 in opp sense for cancelling counter rotor torque
I1 = True
I2 = False
I3 = False
I4 = True 
I5 = False
I6 = False
I7 = False
I8 = False

def invert_pwm(PWM, invert=True):
    if invert == True:
        return PWM_NEUTRAL - (PWM - PWM_NEUTRAL)
    return PWM


# Due to unreliable electronics some thrusters tend to fail, only 6 thrusters with 3 lateral and 3 vertical are reuqired to attain 6 DOFs
# However cacelling the counter rotor torque with one less thruster is impossible and hence unaccounted in such a failure
F1 = 1 # else 0
F2 = 1
F3 = 1
F4 = 1
F5 = 1
F6 = 1
F7 = 1
F8 = 1

failed_thrusters = np.array([F1, F2, F3, F4, F5, F6, F7, F8])
