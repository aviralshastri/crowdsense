import "../styles/dashboard.css";
import { useNavigate } from "react-router-dom";

import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <div className="dashboard">

      {/* TOP BAR */}
      <div className="top-bar">
        <div className="title">CrowdSense</div>

        <div className="top-buttons">
          <button className="large-button" onClick={() => navigate("/sensor")}>sensor data</button>
          <button className="large-button" onClick={() => navigate("/camera")}>camera feed</button>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="main-content">

        {/* MAP SECTION */}
        <div className="map-view">
          <MapContainer
            center={[28.6139, 77.2090]}  
            zoom={13}
            style={{ width: "100%", height: "100%", borderRadius: "16px" }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution="© OpenStreetMap"
            />
          </MapContainer>
        </div>

        {/* RIGHT SIDE PANELS */}
        <div className="right-side">
          <button className="weather-panel" onClick={() => navigate("/weather")}>
            weather data
          </button>
          <button className="alerts-panel" onClick={() => navigate("/alerts")}>
            alerts
          </button>
        </div>

      </div>
    </div>
  );
}