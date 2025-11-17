import { useState, useRef, useEffect } from 'react';

export default function CustomSelect({
  id,
  name,
  value,
  onChange,
  options,
  placeholder = 'Select...',
  className = '',
  searchable = false,
  allowFreeText = false
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef(null);
  const searchInputRef = useRef(null);

  // Filter options based on search term
  const filteredOptions = searchable && searchTerm
    ? options.filter(option =>
        (typeof option === 'string' ? option : option.label)
          .toLowerCase()
          .includes(searchTerm.toLowerCase())
      )
    : options;

  // Get display value - find the label for the current value
  const getDisplayValue = () => {
    if (!value) return placeholder;

    const selectedOption = options.find(option => {
      const optionValue = typeof option === 'string' ? option : option.value;
      return optionValue === value;
    });

    if (selectedOption) {
      return typeof selectedOption === 'string' ? selectedOption : selectedOption.label;
    }

    return placeholder;
  };

  const displayValue = getDisplayValue();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearchTerm('');
      }
    }

    // Close dropdown when scrolling the page (but not the dropdown itself)
    function handleScroll(event) {
      // Don't close if scrolling inside the dropdown
      if (dropdownRef.current && dropdownRef.current.contains(event.target)) {
        return;
      }
      setIsOpen(false);
      setSearchTerm('');
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      window.addEventListener('scroll', handleScroll, true);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, [isOpen]);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && searchable && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen, searchable]);

  const handleSelect = (optionValue) => {
    onChange({ target: { name, value: optionValue } });
    setIsOpen(false);
    setSearchTerm('');
  };

  const toggleDropdown = () => {
    setIsOpen(!isOpen);
    if (isOpen) {
      setSearchTerm('');
    }
  };

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      {/* Selected value display or text input */}
      {allowFreeText ? (
        <input
          type="text"
          id={id}
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className="input-field w-full"
        />
      ) : (
        <button
          type="button"
          id={id}
          onClick={toggleDropdown}
          className="input-field w-full text-left flex items-center justify-between cursor-pointer"
        >
          <span className={value ? '' : 'text-primary-400 dark:text-primary-500'}>
            {displayValue}
          </span>
          <svg
            className={`h-5 w-5 text-primary-400 transition-transform ${isOpen ? 'transform rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      )}

      {/* Dropdown menu (only show for select mode, not free text) */}
      {!allowFreeText && isOpen && (
        <div className="absolute z-50 mt-1 w-full bg-white dark:bg-primary-800 border border-primary-300 dark:border-primary-600 rounded-lg shadow-lg max-h-60 overflow-hidden">
          {/* Search input */}
          {searchable && (
            <div className="p-2 border-b border-primary-200 dark:border-primary-700">
              <input
                ref={searchInputRef}
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search..."
                className="w-full px-3 py-2 text-sm border border-primary-300 dark:border-primary-600 rounded bg-white dark:bg-primary-800 text-primary-900 dark:text-primary-100 focus:ring-2 focus:ring-accent-500 focus:border-transparent"
              />
            </div>
          )}

          {/* Options list */}
          <div className="overflow-y-auto max-h-48">
            {filteredOptions.length === 0 ? (
              <div className="px-4 py-3 text-sm text-primary-500 dark:text-primary-400">
                No options found
              </div>
            ) : (
              filteredOptions.map((option) => {
                const optionValue = typeof option === 'string' ? option : option.value;
                const optionLabel = typeof option === 'string' ? option : option.label;
                const isSelected = optionValue === value;

                return (
                  <button
                    key={optionValue}
                    type="button"
                    onClick={() => handleSelect(optionValue)}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-primary-100 dark:hover:bg-primary-700 ${
                      isSelected
                        ? 'bg-accent-50 dark:bg-accent-900/20 text-accent-700 dark:text-accent-300 font-medium'
                        : 'text-primary-900 dark:text-primary-100'
                    }`}
                  >
                    {optionLabel}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
