import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor — attach JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — handle 401 & try refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const res = await axios.post(`${API_BASE}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const { access_token, refresh_token } = res.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
        }
      } else if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// ─── Auth ───
export const register = (data) => api.post('/auth/register', data);
export const login = (data) => api.post('/auth/login', data);
export const getMe = () => api.get('/auth/me');

// ─── Prediction ───
export const submitPrediction = (data) => api.post('/predict', data);
export const getLatestPrediction = (userId) => api.get(`/predict/${userId}/latest`);

// ─── SHAP ───
export const getShapExplanations = (predictionId) => api.get(`/shap/${predictionId}`);

// ─── Simulation ───
export const simulateFuture = (data) => api.post('/simulate', data);

// ─── Chat ───
export const sendChatMessage = (userId, message) =>
  api.post(`/chat/${userId}/message`, { message });
export const getChatHistory = (userId) => api.get(`/chat/${userId}/history`);

// ─── Admin ───
export const adminListUsers = () => api.get('/admin/users');
export const adminGetUser = (userId) => api.get(`/admin/users/${userId}`);
export const adminCreateUser = (data) => api.post('/admin/users', data);
export const adminUpdateUser = (userId, data) => api.put(`/admin/users/${userId}`, data);
export const adminUpdateRole = (userId, role) => api.put(`/admin/users/${userId}/role`, { role });
export const adminDeleteUser = (userId) => api.delete(`/admin/users/${userId}`);
export const adminGetStats = () => api.get('/admin/users/stats');

// ─── Reports ───
export const generateReport = (userId) => api.post(`/reports/${userId}/generate`);
export const getReportStatus = (reportId) => api.get(`/reports/${reportId}/status`);
export const downloadReport = (reportId) =>
  api.get(`/reports/${reportId}/download`, { responseType: 'blob' });

export default api;
