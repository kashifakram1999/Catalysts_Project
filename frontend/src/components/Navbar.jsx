import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';

export default function Navbar() {
  const [darkMode, setDarkMode] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const isDark = localStorage.getItem('darkMode') === 'true';
    setDarkMode(isDark);
    if (isDark) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', newDarkMode);
    if (newDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen);
  };

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
  };

  return (
    <nav className="bg-white dark:bg-primary-800 shadow-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Logo */}
          <div className="flex items-center flex-none">
            <Link to="/" className="flex items-center" onClick={closeMobileMenu}>
              <span className="text-2xl font-bold text-accent-600 dark:text-accent-400">
                CARB Catalysts
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8 justify-center flex-1 pr-16">
            <Link
              to="/"
              className="text-primary-700 dark:text-primary-300 hover:text-accent-600 dark:hover:text-accent-400 px-3 py-2 text-sm font-medium transition-colors"
            >
              Search
            </Link>
            <Link
              to="/about"
              className="text-primary-700 dark:text-primary-300 hover:text-accent-600 dark:hover:text-accent-400 px-3 py-2 text-sm font-medium transition-colors"
            >
              About
            </Link>
            <Link
              to="/faq"
              className="text-primary-700 dark:text-primary-300 hover:text-accent-600 dark:hover:text-accent-400 px-3 py-2 text-sm font-medium transition-colors"
            >
              FAQ
            </Link>
            <Link
              to="/blogs"
              className="text-primary-700 dark:text-primary-300 hover:text-accent-600 dark:hover:text-accent-400 px-3 py-2 text-sm font-medium transition-colors"
            >
              Blogs
            </Link>
          </div>

          {/* Right side buttons */}
          <div className="flex items-center space-x-2 flex-none">
            {/* Dark mode toggle */}
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg bg-primary-100 dark:bg-primary-700 hover:bg-primary-200 dark:hover:bg-primary-600 transition-colors"
              aria-label="Toggle dark mode"
            >
              {darkMode ? (
                <svg className="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" />
                </svg>
              ) : (
                <svg className="w-5 h-5 text-primary-600" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                </svg>
              )}
            </button>

            {/* Mobile menu button */}
            <button
              onClick={toggleMobileMenu}
              className="md:hidden p-2 rounded-lg bg-primary-100 dark:bg-primary-700 hover:bg-primary-200 dark:hover:bg-primary-600 transition-colors"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? (
                <svg className="w-6 h-6 text-primary-700 dark:text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-6 h-6 text-primary-700 dark:text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-primary-200 dark:border-primary-700">
            <div className="flex flex-col space-y-2">
              <Link
                to="/"
                onClick={closeMobileMenu}
                className="text-primary-700 dark:text-primary-300 hover:text-accent-600 dark:hover:text-accent-400 hover:bg-primary-50 dark:hover:bg-primary-700 px-3 py-2 text-base font-medium transition-colors rounded-md"
              >
                Search
              </Link>
              <Link
                to="/about"
                onClick={closeMobileMenu}
                className="text-primary-700 dark:text-primary-300 hover:text-accent-600 dark:hover:text-accent-400 hover:bg-primary-50 dark:hover:bg-primary-700 px-3 py-2 text-base font-medium transition-colors rounded-md"
              >
                About
              </Link>
              <Link
                to="/faq"
                onClick={closeMobileMenu}
                className="text-primary-700 dark:text-primary-300 hover:text-accent-600 dark:hover:text-accent-400 hover:bg-primary-50 dark:hover:bg-primary-700 px-3 py-2 text-base font-medium transition-colors rounded-md"
              >
                FAQ
              </Link>
              <Link
                to="/blogs"
                onClick={closeMobileMenu}
                className="text-primary-700 dark:text-primary-300 hover:text-accent-600 dark:hover:text-accent-400 hover:bg-primary-50 dark:hover:bg-primary-700 px-3 py-2 text-base font-medium transition-colors rounded-md"
              >
                Blogs
              </Link>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
