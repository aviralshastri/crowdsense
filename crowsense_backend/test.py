import serial
import json
import os

PORT = "COM4"
BAUD = 115200
OUTPUT_FILE = "data_log.json"

def load_existing_data():
    """Load previous JSON array if file exists, else empty list."""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Warning: JSON file corrupted, starting new file.")
            return []
    return []

def save_data(data_list):
    """Save all collected data back to the JSON file."""
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data_list, f, indent=4)

def main():
    
    data_list = load_existing_data()

    
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print(f"Listening on {PORT} at {BAUD} baud...")

    try:
        while True:
            line = ser.readline().decode("utf-8").strip()

            if not line:
                continue
            try:
                data = json.loads(line)
                print("Received:", data)

                data_list.append(data)

                
                save_data(data_list)

            except json.JSONDecodeError:
                print("Invalid JSON skipped:", line)

    except KeyboardInterrupt:
        print("\nStopping...")
        ser.close()
        save_data(data_list)

if __name__ == "__main__":
    main()
