import axios from "axios";

// Free API - No key required for basic usage
// Alternatively, get your free API key from: https://openweathermap.org/api
const WEATHER_API_KEY = ""; // Leave empty to use Open-Meteo (no key required)

// Using Open-Meteo API (completely free, no key required)
export const getWeatherData = async (lat, lon) => {
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,pressure_msl`;
    
    const response = await axios.get(url);
    const current = response.data.current;
    
    return {
      temp: current.temperature_2m,
      feelsLike: current.apparent_temperature,
      humidity: current.relative_humidity_2m,
      windSpeed: current.wind_speed_10m,
      pressure: current.pressure_msl,
      precipitation: current.precipitation,
      condition: getWeatherCondition(current.weather_code),
      weatherCode: current.weather_code,
    };
  } catch (error) {
    console.error("Weather API error:", error);
    throw error;
  }
};

// Alternative: OpenWeatherMap API (requires free API key)
export const getWeatherDataOpenWeather = async (lat, lon) => {
  if (!WEATHER_API_KEY) {
    throw new Error("API key required");
  }
  
  try {
    const url = `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lon}&appid=${WEATHER_API_KEY}&units=metric`;
    
    const response = await axios.get(url);
    const data = response.data;
    
    return {
      temp: data.main.temp,
      feelsLike: data.main.feels_like,
      humidity: data.main.humidity,
      windSpeed: data.wind.speed * 3.6, // Convert m/s to km/h
      pressure: data.main.pressure,
      precipitation: data.rain ? data.rain["1h"] || 0 : 0,
      condition: data.weather[0].description,
      weatherCode: data.weather[0].id,
    };
  } catch (error) {
    console.error("Weather API error:", error);
    throw error;
  }
};

// Convert WMO weather codes to descriptions
function getWeatherCondition(code) {
  const weatherCodes = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
  };
  
  return weatherCodes[code] || "Unknown";
}

// Get weather-based advice
export const getWeatherAdvice = (weather) => {
  const { temp, condition, windSpeed, precipitation, humidity } = weather;
  
  let safe = true;
  let message = "";
  const precautions = [];
  
  // Temperature checks
  if (temp > 40) {
    safe = false;
    message = "Extreme heat! Avoid going outside during peak hours.";
    precautions.push("Stay hydrated - drink plenty of water");
    precautions.push("Wear light-colored, loose clothing");
    precautions.push("Use sunscreen SPF 30+");
    precautions.push("Avoid direct sunlight between 11 AM - 4 PM");
  } else if (temp > 35) {
    safe = false;
    message = "Very hot weather. Take precautions if going outside.";
    precautions.push("Carry water bottle");
    precautions.push("Wear hat or cap");
    precautions.push("Take breaks in shade");
  } else if (temp < 5) {
    safe = false;
    message = "Very cold weather. Dress warmly before going out.";
    precautions.push("Wear warm layered clothing");
    precautions.push("Cover ears, hands, and head");
    precautions.push("Limit outdoor exposure time");
  } else if (temp < 15) {
    message = "Cool weather. Consider light jacket.";
    precautions.push("Carry a light jacket or sweater");
  }
  
  // Rain/Storm checks
  if (condition.toLowerCase().includes("thunder") || condition.toLowerCase().includes("storm")) {
    safe = false;
    message = "Thunderstorm alert! Avoid outdoor activities.";
    precautions.push("Stay indoors if possible");
    precautions.push("Avoid open areas and tall objects");
    precautions.push("Carry umbrella and raincoat");
    precautions.push("Check route for waterlogging");
  } else if (condition.toLowerCase().includes("heavy rain") || precipitation > 5) {
    safe = false;
    message = "Heavy rain expected. Plan accordingly.";
    precautions.push("Carry umbrella or raincoat");
    precautions.push("Wear waterproof footwear");
    precautions.push("Avoid flooded areas");
    precautions.push("Drive carefully if using vehicle");
  } else if (condition.toLowerCase().includes("rain") || condition.toLowerCase().includes("drizzle")) {
    message = "Light rain. Carry umbrella for safety.";
    precautions.push("Keep umbrella handy");
    precautions.push("Watch for slippery surfaces");
  }
  
  // Wind checks
  if (windSpeed > 40) {
    safe = false;
    message = "Strong winds! Be cautious outdoors.";
    precautions.push("Secure loose items");
    precautions.push("Avoid areas with trees or loose structures");
    precautions.push("Walk carefully to maintain balance");
  }
  
  // High humidity
  if (humidity > 80 && temp > 30) {
    if (precautions.length === 0) {
      message = "High humidity makes it feel hotter.";
    }
    precautions.push("Stay hydrated");
    precautions.push("Avoid strenuous activities");
  }
  
  // Perfect weather
  if (safe && temp >= 18 && temp <= 30 && !condition.toLowerCase().includes("rain")) {
    message = "Perfect weather for outdoor activities!";
    precautions.push("Enjoy your day!");
    precautions.push("Stay hydrated");
  } else if (safe && message === "") {
    message = "Weather is moderate. Safe to go outside.";
    precautions.push("Check conditions before long trips");
  }
  
  return {
    safe,
    message,
    precautions,
  };
};