from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import numpy as np
import cv2
import uvicorn
from collections import deque
import threading
import json
import mysql.connector
from mysql.connector import errorcode

# Add these imports at the top of main.py
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import base64
import os
import glob

from detection import PersonDetector
from fuzzylogic import FuzzyLogicIntegrator
from prediction import TCNPredictor, CrowdRecord

class Database:
    """MySQL database handler for storing crowd records"""
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3306,
        user: str = "root",
        password: str = "mysql",
        database: str = "crowdsensedb"
    ):
        self.cfg = {
            "user": user,
            "password": password,
            "host": host,
            "port": port,
            "database": database,
            "raise_on_warnings": True,
        }
        self.conn: Optional[mysql.connector.connection_cext.CMySQLConnection] = None
        self._connect_and_init()
    
    def _connect_and_init(self):
        try:
            self.conn = mysql.connector.connect(**self.cfg)
            self._ensure_table()
            print(f"[Database] Connected to MySQL at {self.cfg['host']}")
        except mysql.connector.Error as err:
            print(f"[Database] MySQL connection failed: {err}. Falling back to in-memory store.")
            self.conn = None
            self._mem_table: List[Dict] = []
    
    def _ensure_table(self):
        if self.conn is None:
            return
        cursor = self.conn.cursor()
        try:
            create_table = (
                "CREATE TABLE IF NOT EXISTS crowd_records ("
                "id INT AUTO_INCREMENT PRIMARY KEY,"
                "timestamp DATETIME NOT NULL,"
                "person_count INT NOT NULL,"
                "temperature FLOAT NOT NULL,"
                "noise FLOAT NOT NULL,"
                "air_quality FLOAT NOT NULL,"
                "fuzzy_score FLOAT NULL,"
                "fuzzy_status VARCHAR(50) NULL,"
                "predicted_count FLOAT NULL,"
                "INDEX idx_timestamp (timestamp)"
                ") ENGINE=InnoDB"
            )
            cursor.execute(create_table)
            self.conn.commit()
            print("[Database] Table 'crowd_records' ready")
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("[Database] Table already exists")
            else:
                raise
        finally:
            cursor.close()
    
    def insert_record(self, record: Dict) -> bool:
        """Insert a crowd record into database"""
        if self.conn is None:
            # Fallback to in-memory
            self._mem_table.append(record)
            return True
        
        try:
            cursor = self.conn.cursor()
            insert_sql = (
                "INSERT INTO crowd_records "
                "(timestamp, person_count, temperature, noise, air_quality, "
                "fuzzy_score, fuzzy_status, predicted_count) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            )
            
            vals = (
                record['timestamp'],
                record['person_count'],
                record['temperature'],
                record['noise'],
                record['air_quality'],
                record.get('fuzzy_score'),
                record.get('fuzzy_status'),
                record.get('predicted_count')
            )
            
            cursor.execute(insert_sql, vals)
            self.conn.commit()
            cursor.close()
            return True
            
        except Exception as e:
            print(f"[Database] Insert error: {e}")
            return False
    
    def fetch_last_n(self, n: int) -> List[Dict]:
        
        if self.conn is None:
            # Fallback to in-memory
            return self._mem_table[-n:]
        
        try:
            cursor = self.conn.cursor(dictionary=True)
            sql = (
                "SELECT timestamp, person_count, temperature, noise, air_quality, "
                "fuzzy_score, fuzzy_status, predicted_count "
                "FROM crowd_records ORDER BY timestamp DESC LIMIT %s"
            )
            cursor.execute(sql, (n,))
            rows = cursor.fetchall()
            cursor.close()
            
            # Convert datetime to string for JSON
            for row in rows:
                if isinstance(row['timestamp'], datetime):
                    row['timestamp'] = row['timestamp'].isoformat()
            
            return list(reversed(rows))  # Return chronological order
            
        except Exception as e:
            print(f"[Database] Fetch error: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        if self.conn is None:
            return {
                "total_records": len(self._mem_table),
                "storage_type": "in-memory"
            }
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM crowd_records")
            count = cursor.fetchone()[0]
            cursor.close()
            
            return {
                "total_records": count,
                "storage_type": "mysql"
            }
        except Exception as e:
            print(f"[Database] Stats error: {e}")
            return {"error": str(e)}

class SensorDataPacket(BaseModel):
    """Schema for sensor data packet"""
    timestamp: float
    sensor_data: dict = Field(..., description="Contains temperature, noise, air_quality arrays")
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": 1234567890.0,
                "sensor_data": {
                    "temperature": [27.0, 27.1, 27.1, 27.0, 27.1],
                    "sound_level": [242, 256, 259, 266, 243],
                    "air_quality": [172, 162, 172, 171, 166]
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
    fuzzy_score: float
    fuzzy_status: str
    person_count: int
    predicted_count: Optional[float]
    sensor_data: dict
    timestamp: str
    saved_to_db: bool


class PredictionResponse(BaseModel):
    """Response for crowd prediction"""
    success: bool
    current_count: int
    predicted_count_10min: Optional[float]
    fuzzy_assessment: dict
    timestamp: str

class GlobalState:
    """Thread-safe global state manager"""
    
    def __init__(self):
        self._lock = threading.Lock()
        
        self.cctv_count_buffer: deque = deque(maxlen=1800)
       
        print("[Init] Connecting to database...")
        self.db = Database(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="mysql",
            database="crowdsensedb"
        )
       
        self.prediction_history: List[CrowdRecord] = []
       
        print("[Init] Loading YOLO person detector...")
        self.person_detector = PersonDetector(
            model_path="best.pt",
            conf_threshold=0.5
        )
       
        print("[Init] Initializing Fuzzy Logic system...")
        self.fuzzy_logic = FuzzyLogicIntegrator()
        
        print("[Init] Initializing TCN predictor...")
        self.tcn_predictor = TCNPredictor(
            window_size=10,
            prediction_horizon=10
        )
        
        try:
            self.tcn_predictor.load_checkpoint("tcn_model.pth")
            print("[Init] Loaded existing TCN checkpoint")
        except:
            print("[Init] No existing TCN checkpoint found, starting fresh")
        
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
    
    def add_to_prediction_history(self, record: CrowdRecord):
        """Add record to prediction history"""
        with self._lock:
            self.prediction_history.append(record)
            # Keep only last 20 records
            if len(self.prediction_history) > 20:
                self.prediction_history = self.prediction_history[-20:]
    
    def get_prediction_history(self) -> List[CrowdRecord]:
        """Get prediction history"""
        with self._lock:
            return self.prediction_history.copy()

app = FastAPI(
    title="CrowdSense API",
    description="Real-time crowd sensing with YOLO detection, Fuzzy Logic, TCN prediction, and MySQL storage",
    version="2.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Changed to allow all origins for WebSocket
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("="*60)
print("INITIALIZING CROWDSENSE SYSTEM")
print("="*60)
state = GlobalState()
print("="*60)
print("SYSTEM READY")
print("="*60)

# Add this class after the GlobalState class
class CameraSimulator:
    """Simulates camera feeds by streaming frames from folders"""
    
    def __init__(self, camera_id: int, frames_folder: str, person_detector):
        self.camera_id = camera_id
        self.frames_folder = frames_folder
        self.person_detector = person_detector
        self.frame_files = []
        self.current_frame_index = 0
        self.load_frames()
    
    def load_frames(self):
        """Load all image files from the camera folder"""
        if os.path.exists(self.frames_folder):
            # Support jpg, jpeg, png
            patterns = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
            for pattern in patterns:
                self.frame_files.extend(
                    glob.glob(os.path.join(self.frames_folder, pattern))
                )
            self.frame_files.sort()  # Sort for consistent order
            print(f"[Camera {self.camera_id}] Loaded {len(self.frame_files)} frames from {self.frames_folder}")
        else:
            print(f"[Camera {self.camera_id}] Warning: Folder {self.frames_folder} not found")
    
    def get_next_frame(self) -> tuple:
        """Get next frame and person count - loops endlessly"""
        if not self.frame_files:
            return None, 0
        
        # Get current frame file
        frame_path = self.frame_files[self.current_frame_index]
        
        # Read and encode frame
        try:
            img = cv2.imread(frame_path)
            if img is None:
                # Move to next frame and try again
                self.current_frame_index = (self.current_frame_index + 1) % len(self.frame_files)
                return None, 0
            
            # Detect persons in frame
            person_count = self.person_detector.detect(img)
            
            # Encode frame to base64
            _, buffer = cv2.imencode('.jpg', img)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Move to next frame (loop back to start if needed - ENDLESS LOOP)
            self.current_frame_index = (self.current_frame_index + 1) % len(self.frame_files)
            
            # Log when loop restarts
            if self.current_frame_index == 0:
                print(f"[Camera {self.camera_id}] Restarting frame loop")
            
            return frame_base64, person_count
            
        except Exception as e:
            print(f"[Camera {self.camera_id}] Error reading frame: {e}")
            # Move to next frame even on error
            self.current_frame_index = (self.current_frame_index + 1) % len(self.frame_files)
            return None, 0
    
    def reset(self):
        """Reset to first frame"""
        self.current_frame_index = 0
        print(f"[Camera {self.camera_id}] Reset to first frame")


# Initialize camera simulators (add this after state = GlobalState())
camera_simulators = {}
for i in range(1, 7):
    folder_path = f"simulated_cameras/cam{i}"
    camera_simulators[i] = CameraSimulator(i, folder_path, state.person_detector)
    print(f"[Init] Camera {i} simulator initialized")


@app.websocket("/ws/camera/{camera_id}")
async def websocket_camera_feed(websocket: WebSocket, camera_id: int):
    """WebSocket endpoint for streaming simulated camera feeds - endless loop"""
    
    if camera_id < 1 or camera_id > 6:
        await websocket.close(code=1003)
        return
    
    await websocket.accept()
    print(f"[WebSocket] Camera {camera_id} client connected")
    
    simulator = camera_simulators.get(camera_id)
    
    # ADD THIS DEBUG INFO
    print(f"[Camera {camera_id}] Simulator exists: {simulator is not None}")
    if simulator:
        print(f"[Camera {camera_id}] Frame files: {len(simulator.frame_files)}")
        print(f"[Camera {camera_id}] Person detector: {simulator.person_detector is not None}")
    
    if not simulator or not simulator.frame_files:
        await websocket.send_json({
            "type": "error",
            "message": f"No frames available for camera {camera_id}"
        })
        await websocket.close()
        return
    
@app.get("/")
async def root():
    """Health check endpoint"""
    db_stats = state.db.get_statistics()
    
    return {
        "status": "online",
        "service": "CrowdSense API v2.0",
        "version": "2.0.0",
        "buffer_size": state.get_buffer_size(),
        "database": db_stats,
        "components": {
            "person_detection": "YOLO (best.pt)",
            "fuzzy_logic": "Active",
            "tcn_prediction": "Active",
            "database": db_stats.get("storage_type", "unknown")
        }
    }


@app.post("/stream_cctv", response_model=CCTVStreamResponse)
async def stream_cctv(file: UploadFile = File(...)):
    
    try:
       
        contents = await file.read()
        
       
        nparr = np.frombuffer(contents, np.uint8)
        
        
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid image format. Could not decode image."
            )
        
        person_count = state.person_detector.detect(img)
        
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
    
    try:
        
        sensor_data = data.sensor_data
        
        required_keys = ['temperature', 'sound_level', 'air_quality']
        if not all(key in sensor_data for key in required_keys):
            raise HTTPException(
                status_code=400,
                detail=f"Missing required sensor data fields: {required_keys}"
            )
        
        temp_avg = float(np.mean(sensor_data['temperature']))
        noise_avg = float(np.mean(sensor_data['sound_level']))
        aqi_avg = float(np.mean(sensor_data['air_quality']))
        
        cctv_average = state.get_cctv_average_and_clear()
        
        if cctv_average is None:
            print("[Warning] No CCTV data available, using default person_count = 0")
            person_count = 0  
        else:
            person_count = int(round(cctv_average))
        
        record_time = datetime.fromtimestamp(data.timestamp)
        
        fuzzy_result = state.fuzzy_logic.assess_crowd(
            person_count=person_count,
            temperature=temp_avg,
            noise_level=noise_avg,
            air_quality=aqi_avg
        )
        
        crowd_record = CrowdRecord(
            timestamp=record_time,
            crowd_count=float(person_count),
            temperature=temp_avg,
            noise=noise_avg,
            air_quality=aqi_avg
        )
        
        state.add_to_prediction_history(crowd_record)
        
        history = state.get_prediction_history()
        
        predicted_count = None
        if len(history) >= 10:
            predicted_count = state.tcn_predictor.predict(history)
        
        record_dict = {
            "timestamp": record_time.strftime('%Y-%m-%d %H:%M:%S'),
            "person_count": person_count,
            "temperature": temp_avg,
            "noise": noise_avg,
            "air_quality": aqi_avg,
            "fuzzy_score": fuzzy_result['score'],
            "fuzzy_status": fuzzy_result['status'],
            "predicted_count": predicted_count
        }
        
        saved = state.db.insert_record(record_dict)
        
        if len(history) >= 10 and predicted_count is not None:
            background_tasks.add_task(
                train_tcn_model,
                history,
                float(person_count)
            )
        
        return SensorDataResponse(
            success=True,
            message="Sensor data processed and saved to database",
            fuzzy_score=fuzzy_result['score'],
            fuzzy_status=fuzzy_result['status'],
            person_count=person_count,
            predicted_count=predicted_count,
            sensor_data={
                "temperature": temp_avg,
                "noise": noise_avg,
                "air_quality": aqi_avg
            },
            timestamp=record_time.isoformat(),
            saved_to_db=saved
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing sensor data: {str(e)}"
        )


@app.post("/predict_crowd", response_model=PredictionResponse)
async def predict_crowd(file: UploadFile = File(...)):
    
    try:
    
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid image format"
            )
        
        person_count = state.person_detector.detect(img)
        
        recent_records = state.db.fetch_last_n(1)
        if recent_records:
            last_record = recent_records[0]
            temp = last_record.get('temperature', 27.0)
            noise = last_record.get('noise', 250.0)
            aqi = last_record.get('air_quality', 170.0)
        else:
           
            temp, noise, aqi = 27.0, 250.0, 170.0
        
        fuzzy_result = state.fuzzy_logic.assess_crowd(
            person_count=person_count,
            temperature=temp,
            noise_level=noise,
            air_quality=aqi
        )
        
        history = state.get_prediction_history()
        predicted_count = None
        if len(history) >= 10:
            predicted_count = state.tcn_predictor.predict(history)
        
        return PredictionResponse(
            success=True,
            current_count=person_count,
            predicted_count_10min=predicted_count,
            fuzzy_assessment=fuzzy_result,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in prediction: {str(e)}"
        )


def train_tcn_model(history: List[CrowdRecord], actual_count: float):
    
    try:
        state.tcn_predictor.train_step(history, actual_count, steps=3)
        print(f"[TCN Training] Trained with actual count: {actual_count:.2f}")
        
        state.tcn_predictor.save_checkpoint("tcn_model.pth")
        
    except Exception as e:
        print(f"[Background] Error in TCN training: {e}")


@app.get("/stats")
async def get_stats():
    """Get current system statistics"""
    try:
        db_stats = state.db.get_statistics()
        records = state.db.fetch_last_n(100)
        
        if records:
            person_counts = [r['person_count'] for r in records]
            fuzzy_scores = [r['fuzzy_score'] for r in records if r.get('fuzzy_score')]
            
            stats = {
                "database": db_stats,
                "buffer_size": state.get_buffer_size(),
                "history_size": len(state.prediction_history),
                "recent_records": len(records),
                "average_crowd": sum(person_counts) / len(person_counts) if person_counts else 0,
                "average_fuzzy_score": sum(fuzzy_scores) / len(fuzzy_scores) if fuzzy_scores else 0,
                "max_crowd": max(person_counts) if person_counts else 0,
                "min_crowd": min(person_counts) if person_counts else 0
            }
        else:
            stats = {
                "database": db_stats,
                "buffer_size": state.get_buffer_size(),
                "history_size": len(state.prediction_history),
                "message": "No records yet"
            }
        
        return stats
        
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
        
        return {
            "count": len(records),
            "records": records
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching records: {str(e)}"
        )


@app.post("/save_checkpoint")
async def save_checkpoint():
    """Manually save TCN model checkpoint"""
    try:
        state.tcn_predictor.save_checkpoint("tcn_model.pth")
        return {
            "success": True,
            "message": "TCN model checkpoint saved successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving checkpoint: {str(e)}"
        )


@app.get("/model_info")
async def get_model_info():
    """Get information about loaded models"""
    return {
        "person_detector": state.person_detector.get_model_info(),
        "fuzzy_logic": "Active - 15 rules",
        "tcn_predictor": {
            "window_size": state.tcn_predictor.window_size,
            "prediction_horizon": state.tcn_predictor.prediction_horizon,
            "device": str(state.tcn_predictor.device)
        },
        "database": state.db.get_statistics()
    }


@app.get("/live_sensor_data")
async def get_live_sensor_data():
    """
    Get live sensor data from sensor_data.json file.
    Returns the latest sensor readings for display in the frontend.
    """
    try:
        import os
        sensor_file_path = "sensor_data.json"
        
        if not os.path.exists(sensor_file_path):
            raise HTTPException(
                status_code=404,
                detail="sensor_data.json file not found"
            )
        
        with open(sensor_file_path, 'r') as f:
            sensor_json = json.load(f)
        
        if isinstance(sensor_json, list) and len(sensor_json) > 0:
            latest_data = sensor_json[-1]
        elif isinstance(sensor_json, dict):
            latest_data = sensor_json
        else:
            raise HTTPException(
                status_code=500,
                detail="Invalid sensor data format"
            )
        
        data = latest_data.get('data', {})
        timestamp_str = latest_data.get('timestamp', datetime.now().isoformat())
        
        temperature_array = data.get('temperature', [26.0])
        humidity_array = data.get('humidity', [32.0])
        mq_array = data.get('mq', [580])  
        ky_array = data.get('ky', [370])  
        pir_total = data.get('pir_total', 0)
        
        avg_temp = sum(temperature_array) / len(temperature_array) if temperature_array else 26.0
        avg_humidity = sum(humidity_array) / len(humidity_array) if humidity_array else 32.0
        avg_aqi = sum(mq_array) / len(mq_array) if mq_array else 580
        avg_noise = sum(ky_array) / len(ky_array) if ky_array else 370
        
        def get_status(temp, noise, aqi):
            critical_count = sum([
                temp >= 35,
                noise >= 400,
                aqi >= 600
            ])
            
            if critical_count >= 2:
                return "critical"
            elif temp >= 32 or noise >= 380 or aqi >= 590:
                return "warning"
            else:
                return "normal"
        
        status = get_status(avg_temp, avg_noise, avg_aqi)
        
        zone_data = {
            "id": 1,
            "name": "Main Sensor Zone",
            "temp": round(avg_temp, 1),
            "humidity": round(avg_humidity, 1),
            "noise": round(avg_noise, 0),
            "aqi": round(avg_aqi, 0),
            "pir": pir_total > 0,
            "status": status,
            "timestamp": timestamp_str,
            "raw_data": {
                "temperature": temperature_array,
                "humidity": humidity_array,
                "mq": mq_array,
                "ky": ky_array,
                "pir_total": pir_total
            }
        }
        
        return {
            "success": True,
            "zone": zone_data,
            "last_updated": timestamp_str
        }
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="sensor_data.json file not found"
        )
    except Exception as e:
        print(f"[Sensor Data] Error reading sensor data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reading sensor data: {str(e)}"
        )


@app.get("/alerts")
async def get_alerts():
    """
    Get zone-based alerts with crowd density and barricading status.
    Returns alerts in the format expected by the frontend.
    Generates alerts from latest data for different assessment criteria.
    """
    try:
       
        sensor_file_path = "sensor_data.json"
        latest_sensor_data = None
        
        try:
            import os
            if os.path.exists(sensor_file_path):
                with open(sensor_file_path, 'r') as f:
                    sensor_json = json.load(f)
                    
                    if isinstance(sensor_json, list) and len(sensor_json) > 0:
                        latest_sensor_data = sensor_json[-1]
                        print(f"[Alerts] Loaded sensor data from file: {sensor_file_path}")
                    elif isinstance(sensor_json, dict):
                        latest_sensor_data = sensor_json
                        print(f"[Alerts] Loaded sensor data from file: {sensor_file_path}")
        except Exception as e:
            print(f"[Alerts] Could not read sensor_data.json: {e}")
        
        if latest_sensor_data:
            data = latest_sensor_data.get('data', {})
            
            temperature_array = data.get('temperature', [26.0])
            mq_array = data.get('mq', [580])  
            ky_array = data.get('ky', [370]) 
            pir_count = data.get('pir_total', 0)  
            
            temperature = sum(temperature_array) / len(temperature_array) if temperature_array else 26.0
            air_quality = sum(mq_array) / len(mq_array) if mq_array else 580
            noise = sum(ky_array) / len(ky_array) if ky_array else 370
            person_count = pir_count
            
            timestamp_str = latest_sensor_data.get('timestamp', datetime.now().isoformat())
            try:
                dt = datetime.fromisoformat(timestamp_str)
                time_str = dt.strftime("%I:%M %p")
            except:
                time_str = datetime.now().strftime("%I:%M %p")
            
            print(f"[Alerts] Sensor values - Temp: {temperature:.1f}°C, Noise: {noise:.0f}, AQI: {air_quality:.0f}, People: {person_count}")
            
            alerts = []
            
            if person_count >= 100:
                alerts.append({
                    "zone": "Zone 1",
                    "crowd": "CRITICAL CROWD",
                    "level": "critical",
                    "barricade": "YES",
                    "time": time_str,
                    "icon": "🔴",
                    "person_count": person_count
                })
            elif person_count >= 50:
                alerts.append({
                    "zone": "Zone 1",
                    "crowd": "High Density",
                    "level": "high",
                    "barricade": "YES",
                    "time": time_str,
                    "icon": "🚨",
                    "person_count": person_count
                })
            elif person_count >= 20:
                alerts.append({
                    "zone": "Zone 1",
                    "crowd": "Medium Density",
                    "level": "medium",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "⚠️",
                    "person_count": person_count
                })
            else:
                alerts.append({
                    "zone": "Zone 1",
                    "crowd": "Low Density",
                    "level": "low",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "✅",
                    "person_count": person_count
                })
            
            if temperature >= 35:
                alerts.append({
                    "zone": "Zone 2",
                    "crowd": f"CRITICAL TEMPERATURE ({temperature:.1f}°C)",
                    "level": "critical",
                    "barricade": "YES",
                    "time": time_str,
                    "icon": "🌡️"
                })
            elif temperature >= 30:
                alerts.append({
                    "zone": "Zone 2",
                    "crowd": f"High Temperature ({temperature:.1f}°C)",
                    "level": "high",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "🌡️"
                })
            elif temperature >= 25:
                alerts.append({
                    "zone": "Zone 2",
                    "crowd": f"Moderate Temperature ({temperature:.1f}°C)",
                    "level": "medium",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "🌡️"
                })
            
            if noise >= 400:
                alerts.append({
                    "zone": "Zone 3",
                    "crowd": f"CRITICAL NOISE ({noise:.0f})",
                    "level": "critical",
                    "barricade": "YES",
                    "time": time_str,
                    "icon": "🔊"
                })
            elif noise >= 380:
                alerts.append({
                    "zone": "Zone 3",
                    "crowd": f"High Noise Level ({noise:.0f})",
                    "level": "high",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "🔊"
                })
            elif noise >= 360:
                alerts.append({
                    "zone": "Zone 3",
                    "crowd": f"Moderate Noise ({noise:.0f})",
                    "level": "medium",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "🔊"
                })
            
            if air_quality >= 600:
                alerts.append({
                    "zone": "Zone 4",
                    "crowd": f"CRITICAL AIR QUALITY ({air_quality:.0f})",
                    "level": "critical",
                    "barricade": "YES",
                    "time": time_str,
                    "icon": "💨"
                })
            elif air_quality >= 590:
                alerts.append({
                    "zone": "Zone 4",
                    "crowd": f"Poor Air Quality ({air_quality:.0f})",
                    "level": "high",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "💨"
                })
            elif air_quality >= 580:
                alerts.append({
                    "zone": "Zone 4",
                    "crowd": f"Moderate Air Quality ({air_quality:.0f})",
                    "level": "medium",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "💨"
                })
            
            high_risk_count = sum([
                person_count >= 50,
                temperature >= 30,
                noise >= 380,
                air_quality >= 590
            ])
            
            if high_risk_count >= 3:
                alerts.append({
                    "zone": "Zone 5",
                    "crowd": "Overall Status: CRITICAL",
                    "level": "critical",
                    "barricade": "YES",
                    "time": time_str,
                    "icon": "🎯"
                })
            elif high_risk_count >= 2:
                alerts.append({
                    "zone": "Zone 5",
                    "crowd": "Overall Status: HIGH RISK",
                    "level": "high",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "🎯"
                })
            elif high_risk_count >= 1:
                alerts.append({
                    "zone": "Zone 5",
                    "crowd": "Overall Status: MODERATE",
                    "level": "medium",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "🎯"
                })
            else:
                alerts.append({
                    "zone": "Zone 5",
                    "crowd": "Overall Status: LOW RISK",
                    "level": "low",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "🎯"
                })
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            alerts.sort(key=lambda x: severity_order.get(x['level'], 4))
            
            return {
                "success": True,
                "alerts": alerts
            }
        
        records = state.db.fetch_last_n(10)
        
        if not records or len(records) == 0:
            
            print("[Alerts] No sensor data file and no database records, generating dummy data")
            current_time = datetime.now().strftime("%I:%M %p")
            
            return {
                "success": True,
                "alerts": [
                    {
                        "zone": "Zone 1",
                        "crowd": "Low Density",
                        "level": "low",
                        "barricade": "NO",
                        "time": current_time,
                        "icon": "✅",
                        "person_count": 0
                    },
                    {
                        "zone": "Zone 2",
                        "crowd": "Moderate Temperature (27.0°C)",
                        "level": "medium",
                        "barricade": "NO",
                        "time": current_time,
                        "icon": "🌡️"
                    },
                    {
                        "zone": "Zone 3",
                        "crowd": "Moderate Noise (370)",
                        "level": "medium",
                        "barricade": "NO",
                        "time": current_time,
                        "icon": "🔊"
                    },
                    {
                        "zone": "Zone 4",
                        "crowd": "Moderate Air Quality (580)",
                        "level": "medium",
                        "barricade": "NO",
                        "time": current_time,
                        "icon": "💨"
                    },
                    {
                        "zone": "Zone 5",
                        "crowd": "Overall Status: MODERATE",
                        "level": "medium",
                        "barricade": "NO",
                        "time": current_time,
                        "icon": "🎯"
                    }
                ]
            }
        
        alerts = []
        
        latest_record = records[-1]
        person_count = latest_record.get('person_count', 0)
        temperature = latest_record.get('temperature', 0)
        noise = latest_record.get('noise', 0)
        air_quality = latest_record.get('air_quality', 0)
        fuzzy_status = latest_record.get('fuzzy_status', 'LOW').upper()
        predicted_count = latest_record.get('predicted_count', None)
        
        try:
            timestamp = latest_record.get('timestamp')
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp)
            else:
                dt = timestamp
            time_str = dt.strftime("%I:%M %p")
        except:
            time_str = datetime.now().strftime("%I:%M %p")
        
        if person_count >= 100:
            alerts.append({
                "zone": "Zone 1",
                "crowd": "CRITICAL CROWD",
                "level": "critical",
                "barricade": "YES",
                "time": time_str,
                "icon": "🔴",
                "person_count": person_count
            })
        elif person_count >= 50:
            alerts.append({
                "zone": "Zone 1",
                "crowd": "High Density",
                "level": "high",
                "barricade": "YES",
                "time": time_str,
                "icon": "🚨",
                "person_count": person_count
            })
        elif person_count >= 20:
            alerts.append({
                "zone": "Zone 1",
                "crowd": "Medium Density",
                "level": "medium",
                "barricade": "NO",
                "time": time_str,
                "icon": "⚠️",
                "person_count": person_count
            })
        else:
            alerts.append({
                "zone": "Zone 1",
                "crowd": "Low Density",
                "level": "low",
                "barricade": "NO",
                "time": time_str,
                "icon": "✅",
                "person_count": person_count
            })
        
        if temperature >= 35:
            alerts.append({
                "zone": "Zone 2",
                "crowd": f"CRITICAL TEMPERATURE ({temperature:.1f}°C)",
                "level": "critical",
                "barricade": "YES",
                "time": time_str,
                "icon": "🌡️"
            })
        elif temperature >= 30:
            alerts.append({
                "zone": "Zone 2",
                "crowd": f"High Temperature ({temperature:.1f}°C)",
                "level": "high",
                "barricade": "NO",
                "time": time_str,
                "icon": "🌡️"
            })
        elif temperature >= 25:
            alerts.append({
                "zone": "Zone 2",
                "crowd": f"Moderate Temperature ({temperature:.1f}°C)",
                "level": "medium",
                "barricade": "NO",
                "time": time_str,
                "icon": "🌡️"
            })
        
        if noise >= 350:
            alerts.append({
                "zone": "Zone 3",
                "crowd": f"CRITICAL NOISE ({noise:.0f} dB)",
                "level": "critical",
                "barricade": "YES",
                "time": time_str,
                "icon": "🔊"
            })
        elif noise >= 300:
            alerts.append({
                "zone": "Zone 3",
                "crowd": f"High Noise Level ({noise:.0f} dB)",
                "level": "high",
                "barricade": "NO",
                "time": time_str,
                "icon": "🔊"
            })
        elif noise >= 250:
            alerts.append({
                "zone": "Zone 3",
                "crowd": f"Moderate Noise ({noise:.0f} dB)",
                "level": "medium",
                "barricade": "NO",
                "time": time_str,
                "icon": "🔊"
            })
        
        if air_quality >= 250:
            alerts.append({
                "zone": "Zone 4",
                "crowd": f"CRITICAL AIR QUALITY ({air_quality:.0f})",
                "level": "critical",
                "barricade": "YES",
                "time": time_str,
                "icon": "💨"
            })
        elif air_quality >= 200:
            alerts.append({
                "zone": "Zone 4",
                "crowd": f"Poor Air Quality ({air_quality:.0f})",
                "level": "high",
                "barricade": "NO",
                "time": time_str,
                "icon": "💨"
            })
        elif air_quality >= 150:
            alerts.append({
                "zone": "Zone 4",
                "crowd": f"Moderate Air Quality ({air_quality:.0f})",
                "level": "medium",
                "barricade": "NO",
                "time": time_str,
                "icon": "💨"
            })
        
        if fuzzy_status in ['CRITICAL', 'HIGH']:
            level = "critical" if fuzzy_status == 'CRITICAL' else "high"
            alerts.append({
                "zone": "Zone 5",
                "crowd": f"Overall Status: {fuzzy_status}",
                "level": level,
                "barricade": "YES" if level == "critical" else "NO",
                "time": time_str,
                "icon": "🎯"
            })
        elif fuzzy_status == 'MODERATE':
            alerts.append({
                "zone": "Zone 5",
                "crowd": "Overall Status: MODERATE",
                "level": "medium",
                "barricade": "NO",
                "time": time_str,
                "icon": "🎯"
            })
        
        if predicted_count is not None and predicted_count > 0:
            if predicted_count >= 100:
                alerts.append({
                    "zone": "Zone 6",
                    "crowd": f"Predicted: CRITICAL ({predicted_count:.0f} people)",
                    "level": "critical",
                    "barricade": "YES",
                    "time": time_str,
                    "icon": "🔮"
                })
            elif predicted_count >= 50:
                alerts.append({
                    "zone": "Zone 6",
                    "crowd": f"Predicted: HIGH ({predicted_count:.0f} people)",
                    "level": "high",
                    "barricade": "YES",
                    "time": time_str,
                    "icon": "🔮"
                })
            elif predicted_count >= 20:
                alerts.append({
                    "zone": "Zone 6",
                    "crowd": f"Predicted: MODERATE ({predicted_count:.0f} people)",
                    "level": "medium",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "🔮"
                })
        
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        alerts.sort(key=lambda x: severity_order.get(x['level'], 4))
        
        return {
            "success": True,
            "alerts": alerts
        }
        
    except Exception as e:
        print(f"[Alerts] Error generating alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating alerts: {str(e)}"
        )
   
    try:
        
        records = state.db.fetch_last_n(10)
        
        if not records or len(records) == 0:
           
            print("[Alerts] No records in database, generating dummy data for testing")
            current_time = datetime.now().strftime("%I:%M %p")
            
            return {
                "success": True,
                "alerts": [
                    {
                        "zone": "Zone 1",
                        "crowd": "Low Density",
                        "level": "low",
                        "barricade": "NO",
                        "time": current_time,
                        "icon": "✅",
                        "person_count": 0
                    },
                    {
                        "zone": "Zone 2",
                        "crowd": "Moderate Temperature (27.0°C)",
                        "level": "medium",
                        "barricade": "NO",
                        "time": current_time,
                        "icon": "🌡️"
                    },
                    {
                        "zone": "Zone 3",
                        "crowd": "Moderate Noise (250 dB)",
                        "level": "medium",
                        "barricade": "NO",
                        "time": current_time,
                        "icon": "🔊"
                    },
                    {
                        "zone": "Zone 4",
                        "crowd": "Moderate Air Quality (170)",
                        "level": "medium",
                        "barricade": "NO",
                        "time": current_time,
                        "icon": "💨"
                    },
                    {
                        "zone": "Zone 5",
                        "crowd": "Overall Status: MODERATE",
                        "level": "medium",
                        "barricade": "NO",
                        "time": current_time,
                        "icon": "🎯"
                    }
                ]
            }
        
        alerts = []
        
       
        latest_record = records[-1]
        person_count = latest_record.get('person_count', 0)
        temperature = latest_record.get('temperature', 0)
        noise = latest_record.get('noise', 0)
        air_quality = latest_record.get('air_quality', 0)
        fuzzy_status = latest_record.get('fuzzy_status', 'LOW').upper()
        predicted_count = latest_record.get('predicted_count', None)
       
        try:
            timestamp = latest_record.get('timestamp')
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp)
            else:
                dt = timestamp
            time_str = dt.strftime("%I:%M %p")
        except:
            time_str = datetime.now().strftime("%I:%M %p")
        
        if person_count >= 100:
            alerts.append({
                "zone": "Zone 1",
                "crowd": "CRITICAL CROWD",
                "level": "critical",
                "barricade": "YES",
                "time": time_str,
                "icon": "🔴",
                "person_count": person_count
            })
        elif person_count >= 50:
            alerts.append({
                "zone": "Zone 1",
                "crowd": "High Density",
                "level": "high",
                "barricade": "YES",
                "time": time_str,
                "icon": "🚨",
                "person_count": person_count
            })
        elif person_count >= 20:
            alerts.append({
                "zone": "Zone 1",
                "crowd": "Medium Density",
                "level": "medium",
                "barricade": "NO",
                "time": time_str,
                "icon": "⚠️",
                "person_count": person_count
            })
        else:
            alerts.append({
                "zone": "Zone 1",
                "crowd": "Low Density",
                "level": "low",
                "barricade": "NO",
                "time": time_str,
                "icon": "✅",
                "person_count": person_count
            })
        
        if temperature >= 35:
            alerts.append({
                "zone": "Zone 2",
                "crowd": f"CRITICAL TEMPERATURE ({temperature:.1f}°C)",
                "level": "critical",
                "barricade": "YES",
                "time": time_str,
                "icon": "🌡️"
            })
        elif temperature >= 30:
            alerts.append({
                "zone": "Zone 2",
                "crowd": f"High Temperature ({temperature:.1f}°C)",
                "level": "high",
                "barricade": "NO",
                "time": time_str,
                "icon": "🌡️"
            })
        elif temperature >= 25:
            alerts.append({
                "zone": "Zone 2",
                "crowd": f"Moderate Temperature ({temperature:.1f}°C)",
                "level": "medium",
                "barricade": "NO",
                "time": time_str,
                "icon": "🌡️"
            })
        
        if noise >= 350:
            alerts.append({
                "zone": "Zone 3",
                "crowd": f"CRITICAL NOISE ({noise:.0f} dB)",
                "level": "critical",
                "barricade": "YES",
                "time": time_str,
                "icon": "🔊"
            })
        elif noise >= 300:
            alerts.append({
                "zone": "Zone 3",
                "crowd": f"High Noise Level ({noise:.0f} dB)",
                "level": "high",
                "barricade": "NO",
                "time": time_str,
                "icon": "🔊"
            })
        elif noise >= 250:
            alerts.append({
                "zone": "Zone 3",
                "crowd": f"Moderate Noise ({noise:.0f} dB)",
                "level": "medium",
                "barricade": "NO",
                "time": time_str,
                "icon": "🔊"
            })
        
        if air_quality >= 250:
            alerts.append({
                "zone": "Zone 4",
                "crowd": f"CRITICAL AIR QUALITY ({air_quality:.0f})",
                "level": "critical",
                "barricade": "YES",
                "time": time_str,
                "icon": "💨"
            })
        elif air_quality >= 200:
            alerts.append({
                "zone": "Zone 4",
                "crowd": f"Poor Air Quality ({air_quality:.0f})",
                "level": "high",
                "barricade": "NO",
                "time": time_str,
                "icon": "💨"
            })
        elif air_quality >= 150:
            alerts.append({
                "zone": "Zone 4",
                "crowd": f"Moderate Air Quality ({air_quality:.0f})",
                "level": "medium",
                "barricade": "NO",
                "time": time_str,
                "icon": "💨"
            })
        if fuzzy_status in ['CRITICAL', 'HIGH']:
            level = "critical" if fuzzy_status == 'CRITICAL' else "high"
            alerts.append({
                "zone": "Zone 5",
                "crowd": f"Overall Status: {fuzzy_status}",
                "level": level,
                "barricade": "YES" if level == "critical" else "NO",
                "time": time_str,
                "icon": "🎯"
            })
        elif fuzzy_status == 'MODERATE':
            alerts.append({
                "zone": "Zone 5",
                "crowd": "Overall Status: MODERATE",
                "level": "medium",
                "barricade": "NO",
                "time": time_str,
                "icon": "🎯"
            })
        
        if predicted_count is not None and predicted_count > 0:
            if predicted_count >= 100:
                alerts.append({
                    "zone": "Zone 6",
                    "crowd": f"Predicted: CRITICAL ({predicted_count:.0f} people)",
                    "level": "critical",
                    "barricade": "YES",
                    "time": time_str,
                    "icon": "🔮"
                })
            elif predicted_count >= 50:
                alerts.append({
                    "zone": "Zone 6",
                    "crowd": f"Predicted: HIGH ({predicted_count:.0f} people)",
                    "level": "high",
                    "barricade": "YES",
                    "time": time_str,
                    "icon": "🔮"
                })
            elif predicted_count >= 20:
                alerts.append({
                    "zone": "Zone 6",
                    "crowd": f"Predicted: MODERATE ({predicted_count:.0f} people)",
                    "level": "medium",
                    "barricade": "NO",
                    "time": time_str,
                    "icon": "🔮"
                })
        
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        alerts.sort(key=lambda x: severity_order.get(x['level'], 4))
        
        return {
            "success": True,
            "alerts": alerts
        }
        
    except Exception as e:
        print(f"[Alerts] Error generating alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating alerts: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,  
        reload=True,
        log_level="info"
    )


