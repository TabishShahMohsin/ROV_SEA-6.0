import cv2
from collections import Counter
from pyzbar import pyzbar
from preprocessing import white_balance, contrast_enhancement


def scan_qr_from_video(video_source, show_window=True, window_name='QR Code Scanner'):
    """
    Automatically scan QR codes from a video source and yield processed frames.
    
    Parameters:
    -----------
    video_source : str or int
        Path to video file (str) or camera index (int, e.g., 0 for default camera)
    show_window : bool, optional
        Whether to display the video window during processing (default: True)
    window_name : str, optional
        Name of the display window (default: 'QR Code Scanner')
    
    Yields:
    -------
    tuple : (processed_frame, frame_info)
        - processed_frame: numpy array of the frame with QR annotations
        - frame_info: dict containing current detection state
    
    Returns:
    --------
    dict : Final results dictionary containing:
        - 'final_decision': Most frequently detected QR code
        - 'instruction_list': List with the final decision
        - 'total_frames': Total number of frames processed
        - 'qr_detected_frames': Number of frames where QR codes were detected
        - 'detection_rate': Percentage of frames with QR detection
        - 'all_detections': List of all QR codes detected
        - 'qr_votes': Counter object with vote counts for each QR code
    """
    detected_qrs = []
    qr_votes = Counter()
    final_decision = None
    instruction_list = list()

    print("Starting automatic QR detection...")

    cap = cv2.VideoCapture(video_source)
    
    if not cap.isOpened():
        print(f"Error: Could not open video source: {video_source}")
        return None

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    total_frames = 0
    qr_detected_frames = 0

    if show_window:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("End of video or cannot fetch the frame.")
                break

            display_frame = white_balance(frame.copy())
            display_frame = contrast_enhancement(display_frame)

            total_frames += 1
            qrs = pyzbar.decode(display_frame)
            frame_qrs = set()
            current_frame_qrs = []

            if qrs:
                qr_detected_frames += 1

                for qr in qrs:
                    qr_data = qr.data.decode('utf-8')
                    frame_qrs.add(qr_data)
                    current_frame_qrs.append(qr_data)

                    (x, y, w, h) = qr.rect
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(display_frame, qr_data, (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                for qr_data in frame_qrs:
                    detected_qrs.append(qr_data)
                    qr_votes[qr_data] += 1

            if qr_votes:
                final_decision = qr_votes.most_common(1)[0][0]
                cv2.putText(display_frame, f"Final Decision: {final_decision}",
                            (10, height - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

            # Frame info for this frame
            frame_info = {
                'frame_number': total_frames,
                'qrs_in_frame': current_frame_qrs,
                'current_decision': final_decision,
                'total_detections': len(detected_qrs)
            }

            if show_window:
                cv2.imshow(window_name, display_frame)
            
            # Yield the processed frame and info
            yield display_frame, frame_info
            
            # Allow early exit with 'q' key
            if show_window and cv2.waitKey(1) & 0xFF == ord('q'):
                print("Quitting.")
                break

    finally:
        # Finalize the decision after processing all frames
        if qr_votes:
            final_decision = qr_votes.most_common(1)[0][0]
            instruction_list.append(final_decision)
            print("FINAL DECISION:", final_decision)

        cap.release()
        if show_window:
            cv2.destroyAllWindows()

        detection_rate = (qr_detected_frames / total_frames) * 100 if total_frames > 0 else 0

        print("Total frames processed:", total_frames)
        print("Frames with QR code detected:", qr_detected_frames)
        print("Detection Rate: {:.2f}%".format(detection_rate))
        print("Instructions List:", instruction_list)

        # Return final results
        return {
            'final_decision': final_decision,
            'instruction_list': instruction_list,
            'total_frames': total_frames,
            'qr_detected_frames': qr_detected_frames,
            'detection_rate': detection_rate,
            'all_detections': detected_qrs,
            'qr_votes': qr_votes
        }


# Example usage when running this file directly
if __name__ == "__main__":
    # For video file with frame-by-frame access
    scanner = scan_qr_from_video('recording3.mp4')
    
    for frame, info in scanner:
        # You can process each frame here
        # For example, send it over network, save to custom format, etc.
        pass
    
    # Get final results (returned after iteration completes)
    result = scanner
    if result:
        print("\nFinal Results:")
        print(f"Final Decision: {result['final_decision']}")
        print(f"Detection Rate: {result['detection_rate']:.2f}%")