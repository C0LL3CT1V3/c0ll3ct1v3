import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL;

const authAPI = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const authService = {
  // Legacy endpoint helpers retained for transition only.
  async registerLegacy(userData) {
    try {
      const response = await authAPI.post('/auth/register', userData);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Registration failed');
    }
  },

  async loginLegacy(credentials) {
    try {
      const response = await authAPI.post('/auth/login', credentials);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  },

  async getCurrentUser(apiClient) {
    if (!apiClient) {
      throw new Error('getCurrentUser requires an authenticated API client.');
    }
    try {
      const response = await apiClient.get('/auth/me');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to get user info');
    }
  },

  logout() {},
};
