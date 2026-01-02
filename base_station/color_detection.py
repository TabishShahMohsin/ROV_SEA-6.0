import cv2
import numpy as np
from preprocessing import white_balance, contrast_enhancement, enhance_low_light


def detect_color_from_video(video_source, assigned_color="GREEN", show_window=True, window_name='Color Detection'):
    cap = cv2.VideoCapture(video_source)
    
    if not cap.isOpened():
        print(f"Error: Could not open video source: {video_source}")
        return
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    contour_area_threshold = 3000

    if show_window:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("End of video or cannot read frame.")
                break
            
            # Apply preprocessing
            processed_frame = white_balance(frame)
            processed_frame = contrast_enhancement(processed_frame)
            #processed_frame = enhance_low_light(processed_frame)
            
            hsv_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2HSV)

            # Define color ranges
            lower_green = np.array([35, 20, 20])
            upper_green = np.array([80, 255, 255])
            
            lower_red1 = np.array([0, 160, 20])
            upper_red1 = np.array([10, 255, 255])
            
            lower_red2 = np.array([160, 150, 20])
            upper_red2 = np.array([180, 255, 255])
            
            # Create masks
            red_mask = cv2.bitwise_or(cv2.inRange(hsv_frame, lower_red1, upper_red1),
                                    cv2.inRange(hsv_frame, lower_red2, upper_red2))
            green_mask = cv2.inRange(hsv_frame, lower_green, upper_green)
            
            red_pixels = cv2.countNonZero(red_mask)
            green_pixels = cv2.countNonZero(green_mask)

            # Apply morphological operations
            kernel = np.ones((7, 7), np.uint8)
            masks = [green_mask, red_mask]
            for i in range(len(masks)):
                masks[i] = cv2.morphologyEx(masks[i], cv2.MORPH_OPEN, kernel)
                masks[i] = cv2.morphologyEx(masks[i], cv2.MORPH_CLOSE, kernel)

            green_mask, red_mask = masks

            # Find and draw contours
            color_info = [
                ("Red", red_mask, (0, 0, 255)),
                ("Green", green_mask, (0, 255, 0))
            ]

            for name, mask, bgr in color_info:
                contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > contour_area_threshold:
                        x, y, w, h = cv2.boundingRect(contour)
                        cv2.rectangle(processed_frame, (x, y), (x + w, y + h), bgr, 4)
                        cv2.putText(processed_frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.7, bgr, 2)

            # Determine detected color
            if red_pixels > green_pixels and red_pixels > 1000:
                detected_color = "Red"
                detected_color_value = (0, 0, 255)
            elif green_pixels > red_pixels and green_pixels > 1000:
                detected_color = "Green"
                detected_color_value = (0, 255, 0)
            else:
                detected_color = "None"
                detected_color_value = (255, 255, 255)
                
            cv2.putText(processed_frame, f"Color Detected: {detected_color}",
                                (18, height - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.4, detected_color_value, 4)

            if show_window:
                cv2.imshow(window_name, processed_frame)
            
            # Yield only the processed frame
            yield processed_frame
            
            # Allow early exit with 'q' key
            if show_window and cv2.waitKey(1) & 0xFF == ord('q'):
                print("Quitting.")
                break

    finally:
        cap.release()
        if show_window:
            cv2.destroyAllWindows()


# Example usage when running this file directly
if __name__ == "__main__":
    # For webcam
    detector = detect_color_from_video(0)
    
    for frame in detector:
        # Just get the frame feed
        pass