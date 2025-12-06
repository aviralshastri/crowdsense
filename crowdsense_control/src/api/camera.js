import { API_ENDPOINTS } from '../config/api';
export const uploadCameraFrame = async (imageFile) => {
  try {
    const formData = new FormData();
    formData.append('file', imageFile);

    const response = await fetch(API_ENDPOINTS.STREAM_CCTV, {
      method: 'POST',
      body: formData,
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
    console.error('Error uploading camera frame:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

export const getPrediction = async (imageFile) => {
  try {
    const formData = new FormData();
    formData.append('file', imageFile);

    const response = await fetch(API_ENDPOINTS.PREDICT_CROWD, {
      method: 'POST',
      body: formData,
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
    console.error('Error getting prediction:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

export const getStats = async () => {
  try {
    const response = await fetch(API_ENDPOINTS.STATS);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      success: true,
      data: data
    };
  } catch (error) {
    console.error('Error fetching stats:', error);
    return {
      success: false,
      error: error.message
    };
  }
};