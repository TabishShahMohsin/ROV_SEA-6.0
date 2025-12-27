import pygame
import numpy as np
from config import CONTROLLER_TYPE, XBOX, PS, KEYBAORD


class XboxController:
    """Handles connection and reading of an Xbox controller."""
    def __init__(self, deadzone=0.1):
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            raise RuntimeError("Error: No Xbox controller detected.")

        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        print(f"Xbox Controller Connected: {self.joystick.get_name()}")
        self.deadzone = deadzone

    def get_input_vector(self):
        """Reads axes and returns (surge, sway, yaw)."""
        surge_input = -self.joystick.get_axis(1)   # Left stick Y (invert)
        sway_input = self.joystick.get_axis(0)     # Left stick X
        yaw_input = (self.joystick.get_axis(5) - self.joystick.get_axis(2)) / 2  # Triggers

        # Found the r(=x2 + y2) for a joystick to be exceeding 1
        if (np.pow(surge_input, 2) + np.pow(sway_input, 2)) > 1:
            r = np.pow(np.pow(surge_input, 2) + np.pow(sway_input, 2), 1/2)
            surge_input = surge_input / r
            sway_input = sway_input / r

        # Apply deadzone
        surge_input = 0.0 if abs(surge_input) < self.deadzone else surge_input
        sway_input = 0.0 if abs(sway_input) < self.deadzone else sway_input
        yaw_input = 0.0 if abs(yaw_input) < self.deadzone else yaw_input

        return np.array([surge_input, sway_input, yaw_input])


class PSController:
    """Handles connection and reading of a PS4/PS5 controller."""
    def __init__(self, deadzone=0.1):
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            raise RuntimeError("Error: No PS controller detected.")

        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        print(f"PS Controller Connected: {self.joystick.get_name()}")
        self.deadzone = deadzone

    def get_input_vector(self):
        """Reads axes and returns (surge, sway, yaw)."""
        surge_input = -self.joystick.get_axis(1)   # Left stick Y
        sway_input = self.joystick.get_axis(0)     # Left stick X
        yaw_input = self.joystick.get_axis(2) - self.joystick.get_axis(5)  # Right stick X diff

        # Found the r(=x2 + y2) for a joystick to be exceeding 1
        if (np.pow(surge_input, 2) + np.pow(sway_input, 2)) > 1:
            r = np.pow(np.pow(surge_input, 2) + np.pow(sway_input, 2), 1/2)
            surge_input = surge_input / r
            sway_input = sway_input / r

        # Apply deadzone
        surge_input = 0.0 if abs(surge_input) < self.deadzone else surge_input
        sway_input = 0.0 if abs(sway_input) < self.deadzone else sway_input
        yaw_input = 0.0 if abs(yaw_input) < self.deadzone else yaw_input

        return np.array([surge_input, sway_input, yaw_input])

class KeyboardController:
    """Mimics a controller using WASD, Arrows, and Space/Shift for 6-DoF control."""
    def __init__(self, deadzone=0.0):
        print("6-DoF Keyboard Control Mode Active:")
        print(" - WASD: Surge/Sway")
        print(" - Q / E: Yaw")
        print(" - Space / L-Shift: Heave (Up/Down)")
        print(" - I / K: Pitch")
        print(" - J / L: Roll")
        
        # State for smoothing (0.0 to 1.0)
        self.surge = 0.0
        self.sway = 0.0
        self.heave = 0.0
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        
        self.ramp_speed = 0.1  # Smoothing factor

    def get_input_vector(self):
        """Processes keyboard state and returns (surge, sway, heave, roll, pitch, yaw)."""
        keys = pygame.key.get_pressed()

        # --- Linear Motion ---
        target_surge = 0.0
        if keys[pygame.K_w]: target_surge += 1.0
        if keys[pygame.K_s]: target_surge -= 1.0

        target_sway = 0.0
        if keys[pygame.K_d]: target_sway += 1.0
        if keys[pygame.K_a]: target_sway -= 1.0

        target_heave = 0.0
        if keys[pygame.K_SPACE]:  target_heave += 1.0
        if keys[pygame.K_LSHIFT]: target_heave -= 1.0

        # --- Rotational Motion ---
        target_yaw = 0.0
        if keys[pygame.K_e]: target_yaw -= 1.0
        if keys[pygame.K_q]: target_yaw += 1.0

        target_pitch = 0.0
        if keys[pygame.K_i]: target_pitch += 1.0
        if keys[pygame.K_k]: target_pitch -= 1.0

        target_roll = 0.0
        if keys[pygame.K_l]: target_roll += 1.0
        if keys[pygame.K_j]: target_roll -= 1.0

        # --- Apply Smoothing ---
        self.surge = self._approach(self.surge, target_surge, self.ramp_speed)
        self.sway = self._approach(self.sway, target_sway, self.ramp_speed)
        self.heave = self._approach(self.heave, target_heave, self.ramp_speed)
        self.roll = self._approach(self.roll, target_roll, self.ramp_speed)
        self.pitch = self._approach(self.pitch, target_pitch, self.ramp_speed)
        self.yaw = self._approach(self.yaw, target_yaw, self.ramp_speed)

        # --- Normalization (Linear only) ---
        # Prevents faster diagonal movement
        linear_mags = np.sqrt(self.surge**2 + self.sway**2 + self.heave**2)
        if linear_mags > 1.0:
            self.surge /= linear_mags
            self.sway /= linear_mags
            self.heave /= linear_mags

        return np.array([
            self.surge, self.sway, self.heave, 
            self.roll, self.pitch, self.yaw
        ])

    def _approach(self, current, target, step):
        """Helper to move current value toward target by a small step."""
        if current < target:
            return min(current + step, target)
        elif current > target:
            return max(current - step, target)
        return current

controller_type = CONTROLLER_TYPE.upper()

if controller_type == XBOX:
    JoystickController = XboxController
elif controller_type == PS:
    JoystickController = PSController
elif controller_type == KEYBAORD:
    JoystickController = KeyboardController
else:
    # Fallback: If no controller is found, don't crash, use Keyboard
    print(f"Warning: '{CONTROLLER_TYPE}' not found. Falling back to Keyboard.")
    JoystickController = KeyboardController
