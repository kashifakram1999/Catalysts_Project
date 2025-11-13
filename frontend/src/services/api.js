import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

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

export const blogAPI = {
  // Get the most recent published blog post
  getLatest: () => api.get('/blogs/latest/'),

  // Get all published blogs
  getBlogs: (params) => api.get('/blogs/', { params }),

  // Get a single blog by slug
  getBlog: (slug) => api.get(`/blogs/${slug}/`),
};

export default api;
