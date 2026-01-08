import pyrealsense2 as rs
import numpy as np
import cv2
import sys
import time

'''
Need USB - 3.0 cable for getting the gyro - acc readings
Need to install dependencies
brew install librealsense/ really tough on pi
pip install pyrealsense2
'''

# Configure pipeline
pipeline = rs.pipeline()
config = rs.config()

# Reduce resolution for better performance
res_w, res_h = 640, 480

config.enable_stream(rs.stream.depth, res_w, res_h, rs.format.z16, 30)
config.enable_stream(rs.stream.color, res_w, res_h, rs.format.bgr8, 30)
config.enable_stream(rs.stream.infrared, 1, res_w, res_h, rs.format.y8, 30)
config.enable_stream(rs.stream.infrared, 2, res_w, res_h, rs.format.y8, 30)
# config.enable_stream(rs.stream.accel)
# config.enable_stream(rs.stream.gyro)

# Start streaming
profile = pipeline.start(config)

# --- TURN IR EMITTER OFF ---
device = profile.get_device()
depth_sensor = device.query_sensors()[0]
if depth_sensor.supports(rs.option.emitter_enabled):
    depth_sensor.set_option(rs.option.emitter_enabled, 0)

# Colorizer for depth and a filter to simulate confidence/disparity
colorizer = rs.colorizer()

try:
    while True:
        time.sleep(0.1)
        frames = pipeline.wait_for_frames()
        
        # Get frames
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        ir_left = frames.get_infrared_frame(1)
        ir_right = frames.get_infrared_frame(2)
        #accel = frames.first_or_default(rs.stream.accel).as_motion_frame().get_motion_data()
        #gyro = frames.first_or_default(rs.stream.gyro).as_motion_frame().get_motion_data()

        if not depth_frame or not color_frame: continue

        # Convert to numpy arrays
        depth_image = np.asanyarray(colorizer.colorize(depth_frame).get_data())
        color_image = np.asanyarray(color_frame.get_data())
        ir_left_image = np.asanyarray(ir_left.get_data())
        ir_right_image = np.asanyarray(ir_right.get_data())

        # Build display tiles
        top_row = np.hstack((color_image, depth_image))
        mid_row = np.hstack((cv2.cvtColor(ir_left_image, cv2.COLOR_GRAY2BGR), 
                             cv2.cvtColor(ir_right_image, cv2.COLOR_GRAY2BGR)))
        display = np.vstack((top_row, mid_row))

        cv2.imshow('D435i: RGB | Depth | IR-L | IR-R', cv2.resize(display, (1280, 720)))

        '''
        # Dashboard printing (leveled in terminal)
        ts = frames.get_timestamp()
        status = (f"\rTS: {ts:.2f} | ACCEL: x:{accel.x:>5.2f} y:{accel.y:>5.2f} z:{accel.z:>5.2f} | "
                  f"GYRO: x:{gyro.x:>5.2f} y:{gyro.y:>5.2f} z:{gyro.z:>5.2f}")
        sys.stdout.write(status)
        sys.stdout.flush()
        '''

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
    print("\nStreams stopped.")
