import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/dashboard.jsx";
import SensorData from "./pages/sensordata.jsx";
import CameraFeed from "./pages/camerafeed.jsx";
import WeatherData from "./pages/weatherdata.jsx";
import AlertsPage from "./pages/alertpages.jsx";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/sensor" element={<SensorData />} />
        <Route path="/camera" element={<CameraFeed />} />
        <Route path="/weather" element={<WeatherData />} />
        <Route path="/alerts" element={<AlertsPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
