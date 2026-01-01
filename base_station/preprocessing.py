import cv2 as cv
import numpy as np

def white_balance(img, eps=1e-6):
   # White balance using Gray World Algorithm
   img = img.astype(np.float32)

   # Calculate the mean for each channel (B, G, R)
   mean = np.mean(img, axis=(0, 1))
   mean_gray = np.mean(mean)

   # eps is added to avoid division by zero
   scale = mean_gray / (mean + eps)
   scale = np.clip(scale, 0.5, 1.2)  # Prevent extreme amplification

   img *= scale
   img = np.clip(img, 0, 255)

   return img.astype(np.uint8)


def contrast_enhancement(img):
   lab_image = cv.cvtColor(img, cv.COLOR_BGR2LAB)
   L,A,B = cv.split(lab_image)
   # ClipLimit = Controls the enhancement limiting
   # TileGridSize = controls the size of grid 
   clahe = cv.createCLAHE(clipLimit=1, tileGridSize=(8,8))
   cl = clahe.apply(L)
   limg = cv.merge((cl,A,B))
   enhanced_img = cv.cvtColor(limg, cv.COLOR_LAB2BGR)
   return enhanced_img

def enhance_low_light(frame):
    lab = cv.cvtColor(frame, cv.COLOR_BGR2LAB)
    l, a, b = cv.split(lab)

    clahe = cv.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    l = clahe.apply(l)

    enhanced = cv.merge((l, a, b))
    return cv.cvtColor(enhanced, cv.COLOR_LAB2BGR)

if __name__ == "__main__":
   video = cv.VideoCapture('recording2.mp4')
   frame_count = 0
   while True:
      ret, frame = video.read()
      if not ret:
         break
      white_balanced_frame = white_balance(frame)
      enhanced_frame = contrast_enhancement(white_balanced_frame)
      final_frame = enhance_low_light(enhanced_frame)
      frame_count += 1

      cv.imshow('frame', final_frame)
      cv.imshow('original', frame)
      if cv.waitKey(1) & 0xFF == ord('q'):
         break

   video.release()
   cv.destroyAllWindows()
   print(frame_count)

