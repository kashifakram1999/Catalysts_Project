import { Link } from 'react-router-dom';

export default function BlogCard({ post, variant = 'default' }) {
  if (!post) {
    return null;
  }

  const publishedDate = post.published_at
    ? new Date(post.published_at).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    : null;

  const image = post.hero_image_url || null;

  return (
    <article className={`card h-full flex flex-col overflow-hidden ${variant === 'featured' ? 'md:flex-row gap-6' : ''}`}>
      {image ? (
        <img
          src={image}
          alt={post.title}
          className={`${variant === 'featured' ? 'md:w-1/2 h-56' : 'h-48'} w-full object-cover`}
          loading="lazy"
        />
      ) : (
        <div className={`${variant === 'featured' ? 'md:w-1/2' : ''} w-full ${variant === 'featured' ? 'h-56' : 'h-48'} bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-primary-500`}>
          Image coming soon
        </div>
      )}

      <div className={`${variant === 'featured' ? 'md:w-1/2' : ''} flex flex-col p-6`}> 
        <h3 className="mt-2 text-xl font-semibold text-primary-900 dark:text-white">
          {post.title}
        </h3>
        {publishedDate && (
          <p className="mt-1 text-sm text-primary-500 dark:text-primary-400">{publishedDate}</p>
        )}
        <p className="mt-3 text-primary-600 dark:text-primary-300 flex-grow">
          {post.excerpt}
        </p>
        <div className="mt-4">
          <Link
            to={`/blogs/${post.slug}`}
            className="inline-flex items-center text-accent-600 dark:text-accent-400 font-semibold hover:underline"
          >
            Read more
            <svg className="w-4 h-4 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      </div>
    </article>
  );
}
