export default function PageHero({ eyebrow, title, subtitle, alignment = 'left' }) {
  const alignmentClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right'
  };

  const alignClass = alignmentClasses[alignment] || alignmentClasses.left;

  return (
    <div className="bg-gradient-to-r from-primary-700 to-accent-600 py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className={alignClass}>
          {eyebrow && (
            <p className="text-sm font-semibold text-primary-200 uppercase tracking-wide mb-2">
              {eyebrow}
            </p>
          )}
          <h1 className="text-4xl font-bold text-white mb-4">
            {title}
          </h1>
          {subtitle && (
            <p className="text-xl text-primary-100 max-w-3xl mx-auto">
              {subtitle}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
