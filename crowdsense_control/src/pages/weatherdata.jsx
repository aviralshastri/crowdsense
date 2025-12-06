import { useState, useEffect } from 'react';
import "../styles/weather.css";

export default function WeatherData() {
  const [isLoaded, setIsLoaded] = useState(false);

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

  const temperature = 32;         
  const humidity = 68;            
  const condition = "Sunny";      
  const wind = "4.8 m/s";         
  const feelsLike = 35;           
  const visibility = "5.4 km";    
  const uvIndex = 7;              
  const rainChance = "10%";       
  const sunrise = "06:12 AM";     
  const sunset = "06:45 PM";      

  let suggestion = "";
  if (temperature > 38) suggestion = "Stay hydrated and avoid going out in afternoon.";
  else if (temperature < 15) suggestion = "Wear warm clothing, temperature is low.";
  else if (humidity > 80) suggestion = "Humidity is high, avoid crowded places.";
  else if (uvIndex > 6) suggestion = "UV index is high, use sunscreen.";
  else suggestion = "Weather looks normal. No special precautions needed.";

  let warning = "";
  if (temperature > 40) warning = "Extreme Heat Alert!";
  else if (uvIndex > 9) warning = "UV Radiation Danger!";
  else if (rainChance.replace('%','') > 60) warning = "High chance of rain!";
  else warning = "No severe weather warnings.";

  const weatherBoxes = [
    { label: "Temperature", value: `${temperature}°C`, icon: "🌡️" },
    { label: "Humidity", value: `${humidity}%`, icon: "💧" },
    { label: "Feels Like", value: `${feelsLike}°C`, icon: "🤚" },
    { label: "Condition", value: condition, icon: "☀️" },
    { label: "Wind Speed", value: wind, icon: "💨" },
    { label: "Visibility", value: visibility, icon: "👁️" },
    { label: "UV Index", value: uvIndex, icon: "☀️" },
    { label: "Rain Probability", value: rainChance, icon: "🌧️" }
  ];

  return (
    <div className={`weather-page ${isLoaded ? 'loaded' : ''}`}>
      
      <div className="weather-header">
        <div className="weather-title">Weather Data</div>
        <div className="live-indicator">
          <span className="live-dot"></span>
          LIVE
        </div>
      </div>

      <div className="weather-grid">
        {weatherBoxes.map((box, index) => (
          <div 
            key={index} 
            className="weather-box"
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            <div className="box-header">
              <span className="box-icon">{box.icon}</span>
              <span className="box-label">{box.label}</span>
            </div>
            <div className="weather-value">{box.value}</div>
            <div className="box-shimmer"></div>
          </div>
        ))}
      </div>

      {/* Suggestion Box */}
      <div className="weather-suggestion info-box">
        <div className="info-icon">💡</div>
        <div className="info-content">
          <span className="info-label">Suggestion: </span>
          {suggestion}
        </div>
      </div>

      {/* Warning Box */}
      <div className="weather-warning info-box">
        <div className="info-icon">⚠️</div>
        <div className="info-content">
          <span className="info-label">Warning: </span>
          <span className={warning.includes("Alert") || warning.includes("Danger") ? "warning-red" : "warning-green"}>
            {warning}
          </span>
        </div>
      </div>

      {/* Sunrise/Sunset Box */}
      <div className="weather-sun info-box">
        <div className="sun-item">
          <span className="sun-icon">🌅</span>
          <div>
            <div className="sun-label">Sunrise</div>
            <div className="sun-time">{sunrise}</div>
          </div>
        </div>
        <div className="sun-divider"></div>
        <div className="sun-item">
          <span className="sun-icon">🌇</span>
          <div>
            <div className="sun-label">Sunset</div>
            <div className="sun-time">{sunset}</div>
          </div>
        </div>
      </div>

    </div>
  );
}