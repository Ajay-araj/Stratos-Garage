
import axios from 'axios';
import useAuthStore from '../store/useAuthStore';

const API_BASE_URL =
  import.meta.env.VITE_API_URL || 'http://localhost:8000/api/';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' }
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = useAuthStore.getState().refreshToken;

        const response = await axios.post(
          `${API_BASE_URL}users/auth/refresh/`,
          { refresh: refreshToken }
        );

        const { access } = response.data;
        useAuthStore.getState().setToken(access);
        api.defaults.headers.common['Authorization'] = `Bearer ${access}`;

        return api(originalRequest);
      } catch (err) {
        useAuthStore.getState().logout();
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default api;
