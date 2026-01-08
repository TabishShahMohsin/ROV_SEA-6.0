'''
sudo apt update
sudo apt install python3-picamera2 python3-opencv
'''

'''
rpicam-hello --list-cameras
'''

import cv2
from picamera2 import Picamera2

# 1. Initialize the camera
picam2 = Picamera2()

# 2. Configure the stream resolution
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)

# 3. Start the camera
picam2.start()

print("Press 'q' to quit")

while True:
    # Capture a single frame (Returns RGB array)
    frame = picam2.capture_array()
    
    # --- CONVERSION STEP ---
    # Convert RGB (Picamera2 default) to BGR (OpenCV default)
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    
    # Display the converted feed
    cv2.imshow("RPi Camera Feed", frame_bgr)
    
    # Break loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

picam2.stop()
cv2.destroyAllWindows()