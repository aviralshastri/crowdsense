const API_BASE_URL = 'http://localhost:5000';  

export const API_ENDPOINTS = {
 
  STREAM_CCTV: `${API_BASE_URL}/stream_cctv`,
  PREDICT_CROWD: `${API_BASE_URL}/predict_crowd`,
  
  PUSH_SENSOR_DATA: `${API_BASE_URL}/push_sensor_data`,
  LIVE_SENSOR_DATA: `${API_BASE_URL}/live_sensor_data`,
 
  STATS: `${API_BASE_URL}/stats`,
  RECENT_RECORDS: `${API_BASE_URL}/recent_records`,
  MODEL_INFO: `${API_BASE_URL}/model_info`,

  ALERTS: `${API_BASE_URL}/alerts`,
 
  HEALTH: `${API_BASE_URL}/`,

  SAVE_CHECKPOINT: `${API_BASE_URL}/save_checkpoint`,
};

export default API_BASE_URL;