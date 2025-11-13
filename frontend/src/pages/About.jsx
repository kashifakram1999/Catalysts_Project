export default function About() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="card p-8">
          <h1 className="text-3xl font-bold text-primary-900 dark:text-primary-100 mb-6">
            About CARB Catalytic Converters
          </h1>

          <div className="prose prose-primary dark:prose-invert max-w-none space-y-6">
            <section>
              <h2 className="text-2xl font-semibold text-primary-900 dark:text-primary-100 mb-3">
                What is CARB?
              </h2>
              <p className="text-primary-700 dark:text-primary-300">
                The California Air Resources Board (CARB) is a regulatory agency responsible for protecting public health and the environment by controlling air pollution in California. CARB sets strict emissions standards that are often more stringent than federal requirements.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-primary-900 dark:text-primary-100 mb-3">
                Why CARB Compliance Matters
              </h2>
              <p className="text-primary-700 dark:text-primary-300 mb-3">
                In California and several other states (including New York, Colorado, and Maine), aftermarket catalytic converters must be CARB-approved to be legal for installation. Using a non-CARB-approved converter in these states can result in:
              </p>
              <ul className="list-disc list-inside text-primary-700 dark:text-primary-300 space-y-2 ml-4">
                <li>Failed emissions inspections</li>
                <li>Vehicle registration issues</li>
                <li>Potential fines</li>
                <li>Warranty complications</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-primary-900 dark:text-primary-100 mb-3">
                How to Use This Tool
              </h2>
              <p className="text-primary-700 dark:text-primary-300 mb-3">
                Our search tool helps you find CARB-approved catalytic converters by:
              </p>
              <ol className="list-decimal list-inside text-primary-700 dark:text-primary-300 space-y-2 ml-4">
                <li>Entering your vehicle's year, make, model, and engine size</li>
                <li>Browsing the search results for compatible converters</li>
                <li>Viewing detailed information including Executive Order (EO) numbers</li>
                <li>Verifying the converter meets your specific vehicle requirements</li>
              </ol>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-primary-900 dark:text-primary-100 mb-3">
                Data Sources
              </h2>
              <p className="text-primary-700 dark:text-primary-300">
                All data is sourced directly from official CARB resources and updated regularly to ensure accuracy. We pull information from CARB's aftermarket parts database and Executive Order documentation.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-primary-900 dark:text-primary-100 mb-3">
                Disclaimer
              </h2>
              <p className="text-primary-700 dark:text-primary-300">
                While we strive for accuracy, always verify the Executive Order number and specifications with your installer or CARB directly before purchase. This tool is for informational purposes only.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
