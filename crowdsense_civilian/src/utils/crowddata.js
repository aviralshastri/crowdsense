// Sample crowd data for different locations
// In production, this will come from your backend API

export const sampleCrowdData = [
  // Bhopal locations
  {
    id: 1,
    name: "DB Mall Bhopal",
    lat: 23.2156,
    lon: 77.4305,
    crowdLevel: "high", // high, medium, low
    crowdCount: 850,
    category: "Shopping Mall",
  },
  {
    id: 2,
    name: "New Market Area",
    lat: 23.2599,
    lon: 77.4126,
    crowdLevel: "high",
    crowdCount: 920,
    category: "Market",
  },
  {
    id: 3,
    name: "Railway Station Bhopal",
    lat: 23.2687,
    lon: 77.4085,
    crowdLevel: "medium",
    crowdCount: 450,
    category: "Transport Hub",
  },
  {
    id: 4,
    name: "Van Vihar National Park",
    lat: 23.2156,
    lon: 77.4305,
    crowdLevel: "low",
    crowdCount: 120,
    category: "Park",
  },
  {
    id: 5,
    name: "Upper Lake Area",
    lat: 23.2494,
    lon: 77.3756,
    crowdLevel: "medium",
    crowdCount: 380,
    category: "Tourist Spot",
  },
  {
    id: 6,
    name: "MP Nagar Zone 1",
    lat: 23.2328,
    lon: 77.4065,
    crowdLevel: "high",
    crowdCount: 750,
    category: "Commercial Area",
  },
  {
    id: 7,
    name: "Boat Club",
    lat: 23.2420,
    lon: 77.3890,
    crowdLevel: "low",
    crowdCount: 95,
    category: "Recreation",
  },
  {
    id: 8,
    name: "Arera Colony Market",
    lat: 23.2190,
    lon: 77.4230,
    crowdLevel: "medium",
    crowdCount: 420,
    category: "Market",
  },
  {
    id: 9,
    name: "Bittan Market",
    lat: 23.2425,
    lon: 77.4310,
    crowdLevel: "high",
    crowdCount: 680,
    category: "Market",
  },
  {
    id: 10,
    name: "Shahpura Lake",
    lat: 23.1853,
    lon: 77.4631,
    crowdLevel: "low",
    crowdCount: 75,
    category: "Lake",
  },
];

// Function to get crowd color based on level
export const getCrowdColor = (level) => {
  switch (level) {
    case "high":
      return "#ef4444"; // Red
    case "medium":
      return "#f59e0b"; // Yellow/Orange
    case "low":
      return "#22c55e"; // Green
    default:
      return "#6b7280"; // Gray
  }
};

// Function to get crowd label
export const getCrowdLabel = (level) => {
  switch (level) {
    case "high":
      return "High Crowd";
    case "medium":
      return "Medium Crowd";
    case "low":
      return "Low Crowd";
    default:
      return "Unknown";
  }
};

// Function to simulate real-time crowd updates (optional)
export const generateRandomCrowdData = (lat, lon, radius = 0.1) => {
  const count = Math.floor(Math.random() * 20) + 5;
  const data = [];
  
  for (let i = 0; i < count; i++) {
    const randomLat = lat + (Math.random() - 0.5) * radius;
    const randomLon = lon + (Math.random() - 0.5) * radius;
    const crowdCount = Math.floor(Math.random() * 1000);
    
    let crowdLevel = "low";
    if (crowdCount > 600) crowdLevel = "high";
    else if (crowdCount > 300) crowdLevel = "medium";
    
    data.push({
      id: `random-${i}`,
      name: `Location ${i + 1}`,
      lat: randomLat,
      lon: randomLon,
      crowdLevel,
      crowdCount,
      category: "Random",
    });
  }
  
  return data;
};