import { Link } from 'react-router-dom';

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8 items-start">
          {/* About Section */}
          <div className="md:col-span-2">
            <h3 className="text-2xl font-bold text-accent-600 dark:text-accent-400 mb-4">
              CARB Catalytic Converter
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed max-w-md">
              Search and find California Air Resources Board (CARB) approved catalytic converters for your vehicle.
              Access comprehensive data on certified converters and manufacturers.
            </p>
          </div>

          {/* Quick Links */}
          {/* <div className="md:col-span-1 flex justify-center md:justify-end">
            <div className="text-center">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 uppercase tracking-wider mb-4">
                Quick Links
              </h3>
              <ul className="space-y-2">
                <li>
                  <Link
                    to="/"
                    className="text-sm text-slate-600 dark:text-slate-400 hover:text-accent-600 dark:hover:text-accent-400 transition-colors"
                  >
                    Home
                  </Link>
                </li>
                <li>
                  <Link
                    to="/about"
                    className="text-sm text-slate-600 dark:text-slate-400 hover:text-accent-600 dark:hover:text-accent-400 transition-colors"
                  >
                    About
                  </Link>
                </li>
                <li>
                  <Link
                    to="/faq"
                    className="text-sm text-slate-600 dark:text-slate-400 hover:text-accent-600 dark:hover:text-accent-400 transition-colors"
                  >
                    FAQ
                  </Link>
                </li>
                <li>
                  <Link
                    to="/blogs"
                    className="text-sm text-slate-600 dark:text-slate-400 hover:text-accent-600 dark:hover:text-accent-400 transition-colors"
                  >
                    Blog
                  </Link>
                </li>
              </ul>
            </div>
          </div> */}
        </div>

        {/* Bottom Section */}
        <div className="pt-8 border-t border-slate-200 dark:border-slate-700">
          <div className="flex flex-col md:flex-row justify-center items-center space-y-4 md:space-y-0">
            <p className="text-sm text-slate-600 dark:text-slate-400 whitespace-nowrap">
              © {currentYear} CARB Converter Lookup
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
