import React, { useState } from "react";
import { Box, Chip, Paper, Typography, Switch, FormControlLabel, Stack, Snackbar, Alert } from "@mui/material";
import { keyframes } from "@mui/system";
import SearchPanel from "../components/searchpannel";
import MapView from "../components/mapview";
import Navbar from "../components/navbar";
import { getRoute } from "../utils/api";
import useNavigation from "../hooks/usenavigation";

// Keyframe Animations
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

const glow = keyframes`
  0%, 100% {
    box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
  }
  50% {
    box-shadow: 0 6px 25px rgba(245, 158, 11, 0.6);
  }
`;

export default function Home() {
  const [place, setPlace] = useState(null);
  const [routeCoords, setRouteCoords] = useState([]);
  const [routeInstructions, setRouteInstructions] = useState([]);
  const [fromPlace, setFromPlace] = useState(null);
  const [toPlace, setToPlace] = useState(null);
  const [showCrowdData, setShowCrowdData] = useState(true);
  const [snackbar, setSnackbar] = useState({ open: false, message: "", severity: "info" });

  const {
    currentPosition,
    currentInstruction,
    distanceToNext,
    isNavigating,
    simulationMode,
    startNavigation,
    stopNavigation,
  } = useNavigation();

  const handleRouteSearch = async ({ from, to }) => {
    try {
      const route = await getRoute(from.lat, from.lon, to.lat, to.lon);
      setRouteCoords(route.coordinates);
      setRouteInstructions(route.instructions);
      setFromPlace(from);
      setToPlace(to);
      return route;
    } catch (error) {
      alert("Failed to find route. Please try again.");
      console.error("Route error:", error);
      return null;
    }
  };

  const handleNavigationStart = () => {
    if (routeInstructions.length > 0 && routeCoords.length > 0) {
      startNavigation(routeInstructions, routeCoords);
    }
  };

  const handleNavigationStop = () => {
    stopNavigation();
  };

  const handleFeatureClick = (feature) => {
    const messages = {
      map: "Live Crowd Map is currently active",
      analytics: "Crowd Analytics feature coming soon! This will show crowd trends and predictions.",
      saved: "Saved Routes feature coming soon! Save your favorite routes for quick access.",
      history: "Route History feature coming soon! View all your past routes.",
      preferences: "Preferences panel coming soon! Customize your experience.",
      about: "CrowdSense - Smart Navigation with Real-time Crowd Monitoring. Version 1.0 Beta",
      profile: "User Profile feature coming soon! Manage your account and preferences.",
    };

    setSnackbar({
      open: true,
      message: messages[feature] || "Feature coming soon!",
      severity: feature === "map" ? "success" : "info",
    });
  };

  const handleSnackbarClose = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  return (
    <Box sx={{ 
      display: "flex", 
      flexDirection: "column", 
      height: "100vh",
      animation: `${fadeIn} 0.5s ease-out`,
    }}>
      {/* Navigation Bar */}
      <Navbar onFeatureClick={handleFeatureClick} />

      {/* Main Content */}
      <Box sx={{ display: "flex", flex: 1, position: "relative", overflow: "hidden" }}>
        
        {/* Simulation Mode Indicator */}
        {simulationMode && (
          <Chip
            label="🎮 GPS SIMULATOR MODE"
            sx={{
              position: "absolute",
              top: 16,
              right: 16,
              zIndex: 1000,
              background: "linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)",
              color: "#fff",
              fontWeight: "bold",
              animation: `${fadeIn} 0.5s ease-out 0.5s backwards, ${pulse} 2s ease-in-out 1s infinite, ${glow} 2s ease-in-out infinite`,
            }}
          />
        )}

        {/* Crowd Legend */}
        <Paper
          sx={{
            position: "absolute",
            bottom: 20,
            right: 20,
            zIndex: 1000,
            p: 2.5,
            background: "linear-gradient(145deg, rgba(255, 255, 255, 0.95) 0%, rgba(241, 245, 249, 0.95) 100%)",
            backdropFilter: "blur(20px)",
            borderRadius: 3,
            border: "1px solid rgba(226, 232, 240, 0.8)",
            boxShadow: "0 10px 40px rgba(0, 0, 0, 0.1)",
            animation: `${fadeInUp} 0.6s ease-out 0.8s backwards`,
            transition: "all 0.3s ease",
            "&:hover": {
              transform: "translateY(-5px)",
              boxShadow: "0 15px 50px rgba(0, 0, 0, 0.15)",
            }
          }}
        >
          <Typography variant="h6" gutterBottom sx={{ 
            fontSize: "14px", 
            fontWeight: "bold", 
            color: "#000",
            mb: 2,
          }}>
            🎯 Crowd Levels
          </Typography>
          <Stack spacing={1.5}>
            {[
              { color: "#ef4444", label: "High Crowd (600+ people)", icon: "🔴", delay: "0.9s" },
              { color: "#f59e0b", label: "Medium Crowd (300-600)", icon: "🟡", delay: "1.0s" },
              { color: "#22c55e", label: "Low Crowd (<300)", icon: "🟢", delay: "1.1s" },
            ].map((item, i) => (
              <Box 
                key={i}
                sx={{ 
                  display: "flex", 
                  alignItems: "center", 
                  gap: 1.5,
                  animation: `${fadeInUp} 0.4s ease-out ${item.delay} backwards`,
                  transition: "all 0.3s ease",
                  p: 1,
                  borderRadius: 1,
                  "&:hover": {
                    background: "rgba(96, 165, 250, 0.1)",
                    transform: "translateX(5px)",
                  }
                }}
              >
                <Box
                  sx={{
                    width: 20,
                    height: 20,
                    borderRadius: "50%",
                    backgroundColor: item.color,
                    boxShadow: `0 0 10px ${item.color}`,
                    animation: `${pulse} 2s ease-in-out ${i * 0.3}s infinite`,
                  }}
                />
                <Typography variant="body2" sx={{ color: "#000", fontWeight: 500 }}>
                  {item.icon} {item.label}
                </Typography>
              </Box>
            ))}
            <FormControlLabel
              control={
                <Switch
                  checked={showCrowdData}
                  onChange={(e) => setShowCrowdData(e.target.checked)}
                  size="small"
                  sx={{
                    "& .MuiSwitch-switchBase.Mui-checked": {
                      color: "#667eea",
                    },
                    "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": {
                      backgroundColor: "#667eea",
                    },
                  }}
                />
              }
              label={<Typography variant="body2" sx={{ color: "#000", fontWeight: 600 }}>Show Crowd Data</Typography>}
              sx={{ mt: 1 }}
            />
          </Stack>
        </Paper>

        {/* Side Panel */}
        <Box
          sx={{
            width: "380px",
            p: 2.5,
            background: "linear-gradient(180deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.98) 100%)",
            borderRight: "1px solid rgba(96, 165, 250, 0.2)",
            overflowY: "auto",
            "&::-webkit-scrollbar": {
              width: "8px",
            },
            "&::-webkit-scrollbar-track": {
              background: "rgba(51, 65, 85, 0.3)",
              borderRadius: "4px",
            },
            "&::-webkit-scrollbar-thumb": {
              background: "rgba(96, 165, 250, 0.5)",
              borderRadius: "4px",
              "&:hover": {
                background: "rgba(96, 165, 250, 0.7)",
              },
            },
          }}
        >
          <SearchPanel
            onPlaceSelect={setPlace}
            onRouteSearch={handleRouteSearch}
            onNavigationStart={handleNavigationStart}
            onNavigationStop={handleNavigationStop}
            currentInstruction={currentInstruction}
            distanceToNext={distanceToNext}
            isNavigating={isNavigating}
          />
        </Box>

        {/* Map */}
        <Box sx={{ flex: 1 }}>
          <MapView
            selectedPlace={place}
            routeCoords={routeCoords}
            fromPlace={fromPlace}
            toPlace={toPlace}
            currentPosition={currentPosition}
            isNavigating={isNavigating}
            showCrowdData={showCrowdData}
          />
        </Box>
      </Box>

      {/* Snackbar for feature notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        sx={{
          "& .MuiAlert-root": {
            animation: `${fadeInUp} 0.3s ease-out`,
          }
        }}
      >
        <Alert 
          onClose={handleSnackbarClose} 
          severity={snackbar.severity} 
          sx={{ 
            width: "100%",
            background: "linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.98) 100%)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(96, 165, 250, 0.3)",
            color: "#fff",
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}