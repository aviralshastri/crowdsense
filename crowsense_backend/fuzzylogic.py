import json
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from typing import Dict, Optional, Tuple
from pathlib import Path


class FuzzyLogicIntegrator:
    
    def __init__(self):
        print("[FuzzyLogic] Initializing fuzzy logic system...")
        
        self.person_count = ctrl.Antecedent(np.arange(0, 51, 1), 'person_count')
        self.temperature = ctrl.Antecedent(np.arange(20, 36, 1), 'temperature')
        self.noise_level = ctrl.Antecedent(np.arange(200, 301, 1), 'noise_level')
        self.air_quality = ctrl.Antecedent(np.arange(100, 251, 1), 'air_quality')
        
        self.crowd_assessment = ctrl.Consequent(np.arange(0, 101, 1), 'crowd_assessment')
        
        self._setup_membership_functions()
        
        self._create_rules()
        
        self.control_system = ctrl.ControlSystem(self.rules)
        self.simulator = ctrl.ControlSystemSimulation(self.control_system)
        
        print("[FuzzyLogic] System initialized successfully")
    
    def _setup_membership_functions(self):
        
        self.person_count['few'] = fuzz.trapmf(self.person_count.universe, [0, 0, 5, 10])
        self.person_count['moderate'] = fuzz.trimf(self.person_count.universe, [8, 15, 22])
        self.person_count['many'] = fuzz.trimf(self.person_count.universe, [20, 30, 40])
        self.person_count['crowded'] = fuzz.trapmf(self.person_count.universe, [35, 45, 50, 50])
        
        self.temperature['cool'] = fuzz.trapmf(self.temperature.universe, [20, 20, 24, 26])
        self.temperature['normal'] = fuzz.trimf(self.temperature.universe, [25, 27, 29])
        self.temperature['warm'] = fuzz.trimf(self.temperature.universe, [28, 30, 32])
        self.temperature['hot'] = fuzz.trapmf(self.temperature.universe, [31, 33, 35, 35])
        
        self.noise_level['quiet'] = fuzz.trapmf(self.noise_level.universe, [200, 200, 230, 245])
        self.noise_level['moderate'] = fuzz.trimf(self.noise_level.universe, [240, 255, 270])
        self.noise_level['loud'] = fuzz.trimf(self.noise_level.universe, [265, 280, 290])
        self.noise_level['very_loud'] = fuzz.trapmf(self.noise_level.universe, [285, 295, 300, 300])
        
        self.air_quality['good'] = fuzz.trapmf(self.air_quality.universe, [100, 100, 140, 160])
        self.air_quality['moderate'] = fuzz.trimf(self.air_quality.universe, [155, 175, 195])
        self.air_quality['poor'] = fuzz.trimf(self.air_quality.universe, [190, 210, 230])
        self.air_quality['unhealthy'] = fuzz.trapmf(self.air_quality.universe, [225, 240, 250, 250])
        
        self.crowd_assessment['very_low'] = fuzz.trapmf(self.crowd_assessment.universe, [0, 0, 15, 25])
        self.crowd_assessment['low'] = fuzz.trimf(self.crowd_assessment.universe, [20, 35, 50])
        self.crowd_assessment['medium'] = fuzz.trimf(self.crowd_assessment.universe, [45, 55, 65])
        self.crowd_assessment['high'] = fuzz.trimf(self.crowd_assessment.universe, [60, 75, 85])
        self.crowd_assessment['critical'] = fuzz.trapmf(self.crowd_assessment.universe, [80, 90, 100, 100])
    
    def _create_rules(self):
        
        self.rules = [
            
            ctrl.Rule(
                self.person_count['few'] & 
                self.temperature['cool'] & 
                self.noise_level['quiet'],
                self.crowd_assessment['very_low']
            ),
            
            ctrl.Rule(
                self.person_count['few'] & 
                self.air_quality['good'],
                self.crowd_assessment['very_low']
            ),
            
            ctrl.Rule(
                self.person_count['moderate'] & 
                self.temperature['normal'] & 
                self.noise_level['moderate'],
                self.crowd_assessment['low']
            ),
            
            ctrl.Rule(
                self.person_count['few'] & 
                self.temperature['warm'],
                self.crowd_assessment['low']
            ),
            
            ctrl.Rule(
                self.person_count['moderate'] & 
                self.temperature['warm'] & 
                self.noise_level['loud'],
                self.crowd_assessment['medium']
            ),
            
            ctrl.Rule(
                self.person_count['moderate'] & 
                self.air_quality['moderate'],
                self.crowd_assessment['medium']
            ),
            
            ctrl.Rule(
                self.person_count['many'] & 
                self.temperature['normal'] & 
                self.noise_level['moderate'],
                self.crowd_assessment['medium']
            ),
            
            ctrl.Rule(
                self.person_count['many'] & 
                self.temperature['hot'] & 
                self.noise_level['loud'],
                self.crowd_assessment['high']
            ),
            
            ctrl.Rule(
                self.person_count['many'] & 
                self.air_quality['poor'],
                self.crowd_assessment['high']
            ),
            
            ctrl.Rule(
                self.person_count['crowded'] & 
                self.temperature['warm'],
                self.crowd_assessment['high']
            ),
            
            ctrl.Rule(
                self.person_count['crowded'] & 
                self.temperature['hot'] & 
                self.noise_level['very_loud'],
                self.crowd_assessment['critical']
            ),
            
            ctrl.Rule(
                self.person_count['crowded'] & 
                self.air_quality['unhealthy'],
                self.crowd_assessment['critical']
            ),
            
            ctrl.Rule(
                self.person_count['many'] & 
                self.temperature['hot'] & 
                self.air_quality['poor'],
                self.crowd_assessment['critical']
            ),
            ctrl.Rule(
                self.temperature['hot'] & 
                self.noise_level['very_loud'] & 
                self.air_quality['poor'],
                self.crowd_assessment['high']
            ),
            
            ctrl.Rule(
                self.person_count['moderate'] & 
                self.temperature['hot'] & 
                self.noise_level['very_loud'],
                self.crowd_assessment['medium']
            ),
        ]
    
    def load_sensor_data(self, json_path: str) -> Optional[Dict]:
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                data = data[0] if data else {}
            
            sensor_data = {
                'temperature': np.mean(data.get('temperature', [27])),
                'noise_level': np.mean(data.get('sound_level', [250])),
                'air_quality': np.mean(data.get('air_quality', [170])),
            }
            
            return sensor_data
            
        except Exception as e:
            print(f"[FuzzyLogic] Error loading sensor data: {e}")
            return None
    
    def assess_crowd(
        self,
        person_count: int,
        temperature: float,
        noise_level: float,
        air_quality: float
    ) -> Dict:
       
        try:
            person_count = np.clip(person_count, 0, 50)
            temperature = np.clip(temperature, 20, 35)
            noise_level = np.clip(noise_level, 200, 300)
            air_quality = np.clip(air_quality, 100, 250)
            
            self.simulator.input['person_count'] = person_count
            self.simulator.input['temperature'] = temperature
            self.simulator.input['noise_level'] = noise_level
            self.simulator.input['air_quality'] = air_quality
            
            self.simulator.compute()
            
            score = self.simulator.output['crowd_assessment']
            
            if score < 25:
                status = "Very Low"
                confidence = "Low Risk"
            elif score < 50:
                status = "Low"
                confidence = "Acceptable"
            elif score < 65:
                status = "Medium"
                confidence = "Moderate Risk"
            elif score < 85:
                status = "High"
                confidence = "High Risk"
            else:
                status = "Critical"
                confidence = "Emergency"
            
            return {
                'score': round(float(score), 2),
                'status': status,
                'confidence': confidence,
                'inputs': {
                    'person_count': int(person_count),
                    'temperature': round(float(temperature), 1),
                    'noise_level': round(float(noise_level), 1),
                    'air_quality': round(float(air_quality), 1)
                }
            }
            
        except Exception as e:
            print(f"[FuzzyLogic] Assessment error: {e}")
            return None
    
    def assess_from_json(
        self,
        person_count: int,
        json_path: str
    ) -> Dict:
        
        sensor_data = self.load_sensor_data(json_path)
        
        if sensor_data is None:
            print("[FuzzyLogic] Using default sensor values")
            sensor_data = {
                'temperature': 27.0,
                'noise_level': 250.0,
                'air_quality': 170.0
            }
        
        return self.assess_crowd(
            person_count=person_count,
            temperature=sensor_data['temperature'],
            noise_level=sensor_data['noise_level'],
            air_quality=sensor_data['air_quality']
        )

if __name__ == "__main__":
    
    print("=== Fuzzy Logic Crowd Assessment System ===\n")
    
    fuzzy = FuzzyLogicIntegrator()
    
    print("\n--- Example 1: Manual Sensor Input ---")
    result = fuzzy.assess_crowd(
        person_count=15,
        temperature=28.5,
        noise_level=255.0,
        air_quality=172.0
    )
    
    if result:
        print(f"Crowd Assessment Score: {result['score']}")
        print(f"Status: {result['status']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Inputs: {result['inputs']}")
    print("\n--- Example 2: From JSON File ---")
    
    sample_data = {
        "motion_count": 6,
        "temperature": [27, 27.1, 27.1, 27.1, 27.1, 27, 27.1, 27, 27, 27],
        "humidity": [67.1, 65.9, 65.9, 65.7, 65.7, 65.7, 65.8, 65.9, 66.1, 66.1],
        "sound_level": [242, 256, 259, 266, 243, 250, 259, 246, 257, 263],
        "air_quality": [172, 162, 172, 171, 166, 163, 167, 173, 166, 172]
    }
    
    with open('sample_sensor_data.json', 'w') as f:
        json.dump(sample_data, f)
    
    result = fuzzy.assess_from_json(
        person_count=18,
        json_path='sample_sensor_data.json'
    )
    
    if result:
        print(f"Crowd Assessment Score: {result['score']}")
        print(f"Status: {result['status']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Inputs: {result['inputs']}")
    
    print("\n--- Example 3: Testing Different Scenarios ---")
    
    scenarios = [
        {"name": "Low Crowd", "count": 5, "temp": 25, "noise": 230, "aqi": 140},
        {"name": "Medium Crowd", "count": 20, "temp": 28, "noise": 260, "aqi": 175},
        {"name": "High Crowd", "count": 35, "temp": 32, "noise": 285, "aqi": 210},
        {"name": "Critical", "count": 45, "temp": 34, "noise": 295, "aqi": 240},
    ]
    
    for scenario in scenarios:
        result = fuzzy.assess_crowd(
            person_count=scenario["count"],
            temperature=scenario["temp"],
            noise_level=scenario["noise"],
            air_quality=scenario["aqi"]
        )
        print(f"\n{scenario['name']}:")
        print(f"  Score: {result['score']} - Status: {result['status']}")