import numpy as np

'''
Predict: Prior belief 
Update: Likelihood
Result: Posterior belief
Let the depth be in m, v be in m/s, pressure be in Pa (N/m**2)
'''

class DepthKalmanFilter:
    def __init__(self, initial_depth=0.0):
        # State: [depth, velocity] -> x ~ N(u, P)
        self.x = np.array([[initial_depth], [0.0]])
        # Assuming no correlation and equal uncertainities in estimate
        self.P = np.eye(2)
        # Process noise # Kind of Doubt # How wrong could the prediction be
        self.Q = np.array([[1e-4, 0], [0, 1e-3]]) 

        # Mesurement Noise Covariance: z = Hx + v, v ~ N(0, R)
        self.R = 0.01 # Measurement noise (Bar30 is very clean, keep this small)
        self.F = np.array([[1, 0.034], [0, 1]]) # State transition (assuming 30Hz dt=0.034 initially)
        self.H = np.array([[1, 0]]) # We only measure depth, not velocity z = Hx

    def update(self, measured_depth, dt):
        # 1. Predict
        self.F[0, 1] = dt
        # depth_new = depth_old + velocity * dt 
        self.x = self.F @ self.x
        # if x ~ N(u, sigma) => Fx ~ N(Fu, F@sigma@F.T)
        self.P = self.F @ self.P @ self.F.T + self.Q # Adding doubt as this is certain to cause drift

        # 2. Update
        y = measured_depth - (self.H @ self.x) # Innovation(Residual): Sensor reading - our prediction
        # Finding out the Kalman Gain
        S = self.H @ self.P @ self.H.T + self.R # Innovation Covariance
        K = self.P @ self.H.T / S
        # Combining the sensor with our prediction
        self.x = self.x + K * y
        self.P = (np.eye(2) - K @ self.H) @ self.P
        
        return self.x[0, 0] # Returns smooth depth