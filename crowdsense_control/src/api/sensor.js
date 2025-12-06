import { API_ENDPOINTS } from '../config/api';
export const pushSensorData = async (sensorData) => {
  try {
    const payload = {
      timestamp: Date.now() / 1000,
      sensor_data: {
        temperature: Array.isArray(sensorData.temperature) 
          ? sensorData.temperature 
          : [sensorData.temperature],
        sound_level: Array.isArray(sensorData.sound_level) 
          ? sensorData.sound_level 
          : [sensorData.noise],
        air_quality: Array.isArray(sensorData.air_quality) 
          ? sensorData.air_quality 
          : [sensorData.aqi]
      }
    };

    const response = await fetch(API_ENDPOINTS.PUSH_SENSOR_DATA, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      success: true,
      data: data
    };
  } catch (error) {
    console.error('Error pushing sensor data:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

export const getLiveSensorData = async () => {
  try {
    const response = await fetch(API_ENDPOINTS.LIVE_SENSOR_DATA);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      success: true,
      data: data
    };
  } catch (error) {
    console.error('Error fetching live sensor data:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

export const getRecentRecords = async (n = 10) => {
  try {
    const response = await fetch(`${API_ENDPOINTS.RECENT_RECORDS}?n=${n}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      success: true,
      data: data
    };
  } catch (error) {
    console.error('Error fetching recent records:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

export const getModelInfo = async () => {
  try {
    const response = await fetch(API_ENDPOINTS.MODEL_INFO);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      success: true,
      data: data
    };
  } catch (error) {
    console.error('Error fetching model info:', error);
    return {
      success: false,
      error: error.message
    };
  }
};