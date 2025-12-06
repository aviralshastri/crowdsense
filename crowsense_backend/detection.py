import cv2
import numpy as np
from ultralytics import YOLO
from typing import Optional, Tuple, List


class PersonDetector:
    
    def __init__(
        self,
        model_path: str = "best.pt",
        conf_threshold: float = 0.5,
        device: Optional[str] = None
    ):
       
        print(f"[PersonDetector] Loading model: {model_path}")
        
        # Load YOLO model
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        
        # Set device
        if device:
            self.device = device
        else:
            import torch
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        print(f"[PersonDetector] Model loaded on: {self.device}")
    
    def detect(self, frame: np.ndarray) -> int:
        
        results = self.model(
            frame,
            conf=self.conf_threshold,
            verbose=False
        )
        person_count = 0
        if results[0].boxes is not None:
            person_count = len(results[0].boxes)
        
        return person_count
    
    def detect_with_boxes(self, frame: np.ndarray) -> Tuple[int, List[List[int]], np.ndarray]:
        
        results = self.model(
            frame,
            conf=self.conf_threshold,
            verbose=False
        )
        
        annotated = frame.copy()
        person_count = 0
        boxes = []
        
        if results[0].boxes is not None:
            person_count = len(results[0].boxes)
            
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0])
                
                boxes.append([x1, y1, x2, y2])
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                label = f'Person {conf:.2f}'
                cv2.putText(
                    annotated, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
                )
        
        cv2.putText(
            annotated, f'Total: {person_count}', (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3
        )
        
        return person_count, boxes, annotated