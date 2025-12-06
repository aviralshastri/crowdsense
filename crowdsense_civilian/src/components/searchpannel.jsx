import React, { useState, useCallback, useRef } from "react";
import {
  TextField,
  Button,
  Typography,
  Card,
  CardContent,
  Stack,
  Autocomplete,
  Box,
  Alert,
  Chip,
  CircularProgress,
} from "@mui/material";
import { keyframes } from "@mui/system";
import { searchLocation } from "../utils/api";
import NavigationIcon from "@mui/icons-material/Navigation";
import StopIcon from "@mui/icons-material/Stop";
import DirectionsIcon from "@mui/icons-material/Directions";
import WeatherWidget from "./weatherwidget";

// Keyframe Animations
const slideInLeft = keyframes`
  from {
    opacity: 0;
    transform: translateX(-50px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
`;

const fadeIn = keyframes`
  from { opacity: 0; }
  to { opacity: 1; }
`;

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

const shimmer = keyframes`
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
`;

const pulse = keyframes`
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.02);
  }
`;

const bounce = keyframes`
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
`;

export default function SearchPanel({ 
  onPlaceSelect, 
  onRouteSearch, 
  onNavigationStart, 
  onNavigationStop,
  currentInstruction,
  distanceToNext,
  isNavigating 
}) {

  // States for From/To
  const [fromOptions, setFromOptions] = useState([]);
  const [toOptions, setToOptions] = useState([]);
  const [fromLoading, setFromLoading] = useState(false);
  const [toLoading, setToLoading] = useState(false);

  const [fromLocation, setFromLocation] = useState(null);
  const [toLocation, setToLocation] = useState(null);

  // Route state
  const [routeFound, setRouteFound] = useState(false);
  const [loading, setLoading] = useState(false);

  // Debounce timers
  const fromTimerRef = useRef(null);
  const toTimerRef = useRef(null);

  // Cache for search results
  const searchCacheRef = useRef({});

  // Debounced search for From field
  const handleFromSearch = useCallback((value) => {
    if (fromTimerRef.current) {
      clearTimeout(fromTimerRef.current);
    }

    if (value.length < 3) {
      setFromOptions([]);
      return;
    }

    if (searchCacheRef.current[value]) {
      setFromOptions(searchCacheRef.current[value]);
      return;
    }

    setFromLoading(true);

    fromTimerRef.current = setTimeout(async () => {
      try {
        const results = await searchLocation(value);
        searchCacheRef.current[value] = results;
        setFromOptions(results);
      } catch (error) {
        console.error("Search error:", error);
        setFromOptions([]);
      } finally {
        setFromLoading(false);
      }
    }, 300);
  }, []);

  // Debounced search for To field
  const handleToSearch = useCallback((value) => {
    if (toTimerRef.current) {
      clearTimeout(toTimerRef.current);
    }

    if (value.length < 3) {
      setToOptions([]);
      return;
    }

    if (searchCacheRef.current[value]) {
      setToOptions(searchCacheRef.current[value]);
      return;
    }

    setToLoading(true);

    toTimerRef.current = setTimeout(async () => {
      try {
        const results = await searchLocation(value);
        searchCacheRef.current[value] = results;
        setToOptions(results);
      } catch (error) {
        console.error("Search error:", error);
        setToOptions([]);
      } finally {
        setToLoading(false);
      }
    }, 300);
  }, []);

  const handleRouteButton = async () => {
    if (!fromLocation || !toLocation) {
      alert("Select both locations first");
      return;
    }

    setLoading(true);
    
    try {
      const routeData = await onRouteSearch({
        from: fromLocation,
        to: toLocation,
      });

      if (routeData) {
        setRouteFound(true);
      }
    } catch (error) {
      console.error("Route search failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartNavigation = () => {
    if (onNavigationStart) {
      onNavigationStart();
    }
  };

  const handleStopNavigation = () => {
    if (onNavigationStop) {
      onNavigationStop();
    }
  };

  const handleNewRoute = () => {
    setRouteFound(false);
    setFromLocation(null);
    setToLocation(null);
  };

  const formatDistance = (meters) => {
    if (meters < 1000) {
      return `${Math.round(meters)}m`;
    }
    return `${(meters / 1000).toFixed(1)}km`;
  };

  return (
    <>
    <Card sx={{ 
      background: "linear-gradient(145deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)",
      backdropFilter: "blur(20px)",
      border: "1px solid rgba(96, 165, 250, 0.2)",
      borderRadius: 3,
      animation: `${slideInLeft} 0.6s ease-out`,
      transition: "all 0.3s ease",
      "&:hover": {
        transform: "translateY(-5px)",
        boxShadow: "0 20px 40px rgba(0, 0, 0, 0.4)",
        border: "1px solid rgba(96, 165, 250, 0.4)",
      }
    }}>
      <CardContent>
        <Typography variant="h5" gutterBottom sx={{ 
          display: "flex", 
          alignItems: "center", 
          gap: 1,
          fontWeight: "bold",
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          backgroundClip: "text",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          animation: `${fadeIn} 0.8s ease-out`,
          mb: 3,
        }}>
          <DirectionsIcon sx={{ color: "#667eea" }} />
          CrowdSense
        </Typography>

        <Stack spacing={2.5}>
          
          {/* From */}
          <Box sx={{ animation: `${fadeInUp} 0.6s ease-out 0.1s backwards` }}>
            <Autocomplete
              options={fromOptions}
              getOptionLabel={(opt) => opt.name || ""}
              onInputChange={(e, val) => handleFromSearch(val)}
              onChange={(e, val) => {
                setFromLocation(val);
                if (val) onPlaceSelect(val);
              }}
              value={fromLocation}
              disabled={isNavigating}
              loading={fromLoading}
              renderInput={(params) => (
                <TextField 
                  {...params} 
                  label="From" 
                  placeholder="Start typing location..." 
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {fromLoading ? <CircularProgress color="inherit" size={20} /> : null}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                  sx={{
                    "& .MuiOutlinedInput-root": {
                      transition: "all 0.3s ease",
                      "&:hover": {
                        transform: "translateX(5px)",
                      },
                      "&.Mui-focused": {
                        "& .MuiOutlinedInput-notchedOutline": {
                          borderColor: "#667eea",
                          borderWidth: "2px",
                        }
                      }
                    }
                  }}
                />
              )}
              noOptionsText={fromLoading ? "Searching..." : "Type at least 3 characters"}
            />
          </Box>

          {/* To */}
          <Box sx={{ animation: `${fadeInUp} 0.6s ease-out 0.2s backwards` }}>
            <Autocomplete
              options={toOptions}
              getOptionLabel={(opt) => opt.name || ""}
              onInputChange={(e, val) => handleToSearch(val)}
              onChange={(e, val) => {
                setToLocation(val);
                if (val) onPlaceSelect(val);
              }}
              value={toLocation}
              disabled={isNavigating}
              loading={toLoading}
              renderInput={(params) => (
                <TextField 
                  {...params} 
                  label="To" 
                  placeholder="Start typing destination..."
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {toLoading ? <CircularProgress color="inherit" size={20} /> : null}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                  sx={{
                    "& .MuiOutlinedInput-root": {
                      transition: "all 0.3s ease",
                      "&:hover": {
                        transform: "translateX(5px)",
                      },
                      "&.Mui-focused": {
                        "& .MuiOutlinedInput-notchedOutline": {
                          borderColor: "#667eea",
                          borderWidth: "2px",
                        }
                      }
                    }
                  }}
                />
              )}
              noOptionsText={toLoading ? "Searching..." : "Type at least 3 characters"}
            />
          </Box>

          {/* Find Route Button */}
          {!routeFound && (
            <Box sx={{ animation: `${fadeInUp} 0.6s ease-out 0.3s backwards` }}>
              <Button
                variant="contained"
                size="large"
                fullWidth
                onClick={handleRouteButton}
                disabled={!fromLocation || !toLocation || loading}
                sx={{
                  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                  color: "#fff",
                  fontWeight: "bold",
                  fontSize: "15px",
                  py: 1.8,
                  borderRadius: 2,
                  position: "relative",
                  overflow: "hidden",
                  transition: "all 0.3s ease",
                  "&:hover": {
                    transform: "scale(1.02)",
                    boxShadow: "0 10px 30px rgba(102, 126, 234, 0.4)",
                  },
                  "&:active": {
                    transform: "scale(0.98)",
                  },
                  "&::before": {
                    content: '""',
                    position: "absolute",
                    top: 0,
                    left: "-100%",
                    width: "100%",
                    height: "100%",
                    background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)",
                    animation: `${shimmer} 3s infinite`,
                  },
                  "&.Mui-disabled": {
                    background: "rgba(100, 116, 139, 0.3)",
                    color: "rgba(255, 255, 255, 0.3)",
                  }
                }}
              >
                {loading ? "🔍 Finding Route..." : "🔍 Find Safest Route"}
              </Button>
            </Box>
          )}

          {/* START Navigation Button */}
          {routeFound && !isNavigating && (
            <Box sx={{ animation: `${fadeInUp} 0.4s ease-out` }}>
              <Button
                variant="contained"
                color="success"
                size="large"
                fullWidth
                startIcon={<NavigationIcon />}
                onClick={handleStartNavigation}
                sx={{ 
                  mb: 1, 
                  fontWeight: "bold",
                  py: 1.8,
                  borderRadius: 2,
                  background: "linear-gradient(135deg, #22c55e 0%, #16a34a 100%)",
                  animation: `${pulse} 2s ease-in-out infinite`,
                  transition: "all 0.3s ease",
                  "&:hover": {
                    transform: "scale(1.02)",
                    boxShadow: "0 10px 30px rgba(34, 197, 94, 0.4)",
                  }
                }}
              >
                START NAVIGATION
              </Button>
              <Button
                variant="outlined"
                size="small"
                fullWidth
                onClick={handleNewRoute}
                sx={{
                  borderColor: "rgba(96, 165, 250, 0.3)",
                  color: "#60a5fa",
                  transition: "all 0.3s ease",
                  "&:hover": {
                    borderColor: "#60a5fa",
                    background: "rgba(96, 165, 250, 0.1)",
                    transform: "translateY(-2px)",
                  }
                }}
              >
                Plan New Route
              </Button>
            </Box>
          )}

          {/* Stop Navigation Button */}
          {isNavigating && (
            <Box sx={{ animation: `${fadeInUp} 0.4s ease-out` }}>
              <Button
                variant="contained"
                color="error"
                size="large"
                fullWidth
                startIcon={<StopIcon />}
                onClick={handleStopNavigation}
                sx={{ 
                  fontWeight: "bold",
                  py: 1.8,
                  borderRadius: 2,
                  background: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
                  animation: `${pulse} 2s ease-in-out infinite`,
                  transition: "all 0.3s ease",
                  "&:hover": {
                    transform: "scale(1.02)",
                    boxShadow: "0 10px 30px rgba(239, 68, 68, 0.4)",
                  }
                }}
              >
                STOP NAVIGATION
              </Button>
            </Box>
          )}

          {/* Navigation Instructions */}
          {isNavigating && (
            <Box sx={{ animation: `${fadeInUp} 0.4s ease-out` }}>
              <Alert 
                severity="info" 
                sx={{ 
                  background: "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
                  color: "white",
                  borderRadius: 2,
                  border: "1px solid rgba(59, 130, 246, 0.5)",
                  backdropFilter: "blur(10px)",
                  animation: `${bounce} 2s ease-in-out infinite`,
                  "& .MuiAlert-icon": { color: "white" }
                }}
              >
                <Typography variant="h6" gutterBottom sx={{ fontWeight: "bold", fontSize: "16px" }}>
                  {currentInstruction || "Follow the route"}
                </Typography>
                {distanceToNext > 0 && (
                  <Chip 
                    label={`in ${formatDistance(distanceToNext)}`}
                    size="small"
                    sx={{ 
                      backgroundColor: "white", 
                      color: "#1976d2",
                      fontWeight: "bold",
                      mt: 1,
                      animation: `${pulse} 1.5s ease-in-out infinite`,
                    }}
                  />
                )}
              </Alert>
            </Box>
          )}

        </Stack>
      </CardContent>
    </Card>
      
    {/* Weather Widget */}
    <WeatherWidget />
    </>
  );
}