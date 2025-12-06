import { API_ENDPOINTS } from '../config/api';
import API_BASE_URL from '../config/api';

export const getSystemStats = async () => {
  try {
    const response = await fetch(API_ENDPOINTS.STATS, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
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
    console.error('Error fetching system stats:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

export const getRecentRecords = async (n = 10) => {
  try {
    const response = await fetch(`${API_ENDPOINTS.RECENT_RECORDS}?n=${n}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      success: true,
      count: data.count,
      records: data.records
    };
  } catch (error) {
    console.error('Error fetching recent records:', error);
    return {
      success: false,
      error: error.message,
      records: []
    };
  }
};

export const getModelInfo = async () => {
  try {
    const response = await fetch(API_ENDPOINTS.MODEL_INFO, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
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
    console.error('Error fetching model info:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

export const saveCheckpoint = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/save_checkpoint`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      success: true,
      message: data.message
    };
  } catch (error) {
    console.error('Error saving checkpoint:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

export const checkBackendHealth = async () => {
  try {
    const response = await fetch(API_ENDPOINTS.HEALTH, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      success: true,
      status: data.status,
      data: data
    };
  } catch (error) {
    console.error('Error checking backend health:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

export const getAlerts = async () => {
  try {
    const response = await fetch(API_ENDPOINTS.ALERTS, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      success: true,
      alerts: data.alerts || []
    };
  } catch (error) {
    console.error('Error fetching alerts:', error);
    return {
      success: false,
      error: error.message,
      alerts: []
    };
  }
};