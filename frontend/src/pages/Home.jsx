import { useState } from 'react';
import SearchForm from '../components/SearchForm';
import ResultsTable from '../components/ResultsTable';
import { convertersAPI } from '../services/api';

export default function Home() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState(null);
  const [currentFilters, setCurrentFilters] = useState({});
  const [searched, setSearched] = useState(false);

  const handleSearch = async (filters, page = 1) => {
    setLoading(true);
    setSearched(true);
    setCurrentFilters(filters);

    try {
      const response = await convertersAPI.getConverters({
        ...filters,
        page
      });

      setResults(response.data.results);
      setPagination({
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous,
        currentPage: page
      });
    } catch (error) {
      console.error('Error fetching converters:', error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (page) => {
    handleSearch(currentFilters, page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleReset = () => {
    setResults([]);
    setPagination(null);
    setCurrentFilters({});
    setSearched(false);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-primary-700 to-accent-600 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-white mb-4">
              CARB Catalytic Converter Lookup
            </h1>
            <p className="text-xl text-primary-100 max-w-2xl mx-auto">
              Find California Air Resources Board (CARB) approved aftermarket catalytic converters for your vehicle
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Form */}
        <SearchForm onSearch={handleSearch} onReset={handleReset} />

        {/* Info Cards */}
        {!searched && (
          <div className="grid md:grid-cols-3 gap-6 mt-8">
            <div className="card p-6">
              <div className="flex items-center justify-center w-12 h-12 bg-accent-100 dark:bg-accent-900 rounded-lg mb-4">
                <svg className="w-6 h-6 text-accent-600 dark:text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-primary-900 dark:text-primary-100 mb-2">
                Accurate Data
              </h3>
              <p className="text-primary-600 dark:text-primary-400">
                Direct from official CARB sources, updated regularly
              </p>
            </div>

            <div className="card p-6">
              <div className="flex items-center justify-center w-12 h-12 bg-accent-100 dark:bg-accent-900 rounded-lg mb-4">
                <svg className="w-6 h-6 text-accent-600 dark:text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-primary-900 dark:text-primary-100 mb-2">
                Fast Search
              </h3>
              <p className="text-primary-600 dark:text-primary-400">
                Quickly find the right converter for your vehicle
              </p>
            </div>

            <div className="card p-6">
              <div className="flex items-center justify-center w-12 h-12 bg-accent-100 dark:bg-accent-900 rounded-lg mb-4">
                <svg className="w-6 h-6 text-accent-600 dark:text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-primary-900 dark:text-primary-100 mb-2">
                Always Updated
              </h3>
              <p className="text-primary-600 dark:text-primary-400">
                Latest CARB approvals and executive orders
              </p>
            </div>
          </div>
        )}

        {/* Results */}
        {searched && (
          <div className="mt-8">
            <ResultsTable
              results={results}
              loading={loading}
              onPageChange={handlePageChange}
              pagination={pagination}
            />
          </div>
        )}
      </div>
    </div>
  );
}
