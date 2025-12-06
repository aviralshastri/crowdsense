import { useState, useEffect } from 'react';
import { pushSensorData, getRecentRecords, getLiveSensorData } from '../api/sensor';
import "../styles/sensor.css";

export default function SensorData() {
  const [isLoaded, setIsLoaded] = useState(false);
  const [selectedZone, setSelectedZone] = useState(null);
  const [sensorZones, setSensorZones] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isLoadingData, setIsLoadingData] = useState(true);

  useEffect(() => {
    const timer = requestAnimationFrame(() => {
      setIsLoaded(true);
    });
    return () => cancelAnimationFrame(timer);
  }, []);

  useEffect(() => {
    document.body.style.overflow = 'auto';
    document.documentElement.style.overflow = 'auto';
    
    return () => {
      document.body.style.overflow = '';
      document.documentElement.style.overflow = '';
    };
  }, []);

  useEffect(() => {
    if (selectedZone) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'auto';
    }
    
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [selectedZone]);

  const fetchLiveSensorData = async () => {
    setIsLoadingData(true);
    try {
      const result = await getLiveSensorData();
      
      if (result.success) {
        const realZone = result.data.zone;
        
        const zones = [
          {
            id: 1,
            name: "Zone 1 - Main Gate (LIVE)",
            temp: realZone.temp,
            humidity: realZone.humidity,
            noise: realZone.noise,
            aqi: realZone.aqi,
            pir: realZone.pir,
            status: realZone.status
          },
          {
            id: 2,
            name: "Zone 2 - Food Court",
            temp: realZone.temp + 2,
            humidity: realZone.humidity + 5,
            noise: realZone.noise + 15,
            aqi: realZone.aqi - 20,
            pir: true,
            status: "warning"
          },
          {
            id: 3,
            name: "Zone 3 - Stage Area",
            temp: realZone.temp - 2,
            humidity: realZone.humidity - 3,
            noise: realZone.noise + 25,
            aqi: realZone.aqi - 40,
            pir: true,
            status: "critical"
          },
          {
            id: 4,
            name: "Zone 4 - Parking",
            temp: realZone.temp + 3,
            humidity: realZone.humidity - 8,
            noise: realZone.noise,
            aqi: realZone.aqi + 10,
            pir: false,
            status: "normal"
          },
          {
            id: 5,
            name: "Zone 5 - Exit Point",
            temp: realZone.temp + 1,
            humidity: realZone.humidity + 2,
            noise: realZone.noise + 5,
            aqi: realZone.aqi - 10,
            pir: true,
            status: "normal"
          },
          {
            id: 6,
            name: "Zone 6 - VIP Area",
            temp: realZone.temp - 4,
            humidity: realZone.humidity - 10,
            noise: realZone.noise - 20,
            aqi: realZone.aqi - 50,
            pir: true,
            status: "normal"
          }
        ];
        
        setSensorZones(zones);
        setLastUpdate(new Date().toLocaleTimeString());
        console.log('Live sensor data loaded:', realZone);
      } else {
        console.error('Failed to fetch live sensor data:', result.error);
        initializeDummyData();
      }
    } catch (error) {
      console.error('Error fetching sensor data:', error);
      initializeDummyData();
    } finally {
      setIsLoadingData(false);
    }
  };

  const initializeDummyData = () => {
    const initialZones = [
      { id: 1, name: "Zone 1 - Main Gate", temp: 31, humidity: 67, noise: 242, aqi: 180, pir: true, status: "normal" },
      { id: 2, name: "Zone 2 - Food Court", temp: 35, humidity: 72, noise: 256, aqi: 145, pir: true, status: "warning" },
      { id: 3, name: "Zone 3 - Stage Area", temp: 28, humidity: 65, noise: 259, aqi: 120, pir: true, status: "critical" },
      { id: 4, name: "Zone 4 - Parking", temp: 33, humidity: 60, noise: 243, aqi: 165, pir: false, status: "normal" },
      { id: 5, name: "Zone 5 - Exit Point", temp: 30, humidity: 68, noise: 250, aqi: 155, pir: true, status: "normal" },
      { id: 6, name: "Zone 6 - VIP Area", temp: 26, humidity: 58, noise: 230, aqi: 95, pir: true, status: "normal" }
    ];
    setSensorZones(initialZones);
  };

  useEffect(() => {
    fetchLiveSensorData();
    const interval = setInterval(fetchLiveSensorData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchRecentRecords = async () => {
    const result = await getRecentRecords(10);
    if (result.success) {
      console.log('Recent records:', result.data);
      setLastUpdate(new Date().toLocaleTimeString());
      alert(`Fetched ${result.data.count} recent records from database`);
    } else {
      console.error('Failed to fetch records:', result.error);
    }
  };

  const sendZoneDataToBackend = async (zone) => {
    setIsSending(true);
    
    try {
      const sensorData = {
        temperature: zone.temp,
        noise: zone.noise,
        aqi: zone.aqi,
        sound_level: zone.noise
      };

      const result = await pushSensorData(sensorData);
      
      if (result.success) {
        console.log('Backend response:', result.data);
        
        alert(
          `✅ Data Sent Successfully!\n\n` +
          `Zone: ${zone.name}\n` +
          `Fuzzy Score: ${result.data.fuzzy_score}\n` +
          `Status: ${result.data.fuzzy_status}\n` +
          `Person Count: ${result.data.person_count}\n` +
          `Predicted Count (10min): ${result.data.predicted_count || 'N/A'}`
        );
        
        setLastUpdate(new Date().toLocaleTimeString());
      } else {
        alert('❌ Failed to send data: ' + result.error);
      }
    } catch (error) {
      console.error('Error sending data:', error);
      alert('❌ Error: ' + error.message);
    } finally {
      setIsSending(false);
    }
  };

  const getStatusClass = (status) => {
    if (status === "critical") return "sensor-critical";
    if (status === "warning") return "sensor-warning";
    return "sensor-normal";
  };

  const getStatusIcon = (status) => {
    if (status === "critical") return "🔴";
    if (status === "warning") return "⚠️";
    return "✅";
  };

  const openModal = (zone) => {
    setSelectedZone(zone);
  };

  const closeModal = () => {
    setSelectedZone(null);
  };

  const getDetailedAnalysis = (zone) => {
    let tempSuggestion = "";
    let tempStatus = "normal";
    if (zone.temp > 40) {
      tempSuggestion = "Extreme heat! Crowd will feel discomfort.";
      tempStatus = "critical";
    } else if (zone.temp > 32) {
      tempSuggestion = "Warm weather. Crowd density may increase stress.";
      tempStatus = "warning";
    } else {
      tempSuggestion = "Temperature is normal.";
    }

    let noiseSuggestion = "";
    let noiseStatus = "normal";
    if (zone.noise > 400) {
      noiseSuggestion = "Dangerously loud! Possible crowd chaos.";
      noiseStatus = "critical";
    } else if (zone.noise > 380) {
      noiseSuggestion = "Loud environment. Indicates crowd activity.";
      noiseStatus = "warning";
    } else {
      noiseSuggestion = "Noise levels are normal.";
    }

    let airSuggestion = "";
    let airStatus = "normal";
    if (zone.aqi > 600) {
      airSuggestion = "Very unhealthy air! Avoid crowd in this zone.";
      airStatus = "critical";
    } else if (zone.aqi > 590) {
      airSuggestion = "Poor air quality. Moderate crowd effects.";
      airStatus = "warning";
    } else {
      airSuggestion = "Air quality is good.";
    }

    return { tempSuggestion, tempStatus, noiseSuggestion, noiseStatus, airSuggestion, airStatus };
  };

  return (
    <div className={`sensor-page ${isLoaded ? 'loaded' : ''}`}>
      <div className="sensor-header">
        <div className="sensor-title">
          <span className="title-icon">📊</span>
          Sensor Data - All Zones {isLoadingData && <span style={{fontSize: '14px', opacity: 0.7}}>🔄</span>}
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            onClick={fetchLiveSensorData}
            disabled={isLoadingData}
            style={{
              padding: '10px 20px',
              background: isLoadingData ? '#ccc' : '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: isLoadingData ? 'not-allowed' : 'pointer',
              fontSize: '14px'
            }}
          >
            🔄 Refresh Live Data
          </button>
          <button
            onClick={fetchRecentRecords}
            disabled={isSending}
            style={{
              padding: '10px 20px',
              background: isSending ? '#ccc' : '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: isSending ? 'not-allowed' : 'pointer',
              fontSize: '14px'
            }}
          >
            📥 Fetch Records
          </button>
          {lastUpdate && (
            <div style={{ color: '#fff', fontSize: '12px' }}>
              Last Update: {lastUpdate}
            </div>
          )}
          <div className="live-indicator">
            <span className="pulse-dot"></span>
            LIVE
          </div>
        </div>
      </div>

      <div className="sensor-zones-grid">
        {sensorZones.map((zone, index) => (
          <div 
            key={zone.id}
            className={`zone-card ${getStatusClass(zone.status)}`}
            style={{ animationDelay: `${index * 0.1}s` }}
            onClick={() => openModal(zone)}
          >
            <div className="zone-header">
              <div className="zone-name">{zone.name}</div>
              <div className="zone-status-icon">{getStatusIcon(zone.status)}</div>
            </div>

            <div className="zone-quick-stats">
              <div className="quick-stat">
                <span className="stat-icon">🌡️</span>
                <span className="stat-value">{zone.temp}°C</span>
              </div>
              <div className="quick-stat">
                <span className="stat-icon">💧</span>
                <span className="stat-value">{zone.humidity}%</span>
              </div>
              <div className="quick-stat">
                <span className="stat-icon">🔊</span>
                <span className="stat-value">{zone.noise}</span>
              </div>
              <div className="quick-stat">
                <span className="stat-icon">🌫️</span>
                <span className="stat-value">{zone.aqi}</span>
              </div>
            </div>

            <div className="zone-pir-status">
              <span className={`pir-dot ${zone.pir ? 'active' : 'inactive'}`}></span>
              {zone.pir ? "Motion Detected" : "No Motion"}
            </div>

            <button
              onClick={(e) => {
                e.stopPropagation();
                sendZoneDataToBackend(zone);
              }}
              disabled={isSending}
              style={{
                position: 'absolute',
                bottom: '10px',
                left: '50%',
                transform: 'translateX(-50%)',
                padding: '8px 16px',
                background: isSending ? '#ccc' : '#2196F3',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: isSending ? 'not-allowed' : 'pointer',
                fontSize: '12px',
                zIndex: 10
              }}
            >
              {isSending ? '⏳ Sending...' : '📤 Send Data'}
            </button>

            <div className="zone-shimmer"></div>
          </div>
        ))}
      </div>

      {selectedZone && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeModal}>×</button>
            
            <div className="modal-header">
              <h2>{selectedZone.name}</h2>
              <div className={`modal-status-badge ${getStatusClass(selectedZone.status)}`}>
                {getStatusIcon(selectedZone.status)} {selectedZone.status.toUpperCase()}
              </div>
            </div>

            <div className="modal-body">
              <div className={`detail-sensor-box sensor-${getDetailedAnalysis(selectedZone).tempStatus}`}>
                <div className="sensor-label">
                  <span className="sensor-icon">🌡️</span>
                  Temperature
                </div>
                <div className="sensor-content">
                  <div className="sensor-value">{selectedZone.temp}°C</div>
                  <div className="sensor-metrics">
                    <div className="metric-item">
                      <span className="metric-label">Min Today</span>
                      <span className="metric-value">{(selectedZone.temp - 7).toFixed(1)}°C</span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">Max Today</span>
                      <span className="metric-value">{(selectedZone.temp + 5).toFixed(1)}°C</span>
                    </div>
                  </div>
                </div>
                <div className="sensor-bar">
                  <div className="sensor-bar-fill" style={{width: `${Math.min((selectedZone.temp / 50) * 100, 100)}%`}}></div>
                </div>
                <div className="sensor-suggestion">
                  <span className="suggestion-icon">💡</span>
                  {getDetailedAnalysis(selectedZone).tempSuggestion}
                </div>
              </div>

              <div className="detail-sensor-box">
                <div className="sensor-label">
                  <span className="sensor-icon">💧</span>
                  Humidity
                </div>
                <div className="sensor-value">{selectedZone.humidity}%</div>
                <div className="sensor-bar">
                  <div className="sensor-bar-fill" style={{width: `${selectedZone.humidity}%`}}></div>
                </div>
                <div className="sensor-suggestion">
                  <span className="suggestion-icon">💡</span>
                  Humidity levels monitored
                </div>
              </div>

              <div className={`detail-sensor-box sensor-${getDetailedAnalysis(selectedZone).noiseStatus}`}>
                <div className="sensor-label">
                  <span className="sensor-icon">🔊</span>
                  Noise Level
                </div>
                <div className="sensor-value">{selectedZone.noise}</div>
                <div className="sensor-bar">
                  <div className="sensor-bar-fill" style={{width: `${Math.min((selectedZone.noise / 450) * 100, 100)}%`}}></div>
                </div>
                <div className="sensor-suggestion">
                  <span className="suggestion-icon">💡</span>
                  {getDetailedAnalysis(selectedZone).noiseSuggestion}
                </div>
              </div>

              <div className={`detail-sensor-box sensor-${getDetailedAnalysis(selectedZone).airStatus}`}>
                <div className="sensor-label">
                  <span className="sensor-icon">🌫️</span>
                  Air Quality (AQI)
                </div>
                <div className="sensor-value">{selectedZone.aqi}</div>
                <div className="sensor-bar">
                  <div className="sensor-bar-fill" style={{width: `${Math.min((selectedZone.aqi / 650) * 100, 100)}%`}}></div>
                </div>
                <div className="sensor-suggestion">
                  <span className="suggestion-icon">💡</span>
                  {getDetailedAnalysis(selectedZone).airSuggestion}
                </div>
              </div>

              <div className={`detail-sensor-box ${selectedZone.pir ? 'sensor-motion' : ''}`}>
                <div className="sensor-label">
                  <span className="sensor-icon">👁️</span>
                  PIR Motion Sensor
                </div>
                <div className="sensor-value">{selectedZone.pir ? "Motion Detected" : "No Motion"}</div>
                <div className="pir-indicator">
                  <div className={`pir-status ${selectedZone.pir ? 'active' : 'inactive'}`}>
                    {selectedZone.pir && <div className="radar-ping"></div>}
                  </div>
                </div>
                <div className="sensor-suggestion">
                  <span className="suggestion-icon">💡</span>
                  {selectedZone.pir ? "Active movement detected in this zone" : "No movement detected currently"}
                </div>
              </div>

              <button
                onClick={() => sendZoneDataToBackend(selectedZone)}
                disabled={isSending}
                style={{
                  marginTop: '20px',
                  padding: '15px',
                  background: isSending ? '#ccc' : '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: isSending ? 'not-allowed' : 'pointer',
                  fontSize: '16px',
                  width: '100%',
                  fontWeight: 'bold'
                }}
              >
                {isSending ? '⏳ Sending to Backend...' : '📤 Send to Backend & Get Fuzzy Assessment'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}