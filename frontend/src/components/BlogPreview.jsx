import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { blogAPI } from '../services/api';
import BlogCard from './BlogCard';

const PREVIEW_COUNT = 4;

export default function BlogPreview({ className = '' }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const fetchBlogs = async () => {
      try {
        const response = await blogAPI.getBlogs();
        if (!isMounted) return;
        setPosts((response.data || []).slice(0, PREVIEW_COUNT));
      } catch (err) {
        if (!isMounted) return;
        console.error('Error fetching blog preview:', err);
        setError('Unable to load blog posts right now.');
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchBlogs();

    return () => {
      isMounted = false;
    };
  }, []);

  if (error) {
    return (
      <div className={`card p-6 ${className}`}>
        <p className="text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <section className={`card p-6 md:p-8 ${className}`}>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-accent-600 dark:text-accent-400 uppercase tracking-wide">
              Latest From The Blog
            </p>
          </div>
          <Link
            to="/blogs"
            className="inline-flex items-center text-accent-600 dark:text-accent-400 font-semibold hover:underline"
          >
            View all blogs
            <svg className="w-4 h-4 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>

        {loading ? (
          <div className="grid gap-6 md:grid-cols-2">
            {[...Array(PREVIEW_COUNT)].map((_, idx) => (
              <div key={idx} className="h-64 bg-slate-200 dark:bg-slate-700 animate-pulse rounded-xl" />
            ))}
          </div>
        ) : posts.length ? (
          <div className="grid gap-6 md:grid-cols-2">
            {posts.map((post) => (
              <BlogCard key={post.slug} post={post} />
            ))}
          </div>
        ) : (
          <p className="text-primary-700 dark:text-primary-300">
            Our team is preparing new blog posts. Check back soon for insights from CARB experts.
          </p>
        )}
      </div>
    </section>
  );
}
