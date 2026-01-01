import cv2
import imagezmq
import numpy as np

# Initialize the hub
image_hub = imagezmq.ImageHub()

print("Base Station (Turbo) Ready via Ethernet...")

while True:
    # recv_jpg() expects a compressed byte stream, not a raw array
    cam_name, jpg_buffer = image_hub.recv_jpg()
    
    # Fast Decode: Convert bytes back to an image
    # np.frombuffer is very fast (zero-copy)
    image = cv2.imdecode(np.frombuffer(jpg_buffer, dtype='uint8'), -1)
    
    # Display
    cv2.imshow(cam_name, image)
    
    # Send 'OK' reply so the Pi sends the next frame
    image_hub.send_reply(b'OK')
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()