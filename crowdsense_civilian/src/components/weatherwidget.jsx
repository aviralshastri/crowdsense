import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Stack,
  Chip,
  CircularProgress,
  Alert,
} from "@mui/material";
import { keyframes } from "@mui/system";
import WbSunnyIcon from "@mui/icons-material/WbSunny";
import CloudIcon from "@mui/icons-material/Cloud";
import ThunderstormIcon from "@mui/icons-material/Thunderstorm";
import AcUnitIcon from "@mui/icons-material/AcUnit";
import OpacityIcon from "@mui/icons-material/Opacity";
import AirIcon from "@mui/icons-material/Air";
import ThermostatIcon from "@mui/icons-material/Thermostat";
import WarningIcon from "@mui/icons-material/Warning";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { getWeatherData, getWeatherAdvice } from "../utils/weatherApi";

// Keyframe Animations
const fadeInUp = keyframes`
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const float = keyframes`
  0%, 100% {
    transform: translateY(0px) rotate(0deg);
  }
  50% {
    transform: translateY(-10px) rotate(5deg);
  }
`;

const pulse = keyframes`
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
`;

const shimmer = keyframes`
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
`;

const spin = keyframes`
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
`;

export default function WeatherWidget() {
  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchWeather();
    // Refresh weather every 30 minutes
    const interval = setInterval(fetchWeather, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const fetchWeather = async () => {
    try {
      setLoading(true);
      // Default location: Bhopal (you can make this dynamic based on user location)
      const data = await getWeatherData(23.2599, 77.4126);
      setWeather(data);
      setError(null);
    } catch (err) {
      setError("Unable to fetch weather data");
      console.error("Weather error:", err);
    } finally {
      setLoading(false);
    }
  };

  const getWeatherIcon = (condition) => {
    const iconProps = { fontSize: "large", sx: { color: "#fff" } };
    
    if (condition.includes("rain") || condition.includes("drizzle")) {
      return <OpacityIcon {...iconProps} />;
    } else if (condition.includes("thunder") || condition.includes("storm")) {
      return <ThunderstormIcon {...iconProps} />;
    } else if (condition.includes("cloud")) {
      return <CloudIcon {...iconProps} />;
    } else if (condition.includes("snow")) {
      return <AcUnitIcon {...iconProps} />;
    } else {
      return <WbSunnyIcon {...iconProps} />;
    }
  };

  if (loading) {
    return (
      <Card sx={{ 
        background: "linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(99, 102, 241, 0.3)",
        borderRadius: 2,
        mt: 2,
        animation: `${fadeInUp} 0.6s ease-out 0.4s backwards`,
      }}>
        <CardContent sx={{ textAlign: "center", py: 3 }}>
          <CircularProgress 
            size={30} 
            sx={{ 
              color: "#667eea",
              animation: `${spin} 1s linear infinite`,
            }} 
          />
          <Typography variant="body2" sx={{ mt: 1, color: "#9ca3af" }}>
            Loading weather...
          </Typography>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card sx={{ 
        background: "linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.15) 100%)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(239, 68, 68, 0.3)",
        borderRadius: 2,
        mt: 2,
        animation: `${fadeInUp} 0.6s ease-out 0.4s backwards`,
      }}>
        <CardContent>
          <Alert 
            severity="error" 
            sx={{ 
              bgcolor: "transparent",
              color: "#ef4444",
              "& .MuiAlert-icon": {
                color: "#ef4444",
              }
            }}
          >
            {error}
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!weather) return null;

  const advice = getWeatherAdvice(weather);

  return (
    <Card sx={{ 
      background: "linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%)",
      backdropFilter: "blur(10px)",
      border: "1px solid rgba(99, 102, 241, 0.3)",
      borderRadius: 2,
      mt: 2,
      animation: `${fadeInUp} 0.6s ease-out 0.4s backwards`,
      transition: "all 0.3s ease",
      position: "relative",
      overflow: "hidden",
      "&:hover": {
        transform: "translateY(-3px)",
        boxShadow: "0 10px 25px rgba(99, 102, 241, 0.3)",
        border: "1px solid rgba(99, 102, 241, 0.5)",
      },
      "&::before": {
        content: '""',
        position: "absolute",
        top: 0,
        left: "-100%",
        width: "100%",
        height: "100%",
        background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)",
        animation: `${shimmer} 3s infinite`,
      }
    }}>
      <CardContent sx={{ position: "relative", zIndex: 1 }}>
        {/* Header */}
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
          <Typography variant="h6" sx={{ 
            fontSize: "16px", 
            fontWeight: "bold", 
            color: "#fff",
            animation: `${fadeInUp} 0.5s ease-out 0.5s backwards`,
          }}>
            ☀️ Weather
          </Typography>
          <Box
            sx={{
              background: "linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)",
              borderRadius: "50%",
              p: 1.2,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              animation: `${float} 3s ease-in-out infinite, ${fadeInUp} 0.5s ease-out 0.5s backwards`,
              boxShadow: "0 5px 15px rgba(251, 191, 36, 0.4)",
              transition: "all 0.3s ease",
              "&:hover": {
                transform: "scale(1.1) rotate(15deg)",
                boxShadow: "0 8px 20px rgba(251, 191, 36, 0.6)",
              }
            }}
          >
            {getWeatherIcon(weather.condition.toLowerCase())}
          </Box>
        </Box>

        {/* Temperature and Condition */}
        <Box sx={{ 
          mb: 2,
          animation: `${fadeInUp} 0.5s ease-out 0.6s backwards`,
        }}>
          <Typography variant="h3" sx={{ 
            color: "#fff", 
            fontWeight: "bold",
            background: "linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)",
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            transition: "all 0.3s ease",
            "&:hover": {
              transform: "scale(1.05)",
            }
          }}>
            {Math.round(weather.temp)}°C
          </Typography>
          <Typography variant="body1" sx={{ color: "#9ca3af", textTransform: "capitalize", fontWeight: 500 }}>
            {weather.condition}
          </Typography>
          <Typography variant="caption" sx={{ color: "#6b7280" }}>
            Feels like {Math.round(weather.feelsLike)}°C
          </Typography>
        </Box>

        {/* Weather Details */}
        <Stack spacing={1} sx={{ mb: 2 }}>
          {[
            { icon: <OpacityIcon sx={{ fontSize: 18, color: "#60a5fa" }} />, label: "Humidity", value: `${weather.humidity}%`, delay: "0.7s" },
            { icon: <AirIcon sx={{ fontSize: 18, color: "#34d399" }} />, label: "Wind", value: `${weather.windSpeed} km/h`, delay: "0.75s" },
            { icon: <ThermostatIcon sx={{ fontSize: 18, color: "#f59e0b" }} />, label: "Pressure", value: `${weather.pressure} hPa`, delay: "0.8s" },
          ].map((item, i) => (
            <Box 
              key={i}
              sx={{ 
                display: "flex", 
                alignItems: "center", 
                gap: 1,
                p: 1,
                borderRadius: 1,
                transition: "all 0.3s ease",
                animation: `${fadeInUp} 0.4s ease-out ${item.delay} backwards`,
                "&:hover": {
                  background: "rgba(99, 102, 241, 0.2)",
                  transform: "translateX(5px)",
                }
              }}
            >
              {item.icon}
              <Typography variant="body2" sx={{ color: "#9ca3af", flex: 1 }}>
                {item.label}: <span style={{ color: "#fff", fontWeight: 600 }}>{item.value}</span>
              </Typography>
            </Box>
          ))}
        </Stack>

        {/* Advice */}
        <Box
          sx={{
            background: advice.safe 
              ? "linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(22, 163, 74, 0.15) 100%)"
              : "linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.15) 100%)",
            border: `1px solid ${advice.safe ? "rgba(34, 197, 94, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
            borderRadius: 2,
            p: 2,
            mb: 2,
            animation: `${fadeInUp} 0.4s ease-out 0.85s backwards, ${pulse} 3s ease-in-out 1s infinite`,
            transition: "all 0.3s ease",
            "&:hover": {
              border: `1px solid ${advice.safe ? "rgba(34, 197, 94, 0.5)" : "rgba(239, 68, 68, 0.5)"}`,
              transform: "scale(1.02)",
            }
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
            {advice.safe ? (
              <CheckCircleIcon sx={{ color: "#22c55e", fontSize: 20 }} />
            ) : (
              <WarningIcon sx={{ color: "#ef4444", fontSize: 20 }} />
            )}
            <Typography
              variant="body2"
              sx={{
                fontWeight: "bold",
                color: advice.safe ? "#22c55e" : "#ef4444",
              }}
            >
              {advice.safe ? "✓ Good to Go Outside" : "⚠ Be Cautious"}
            </Typography>
          </Box>
          <Typography variant="caption" sx={{ color: "#9ca3af", display: "block" }}>
            {advice.message}
          </Typography>
        </Box>

        {/* Precautions */}
        {advice.precautions.length > 0 && (
          <Box sx={{
            animation: `${fadeInUp} 0.4s ease-out 0.9s backwards`,
          }}>
            <Typography
              variant="body2"
              sx={{ color: "#fff", fontWeight: "bold", mb: 1 }}
            >
              💡 Precautions:
            </Typography>
            <Stack spacing={0.5}>
              {advice.precautions.map((precaution, index) => (
                <Chip
                  key={index}
                  label={precaution}
                  size="small"
                  sx={{
                    background: "linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%)",
                    color: "#818cf8",
                    border: "1px solid rgba(99, 102, 241, 0.3)",
                    fontSize: "11px",
                    height: "auto",
                    py: 0.5,
                    transition: "all 0.3s ease",
                    animation: `${fadeInUp} 0.3s ease-out ${0.95 + index * 0.05}s backwards`,
                    "& .MuiChip-label": {
                      whiteSpace: "normal",
                      padding: "4px 8px",
                    },
                    "&:hover": {
                      background: "linear-gradient(135deg, rgba(99, 102, 241, 0.3) 0%, rgba(139, 92, 246, 0.3) 100%)",
                      border: "1px solid rgba(99, 102, 241, 0.5)",
                      transform: "translateX(5px)",
                    }
                  }}
                />
              ))}
            </Stack>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}