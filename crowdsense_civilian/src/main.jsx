import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

import { ThemeProvider, createTheme } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";

import "./styles/global.css";
import "leaflet/dist/leaflet.css";

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#00e0d0",
    },
    background: {
      default: "#0f1724",
      paper: "#0b1220",
    },
  },
  typography: {
    fontFamily: "Inter, Arial",
  },
});

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
