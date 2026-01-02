import time
import cv2
import imagezmq
import numpy as np
import pyrealsense2 as rs
from picamera2 import Picamera2
import simplejpeg  
import os

# 1. Silence Logs
os.environ["LIBCAMERA_LOG_LEVELS"] = "3"

# 2. CONFIGURATION
SERVER_IP = "192.168.137.1" 
JPEG_QUALITY = 95

print(f"Connecting to Base Station at {SERVER_IP}...")
try:
    sender = imagezmq.ImageSender(connect_to=f"tcp://{SERVER_IP}:5555")
    print("  [SUCCESS] Connected.")
except Exception as e:
    print(f"  [FAILURE] Network Error: {e}")
    exit()

# 3. SETUP PI CAMERA (Native)
print("Initializing Pi Camera...")
try:
    picam2 = Picamera2()
    # Request BGR888 so data is ready for processing immediately
    config = picam2.create_video_configuration(
        main={"size": (640, 480), "format": "BGR888"}
    )
    picam2.configure(config)
    picam2.start()
except Exception as e:
    print(f"Pi Cam Error: {e}")
    picam2 = None

# 4. SETUP REALSENSE
print("Initializing RealSense...")
try:
    rs_pipeline = rs.pipeline()
    rs_config = rs.config()
    rs_config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    rs_pipeline.start(rs_config)
except Exception:
    rs_pipeline = None

if picam2 is None and rs_pipeline is None:
    print("CRITICAL: Both cameras failed. Exiting.")
    exit()

print("\n--- Ultra-Turbo Streaming (simplejpeg) ---")

try:
    while True:
        # A. Pi Camera
        if picam2:
            # Capture raw BGR array
            pi_frame = picam2.capture_array()
            
            # FAST ENCODE:
            # - quality=70: Good balance
            # - colorspace='BGR': Matches our camera config
            # - fastdct=True: Uses integer math for speed
            jpg_buffer = simplejpeg.encode_jpeg(
                pi_frame, 
                quality=JPEG_QUALITY, 
                colorspace='RGB', 
                fastdct=True
            )
            
            sender.send_jpg("PiCam_Feed", jpg_buffer)

        # B. RealSense
        if rs_pipeline:
            frames = rs_pipeline.poll_for_frames()
            if frames:
                color_frame = frames.get_color_frame()
                if color_frame:
                    # RealSense data is BGR by default
                    rs_image = np.asanyarray(color_frame.get_data())
                    
                    rs_jpg = simplejpeg.encode_jpeg(
                        rs_image, 
                        quality=JPEG_QUALITY, 
                        colorspace='BGR', 
                        fastdct=True
                    )
                    
                    sender.send_jpg("RealSense_Feed", rs_jpg)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    if picam2: picam2.stop()
    if rs_pipeline: rs_pipeline.stop()