import axios from 'axios';

const API_BASE = 'https://flipkart-gridlock-crowdflow-project.onrender.com';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

// --- Prediction endpoints ---
export const predictEventImpact = async (eventData) => {
  const { data } = await api.post('/predict/event-impact', eventData);
  return data;
};

export const getDiversionPlan = async (planData) => {
  const { data } = await api.post('/predict/diversion-plan', planData);
  return data;
};

// --- Model endpoints ---
export const getModelExplanation = async (predictionId) => {
  const { data } = await api.get(`/model/explain/${predictionId}`);
  return data;
};

export const getModelMetrics = async () => {
  const { data } = await api.get('/model/metrics');
  return data;
};

// --- Events endpoints ---
export const getHistoricalEvents = async (params = {}) => {
  const { data } = await api.get('/events/historical', { params });
  return data;
};

export const getHeatmapData = async () => {
  const { data } = await api.get('/events/heatmap');
  return data;
};

export const getDashboardStats = async () => {
  const { data } = await api.get('/events/stats');
  return data;
};

export const getCorridors = async () => {
  const { data } = await api.get('/events/corridors');
  return data;
};

export const getZones = async () => {
  const { data } = await api.get('/events/zones');
  return data;
};

export const getPoliceStations = async () => {
  const { data } = await api.get('/events/police-stations');
  return data;
};

export const getHealthCheck = async () => {
  const { data } = await api.get('/health');
  return data;
};

export default api;
