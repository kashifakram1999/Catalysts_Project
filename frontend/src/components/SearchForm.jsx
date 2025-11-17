import { useState, useEffect } from 'react';
import { convertersAPI } from '../services/api';
import CustomSelect from './CustomSelect';

export default function SearchForm({ onSearch, onReset }) {
  const [manufacturers, setManufacturers] = useState([]);
  const [makes, setMakes] = useState([]);
  const [years, setYears] = useState([]);
  const [vehicleClasses, setVehicleClasses] = useState([]);
  const [executiveOrders, setExecutiveOrders] = useState([]);
  const [seriesModels, setSeriesModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);

  const [formData, setFormData] = useState({
    manufacturer: '',
    executive_order: '',
    series_model: '',
    year: '',
    make: '',
    vehicle_class: '',
  });

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoadingData(true);
    try {
      const [makesRes, yearsRes, filtersRes] = await Promise.all([
        convertersAPI.getMakes(),
        convertersAPI.getYears(),
        convertersAPI.getFilters(),
      ]);

      setMakes(makesRes.data || []);
      setYears(yearsRes.data.years || []);
      setManufacturers(filtersRes.data.manufacturers || []);
      setVehicleClasses(filtersRes.data.vehicle_classes || []);
      setExecutiveOrders(filtersRes.data.executive_orders || []);
      setSeriesModels(filtersRes.data.series_models || []);
    } catch (error) {
      console.error('Error loading initial data:', error);
      setMakes([]);
      setYears([]);
      setManufacturers([]);
      setVehicleClasses([]);
      setExecutiveOrders([]);
      setSeriesModels([]);
    } finally {
      setLoadingData(false);
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
      manufacturer: '',
      executive_order: '',
      series_model: '',
      year: '',
      make: '',
      vehicle_class: '',
    });
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
        {/* Main Search Row - Matching PDF Structure */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Company (Manufacturer) */}
          <div>
            <label htmlFor="manufacturer" className="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">
              Company
            </label>
            <CustomSelect
              id="manufacturer"
              name="manufacturer"
              value={formData.manufacturer}
              onChange={handleChange}
              options={[
                { value: '', label: 'All Companies' },
                ...manufacturers.map(mfr => ({ value: mfr.id, label: mfr.name }))
              ]}
              placeholder="All Companies"
              searchable={true}
            />
          </div>

          {/* EO Number */}
          <div>
            <label htmlFor="executive_order" className="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">
              EO Number
            </label>
            <CustomSelect
              id="executive_order"
              name="executive_order"
              value={formData.executive_order}
              onChange={handleChange}
              options={[
                { value: '', label: 'All EO Numbers' },
                ...executiveOrders.map(eo => ({ value: eo, label: eo }))
              ]}
              placeholder="All EO Numbers"
              searchable={true}
            />
          </div>

          {/* Series/Model */}
          <div>
            <label htmlFor="series_model" className="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">
              Series/Model
            </label>
            <CustomSelect
              id="series_model"
              name="series_model"
              value={formData.series_model}
              onChange={handleChange}
              options={[
                { value: '', label: 'All Series/Models' },
                ...seriesModels.map(sm => ({ value: sm, label: sm }))
              ]}
              placeholder="All Series/Models"
              searchable={true}
            />
          </div>

          {/* Model Year */}
          <div>
            <label htmlFor="year" className="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">
              Model Year
            </label>
            <CustomSelect
              id="year"
              name="year"
              value={formData.year}
              onChange={handleChange}
              options={[
                { value: '', label: 'All Years' },
                ...[...years].sort((a, b) => b - a).map(year => ({ value: year.toString(), label: year.toString() }))
              ]}
              placeholder="All Years"
              searchable={true}
            />
          </div>

          {/* Make */}
          <div>
            <label htmlFor="make" className="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">
              Vehicle
            </label>
            <CustomSelect
              id="make"
              name="make"
              value={formData.make}
              onChange={handleChange}
              options={[
                { value: '', label: 'All Vehicle' },
                ...makes.map(make => ({ value: make, label: make }))
              ]}
              placeholder="All Vehicle"
              searchable={true}
            />
          </div>

          {/* Class (Vehicle Class) */}
          <div>
            <label htmlFor="vehicle_class" className="block text-sm font-medium text-primary-700 dark:text-primary-300 mb-2">
              Class
            </label>
            <CustomSelect
              id="vehicle_class"
              name="vehicle_class"
              value={formData.vehicle_class}
              onChange={handleChange}
              options={[
                { value: '', label: 'All Classes' },
                ...vehicleClasses.map(vc => ({ value: vc, label: vc }))
              ]}
              placeholder="All Classes"
              searchable={true}
            />
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
