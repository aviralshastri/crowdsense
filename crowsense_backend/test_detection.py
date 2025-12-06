from detection import PersonDetector
import cv2
detector = PersonDetector(model_path="best.pt", conf_threshold=0.5)

frame = cv2.imread("test_image.jpg")  

if frame is not None:
    person_count = detector.detect(frame)
    print(f"Detected {person_count} persons")
else:
    print("Could not load image")