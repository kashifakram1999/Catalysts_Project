import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const convertersAPI = {
  // Get all converters with filters
  getConverters: (params) => api.get('/converters/', { params }),

  // Get single converter
  getConverter: (id) => api.get(`/converters/${id}/`),

  // Get available makes
  getMakes: () => api.get('/converters/makes/'),

  // Get models for a specific make
  getModels: (make) => api.get('/converters/models/', { params: { make } }),

  // Get year range
  getYears: () => api.get('/converters/years/'),

  // Get statistics
  getStats: () => api.get('/converters/stats/'),

  // Get all filter options
  getFilters: () => api.get('/converters/filters/'),
};

export const manufacturersAPI = {
  // Get all manufacturers
  getManufacturers: () => api.get('/manufacturers/'),

  // Get single manufacturer
  getManufacturer: (id) => api.get(`/manufacturers/${id}/`),
};

export default api;
