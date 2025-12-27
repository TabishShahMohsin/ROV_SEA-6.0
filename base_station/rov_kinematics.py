import numpy as np
from config import *

def map_force_to_pwm(normalized_force):
    """Converts a normalized force [-1.0, 1.0] to a PWM signal [1200, 1800]."""

    def thrust_to_pwm(normalized_thrust):

            thrust = normalized_thrust*MAX_THRUST 

            if abs(thrust)<1e-2:
                return 1500
            elif thrust < 0:
                coeffs = np.array([4.58585333,   35.21660561,  169.73509491, 1464.33710736])
                return float(np.array([thrust**3, thrust**2, thrust, 1]) @ coeffs)
            elif thrust > 0:
                coeffs = np.array([2.22716503,  -22.41358258,  135.44774899, 1535.90291842])
                return float(np.array([thrust**3, thrust**2, thrust, 1]) @ coeffs)           

    pwm_value = thrust_to_pwm(normalized_force)
    return int(round(pwm_value))


def compute_thruster_forces(raw_surge, raw_sway, raw_heave, raw_roll, raw_pitch, raw_yaw):

    def hor_thruster_forces(raw_surge, raw_sway, raw_yaw):
        """
        Computes thrust for 4 diagonal thrusters.
        
        Inputs are the SCALED desired physical forces/torques.
        Outputs are normalized thruster forces (-1.0 to 1.0).
        """

        # Convert to desired forces
        # Can find the desired values for the net thrust
        theta = np.arctan2(raw_sway, raw_surge)
        desired_surge = raw_surge * MAX_AXIAL_FORCE * abs(np.cos(theta))
        desired_sway = raw_sway * MAX_AXIAL_FORCE * abs(np.sin(theta))
        desired_yaw = raw_yaw * MAX_YAW_TORQUE

        positions = np.array([
            [-ROV_WIDTH_MM/2,  ROV_LENGTH_MM/2],  # T1 (Front-Left)
            [ ROV_WIDTH_MM/2,  ROV_LENGTH_MM/2],  # T2 (Front-Right)
            [-ROV_WIDTH_MM/2, -ROV_LENGTH_MM/2],  # T3 (Rear-Left)
            [ ROV_WIDTH_MM/2, -ROV_LENGTH_MM/2],  # T4 (Rear-Right)
        ])

        # "V" Configuration: T1(45), T2(135), T3(-45), T4(-135)
        angles = np.deg2rad(THRUSTER_ANGLES_DEG) # Thruster angles from positive x-axis
        
        # Thruster Allocation Matrix (B): [Sway(x), Surge(y), Yaw(t)] x [T1, T2, T3, T4]
        B = np.zeros((3, 4))
        for i, ((x, y), theta) in enumerate(zip(positions, angles)):
            B[0, i] = np.cos(theta)                  # Contribution to Fx (Sway)
            B[1, i] = np.sin(theta)                  # Contribution to Fy (Surge)
            B[2, i] = x * np.sin(theta) - y * np.cos(theta) # Contribution to Torque (Yaw)

        # Desired Force Vector (v contains the scaled demands)
        v = np.array([desired_sway, desired_surge, desired_yaw]) 
        
        # Calculate required thruster forces using the pseudo-inverse (B+)
        # This finds the (least-squares) force combination.
        thruster_forces = np.linalg.pinv(B) @ v

        # --- Saturation/Normalization ---    # This step is critical: it finds the maximum required force and ensures     
        # it does not exceed 1.0, scaling ALL forces proportionally if needed.    
        max_force = np.max(np.abs(thruster_forces))    
        if max_force > 1.0:        
            thruster_forces /= max_force

        return thruster_forces


    def ver_thruster_forces(raw_roll, raw_pitch, raw_heave):
    # def hor_thruster_forces(raw_surge, raw_sway, raw_yaw):
        """
        Computes thrust for 4 vertical thrusters.
        
        Inputs are the SCALED desired physical forces/torques.
        Outputs are normalized thruster forces (-1.0 to 1.0).
        """

        # Convert to desired forces
        desired_roll = raw_roll * MAX_ROLL_TORQUE
        desired_pitch = raw_pitch * MAX_PITCH_TORQUE
        desired_heave = raw_heave * MAX_HEAVE_FORCE

        positions = np.array([
            [-ROV_WIDTH_MM/2,  ROV_LENGTH_MM/2],  # T5 (Front-Left)
            [ ROV_WIDTH_MM/2,  ROV_LENGTH_MM/2],  # T6 (Front-Right)
            [-ROV_WIDTH_MM/2, -ROV_LENGTH_MM/2],  # T7 (Rear-Left)
            [ ROV_WIDTH_MM/2, -ROV_LENGTH_MM/2],  # T8 (Rear-Right)
        ])

        
        # Thruster Allocation Matrix (B): [roll(x), pitch(y), heave(t)] x [T5, T6, T7, T8]
        B = np.zeros((3, 4))
        for i, (x, y) in enumerate(positions):
            B[0, i] = -y # Contribution to Fx (Pitch)
            B[1, i] = -x # Contribution to Fy (Roll)
            B[2, i] = 1 # Contribution to Torque (Heave)

        # Desired Force Vector (v contains the scaled demands)
        v = np.array([desired_pitch, desired_roll, desired_heave]) 
        
        # Calculate required thruster forces using the pseudo-inverse (B+)
        # This finds the (least-squares) force combination.
        thruster_forces = np.linalg.pinv(B) @ v

        # --- Saturation/Normalization ---    # This step is critical: it finds the maximum required force and ensures     
        # it does not exceed 1.0, scaling ALL forces proportionally if needed.    
        max_force = np.max(np.abs(thruster_forces))    
        if max_force > 1.0:        
            thruster_forces /= max_force

        return thruster_forces


    return np.concatenate([hor_thruster_forces(raw_surge, raw_sway, raw_yaw), ver_thruster_forces(raw_roll, raw_pitch, raw_heave)])