import { useState, useEffect, useRef } from "react";
import { calculateDistance } from "../utils/route";

export default function useNavigation() {
  const [currentPosition, setCurrentPosition] = useState(null);
  const [currentInstruction, setCurrentInstruction] = useState("");
  const [distanceToNext, setDistanceToNext] = useState(0);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isNavigating, setIsNavigating] = useState(false);
  const [simulationMode, setSimulationMode] = useState(false);
  
  const watchIdRef = useRef(null);
  const instructionsRef = useRef([]);
  const routeCoordsRef = useRef([]);
  const lastAnnouncedRef = useRef(-1);
  const simulationIndexRef = useRef(0);
  const simulationIntervalRef = useRef(null);

  const startNavigation = (instructions, routeCoordinates) => {
    instructionsRef.current = instructions;
    routeCoordsRef.current = routeCoordinates;
    setCurrentStepIndex(0);
    setIsNavigating(true);

    if (instructions.length > 0) {
      setCurrentInstruction(instructions[0].instruction);
      announceInstruction(instructions[0].instruction);
    }

    if (!navigator.geolocation) {
      console.log("Geolocation not available, using simulation mode");
      startSimulation();
      return;
    }
    navigator.geolocation.getCurrentPosition(
      () => {
        console.log("Using real GPS");
        setSimulationMode(false);
        startRealGPS();
      },
      (error) => {
        console.log("GPS failed, using simulation mode:", error);
        setSimulationMode(true);
        startSimulation();
      },
      {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0,
      }
    );
  };

  const startRealGPS = () => {
    watchIdRef.current = navigator.geolocation.watchPosition(
      (position) => {
        const userPos = {
          lat: position.coords.latitude,
          lon: position.coords.longitude,
        };
        setCurrentPosition(userPos);
        updateNavigationState(userPos);
      },
      (error) => {
        console.error("Location error:", error);
      
        setSimulationMode(true);
        startSimulation();
      },
      {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0,
      }
    );
  };

  const startSimulation = () => {
    const routeCoords = routeCoordsRef.current;
    
    if (!routeCoords || routeCoords.length === 0) {
      alert("No route coordinates available for simulation");
      return;
    }

    simulationIndexRef.current = 0;
    
    setCurrentPosition({
      lat: routeCoords[0][0],
      lon: routeCoords[0][1],
    });

    simulationIntervalRef.current = setInterval(() => {
      const index = simulationIndexRef.current;
      
      if (index >= routeCoords.length - 1) {
        setCurrentInstruction("You have arrived at your destination!");
        announceInstruction("You have arrived at your destination!");
        stopNavigation();
        return;
      }
      simulationIndexRef.current = index + 1;
      const newPos = {
        lat: routeCoords[index + 1][0],
        lon: routeCoords[index + 1][1],
      };
      
      setCurrentPosition(newPos);
      updateNavigationState(newPos);
    }, 1000); 
  };

  const stopNavigation = () => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    if (simulationIntervalRef.current !== null) {
      clearInterval(simulationIntervalRef.current);
      simulationIntervalRef.current = null;
    }
    
    setIsNavigating(false);
    setSimulationMode(false);
    setCurrentInstruction("");
    setDistanceToNext(0);
    setCurrentStepIndex(0);
    lastAnnouncedRef.current = -1;
    simulationIndexRef.current = 0;
  };

  const updateNavigationState = (userPos) => {
    const instructions = instructionsRef.current;
    const stepIndex = currentStepIndex;

    if (!instructions || stepIndex >= instructions.length) {
      return;
    }

    const currentStep = instructions[stepIndex];
    const distance = calculateDistance(
      userPos.lat,
      userPos.lon,
      currentStep.location[0],
      currentStep.location[1]
    );

    setDistanceToNext(distance);

    if (distance < 30) {
      const nextIndex = stepIndex + 1;
      
      if (nextIndex < instructions.length) {
        setCurrentStepIndex(nextIndex);
        const nextStep = instructions[nextIndex];
        setCurrentInstruction(nextStep.instruction);
        
        if (lastAnnouncedRef.current !== nextIndex) {
          announceInstruction(nextStep.instruction);
          lastAnnouncedRef.current = nextIndex;
        }
      } else {
        setCurrentInstruction("You have arrived at your destination!");
        announceInstruction("You have arrived at your destination!");
        stopNavigation();
      }
    } else if (distance < 100 && lastAnnouncedRef.current !== stepIndex) {
      announceInstruction(`In ${Math.round(distance)} meters, ${currentStep.instruction}`);
      lastAnnouncedRef.current = stepIndex;
    }
  };

  const announceInstruction = (text) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1;
      utterance.volume = 1;
      window.speechSynthesis.speak(utterance);
    }
  };
  useEffect(() => {
    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
      if (simulationIntervalRef.current !== null) {
        clearInterval(simulationIntervalRef.current);
      }
    };
  }, []);

  return {
    currentPosition,
    currentInstruction,
    distanceToNext,
    isNavigating,
    simulationMode,
    startNavigation,
    stopNavigation,
  };
}