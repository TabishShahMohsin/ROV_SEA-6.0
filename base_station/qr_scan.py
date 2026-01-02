import cv2
from pyzbar import pyzbar
from preprocessing import white_balance, contrast_enhancement


def process_frame_for_qr(frame):
    display_frame = white_balance(frame.copy())
    display_frame = contrast_enhancement(display_frame)

    qrs = pyzbar.decode(display_frame)

    for qr in qrs:
        qr_data = qr.data.decode('utf-8')
        (x, y, w, h) = qr.rect
        
        cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(display_frame, qr_data, (x, y + h + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    return display_frame


if __name__ == "__main__":
    cap = cv2.VideoCapture('/Users/mohammadbilal/Documents/Projects/ROV_SEA-6.0/base_station/recording3.mp4')
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        processed_frame = process_frame_for_qr(frame)
        cv2.imshow('QR Scanner', processed_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()