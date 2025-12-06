import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap, Circle, CircleMarker } from "react-leaflet";
import { useEffect } from "react";
import L from "leaflet";
import { sampleCrowdData, getCrowdColor, getCrowdLabel } from "../utils/crowddata";

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

// Add custom CSS for map animations - ONLY for navigation markers and user position
const mapStyles = `
  @keyframes markerBounceStart {
    0% {
      transform: translateY(0);
    }
    50% {
      transform: translateY(-10px);
    }
    100% {
      transform: translateY(0);
    }
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @keyframes userPulse {
    0%, 100% {
      transform: scale(1);
      opacity: 0.6;
    }
    50% {
      transform: scale(1.5);
      opacity: 0;
    }
  }

  /* Only animate start/end markers on first appearance */
  .start-marker-icon,
  .end-marker-icon {
    animation: markerBounceStart 0.6s ease-out;
  }

  /* Animate user position marker */
  .user-marker-icon {
    animation: fadeIn 0.3s ease-out;
  }

  /* Custom popup styling */
  .leaflet-popup-content-wrapper {
    background: linear-gradient(145deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.98) 100%) !important;
    backdrop-filter: blur(20px);
    color: #fff !important;
    border-radius: 12px !important;
    border: 1px solid rgba(96, 165, 250, 0.3);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4) !important;
    animation: fadeIn 0.3s ease-out;
  }

  .leaflet-popup-tip {
    background: rgba(15, 23, 42, 0.98) !important;
  }

  /* Smooth map tile loading */
  .leaflet-tile {
    animation: fadeIn 0.3s ease-out;
  }
`;

// Component to handle map updates with smooth animations
function MapUpdater({ selectedPlace, routeCoords, currentPosition, isNavigating }) {
  const map = useMap();

  useEffect(() => {
    if (isNavigating && currentPosition) {
      // Smooth follow during navigation
      map.flyTo([currentPosition.lat, currentPosition.lon], 17, {
        animate: true,
        duration: 1.5,
        easeLinearity: 0.5,
      });
    } else if (routeCoords && routeCoords.length > 0) {
      // Smooth fit to route bounds
      const bounds = L.latLngBounds(routeCoords);
      map.flyToBounds(bounds, {
        padding: [50, 50],
        animate: true,
        duration: 1.5,
      });
    } else if (selectedPlace) {
      // Smooth zoom to selected place
      map.flyTo([selectedPlace.lat, selectedPlace.lon], 14, {
        animate: true,
        duration: 1.5,
      });
    }
  }, [map, selectedPlace, routeCoords, currentPosition, isNavigating]);

  return null;
}

export default function MapView({ 
  selectedPlace, 
  routeCoords, 
  fromPlace, 
  toPlace,
  currentPosition,
  isNavigating,
  showCrowdData = true
}) {
  const center = selectedPlace
    ? [selectedPlace.lat, selectedPlace.lon]
    : [21.1458, 79.0882];

  return (
    <>
      {/* Inject custom CSS */}
      <style>{mapStyles}</style>
      
      <MapContainer
        center={center}
        zoom={14}
        style={{ width: "100%", height: "100%" }}
        zoomControl={true}
        scrollWheelZoom={true}
        attributionControl={true}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {/* Map updater for smooth zoom/pan */}
        <MapUpdater 
          selectedPlace={selectedPlace} 
          routeCoords={routeCoords}
          currentPosition={currentPosition}
          isNavigating={isNavigating}
        />

        {/* Crowd Data Markers - NO ANIMATION, completely still */}
        {showCrowdData && sampleCrowdData.map((location) => (
          <CircleMarker
            key={location.id}
            center={[location.lat, location.lon]}
            radius={15}
            pathOptions={{
              fillColor: getCrowdColor(location.crowdLevel),
              color: getCrowdColor(location.crowdLevel),
              weight: 2,
              opacity: 0.8,
              fillOpacity: 0.6,
            }}
          >
            <Popup>
              <div style={{ minWidth: "200px" }}>
                <h3 style={{ 
                  margin: "0 0 12px 0", 
                  fontSize: "16px", 
                  fontWeight: "bold",
                  color: "#fff",
                }}>
                  📍 {location.name}
                </h3>
                <div style={{ 
                  padding: "6px 12px", 
                  borderRadius: "8px", 
                  background: getCrowdColor(location.crowdLevel),
                  color: "white",
                  fontWeight: "bold",
                  marginBottom: "12px",
                  display: "inline-block",
                  boxShadow: `0 4px 12px ${getCrowdColor(location.crowdLevel)}40`,
                }}>
                  {getCrowdLabel(location.crowdLevel)}
                </div>
                <p style={{ margin: "6px 0", fontSize: "14px", color: "#cbd5e1" }}>
                  <strong style={{ color: "#60a5fa" }}>👥 Crowd Count:</strong> {location.crowdCount} people
                </p>
                <p style={{ margin: "6px 0", fontSize: "14px", color: "#cbd5e1" }}>
                  <strong style={{ color: "#60a5fa" }}>📍 Category:</strong> {location.category}
                </p>
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* From location marker (green) - only bounces once on appearance */}
        {fromPlace && (
          <Marker 
            position={[fromPlace.lat, fromPlace.lon]}
            icon={new L.Icon({
              iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png",
              shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
              iconSize: [25, 41],
              iconAnchor: [12, 41],
              popupAnchor: [1, -34],
              shadowSize: [41, 41],
              className: 'start-marker-icon'
            })}
          >
            <Popup>
              <div style={{ padding: "4px" }}>
                <strong style={{ color: "#22c55e", fontSize: "15px" }}>🚩 Start</strong>
                <p style={{ margin: "4px 0 0 0", color: "#cbd5e1" }}>{fromPlace.name}</p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* To location marker (red) - only bounces once on appearance */}
        {toPlace && (
          <Marker 
            position={[toPlace.lat, toPlace.lon]}
            icon={new L.Icon({
              iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
              shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
              iconSize: [25, 41],
              iconAnchor: [12, 41],
              popupAnchor: [1, -34],
              shadowSize: [41, 41],
              className: 'end-marker-icon'
            })}
          >
            <Popup>
              <div style={{ padding: "4px" }}>
                <strong style={{ color: "#ef4444", fontSize: "15px" }}>🎯 Destination</strong>
                <p style={{ margin: "4px 0 0 0", color: "#cbd5e1" }}>{toPlace.name}</p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Single selected place marker */}
        {selectedPlace && !fromPlace && !toPlace && (
          <Marker position={[selectedPlace.lat, selectedPlace.lon]}>
            <Popup>
              <div style={{ padding: "4px" }}>
                <strong style={{ color: "#60a5fa", fontSize: "15px" }}>📍 {selectedPlace.name}</strong>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Route Polyline - completely still, no animation */}
        {routeCoords && routeCoords.length > 0 && (
          <Polyline
            positions={routeCoords}
            pathOptions={{
              color: "#00bcd4",
              weight: 5,
              opacity: 0.8,
              lineJoin: "round",
              lineCap: "round",
            }}
          />
        )}

        {/* Current user position during navigation */}
        {isNavigating && currentPosition && (
          <>
            <Marker 
              position={[currentPosition.lat, currentPosition.lon]}
              icon={new L.Icon({
                iconUrl: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%232196F3'%3E%3Ccircle cx='12' cy='12' r='10'/%3E%3Ccircle cx='12' cy='12' r='6' fill='white'/%3E%3Ccircle cx='12' cy='12' r='3' fill='%232196F3'/%3E%3C/svg%3E",
                iconSize: [32, 32],
                iconAnchor: [16, 16],
                className: 'user-marker-icon'
              })}
            >
              <Popup>
                <div style={{ padding: "4px" }}>
                  <strong style={{ color: "#2196F3", fontSize: "15px" }}>📍 Your Location</strong>
                  <p style={{ margin: "4px 0 0 0", color: "#cbd5e1", fontSize: "13px" }}>You are here</p>
                </div>
              </Popup>
            </Marker>
            {/* Static circle around user position - no animation */}
            <Circle
              center={[currentPosition.lat, currentPosition.lon]}
              radius={20}
              pathOptions={{
                color: "#2196F3",
                fillColor: "#2196F3",
                fillOpacity: 0.2,
                weight: 2,
              }}
            />
          </>
        )}
      </MapContainer>
    </>
  );
}