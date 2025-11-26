import { useState, useEffect, useRef } from 'react';
import ConverterDetailModal from './ConverterDetailModal';

export default function ResultsTable({ results, loading, onLoadMore, pagination, hasMore }) {
  const [selectedConverter, setSelectedConverter] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const observerRef = useRef(null);
  const loadMoreRef = useRef(null);

  const handleRowClick = (converter) => {
    setSelectedConverter(converter);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedConverter(null);
  };

  // Set up intersection observer for infinite scroll
  useEffect(() => {
    // Cleanup previous observer
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    // Create new observer
    observerRef.current = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        // When the load more element is visible and we have more data to load
        if (entry.isIntersecting && hasMore && !loading) {
          onLoadMore();
        }
      },
      {
        root: null,
        rootMargin: '200px', // Start loading 200px before reaching the bottom
        threshold: 0.1,
      }
    );

    // Observe the load more element
    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current);
    }

    // Cleanup on unmount
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [hasMore, loading, onLoadMore]);

  // Show loading spinner only on initial load (no results yet)
  if (loading && results.length === 0) {
    return (
      <div className="card p-12">
        <div className="flex flex-col items-center justify-center">
          <svg className="animate-spin h-12 w-12 text-accent-600 mb-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-primary-600 dark:text-primary-400">Loading results...</p>
        </div>
      </div>
    );
  }

  if (!results || results.length === 0) {
    return (
      <div className="card p-12">
        <div className="text-center">
          <svg className="mx-auto h-16 w-16 text-primary-400 dark:text-primary-600 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="text-lg font-medium text-primary-900 dark:text-primary-100 mb-2">
            No converters found
          </h3>
          <p className="text-primary-600 dark:text-primary-400">
            Try adjusting your search criteria
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="card overflow-hidden">
        {/* Table for desktop */}
        <div className="hidden md:block overflow-x-auto">
          <table className="min-w-full divide-y divide-primary-200 dark:divide-primary-700">
            <thead className="bg-primary-50 dark:bg-primary-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider">
                  Manufacturer
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider">
                  Location
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider">
                  Quantity
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider">
                  Application
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider">
                  Group
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider whitespace-nowrap">
                  Cert. Level
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider">
                  EO
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-primary-800 divide-y divide-primary-200 dark:divide-primary-700">
              {results.map((converter) => (
                <tr
                  key={converter.id}
                  onClick={() => handleRowClick(converter)}
                  className="hover:bg-primary-50 dark:hover:bg-primary-700 cursor-pointer transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-primary-900 dark:text-primary-100">
                      {converter.manufacturer_name || 'N/A'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-primary-900 dark:text-primary-100">
                      {converter.converter_location || '-'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-primary-900 dark:text-primary-100">
                      {converter.converter_type || '-'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-primary-900 dark:text-primary-100 text-center">
                    {converter.quantity || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className="text-sm text-primary-900 dark:text-primary-100">
                      {converter.application_type || '-'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-primary-900 dark:text-primary-100 font-mono">
                      {converter.test_group || '-'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-primary-900 dark:text-primary-100">
                      {converter.cert_level || '-'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {converter.eo_document_url ? (
                      <a
                        href={converter.eo_document_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="font-mono text-sm text-accent-600 dark:text-accent-400 font-semibold hover:text-accent-700 dark:hover:text-accent-300 underline"
                      >
                        {converter.executive_order}
                      </a>
                    ) : (
                      <span className="font-mono text-sm text-accent-600 dark:text-accent-400 font-semibold">
                        {converter.executive_order}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Cards for mobile */}
        <div className="md:hidden space-y-4 p-4">
          {results.map((converter) => (
            <div
              key={converter.id}
              onClick={() => handleRowClick(converter)}
              className="bg-primary-50 dark:bg-primary-700 rounded-lg p-4 space-y-2 cursor-pointer hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start">
                <div className="font-medium text-primary-900 dark:text-primary-100">
                  {converter.manufacturer_name || 'N/A'}
                </div>
                {converter.eo_document_url ? (
                  <a
                    href={converter.eo_document_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="font-mono text-xs text-accent-600 dark:text-accent-400 font-semibold hover:text-accent-700 dark:hover:text-accent-300 underline"
                  >
                    {converter.executive_order}
                  </a>
                ) : (
                  <span className="font-mono text-xs text-accent-600 dark:text-accent-400 font-semibold">
                    {converter.executive_order}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-primary-500 dark:text-primary-400">Location:</span>
                  <span className="ml-1 text-primary-900 dark:text-primary-100">
                    {converter.converter_location || '-'}
                  </span>
                </div>
                <div>
                  <span className="text-primary-500 dark:text-primary-400">Type:</span>
                  <span className="ml-1 text-primary-900 dark:text-primary-100">
                    {converter.converter_type || '-'}
                  </span>
                </div>
                <div>
                  <span className="text-primary-500 dark:text-primary-400">Quantity:</span>
                  <span className="ml-1 align-item-center text-primary-900 dark:text-primary-100">
                    {converter.quantity || '-'}
                  </span>
                </div>
                <div>
                  <span className="text-primary-500 dark:text-primary-400">Application:</span>
                  <span className="ml-1 text-primary-900 dark:text-primary-100">
                    {converter.application_type || '-'}
                  </span>
                </div>
                <div>
                  <span className="text-primary-500 dark:text-primary-400">Group:</span>
                  <span className="ml-1 text-primary-900 dark:text-primary-100 font-mono text-xs">
                    {converter.test_group || '-'}
                  </span>
                </div>
                <div>
                  <span className="text-primary-500 dark:text-primary-400">Cert Level:</span>
                  <span className="ml-1 text-primary-900 dark:text-primary-100">
                    {converter.cert_level || '-'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Infinite Scroll - Load More Section */}
        {/* Only show this section when there are more results to load or currently loading */}
        {pagination && pagination.count > 0 && (hasMore || loading) && (
          <div className="bg-primary-50 dark:bg-primary-900 px-4 py-3 border-t border-primary-200 dark:border-primary-700 sm:px-6">
            <div className="flex flex-col items-center gap-4">
              {/* Load more trigger element (invisible, used for intersection observer) */}
              <div ref={loadMoreRef} className="h-1" />

              {/* Loading indicator when fetching more results */}
              {loading && (
                <div className="flex flex-col items-center justify-center py-4">
                  <svg className="animate-spin h-8 w-8 text-accent-600 mb-2" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <p className="text-sm text-primary-600 dark:text-primary-400">Loading more results...</p>
                </div>
              )}

              {/* Manual load more button (backup for intersection observer) */}
              {hasMore && !loading && (
                <button
                  onClick={onLoadMore}
                  className="btn-primary px-6 py-2"
                >
                  Load More Results
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {isModalOpen && selectedConverter && (
        <ConverterDetailModal
          converter={selectedConverter}
          isOpen={isModalOpen}
          onClose={closeModal}
        />
      )}
    </>
  );
}
