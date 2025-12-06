import axios from "axios";

// Get route with turn-by-turn instructions using OSRM
export const getRoute = async (fromLat, fromLon, toLat, toLon) => {
  try {
    const url = `https://router.project-osrm.org/route/v1/driving/${fromLon},${fromLat};${toLon},${toLat}?overview=full&geometries=geojson&steps=true`;
    
    const res = await axios.get(url);
    
    if (res.data.code !== "Ok") {
      throw new Error("Route not found");
    }

    const route = res.data.routes[0];
    
    // Extract coordinates for polyline (convert from [lon, lat] to [lat, lon])
    const coordinates = route.geometry.coordinates.map(coord => [coord[1], coord[0]]);
    
    // Extract turn-by-turn instructions
    const instructions = [];
    route.legs.forEach(leg => {
      leg.steps.forEach(step => {
        instructions.push({
          instruction: step.maneuver.instruction || getManeuverText(step.maneuver),
          distance: step.distance, // in meters
          duration: step.duration, // in seconds
          location: [step.maneuver.location[1], step.maneuver.location[0]], // [lat, lon]
          type: step.maneuver.type,
          modifier: step.maneuver.modifier,
        });
      });
    });

    return {
      coordinates,
      instructions,
      distance: route.distance, // total distance in meters
      duration: route.duration, // total duration in seconds
    };
  } catch (error) {
    console.error("Route error:", error);
    throw error;
  }
};

// Convert maneuver type to human-readable instruction
function getManeuverText(maneuver) {
  const type = maneuver.type;
  const modifier = maneuver.modifier;

  const instructions = {
    "depart": "Start your journey",
    "arrive": "You have arrived at your destination",
    "turn": `Turn ${modifier || ""}`,
    "new name": "Continue on the road",
    "continue": "Continue straight",
    "merge": `Merge ${modifier || ""}`,
    "on ramp": "Take the ramp",
    "off ramp": "Take the exit",
    "fork": `Take the ${modifier || ""} fork`,
    "end of road": `Turn ${modifier || ""} at the end of the road`,
    "roundabout": "Enter the roundabout",
    "rotary": "Enter the rotary",
    "roundabout turn": `At the roundabout, take exit and turn ${modifier || ""}`,
    "notification": "Continue on the road",
  };

  return instructions[type] || `${type} ${modifier || ""}`.trim();
}

// Calculate distance between two points (Haversine formula)
export const calculateDistance = (lat1, lon1, lat2, lon2) => {
  const R = 6371e3; // Earth's radius in meters
  const φ1 = (lat1 * Math.PI) / 180;
  const φ2 = (lat2 * Math.PI) / 180;
  const Δφ = ((lat2 - lat1) * Math.PI) / 180;
  const Δλ = ((lon2 - lon1) * Math.PI) / 180;

  const a =
    Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c; // Distance in meters
};