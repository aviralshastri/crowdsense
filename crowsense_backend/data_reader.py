import serial
import json
from datetime import datetime
import time

SERIAL_PORT = 'com16'  
BAUD_RATE = 9600
OUTPUT_FILE = 'sensor_data.json'

def read_uart_to_json():
    
    try:
        
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")
        time.sleep(2)  
        
        try:
            with open(OUTPUT_FILE, 'r') as f:
                data_list = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data_list = []
        
        print(f"Started logging. Press Ctrl+C to stop.")
        
        line_buffer = ""  
        
        while True:
            if ser.in_waiting > 0:
               
                chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                line_buffer += chunk
                
                while '\n' in line_buffer:
                    line, line_buffer = line_buffer.split('\n', 1)
                    line = line.strip()
                    
                    if line: 
                        try:
                            sensor_data = json.loads(line)
                            entry = {
                                "timestamp": datetime.now().isoformat(),
                                "data": sensor_data
                            }
                            
                            data_list.append(entry)
                            
                            with open(OUTPUT_FILE, 'w') as f:
                                json.dump(data_list, f, indent=4)
                            
                            print(f"✓ Saved: {entry['timestamp']}")
                            
                        except json.JSONDecodeError as e:
                            print(f"✗ Invalid JSON: {line[:50]}... Error: {e}")
            
            time.sleep(0.1)  
            
    except serial.SerialException as e:
        print(f"Serial Error: {e}")
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed")

if __name__ == "__main__":
    read_uart_to_json()