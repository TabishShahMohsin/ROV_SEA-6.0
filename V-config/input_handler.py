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
    """Mimics a controller using WASD and Arrow keys with smoothing."""
    def __init__(self, deadzone=0.0):
        print("Keyboard Control Mode Active: Use WASD for Surge/Sway, Q/E or Arrows for Yaw")
        # State for smoothing (0.0 to 1.0)
        self.surge = 0.0
        self.sway = 0.0
        self.yaw = 0.0
        self.ramp_speed = 0.1  # Adjust this to make it feel 'heavier' or 'snappier'

    def get_input_vector(self):
        """Processes keyboard state and returns (surge, sway, yaw)."""
        keys = pygame.key.get_pressed()

        # Target values based on key presses
        target_surge = 0.0
        if keys[pygame.K_w]: target_surge += 1.0
        if keys[pygame.K_s]: target_surge -= 1.0

        target_sway = 0.0
        if keys[pygame.K_d]: target_sway += 1.0
        if keys[pygame.K_a]: target_sway -= 1.0

        target_yaw = 0.0
        if keys[pygame.K_e] or keys[pygame.K_RIGHT]: target_yaw -= 1.0
        if keys[pygame.K_q] or keys[pygame.K_LEFT]:  target_yaw += 1.0

        # --- The "Smoothing Trick" ---
        # Gradually move current values toward target values
        self.surge = self._approach(self.surge, target_surge, self.ramp_speed)
        self.sway = self._approach(self.sway, target_sway, self.ramp_speed)
        self.yaw = self._approach(self.yaw, target_yaw, self.ramp_speed)

        return np.array([self.surge, self.sway, self.yaw])

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
elif controller_type == "KEYBOARD":
    JoystickController = KeyboardController
else:
    # Fallback: If no controller is found, don't crash, use Keyboard
    print(f"Warning: '{CONTROLLER_TYPE}' not found. Falling back to Keyboard.")
    JoystickController = KeyboardController
