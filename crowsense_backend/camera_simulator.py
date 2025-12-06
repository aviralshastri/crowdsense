import cv2
import os
import time
from pathlib import Path

def play_frames_as_camera(folder_path, fps=30):
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    frame_files = sorted([
        os.path.join(folder_path, f) 
        for f in os.listdir(folder_path) 
        if f.lower().endswith(supported_formats)
    ])
    
    if not frame_files:
        print(f"No image files found in {folder_path}")
        return
    
    print(f"Found {len(frame_files)} frames")
    print(f"Playing at {fps} FPS")
    print("Press 'q' to quit")
    delay = 1.0 / fps
    
    cv2.namedWindow('Camera Feed', cv2.WINDOW_NORMAL)
    
    frame_idx = 0
    while True:
        start_time = time.time()

        frame = cv2.imread(frame_files[frame_idx])
        
        if frame is None:
            print(f"Error reading frame: {frame_files[frame_idx]}")
            frame_idx = (frame_idx + 1) % len(frame_files)
            continue
        cv2.imshow('Camera Feed', frame)

        frame_idx = (frame_idx + 1) % len(frame_files)

        elapsed = time.time() - start_time
        wait_time = max(1, int((delay - elapsed) * 1000))

        if cv2.waitKey(wait_time) & 0xFF == ord('q'):
            break
    
    cv2.destroyAllWindows()

if __name__ == "__main__":
    play_frames_as_camera("dummy_frames", fps=30)