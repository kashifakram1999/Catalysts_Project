import { useEffect, useState } from 'react';
import BlogCard from '../components/BlogCard';
import PageHero from '../components/PageHero';
import { blogAPI } from '../services/api';

export default function Blogs() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const fetchPosts = async () => {
      try {
        const response = await blogAPI.getBlogs();
        if (!isMounted) return;
        setPosts(response.data || []);
      } catch (err) {
        if (!isMounted) return;
        console.error('Error loading blogs:', err);
        setError('Unable to load blogs right now.');
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchPosts();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="bg-slate-50 dark:bg-slate-900 min-h-screen">
      <PageHero
        eyebrow="Insights"
        title="CARB Converter Blog"
        subtitle="Field reports, compliance updates, and practical tips curated by CARB data specialists."
      />

      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {error && (
          <div className="card p-6 mb-6">
            <p className="text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="grid gap-6 md:grid-cols-2">
            {[...Array(4)].map((_, idx) => (
              <div key={idx} className="h-72 bg-slate-200 dark:bg-slate-700 animate-pulse rounded-xl" />
            ))}
          </div>
        ) : posts.length ? (
          <div className="grid gap-6 md:grid-cols-2">
            {posts.map((post, idx) => (
              <BlogCard key={post.slug || idx} post={post} />
            ))}
          </div>
        ) : (
          <p className="text-primary-700 dark:text-primary-300">
            No blog posts published yet. Check back soon.
          </p>
        )}
      </section>
    </div>
  );
}
