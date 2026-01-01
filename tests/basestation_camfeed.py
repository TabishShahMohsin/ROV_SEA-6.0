import cv2
import imagezmq
import numpy as np

# Initialize the hub
image_hub = imagezmq.ImageHub()

print("Base Station Ready via Ethernet...")

while True:
    cam_name, jpg_buffer = image_hub.recv_jpg()
    image = cv2.imdecode(np.frombuffer(jpg_buffer, dtype='uint8'), -1)
    
    # Process based on which camera sent the frame
    if cam_name == "PiCam_Feed":  # Replace with your actual camera name
        # Do something specific to camera 1
        processed = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        cv2.imshow("Camera 1 - Grayscale", processed)
        
    elif cam_name == "RealSense_Feed":  # Replace with your actual camera name
        # Do something specific to camera 2
        processed = cv2.GaussianBlur(image, (15, 15), 0)
        cv2.imshow("Camera 2 - Blurred", processed)
    
    else:
        # Default display for unknown cameras
        cv2.imshow(cam_name, image)
    
    image_hub.send_reply(b'OK')
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()