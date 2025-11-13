import { useState, useEffect } from 'react';
import { convertersAPI } from '../services/api';

export default function SearchForm({ onSearch, onReset }) {
  const [makes, setMakes] = useState([]);
  const [models, setModels] = useState([]);
  const [years, setYears] = useState([]);
  const [engineSizes, setEngineSizes] = useState([]);
  const [applicationTypes, setApplicationTypes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);

  const [formData, setFormData] = useState({
    year: '',
    make: '',
    model: '',
    engine_size: '',
    test_group: '',
    application_type: '',
  });

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (formData.make) {
      loadModels(formData.make);
    } else {
      setModels([]);
    }
  }, [formData.make]);

  const loadInitialData = async () => {
    setLoadingData(true);
    try {
      const [makesRes, yearsRes, filtersRes] = await Promise.all([
        convertersAPI.getMakes(),
        convertersAPI.getYears(),
        convertersAPI.getFilters(),
      ]);

      console.log('Makes:', makesRes.data);
      console.log('Years:', yearsRes.data);
      console.log('Filters:', filtersRes.data);

      setMakes(makesRes.data || []);
      setYears(yearsRes.data.years || []);
      setApplicationTypes(filtersRes.data.application_types || []);

      // Extract unique engine sizes from filters if available
      const engineSizesFromFilters = filtersRes.data.engine_sizes || [];
      setEngineSizes(engineSizesFromFilters);
    } catch (error) {
      console.error('Error loading initial data:', error);
      // Set empty arrays on error
      setMakes([]);
      setYears([]);
      setApplicationTypes([]);
    } finally {
      setLoadingData(false);
    }
  };

  const loadModels = async (make) => {
    try {
      const res = await convertersAPI.getModels(make);
      console.log('Models for', make, ':', res.data);
      setModels(res.data || []);
    } catch (error) {
      console.error('Error loading models:', error);
      setModels([]);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setLoading(true);
    // Filter out empty values
    const filters = Object.entries(formData).reduce((acc, [key, value]) => {
      if (value) acc[key] = value;
      return acc;
    }, {});
    onSearch(filters);
    setTimeout(() => setLoading(false), 500);
  };

  const handleReset = () => {
    setFormData({
      year: '',
      make: '',
      model: '',
      engine_size: '',
      test_group: '',
      application_type: '',
    });
    setModels([]);
    onReset();
  };

  if (loadingData) {
    return (
      <div className="card p-6 mb-6">
        <div className="flex items-center justify-center py-8">
          <svg className="animate-spin h-8 w-8 text-accent-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="ml-3 text-primary-600 dark:text-primary-400">Loading search options...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6 mb-6">
      <h2 className="text-2xl font-bold text-primary-900 dark:text-primary-100 mb-6">
        Find Your Catalytic Converter
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Main Search Row - Similar to carbcats.com */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {/* Year Select */}
          <div>
            <label htmlFor="year" className="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">
              Year
            </label>
            <select
              id="year"
              name="year"
              value={formData.year}
              onChange={handleChange}
              className="input-field"
            >
              <option value="">All Years</option>
              {years.sort((a, b) => b - a).map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>

          {/* Make Select */}
          <div>
            <label htmlFor="make" className="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">
              Make
            </label>
            <select
              id="make"
              name="make"
              value={formData.make}
              onChange={handleChange}
              className="input-field"
            >
              <option value="">All Makes</option>
              {makes.map(make => (
                <option key={make} value={make}>{make}</option>
              ))}
            </select>
          </div>

          {/* Model Select */}
          <div>
            <label htmlFor="model" className="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">
              Model
            </label>
            <select
              id="model"
              name="model"
              value={formData.model}
              onChange={handleChange}
              disabled={!formData.make}
              className="input-field disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">All Models</option>
              {models.map(model => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          </div>

          {/* Engine Size Input */}
          <div>
            <label htmlFor="engine_size" className="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">
              Engine Size
            </label>
            <input
              type="text"
              id="engine_size"
              name="engine_size"
              value={formData.engine_size}
              onChange={handleChange}
              placeholder="e.g., 2.9"
              className="input-field"
            />
          </div>

          {/* Group (Test Group) Input */}
          <div>
            <label htmlFor="test_group" className="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">
              Group
            </label>
            <input
              type="text"
              id="test_group"
              name="test_group"
              value={formData.test_group}
              onChange={handleChange}
              placeholder="Test Group"
              className="input-field"
            />
          </div>

          {/* Application Select */}
          <div>
            <label htmlFor="application_type" className="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">
              Application
            </label>
            <select
              id="application_type"
              name="application_type"
              value={formData.application_type}
              onChange={handleChange}
              className="input-field"
            >
              <option value="">All Types</option>
              {applicationTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Searching...
              </span>
            ) : (
              'Search'
            )}
          </button>
          <button
            type="button"
            onClick={handleReset}
            className="btn-secondary px-8"
          >
            Reset
          </button>
        </div>
      </form>
    </div>
  );
}
