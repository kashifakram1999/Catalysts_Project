import { useState } from 'react';
import ConverterDetailModal from './ConverterDetailModal';

export default function ResultsTable({ results, loading, onPageChange, pagination }) {
  const [selectedConverter, setSelectedConverter] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleRowClick = (converter) => {
    setSelectedConverter(converter);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedConverter(null);
  };

  if (loading) {
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
                  EO Number
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider">
                  Manufacturer
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider">
                  Series/Model
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider">
                  Vehicle
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider">
                  Model Year
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-700 dark:text-primary-300 uppercase tracking-wider">
                  Class
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
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-primary-900 dark:text-primary-100">
                      {converter.manufacturer_name || 'N/A'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-primary-900 dark:text-primary-100 font-mono">
                      {converter.series_model || '-'}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-primary-900 dark:text-primary-100">
                      {converter.make || '-'} {converter.model || ''}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-primary-900 dark:text-primary-100">
                    {converter.year_range}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-primary-900 dark:text-primary-100">
                      {converter.vehicle_class || 'N/A'}
                    </span>
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
                <span className="px-2 py-1 text-xs font-semibold rounded-full bg-accent-100 dark:bg-accent-900 text-accent-800 dark:text-accent-200">
                  {converter.vehicle_class || 'N/A'}
                </span>
              </div>
              <div>
                <div className="font-medium text-primary-900 dark:text-primary-100">
                  {converter.manufacturer_name || 'N/A'}
                </div>
                <div className="text-sm text-primary-500 dark:text-primary-400 font-mono">
                  {converter.series_model || '-'}
                </div>
              </div>
              <div className="text-sm">
                <span className="text-primary-900 dark:text-primary-100">
                  {converter.make || '-'} {converter.model || ''}
                </span>
                {' • '}
                <span className="text-primary-600 dark:text-primary-400">
                  {converter.year_range}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Pagination */}
        {pagination && pagination.count > 0 && (
          <div className="bg-primary-50 dark:bg-primary-900 px-4 py-3 border-t border-primary-200 dark:border-primary-700 sm:px-6">
            <div className="flex items-center justify-between">
              <div className="text-sm text-primary-700 dark:text-primary-300">
                Showing <span className="font-medium">{((pagination.currentPage - 1) * 25) + 1}</span> to{' '}
                <span className="font-medium">
                  {Math.min(pagination.currentPage * 25, pagination.count)}
                </span> of{' '}
                <span className="font-medium">{pagination.count}</span> results
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => onPageChange(pagination.currentPage - 1)}
                  disabled={!pagination.previous}
                  className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => onPageChange(pagination.currentPage + 1)}
                  disabled={!pagination.next}
                  className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
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
