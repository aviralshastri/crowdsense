from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import numpy as np
import cv2
import uvicorn
from collections import deque
import threading

# Import from helper_module.py
from helper_module import (
    Database,
    OutlierRejector,
    StreamingNormalizer,
    FeatureBuilder,
    SensorRegressor,
    KalmanFusion,
    IngestHandler,
    ModelManager,
    Predictor,
    Trainer,
    YOLOCrowdCounter,
    MinuteRecord
)

# =====================================================
# Pydantic Models for Request/Response
# =====================================================

class SensorDataPacket(BaseModel):
    """Schema for ESP32 sensor data packet"""
    timestamp: float
    sensor_data: dict = Field(..., description="Contains noise, gas, temp arrays and pir_count")
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": 1234567890.0,
                "sensor_data": {
                    "noise": [45.2, 46.1, 44.8, 45.5, 46.0],
                    "gas": [120.5, 121.3, 119.8, 120.2, 121.0],
                    "temp": [22.5, 22.6, 22.4, 22.5, 22.6],
                    "pir_count": 15
                }
            }
        }


class CCTVStreamResponse(BaseModel):
    """Response for CCTV frame processing"""
    success: bool
    person_count: int
    message: str
    buffer_size: int


class SensorDataResponse(BaseModel):
    """Response for sensor data ingestion"""
    success: bool
    message: str
    fused_gt: float
    sensor_est: float
    cctv_average: Optional[float]
    timestamp: str


# =====================================================
# Global State Management
# =====================================================

class GlobalState:
    """Thread-safe global state manager"""
    
    def __init__(self):
        self._lock = threading.Lock()
        
        # Rotating buffer for CCTV person counts (max 1800 elements = 1 minute @ 30fps)
        self.cctv_count_buffer: deque = deque(maxlen=1800)
        
        # Initialize database with fallback to in-memory
        print("[Init] Connecting to database...")
        self.db = Database(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="mysql",
            database="crowdsensedb"
        )
        
        # Initialize preprocessing components
        print("[Init] Initializing preprocessing pipeline...")
        self.outlier = OutlierRejector()
        self.normalizer = StreamingNormalizer()
        self.builder = FeatureBuilder()
        
        # Initialize fusion components
        print("[Init] Initializing fusion components...")
        self.sensor_reg = SensorRegressor(lr=1e-4)
        self.kalman = KalmanFusion()
        
        # Initialize ingest handler
        self.ingest_handler = IngestHandler(
            self.db,
            self.outlier,
            self.normalizer,
            self.builder,
            self.sensor_reg,
            self.kalman
        )
        
        # Initialize model manager for TCN predictions
        print("[Init] Initializing TCN model...")
        self.model_mgr = ModelManager(window_size=10, lr=3e-4)
        
        # Try to load existing checkpoint
        try:
            self.model_mgr.load("tcn_checkpoint.pth")
            print("[Init] Loaded existing model checkpoint")
        except:
            print("[Init] No existing checkpoint found, starting fresh")
        
        # Initialize predictor and trainer
        self.predictor = Predictor(self.db, self.model_mgr, self.normalizer)
        self.trainer = Trainer(self.db, self.model_mgr, self.normalizer)
        
        # Initialize YOLO crowd counter
        print("[Init] Loading YOLO model...")
        self.yolo_counter = YOLOCrowdCounter(
            model_path="detector_model.pt",  # Make sure this file exists or will be downloaded
            conf_threshold=0.25,
            iou_threshold=0.45,
            verbose=False
        )
        
        print("[Init] All components initialized successfully!")
    
    def add_cctv_count(self, count: int) -> int:
        """Thread-safe add count to buffer and return current buffer size"""
        with self._lock:
            self.cctv_count_buffer.append(count)
            return len(self.cctv_count_buffer)
    
    def get_cctv_average_and_clear(self) -> Optional[float]:
        """Thread-safe get average and clear buffer"""
        with self._lock:
            if len(self.cctv_count_buffer) == 0:
                return None
            avg = sum(self.cctv_count_buffer) / len(self.cctv_count_buffer)
            self.cctv_count_buffer.clear()
            return avg
    
    def get_buffer_size(self) -> int:
        """Thread-safe get buffer size"""
        with self._lock:
            return len(self.cctv_count_buffer)


# =====================================================
# FastAPI Application
# =====================================================

app = FastAPI(
    title="CrowdSense API",
    description="Real-time crowd sensing with sensor fusion and temporal prediction",
    version="1.0.0"
)

# Initialize global state
print("="*60)
print("INITIALIZING CROWDSENSE SYSTEM")
print("="*60)
state = GlobalState()
print("="*60)
print("SYSTEM READY")
print("="*60)


# =====================================================
# API Routes
# =====================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "CrowdSense API",
        "version": "1.0.0",
        "buffer_size": state.get_buffer_size(),
        "yolo_info": state.yolo_counter.get_model_info()
    }


@app.post("/stream_cctv", response_model=CCTVStreamResponse)
async def stream_cctv(file: UploadFile = File(...)):
    """
    Process CCTV frame and count people using YOLO.
    Stores count in rotating buffer (max 1800 elements).
    
    Expected: Image file (JPEG, PNG, etc.)
    Returns: Person count and buffer status
    """
    try:
        # Read uploaded image file
        contents = await file.read()
        
        # Convert bytes to numpy array
        nparr = np.frombuffer(contents, np.uint8)
        
        # Decode image
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid image format. Could not decode image."
            )
        
        # Run YOLO prediction
        person_count = state.yolo_counter.predict(img)
        
        # Add to rotating buffer
        buffer_size = state.add_cctv_count(person_count)
        
        return CCTVStreamResponse(
            success=True,
            person_count=person_count,
            message=f"Frame processed successfully. Detected {person_count} person(s).",
            buffer_size=buffer_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing frame: {str(e)}"
        )


@app.post("/push_sensor_data", response_model=SensorDataResponse)
async def push_sensor_data(data: SensorDataPacket, background_tasks: BackgroundTasks):
    """
    Receive sensor data from ESP32, fuse with CCTV average, and store in DB.
    This endpoint should be called every 1 minute by the ESP32.
    
    Flow:
    1. Calculate average of CCTV counts from buffer (last 1 minute)
    2. Average sensor arrays (noise, gas, temp)
    3. Create MinuteRecord with sensor data
    4. Process through pipeline (outlier rejection, normalization, fusion)
    5. Store in database
    6. Clear CCTV buffer for next minute
    7. Trigger prediction and training in background
    """
    try:
        # Extract sensor data
        sensor_data = data.sensor_data
        
        # Validate sensor data structure
        if not all(key in sensor_data for key in ['noise', 'gas', 'temp', 'pir_count']):
            raise HTTPException(
                status_code=400,
                detail="Missing required sensor data fields (noise, gas, temp, pir_count)"
            )
        
        # Calculate averages from sensor arrays
        noise_avg = float(np.mean(sensor_data['noise']))
        gas_avg = float(np.mean(sensor_data['gas']))
        temp_avg = float(np.mean(sensor_data['temp']))
        pir_count = float(sensor_data['pir_count'])
        
        # Get CCTV average from buffer and clear it
        cctv_average = state.get_cctv_average_and_clear()
        
        # Create timestamp
        record_time = datetime.fromtimestamp(data.timestamp)
        
        # Create MinuteRecord
        raw_record = MinuteRecord(
            time=record_time,
            cctv_count=cctv_average,  # May be None if no CCTV data
            gas=gas_avg,
            pir=pir_count,
            temperature=temp_avg,
            noise=noise_avg
        )
        
        # Process through ingestion pipeline
        # This will: clean outliers, normalize, predict sensor_est, fuse with cctv, save to DB
        processed_record = state.ingest_handler.process_minute(raw_record)
        
        # Schedule background tasks for prediction and training
        background_tasks.add_task(run_prediction_and_training)
        
        return SensorDataResponse(
            success=True,
            message=f"Sensor data processed and stored successfully",
            fused_gt=processed_record.fused_gt,
            sensor_est=processed_record.sensor_est,
            cctv_average=cctv_average,
            timestamp=record_time.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing sensor data: {str(e)}"
        )


# =====================================================
# Background Tasks
# =====================================================

def run_prediction_and_training():
    """
    Background task to run prediction and training after sensor data ingestion.
    This runs asynchronously to avoid blocking the API response.
    """
    try:
        # Run predictor (predict next minute's crowd count)
        pred_result = state.predictor.run()
        if pred_result:
            timestamp, prediction = pred_result
            print(f"[Predictor] Predicted {prediction:.2f} for timestamp {timestamp}")
        
        # Run trainer (update model with latest fused_gt)
        train_result = state.trainer.run()
        if train_result:
            timestamp, target, error = train_result
            print(f"[Trainer] Trained on {timestamp}, target={target:.2f}, error={error:.2f}")
            
    except Exception as e:
        print(f"[Background] Error in prediction/training: {e}")


@app.get("/stats")
async def get_stats():
    """Get current system statistics"""
    try:
        # Fetch last 10 records from DB
        records = state.db.fetch_last_n(10)
        
        # Calculate stats
        if records:
            recent_errors = [r.error for r in records if r.error is not None]
            avg_error = sum(recent_errors) / len(recent_errors) if recent_errors else None
            
            recent_predictions = [r.prediction for r in records if r.prediction is not None]
            avg_prediction = sum(recent_predictions) / len(recent_predictions) if recent_predictions else None
        else:
            avg_error = None
            avg_prediction = None
        
        return {
            "buffer_size": state.get_buffer_size(),
            "records_in_db": len(records),
            "avg_recent_error": avg_error,
            "avg_recent_prediction": avg_prediction,
            "model_window_size": state.model_mgr.window_size,
            "replay_buffer_size": len(state.model_mgr.replay),
            "normalizer_counts": {
                name: state.normalizer._state[name]["count"] 
                for name in ["gas", "pir", "temperature", "noise"]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stats: {str(e)}"
        )


@app.get("/recent_records")
async def get_recent_records(n: int = 10):
    """Get last N records from database"""
    try:
        if n < 1 or n > 1000:
            raise HTTPException(
                status_code=400,
                detail="Parameter 'n' must be between 1 and 1000"
            )
        
        records = state.db.fetch_last_n(n)
        
        # Convert to dict for JSON serialization
        records_dict = []
        for r in records:
            records_dict.append({
                "time": r.time.isoformat(),
                "cctv_count": r.cctv_count,
                "gas": r.gas,
                "pir": r.pir,
                "temperature": r.temperature,
                "noise": r.noise,
                "sensor_est": r.sensor_est,
                "fused_gt": r.fused_gt,
                "prediction": r.prediction,
                "error": r.error
            })
        
        return {
            "count": len(records_dict),
            "records": records_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching records: {str(e)}"
        )



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )