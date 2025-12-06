import { useState, useEffect, useRef } from "react";
import { getStats } from "../api/camera";
import "../styles/camera.css";

export default function CameraFeed() {
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [personCounts, setPersonCounts] = useState({});
  const [liveFrames, setLiveFrames] = useState({});
  const wsRefs = useRef({});

  const cameras = [
    "Camera 1 - Main Gate",
    "Camera 2 - Food Court",
    "Camera 3 - Stage Area",
    "Camera 4 - Parking",
    "Camera 5 - Exit Point",
    "Camera 6 - VIP Area",
  ];

  // WebSocket connection for live camera feeds
  useEffect(() => {
    cameras.forEach((_, index) => {
      const ws = new WebSocket(`ws://localhost:5000/ws/camera/${index + 1}`);
      
      ws.onopen = () => {
        console.log(`WebSocket connected for Camera ${index + 1}`);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'frame') {
            // Update live frame
            setLiveFrames(prev => ({
              ...prev,
              [index]: `data:image/jpeg;base64,${data.frame}`
            }));
          }
          
          if (data.type === 'detection') {
            // Update person count
            setPersonCounts(prev => ({
              ...prev,
              [index]: data.person_count
            }));
          }
        } catch (error) {
          console.error(`Error parsing WebSocket message for Camera ${index + 1}:`, error);
        }
      };

      ws.onerror = (error) => {
        console.error(`WebSocket error for Camera ${index + 1}:`, error);
      };

      ws.onclose = () => {
        console.log(`WebSocket closed for Camera ${index + 1}`);
      };

      wsRefs.current[index] = ws;
    });

    // Cleanup on unmount
    return () => {
      Object.values(wsRefs.current).forEach(ws => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      });
    };
  }, []);

  const fetchStats = async () => {
    const result = await getStats();
    if (result.success) {
      alert(`System Stats:\nBuffer Size: ${result.data.buffer_size}\nRecent Records: ${result.data.recent_records || 'N/A'}`);
    }
  };

  return (
    <div className="camera-page">
      <div className="header">
        <div className="camera-title">Camera Feeds</div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button 
            onClick={fetchStats}
            style={{
              padding: '8px 16px',
              background: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            📊 Stats
          </button>
          <div className="live-indicator">
            <div className="live-dot"></div>
            <span className="live-text">LIVE</span>
          </div>
        </div>
      </div>

      <div className="camera-grid">
        {cameras.map((cam, index) => (
          <div
            key={index}
            className="camera-box"
            style={{ animationDelay: `${index * 0.1}s` }}
            onClick={() => setSelectedCamera(index)}
          >
            <div className="camera-label">{cam}</div>
            
            {/* Live frame preview */}
            {liveFrames[index] && (
              <img 
                src={liveFrames[index]} 
                alt={`Camera ${index + 1}`}
                style={{
                  position: 'absolute',
                  top: '40px',
                  left: '10px',
                  right: '10px',
                  bottom: '80px',
                  objectFit: 'cover',
                  borderRadius: '5px',
                  opacity: 0.8
                }}
              />
            )}
            
            {personCounts[index] !== undefined && (
              <div style={{
                position: 'absolute',
                top: '10px',
                right: '10px',
                background: 'rgba(255, 0, 0, 0.8)',
                color: 'white',
                padding: '5px 10px',
                borderRadius: '5px',
                fontWeight: 'bold',
                fontSize: '14px',
                zIndex: 10
              }}>
                👤 {personCounts[index]}
              </div>
            )}
            
            <div className="status-bar">
              <div className="status-dot"></div>
              <span className="status-text">Active</span>
            </div>
          </div>
        ))}
      </div>

      {selectedCamera !== null && (
        <div 
          className="camera-popup-bg" 
          onClick={() => setSelectedCamera(null)}
        >
          <div 
            className="camera-popup-box" 
            onClick={(e) => e.stopPropagation()}
          >
            <div
              className="popup-close"
              onClick={() => setSelectedCamera(null)}
            >
              ✕
            </div>

            <div className="popup-content">
              <h1 className="popup-title">
                {cameras[selectedCamera]}
              </h1>
              
              {/* Live frame in popup */}
              {liveFrames[selectedCamera] && (
                <div style={{
                  marginTop: '20px',
                  borderRadius: '10px',
                  overflow: 'hidden',
                  maxHeight: '400px'
                }}>
                  <img 
                    src={liveFrames[selectedCamera]} 
                    alt={`Camera ${selectedCamera + 1}`}
                    style={{
                      width: '100%',
                      height: 'auto',
                      display: 'block'
                    }}
                  />
                </div>
              )}
              
              {personCounts[selectedCamera] !== undefined && (
                <div style={{
                  background: 'rgba(76, 175, 80, 0.2)',
                  border: '2px solid #4CAF50',
                  padding: '15px',
                  borderRadius: '10px',
                  marginTop: '20px',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#4CAF50' }}>
                    Detected Persons
                  </div>
                  <div style={{ fontSize: '48px', fontWeight: 'bold', color: '#4CAF50', marginTop: '10px' }}>
                    {personCounts[selectedCamera]}
                  </div>
                </div>
              )}
              
              <div className="fullscreen-status-bar">
                <div className="status-dot"></div>
                <span className="status-text">Live Stream Active</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}