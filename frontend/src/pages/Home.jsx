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
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  const handleSearch = async (filters, page = 1, isLoadMore = false) => {
    setLoading(true);
    setSearched(true);

    // Only update filters and reset results on new search
    if (!isLoadMore) {
      setCurrentFilters(filters);
      setResults([]);
      setCurrentPage(1);
    }

    try {
      const response = await convertersAPI.getConverters({
        ...filters,
        page
      });

      // Append results for load more, replace for new search
      if (isLoadMore) {
        setResults(prev => [...prev, ...response.data.results]);
      } else {
        setResults(response.data.results);
      }

      setPagination({
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous,
        currentPage: page
      });

      setHasMore(!!response.data.next);
      setCurrentPage(page);
    } catch (error) {
      console.error('Error fetching converters:', error);
      if (!isLoadMore) {
        setResults([]);
      }
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadMore = () => {
    if (!loading && hasMore) {
      handleSearch(currentFilters, currentPage + 1, true);
    }
  };

  const handleReset = () => {
    setResults([]);
    setPagination(null);
    setCurrentFilters({});
    setSearched(false);
    setCurrentPage(1);
    setHasMore(false);
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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-8">
        <div className="order-1">
          <SearchForm onSearch={handleSearch} onReset={handleReset} />
        </div>

        {searched && (
          <div className="order-2">
            <ResultsTable
              results={results}
              loading={loading}
              onLoadMore={handleLoadMore}
              pagination={pagination}
              hasMore={hasMore}
            />
          </div>
        )}
      </div>
    </div>
  );
}
