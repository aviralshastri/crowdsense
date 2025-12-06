import { useState, useEffect } from 'react';
import { getAlerts } from '../api/alerts';
import "../styles/alerts.css";

export default function AlertsPage() {
  const [isLoaded, setIsLoaded] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await getAlerts();
      
      console.log('Backend response:', response); 
      console.log('Alerts received:', response.alerts); 
      
      if (response.success) {
       
        if (response.alerts.length === 0) {
          console.log('No alerts from backend, using dummy data');
          setAlerts([
            {
              zone: "Zone 1",
              crowd: "Low Density",
              level: "low",
              barricade: "NO",
              time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
              icon: "✅"
            }
          ]);
        } else {
          console.log('Setting alerts from backend:', response.alerts.length, 'alerts');
          setAlerts(response.alerts);
        }
      } else {
        console.error('Failed to fetch alerts:', response.error);
        setError('Failed to fetch alerts');
        
        setAlerts([
          {
            zone: "Zone 1",
            crowd: "No Data Available",
            level: "low",
            barricade: "NO",
            time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
            icon: "⚠️"
          }
        ]);
      }
    } catch (err) {
      console.error('Error fetching alerts:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 15000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityClass = (level) => {
    if (level === "low") return "severity-low";
    if (level === "medium") return "severity-medium";
    if (level === "high") return "severity-high";
    if (level === "critical") return "severity-critical";
  };

  const getSeverityLabel = (level) => {
    if (level === "low") return "LOW RISK";
    if (level === "medium") return "MODERATE";
    if (level === "high") return "HIGH RISK";
    if (level === "critical") return "CRITICAL";
  };

  return (
    <div className={`alert-page ${isLoaded ? 'loaded' : ''}`}>

      <div className="alert-header-section">
        <div className="alert-title">
          Crowd Alerts
          {loading && <span style={{marginLeft: '10px', fontSize: '14px', opacity: 0.7}}>🔄 Refreshing...</span>}
        </div>
        <div className="alert-stats">
          <div className="stat-item critical-stat">
            <span className="stat-number">{alerts.filter(a => a.level === 'critical').length}</span>
            <span className="stat-label">Critical</span>
          </div>
          <div className="stat-item high-stat">
            <span className="stat-number">{alerts.filter(a => a.level === 'high').length}</span>
            <span className="stat-label">High</span>
          </div>
          <div className="stat-item medium-stat">
            <span className="stat-number">{alerts.filter(a => a.level === 'medium').length}</span>
            <span className="stat-label">Medium</span>
          </div>
          <div className="stat-item low-stat">
            <span className="stat-number">{alerts.filter(a => a.level === 'low').length}</span>
            <span className="stat-label">Low</span>
          </div>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '1rem',
          margin: '1rem',
          background: 'rgba(220, 53, 69, 0.1)',
          border: '1px solid rgba(220, 53, 69, 0.3)',
          borderRadius: '8px',
          color: '#dc3545'
        }}>
          ⚠️ {error} - Using fallback data
        </div>
      )}

      <div className="alert-list">
        {alerts.map((a, index) => (
          <div 
            key={index} 
            className={`alert-box ${getSeverityClass(a.level)}`}
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            
            <div className="alert-top">
              <div className="alert-icon">{a.icon}</div>
              <div className="alert-header-content">
                <div className="alert-zone">{a.zone}</div>
                <div className={`alert-badge ${getSeverityClass(a.level)}`}>
                  {getSeverityLabel(a.level)}
                </div>
              </div>
              <div className="alert-time">{a.time}</div>
            </div>

            <div className="alert-crowd-level">
              {a.crowd}
            </div>

            <div className="alert-details">
              <div className="alert-detail-item">
                <span className="detail-icon">👥</span>
                <span className="detail-label">Crowd Level:</span>
                <span className="detail-value">{a.crowd}</span>
              </div>

              <div className="alert-detail-item">
                <span className="detail-icon">🚧</span>
                <span className="detail-label">Barricading:</span>
                <span className={`detail-value ${a.barricade === 'YES' ? 'barricade-yes' : 'barricade-no'}`}>
                  {a.barricade}
                </span>
              </div>
            </div>

            <div className="alert-shimmer"></div>
          </div>
        ))}
      </div>

    </div>
  );
}