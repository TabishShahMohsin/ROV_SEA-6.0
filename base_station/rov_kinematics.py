import numpy as np
from config import *

def map_force_to_pwm(thrust):
    """
    Regression over thrust vs pwm graph for T200 at 14V 
    """

    if abs(thrust)<1e-2:
        pwm_value =  1500
    elif thrust < 0:
        coeffs = np.array([4.58585333,   35.21660561,  169.73509491, 1464.33710736])
        pwm_value = float(np.array([thrust**3, thrust**2, thrust, 1]) @ coeffs)
    elif thrust > 0:
        coeffs = np.array([2.22716503,  -22.41358258,  135.44774899, 1535.90291842])
        pwm_value = float(np.array([thrust**3, thrust**2, thrust, 1]) @ coeffs)           

    return int(round(pwm_value))


def compute_thruster_forces(raw_surge, raw_sway, raw_heave, raw_roll, raw_pitch, raw_yaw):
    """
    First computes the desired motion
    Then computes the desired thrusts
    """
    theta = np.arctan2(abs(raw_sway), abs(raw_surge))

    # The thrusters max out before the joystick reaches extreme in some directions, this happens as the max thrust in drxns like 45 deg aren't same as max in x or max in y
    desired_surge = raw_surge * MAX_AXIAL_FORCE * np.cos(theta)
    desired_sway = raw_sway * MAX_AXIAL_FORCE * np.sin(theta)
    desired_yaw = raw_yaw * MAX_YAW_TORQUE 
    desired_roll = raw_roll * MAX_ROLL_TORQUE
    desired_pitch = raw_pitch * MAX_PITCH_TORQUE
    desired_heave = raw_heave * MAX_HEAVE_FORCE

    positions = np.array([
            [ ROV_LENGTH_MM/2, -ROV_WIDTH_MM/2],  # T1 (Front-Left)
            [ ROV_LENGTH_MM/2,  ROV_WIDTH_MM/2],  # T2 (Front-Right)
            [-ROV_LENGTH_MM/2, -ROV_WIDTH_MM/2],  # T3 (Rear-Left)
            [-ROV_LENGTH_MM/2,  ROV_WIDTH_MM/2],  # T4 (Rear-Right)
            [ ROV_LENGTH_MM/2, -ROV_WIDTH_MM/2],  # T5 (Front-Left)
            [ ROV_LENGTH_MM/2,  ROV_WIDTH_MM/2],  # T6 (Front-Right)
            [-ROV_LENGTH_MM/2, -ROV_WIDTH_MM/2],  # T7 (Rear-Left)
            [-ROV_LENGTH_MM/2,  ROV_WIDTH_MM/2],  # T8 (Rear-Right)
        ])
    
    lateral_thrusters_angles = np.deg2rad(THRUSTER_ANGLES_DEG)

    # Solving column matrix t having thrusts such that B @ t = v --> t = (B+) @ v
    B_lateral = np.zeros((3, 4)) 
    B_vertical = np.zeros((3, 4))

    for i, ((x, y), theta) in enumerate(zip(positions, lateral_thrusters_angles)):
        B_lateral[0, i] = np.sin(theta) # Contribution to Fx (Surge)
        B_lateral[1, i] = np.cos(theta) # Contribution to Fy (Sway)
        B_lateral[2, i] = x * np.cos(theta) - y * np.sin(theta) # Contribution to Tz (Yaw)

    for i, (x, y) in enumerate(positions[4:]):
        B_vertical[0, i] = -x # Contribution to Ty (Pitch)
        B_vertical[1, i] = y # Contribution to Tx (Roll)
        B_vertical[2, i] = 1 # Contribution to Fz (Heave)

    v = np.array([desired_surge, desired_sway, desired_yaw, desired_pitch, desired_roll, desired_heave]) 

    # Sets the failed thruster column to 0, atleast 3 lateral and 3 vertical thrusters are required for 6 DOF
    B_lateral = B_lateral * WORKING_THRUSTERS[:4]
    B_vertical = B_vertical * WORKING_THRUSTERS[4:]

    lateral_thruster_forces = np.linalg.pinv(B_lateral) @ v[:3]
    vertical_thruster_forces = np.linalg.pinv(B_vertical) @ v[3:]

    # PID on vertical shouldn't disturb lateral thrusters
    max_force = np.max(np.abs(lateral_thruster_forces))    
    if max_force > MAX_THRUST:
        lateral_thruster_forces /= (max_force / MAX_THRUST)
    max_force = np.max(np.abs(vertical_thruster_forces))    
    if max_force > MAX_THRUST:
        vertical_thruster_forces /= (max_force / MAX_THRUST)

    return np.concatenate([lateral_thruster_forces, vertical_thruster_forces])
