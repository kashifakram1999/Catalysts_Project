export default function ConverterDetailModal({ converter, isOpen, onClose }) {
  if (!isOpen) return null;

  const DetailRow = ({ label, value }) => (
    <div className="py-3 border-b border-primary-200 dark:border-primary-700">
      <dt className="text-sm font-medium text-primary-500 dark:text-primary-400">{label}</dt>
      <dd className="mt-1 text-sm text-primary-900 dark:text-primary-100">{value || 'N/A'}</dd>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          aria-hidden="true"
          onClick={onClose}
        ></div>

        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">
          &#8203;
        </span>

        {/* Modal panel */}
        <div className="relative inline-block align-bottom bg-white dark:bg-primary-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-3xl sm:w-full">
          <div className="bg-white dark:bg-primary-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="sm:flex sm:items-start">
              <div className="w-full mt-3 text-center sm:mt-0 sm:text-left">
                {/* Header */}
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h3 className="text-2xl leading-6 font-bold text-primary-900 dark:text-primary-100" id="modal-title">
                      Converter Details
                    </h3>
                    <p className="mt-2 text-sm text-primary-500 dark:text-primary-400">
                      Executive Order: {converter.eo_document_url ? (
                        <a
                          href={converter.eo_document_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono font-semibold text-accent-600 dark:text-accent-400 hover:text-accent-700 dark:hover:text-accent-300 underline"
                        >
                          {converter.executive_order}
                        </a>
                      ) : (
                        <span className="font-mono font-semibold text-accent-600 dark:text-accent-400">
                          {converter.executive_order}
                        </span>
                      )}
                    </p>
                  </div>
                  <button
                    onClick={onClose}
                    className="rounded-md text-primary-400 hover:text-primary-500 focus:outline-none"
                  >
                    <span className="sr-only">Close</span>
                    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {/* Content */}
                <div className="max-h-96 overflow-y-auto">
                  <dl className="divide-y divide-primary-200 dark:divide-primary-700">
                    <DetailRow label="Manufacturer" value={converter.manufacturer_name} />
                    <DetailRow label="Series/Model" value={converter.series_model} />

                    <div className="py-3 border-b border-primary-200 dark:border-primary-700">
                      <dt className="text-sm font-medium text-primary-500 dark:text-primary-400 mb-2">Vehicle Information</dt>
                      <dd className="text-sm text-primary-900 dark:text-primary-100 space-y-1">
                        <div><span className="font-medium">Make:</span> {converter.make || 'N/A'}</div>
                        <div><span className="font-medium">Model:</span> {converter.model || 'N/A'}</div>
                        <div><span className="font-medium">Year:</span> {converter.year_range}</div>
                        <div><span className="font-medium">Vehicle Class:</span> {converter.vehicle_class || 'N/A'}</div>
                      </dd>
                    </div>

                    {/* <DetailRow
                      label="Executive Order Date"
                      value={converter.eo_date ? new Date(converter.eo_date).toLocaleDateString() : 'N/A'}
                    /> */}
                  </dl>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="bg-primary-50 dark:bg-primary-900 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              onClick={onClose}
              className="btn-primary w-full sm:w-auto sm:ml-3"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
