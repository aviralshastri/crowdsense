import serial
import json
import numpy as np
from filterpy.kalman import ExtendedKalmanFilter
from numpy import dot, array, sqrt
from typing import Optional, Dict, List, Tuple
from ultralytics import YOLO


class ReadData:
    """
    UART Serial reader for sensor data.
    Reads JSON formatted data from Arduino/ESP32.
    """
    def __init__(self, com_port: str, baud_rate: int):
        self.ser = serial.Serial(com_port, baud_rate)
    
    def read_uart(self) -> Dict:
        """
        Read and parse JSON data from UART.
        
        Returns:
            Dictionary containing sensor data
        """
        data_line = self.ser.readline().decode('utf-8').rstrip()
        print(f"[UART] Raw: {data_line}")
        python_object = json.loads(data_line)
        return python_object
    
    def __del__(self):
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()


class YOLOCrowdCounter:
    """
    Uses YOLO model (via ultralytics) to count people in images.
    Loads model once at initialization and provides fast inference.
    """

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        person_class_id: int = 0,
        device: Optional[str] = None,
        verbose: bool = False
    ):
        """
        Initialize YOLO model for crowd counting.
        
        Args:
            model_path: Path to YOLO model weights (.pt file)
            conf_threshold: Confidence threshold for detections (0-1)
            iou_threshold: IoU threshold for NMS (0-1)
            person_class_id: Class ID for 'person' in COCO (default: 0)
            device: Device to run inference on ('cpu', 'cuda', '0', '1', etc.)
                   If None, automatically selects best available device
            verbose: Whether to print model loading info
        """
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.person_class_id = person_class_id
        self.verbose = verbose
        
        # Load YOLO model
        try:
            print(f"[YOLOCrowdCounter] Loading model from: {model_path}")
            self.model = YOLO(model_path)
            
            # Set device
            if device is not None:
                self.model.to(device)
                self.device = device
            else:
                # Auto-detect device
                import torch
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
                self.model.to(self.device)
            
            print(f"[YOLOCrowdCounter] Model loaded successfully on device: {self.device}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load YOLO model from {model_path}: {e}")

    def predict(self, image: np.ndarray) -> int:
        """
        Predict crowd count from an OpenCV image.
        
        Args:
            image: OpenCV image (BGR format, numpy array)
                   Shape should be (height, width, 3)
        
        Returns:
            count: Number of people detected in the image
        """
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("Image must be a valid numpy array (OpenCV image)")
        
        if len(image.shape) != 3 or image.shape[2] != 3:
            raise ValueError(f"Image must be BGR format with shape (H, W, 3), got shape: {image.shape}")
        
        try:
            results = self.model.predict(
                source=image,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=self.verbose,
                device=self.device
            )
            
            result = results[0]
            
            person_count = 0
            if result.boxes is not None and len(result.boxes) > 0:
                class_ids = result.boxes.cls.cpu().numpy()
                person_count = int(np.sum(class_ids == self.person_class_id))
            
            if self.verbose:
                print(f"[YOLOCrowdCounter] Detected {person_count} person(s) in image")
            
            return person_count
            
        except Exception as e:
            print(f"[YOLOCrowdCounter] Prediction failed: {e}")
            return 0

    def get_model_info(self) -> Dict:
        """
        Get information about the loaded model.
        
        Returns:
            info: Dictionary containing model metadata
        """
        return {
            "model_type": self.model.type,
            "device": self.device,
            "conf_threshold": self.conf_threshold,
            "iou_threshold": self.iou_threshold,
            "person_class_id": self.person_class_id,
            "model_task": self.model.task,
        }


class SensorCalibrator:
    """
    Automatic calibration for sensor-to-people mappings.
    Collects training data and learns the relationship between
    sensor readings and actual people count.
    """
    
    def __init__(self):
        self.calibration_data = {
            'people_count': [],
            'co2': [],
            'sound': [],
            'temp': [],
            'pir': []
        }
        self.is_calibrated = False
        
        # Learned parameters
        self.co2_per_person = 100.0
        self.sound_per_person = 5.0
        self.temp_per_person = 0.3
        self.pir_per_person = 1.2
        
        self.co2_baseline = 400.0
        self.sound_baseline = 30.0
        self.temp_baseline = 22.0
        
    def add_sample(
        self,
        ground_truth_count: int,
        avg_co2: float,
        avg_sound: float,
        avg_temp: float,
        pir_count: Optional[int] = None
    ):
        """
        Add a calibration sample.
        
        Args:
            ground_truth_count: Actual number of people (from manual count or reliable YOLO)
            avg_co2: Average CO2 reading
            avg_sound: Average sound reading
            avg_temp: Average temperature reading
            pir_count: PIR motion count
        """
        self.calibration_data['people_count'].append(ground_truth_count)
        self.calibration_data['co2'].append(avg_co2)
        self.calibration_data['sound'].append(avg_sound)
        self.calibration_data['temp'].append(avg_temp)
        self.calibration_data['pir'].append(pir_count if pir_count is not None else 0)
        
        print(f"[Calibrator] Added sample #{len(self.calibration_data['people_count'])}: "
              f"{ground_truth_count} people, CO2={avg_co2:.1f}, Sound={avg_sound:.1f}, Temp={avg_temp:.1f}")
    
    def calibrate(self, min_samples: int = 10) -> bool:
        """
        Perform calibration using collected samples.
        Uses linear regression to learn sensor-to-people mappings.
        
        Args:
            min_samples: Minimum number of samples required for calibration
        
        Returns:
            True if calibration successful, False otherwise
        """
        n_samples = len(self.calibration_data['people_count'])
        
        if n_samples < min_samples:
            print(f"[Calibrator] Not enough samples: {n_samples}/{min_samples}")
            return False
        
        print(f"[Calibrator] Starting calibration with {n_samples} samples...")
        
        people = np.array(self.calibration_data['people_count'])
        co2 = np.array(self.calibration_data['co2'])
        sound = np.array(self.calibration_data['sound'])
        temp = np.array(self.calibration_data['temp'])
        pir = np.array(self.calibration_data['pir'])
        
        # Find baseline (readings when people_count = 0)
        zero_count_mask = people == 0
        if np.any(zero_count_mask):
            self.co2_baseline = np.mean(co2[zero_count_mask])
            self.sound_baseline = np.mean(sound[zero_count_mask])
            self.temp_baseline = np.mean(temp[zero_count_mask])
            print(f"[Calibrator] Baselines: CO2={self.co2_baseline:.1f}, "
                  f"Sound={self.sound_baseline:.1f}, Temp={self.temp_baseline:.1f}")
        
        # Calculate per-person change (using samples with people > 0)
        nonzero_mask = people > 0
        if np.any(nonzero_mask):
            people_nz = people[nonzero_mask]
            
            # CO2 per person (linear regression)
            co2_delta = co2[nonzero_mask] - self.co2_baseline
            self.co2_per_person = np.mean(co2_delta / people_nz) if len(people_nz) > 0 else 100.0
            
            # Sound per person
            sound_delta = sound[nonzero_mask] - self.sound_baseline
            self.sound_per_person = np.mean(sound_delta / people_nz) if len(people_nz) > 0 else 5.0
            
            # Temperature per person
            temp_delta = temp[nonzero_mask] - self.temp_baseline
            self.temp_per_person = np.mean(temp_delta / people_nz) if len(people_nz) > 0 else 0.3
            
            # PIR per person
            pir_nz = pir[nonzero_mask]
            self.pir_per_person = np.mean(pir_nz / people_nz) if len(people_nz) > 0 else 1.2
        
        # Prevent division by zero
        self.co2_per_person = max(self.co2_per_person, 1.0)
        self.sound_per_person = max(self.sound_per_person, 0.1)
        self.temp_per_person = max(self.temp_per_person, 0.01)
        self.pir_per_person = max(self.pir_per_person, 0.1)
        
        self.is_calibrated = True
        
        print(f"[Calibrator] ✓ Calibration complete!")
        print(f"  CO2 per person: {self.co2_per_person:.2f} ppm")
        print(f"  Sound per person: {self.sound_per_person:.2f} dB")
        print(f"  Temp per person: {self.temp_per_person:.3f} °C")
        print(f"  PIR per person: {self.pir_per_person:.2f} motions")
        
        return True
    
    def get_calibration_params(self) -> Dict:
        """
        Get calibration parameters.
        
        Returns:
            Dictionary with all calibration parameters
        """
        return {
            'co2_per_person': self.co2_per_person,
            'sound_per_person': self.sound_per_person,
            'temp_per_person': self.temp_per_person,
            'pir_per_person': self.pir_per_person,
            'co2_baseline': self.co2_baseline,
            'sound_baseline': self.sound_baseline,
            'temp_baseline': self.temp_baseline,
            'is_calibrated': self.is_calibrated,
            'num_samples': len(self.calibration_data['people_count'])
        }
    
    def save_calibration(self, filepath: str = 'sensor_calibration.json'):
        """Save calibration parameters to file."""
        import json
        params = self.get_calibration_params()
        with open(filepath, 'w') as f:
            json.dump(params, f, indent=4)
        print(f"[Calibrator] Saved calibration to {filepath}")
    
    def load_calibration(self, filepath: str = 'sensor_calibration.json') -> bool:
        """Load calibration parameters from file."""
        try:
            import json
            with open(filepath, 'r') as f:
                params = json.load(f)
            
            self.co2_per_person = params['co2_per_person']
            self.sound_per_person = params['sound_per_person']
            self.temp_per_person = params['temp_per_person']
            self.pir_per_person = params['pir_per_person']
            self.co2_baseline = params['co2_baseline']
            self.sound_baseline = params['sound_baseline']
            self.temp_baseline = params['temp_baseline']
            self.is_calibrated = params['is_calibrated']
            
            print(f"[Calibrator] ✓ Loaded calibration from {filepath}")
            return True
        except Exception as e:
            print(f"[Calibrator] Failed to load calibration: {e}")
            return False


class CrowdCountingEKF:
    """
    Extended Kalman Filter for fusing:
    - YOLO people count (computer vision)
    - MQ-135 readings (10 values - air quality/CO2)
    - KY-037 readings (10 values - sound level)
    - DHT22 readings (10 values - temp, humidity, etc.)
    - PIR motion count (1 value - motion events)
    
    State vector: [people_count, people_velocity, avg_co2, avg_sound, avg_temp]
    """
    
    def __init__(
        self,
        calibrator: Optional[SensorCalibrator] = None,
        initial_count: float = 0.0,
        dt: float = 60.0,
        process_noise: float = 0.1,
        yolo_noise: float = 1.5,
        sensor_noise: float = 2.0,
        pir_noise: float = 3.0
    ):
        """
        Initialize EKF for crowd counting sensor fusion.
        
        Args:
            calibrator: SensorCalibrator instance with learned parameters
            initial_count: Initial people count estimate
            dt: Time step in seconds (default: 60s = 1 minute)
            process_noise: Process noise (how much count can change per minute)
            yolo_noise: Measurement noise for YOLO detections
            sensor_noise: Measurement noise for sensor-derived estimates
            pir_noise: Measurement noise for PIR motion-derived estimates
        """
        self.dt = dt
        self.calibrator = calibrator
        
        # State vector: [count, velocity, co2_level, sound_level, temp_level]
        self.dim_x = 5
        self.dim_z_max = 3
        
        # Create EKF
        self.ekf = ExtendedKalmanFilter(dim_x=self.dim_x, dim_z=self.dim_z_max)
        
        # Initial state
        if calibrator and calibrator.is_calibrated:
            self.ekf.x = np.array([
                initial_count, 
                0.0, 
                calibrator.co2_baseline, 
                calibrator.sound_baseline, 
                calibrator.temp_baseline
            ])
        else:
            self.ekf.x = np.array([initial_count, 0.0, 400.0, 50.0, 25.0])
        
        # Initial uncertainty
        self.ekf.P = np.eye(self.dim_x) * 10.0
        
        # Process noise covariance Q
        q = process_noise
        self.ekf.Q = np.array([
            [q, 0, 0, 0, 0],
            [0, q*0.1, 0, 0, 0],
            [0, 0, q*0.5, 0, 0],
            [0, 0, 0, q*0.5, 0],
            [0, 0, 0, 0, q*0.2]
        ])
        
        # Measurement noise covariances
        self.R_yolo = yolo_noise ** 2
        self.R_sensor = sensor_noise ** 2
        self.R_pir = pir_noise ** 2
        
        # Use calibrated parameters if available
        if calibrator and calibrator.is_calibrated:
            self.co2_per_person = calibrator.co2_per_person
            self.sound_per_person = calibrator.sound_per_person
            self.temp_per_person = calibrator.temp_per_person
            self.pir_per_person = calibrator.pir_per_person
            self.co2_baseline = calibrator.co2_baseline
            self.sound_baseline = calibrator.sound_baseline
            self.temp_baseline = calibrator.temp_baseline
            print("[EKF] Using calibrated sensor parameters")
        else:
            # Default parameters
            self.co2_per_person = 100.0
            self.sound_per_person = 5.0
            self.temp_per_person = 0.3
            self.pir_per_person = 1.2
            self.co2_baseline = 400.0
            self.sound_baseline = 30.0
            self.temp_baseline = 22.0
            print("[EKF] Using default sensor parameters (not calibrated)")
    
    def state_transition_function(self, x: np.ndarray, dt: float) -> np.ndarray:
        """
        State transition function: predicts next state.
        
        Args:
            x: Current state [count, velocity, co2, sound, temp]
            dt: Time step
        
        Returns:
            Predicted next state
        """
        count, vel, co2, sound, temp = x
        
        # Predict next state
        new_count = max(0, count + vel * dt)
        new_vel = vel
        
        # Sensor levels decay toward baseline
        decay = 0.95
        new_co2 = self.co2_baseline + (co2 - self.co2_baseline) * decay
        new_sound = self.sound_baseline + (sound - self.sound_baseline) * decay
        new_temp = self.temp_baseline + (temp - self.temp_baseline) * decay
        
        return np.array([new_count, new_vel, new_co2, new_sound, new_temp])
    
    def measurement_function(self, x: np.ndarray, measurement_type: str = 'all') -> np.ndarray:
        """
        Measurement function: maps state to expected measurements.
        
        Args:
            x: State vector
            measurement_type: Type of measurement
        
        Returns:
            Expected measurement vector
        """
        count, vel, co2, sound, temp = x
        measurements = []
        
        if measurement_type in ['yolo', 'all']:
            measurements.append(count)
        
        if measurement_type in ['sensor', 'all']:
            co2_est = max(0, (co2 - self.co2_baseline) / self.co2_per_person)
            sound_est = max(0, (sound - self.sound_baseline) / self.sound_per_person)
            temp_est = max(0, (temp - self.temp_baseline) / self.temp_per_person)
            sensor_est = 0.5 * co2_est + 0.3 * sound_est + 0.2 * temp_est
            measurements.append(sensor_est)
        
        if measurement_type in ['pir', 'all']:
            pir_est = count * self.pir_per_person
            measurements.append(pir_est)
        
        return np.array(measurements)
    
    def jacobian_F(self, x: np.ndarray, dt: float) -> np.ndarray:
        """Jacobian of state transition function."""
        F = np.array([
            [1, dt, 0, 0, 0],
            [0, 1, 0, 0, 0],
            [0, 0, 0.95, 0, 0],
            [0, 0, 0, 0.95, 0],
            [0, 0, 0, 0, 0.95]
        ])
        return F
    
    def jacobian_H(self, x: np.ndarray, measurement_type: str = 'all') -> np.ndarray:
        """Jacobian of measurement function."""
        H_list = []
        
        if measurement_type in ['yolo', 'all']:
            H_list.append([1, 0, 0, 0, 0])
        
        if measurement_type in ['sensor', 'all']:
            dh_dco2 = 0.5 / self.co2_per_person
            dh_dsound = 0.3 / self.sound_per_person
            dh_dtemp = 0.2 / self.temp_per_person
            H_list.append([0, 0, dh_dco2, dh_dsound, dh_dtemp])
        
        if measurement_type in ['pir', 'all']:
            H_list.append([self.pir_per_person, 0, 0, 0, 0])
        
        return np.array(H_list)
    
    def process_sensor_data(
        self,
        mq135_readings: List[float],
        ky037_readings: List[float],
        dht22_readings: List[float]
    ) -> Tuple[float, float, float]:
        """
        Process raw sensor data to extract meaningful features.
        
        Returns:
            (avg_co2, avg_sound, avg_temp)
        """
        avg_co2 = np.mean(mq135_readings) * 2.0
        avg_sound = np.mean(ky037_readings) * 0.5
        avg_temp = np.mean(dht22_readings[:3]) if len(dht22_readings) >= 3 else 25.0
        
        return avg_co2, avg_sound, avg_temp
    
    def predict(self):
        """EKF Prediction step."""
        self.ekf.x = self.state_transition_function(self.ekf.x, self.dt)
        F = self.jacobian_F(self.ekf.x, self.dt)
        self.ekf.P = dot(F, dot(self.ekf.P, F.T)) + self.ekf.Q
    
    def update(
        self,
        yolo_count: Optional[int] = None,
        mq135_readings: Optional[List[float]] = None,
        ky037_readings: Optional[List[float]] = None,
        dht22_readings: Optional[List[float]] = None,
        pir_motion_count: Optional[int] = None
    ) -> float:
        """
        EKF Update step with multiple sensor measurements.
        
        Args:
            yolo_count: People count from YOLO
            mq135_readings: 10 analog readings from MQ-135
            ky037_readings: 10 analog readings from KY-037
            dht22_readings: 10 readings from DHT22
            pir_motion_count: Motion event count from PIR
        
        Returns:
            Fused people count estimate
        """
        # Update internal sensor state estimates
        if mq135_readings and ky037_readings and dht22_readings:
            avg_co2, avg_sound, avg_temp = self.process_sensor_data(
                mq135_readings, ky037_readings, dht22_readings
            )
            self.ekf.x[2] = avg_co2
            self.ekf.x[3] = avg_sound
            self.ekf.x[4] = avg_temp
        
        # Build measurement vector
        z = []
        H_rows = []
        R_diag = []
        
        if yolo_count is not None:
            z.append(float(yolo_count))
            H_rows.append([1, 0, 0, 0, 0])
            R_diag.append(self.R_yolo)
        
        if mq135_readings and ky037_readings and dht22_readings:
            sensor_measurement = self.measurement_function(self.ekf.x, 'sensor')[0]
            z.append(sensor_measurement)
            H_rows.extend(self.jacobian_H(self.ekf.x, 'sensor').tolist())
            R_diag.append(self.R_sensor)
        
        if pir_motion_count is not None:
            z.append(float(pir_motion_count))
            H_rows.append([self.pir_per_person, 0, 0, 0, 0])
            R_diag.append(self.R_pir)
        
        # Perform update if measurements available
        if len(z) > 0:
            z = np.array(z)
            H = np.array(H_rows)
            R = np.diag(R_diag)
            
            S = dot(H, dot(self.ekf.P, H.T)) + R
            K = dot(self.ekf.P, dot(H.T, np.linalg.inv(S)))
            
            z_pred = dot(H, self.ekf.x)
            y = z - z_pred
            
            self.ekf.x = self.ekf.x + dot(K, y)
            I_KH = np.eye(self.dim_x) - dot(K, H)
            self.ekf.P = dot(I_KH, self.ekf.P)
        
        self.ekf.x[0] = max(0, self.ekf.x[0])
        return float(self.ekf.x[0])
    
    def get_state(self) -> Dict:
        """Get current filter state."""
        return {
            'people_count': float(self.ekf.x[0]),
            'velocity': float(self.ekf.x[1]),
            'co2_level': float(self.ekf.x[2]),
            'sound_level': float(self.ekf.x[3]),
            'temp_level': float(self.ekf.x[4]),
            'uncertainty': float(np.sqrt(self.ekf.P[0, 0]))
        }