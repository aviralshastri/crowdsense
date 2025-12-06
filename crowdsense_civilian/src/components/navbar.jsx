import React, { useState } from "react";
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Badge,
  Menu,
  MenuItem,
  Box,
  Tooltip,
  Switch,
  Divider,
  ListItemIcon,
  ListItemText,
  Chip,
} from "@mui/material";
import { keyframes } from "@mui/system";
import GroupsIcon from "@mui/icons-material/Groups";
import NotificationsIcon from "@mui/icons-material/Notifications";
import MapIcon from "@mui/icons-material/Map";
import HistoryIcon from "@mui/icons-material/History";
import SettingsIcon from "@mui/icons-material/Settings";
import InfoIcon from "@mui/icons-material/Info";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";
import BookmarkIcon from "@mui/icons-material/Bookmark";
import TrafficIcon from "@mui/icons-material/Traffic";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import PersonIcon from "@mui/icons-material/Person";

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

const float = keyframes`
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-5px);
  }
`;

const glow = keyframes`
  0%, 100% {
    box-shadow: 0 0 20px rgba(96, 165, 250, 0.3);
  }
  50% {
    box-shadow: 0 0 30px rgba(96, 165, 250, 0.6);
  }
`;

const pulse = keyframes`
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
`;

const slideDown = keyframes`
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

export default function Navbar({ onFeatureClick }) {
  const [notificationsAnchor, setNotificationsAnchor] = useState(null);
  const [settingsAnchor, setSettingsAnchor] = useState(null);
  const [darkMode, setDarkMode] = useState(true);
  const [liveAlerts, setLiveAlerts] = useState(true);

  const notifications = [
    {
      id: 1,
      type: "warning",
      title: "High Crowd Alert",
      message: "DB Mall area showing high crowd density",
      time: "5 min ago",
    },
    {
      id: 2,
      type: "info",
      title: "Route Update",
      message: "Faster route available to your destination",
      time: "12 min ago",
    },
    {
      id: 3,
      type: "success",
      title: "Weather Clear",
      message: "Perfect weather for outdoor travel",
      time: "1 hour ago",
    },
  ];

  const handleNotificationsClick = (event) => {
    setNotificationsAnchor(event.currentTarget);
  };

  const handleSettingsClick = (event) => {
    setSettingsAnchor(event.currentTarget);
  };

  const handleClose = () => {
    setNotificationsAnchor(null);
    setSettingsAnchor(null);
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case "warning":
        return <WarningAmberIcon sx={{ color: "#f59e0b", fontSize: 20 }} />;
      case "info":
        return <InfoIcon sx={{ color: "#3b82f6", fontSize: 20 }} />;
      case "success":
        return <TrafficIcon sx={{ color: "#22c55e", fontSize: 20 }} />;
      default:
        return <NotificationsIcon sx={{ fontSize: 20 }} />;
    }
  };

  return (
    <AppBar 
      position="static" 
      sx={{ 
        background: "linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.98) 100%)",
        backdropFilter: "blur(20px)",
        boxShadow: "0 4px 20px rgba(0,0,0,0.3)",
        borderBottom: "1px solid rgba(96, 165, 250, 0.2)",
        animation: `${fadeIn} 0.5s ease-out`,
      }}
    >
      <Toolbar sx={{ justifyContent: "space-between" }}>
        {/* Logo and Title */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Box sx={{
            width: 45,
            height: 45,
            borderRadius: 2,
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            animation: `${float} 3s ease-in-out infinite, ${glow} 2s ease-in-out infinite`,
            transition: "all 0.3s ease",
            cursor: "pointer",
            "&:hover": {
              transform: "scale(1.1) translateY(-5px)",
            }
          }}>
            <GroupsIcon sx={{ fontSize: 28, color: "#fff" }} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ 
              fontWeight: "bold", 
              color: "#fff", 
              lineHeight: 1,
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              backgroundClip: "text",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}>
              CrowdSense
            </Typography>
            <Typography variant="caption" sx={{ color: "#94a3b8" }}>
              Smart Navigation & Crowd Monitoring
            </Typography>
          </Box>
          <Chip
            label="BETA"
            size="small"
            sx={{
              background: "linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)",
              color: "#fff",
              fontWeight: "bold",
              fontSize: "10px",
              height: "22px",
              animation: `${pulse} 2s ease-in-out infinite`,
            }}
          />
        </Box>

        {/* Navigation Items */}
        <Box sx={{ display: "flex", gap: 1 }}>
          {[
            { icon: <MapIcon />, tooltip: "Live Crowd Map", feature: "map" },
            { icon: <TrendingUpIcon />, tooltip: "Crowd Analytics", feature: "analytics" },
            { icon: <BookmarkIcon />, tooltip: "Saved Routes", feature: "saved" },
            { icon: <HistoryIcon />, tooltip: "Route History", feature: "history" },
          ].map((item, index) => (
            <Tooltip key={index} title={item.tooltip}>
              <IconButton
                color="inherit"
                onClick={() => onFeatureClick?.(item.feature)}
                sx={{ 
                  color: "#94a3b8",
                  transition: "all 0.3s ease",
                  animation: `${fadeInUp} 0.5s ease-out ${index * 0.05}s backwards`,
                  "&:hover": { 
                    color: "#60a5fa",
                    transform: "translateY(-3px)",
                    background: "rgba(96, 165, 250, 0.1)",
                  }
                }}
              >
                {item.icon}
              </IconButton>
            </Tooltip>
          ))}

          {/* Notifications */}
          <Tooltip title="Notifications">
            <IconButton
              color="inherit"
              onClick={handleNotificationsClick}
              sx={{ 
                color: "#94a3b8",
                transition: "all 0.3s ease",
                animation: `${fadeInUp} 0.5s ease-out 0.2s backwards`,
                "&:hover": { 
                  color: "#60a5fa",
                  transform: "translateY(-3px)",
                  background: "rgba(96, 165, 250, 0.1)",
                }
              }}
            >
              <Badge 
                badgeContent={notifications.length} 
                sx={{
                  "& .MuiBadge-badge": {
                    background: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
                    animation: `${pulse} 2s ease-in-out infinite`,
                  }
                }}
              >
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>

          {/* Settings */}
          <Tooltip title="Settings">
            <IconButton
              color="inherit"
              onClick={handleSettingsClick}
              sx={{ 
                color: "#94a3b8",
                transition: "all 0.3s ease",
                animation: `${fadeInUp} 0.5s ease-out 0.25s backwards`,
                "&:hover": { 
                  color: "#60a5fa",
                  transform: "translateY(-3px) rotate(45deg)",
                  background: "rgba(96, 165, 250, 0.1)",
                }
              }}
            >
              <SettingsIcon />
            </IconButton>
          </Tooltip>

          {/* Profile */}
          <Tooltip title="Profile">
            <IconButton
              color="inherit"
              onClick={() => onFeatureClick?.("profile")}
              sx={{ 
                color: "#94a3b8",
                transition: "all 0.3s ease",
                animation: `${fadeInUp} 0.5s ease-out 0.3s backwards`,
                "&:hover": { 
                  color: "#60a5fa",
                  transform: "translateY(-3px)",
                  background: "rgba(96, 165, 250, 0.1)",
                }
              }}
            >
              <PersonIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>

      {/* Notifications Menu */}
      <Menu
        anchorEl={notificationsAnchor}
        open={Boolean(notificationsAnchor)}
        onClose={handleClose}
        PaperProps={{
          sx: {
            width: 350,
            background: "linear-gradient(145deg, rgba(30, 41, 59, 0.98) 0%, rgba(15, 23, 42, 0.98) 100%)",
            backdropFilter: "blur(20px)",
            color: "#fff",
            maxHeight: 400,
            border: "1px solid rgba(96, 165, 250, 0.2)",
            borderRadius: 2,
            animation: `${slideDown} 0.3s ease-out`,
          },
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <Box sx={{ px: 2, py: 1.5, borderBottom: "1px solid rgba(96, 165, 250, 0.2)" }}>
          <Typography variant="h6" sx={{ fontSize: "16px", fontWeight: "bold" }}>
            🔔 Notifications
          </Typography>
          <Typography variant="caption" sx={{ color: "#94a3b8" }}>
            You have {notifications.length} new notifications
          </Typography>
        </Box>
        {notifications.map((notif, index) => (
          <MenuItem
            key={notif.id}
            onClick={handleClose}
            sx={{
              py: 1.5,
              borderBottom: "1px solid rgba(96, 165, 250, 0.1)",
              transition: "all 0.3s ease",
              animation: `${fadeInUp} 0.3s ease-out ${index * 0.05}s backwards`,
              "&:hover": { 
                background: "rgba(96, 165, 250, 0.1)",
                transform: "translateX(5px)",
              },
            }}
          >
            <ListItemIcon>{getNotificationIcon(notif.type)}</ListItemIcon>
            <ListItemText
              primary={notif.title}
              secondary={
                <>
                  <Typography variant="body2" sx={{ color: "#94a3b8", fontSize: "13px" }}>
                    {notif.message}
                  </Typography>
                  <Typography variant="caption" sx={{ color: "#64748b" }}>
                    {notif.time}
                  </Typography>
                </>
              }
            />
          </MenuItem>
        ))}
        <MenuItem
          onClick={handleClose}
          sx={{
            justifyContent: "center",
            color: "#60a5fa",
            fontWeight: "bold",
            transition: "all 0.3s ease",
            "&:hover": { 
              background: "rgba(96, 165, 250, 0.1)",
            },
          }}
        >
          View All Notifications
        </MenuItem>
      </Menu>

      {/* Settings Menu */}
      <Menu
        anchorEl={settingsAnchor}
        open={Boolean(settingsAnchor)}
        onClose={handleClose}
        PaperProps={{
          sx: {
            width: 280,
            background: "linear-gradient(145deg, rgba(30, 41, 59, 0.98) 0%, rgba(15, 23, 42, 0.98) 100%)",
            backdropFilter: "blur(20px)",
            color: "#fff",
            border: "1px solid rgba(96, 165, 250, 0.2)",
            borderRadius: 2,
            animation: `${slideDown} 0.3s ease-out`,
          },
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <Box sx={{ px: 2, py: 1.5, borderBottom: "1px solid rgba(96, 165, 250, 0.2)" }}>
          <Typography variant="h6" sx={{ fontSize: "16px", fontWeight: "bold" }}>
            ⚙️ Settings
          </Typography>
        </Box>

        <MenuItem sx={{ 
          transition: "all 0.3s ease",
          animation: `${fadeInUp} 0.3s ease-out 0.05s backwards`,
          "&:hover": { 
            background: "rgba(96, 165, 250, 0.1)",
          } 
        }}>
          <ListItemIcon>
            {darkMode ? (
              <DarkModeIcon sx={{ color: "#60a5fa" }} />
            ) : (
              <LightModeIcon sx={{ color: "#f59e0b" }} />
            )}
          </ListItemIcon>
          <ListItemText primary="Dark Mode" />
          <Switch
            checked={darkMode}
            onChange={(e) => setDarkMode(e.target.checked)}
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
        </MenuItem>

        <MenuItem sx={{ 
          transition: "all 0.3s ease",
          animation: `${fadeInUp} 0.3s ease-out 0.1s backwards`,
          "&:hover": { 
            background: "rgba(96, 165, 250, 0.1)",
          } 
        }}>
          <ListItemIcon>
            <WarningAmberIcon sx={{ color: "#ef4444" }} />
          </ListItemIcon>
          <ListItemText primary="Live Alerts" />
          <Switch
            checked={liveAlerts}
            onChange={(e) => setLiveAlerts(e.target.checked)}
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
        </MenuItem>

        <Divider sx={{ backgroundColor: "rgba(96, 165, 250, 0.2)", my: 1 }} />

        <MenuItem
          onClick={() => {
            handleClose();
            onFeatureClick?.("preferences");
          }}
          sx={{ 
            transition: "all 0.3s ease",
            animation: `${fadeInUp} 0.3s ease-out 0.15s backwards`,
            "&:hover": { 
              background: "rgba(96, 165, 250, 0.1)",
              transform: "translateX(5px)",
            } 
          }}
        >
          <ListItemIcon>
            <SettingsIcon sx={{ color: "#94a3b8" }} />
          </ListItemIcon>
          <ListItemText primary="Preferences" />
        </MenuItem>

        <MenuItem
          onClick={() => {
            handleClose();
            onFeatureClick?.("about");
          }}
          sx={{ 
            transition: "all 0.3s ease",
            animation: `${fadeInUp} 0.3s ease-out 0.2s backwards`,
            "&:hover": { 
              background: "rgba(96, 165, 250, 0.1)",
              transform: "translateX(5px)",
            } 
          }}
        >
          <ListItemIcon>
            <InfoIcon sx={{ color: "#94a3b8" }} />
          </ListItemIcon>
          <ListItemText primary="About CrowdSense" />
        </MenuItem>
      </Menu>
    </AppBar>
  );
}