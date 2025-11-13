import { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { blogAPI } from '../services/api';

export default function BlogDetail() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const fetchPost = async () => {
      try {
        const response = await blogAPI.getBlog(slug);
        if (!isMounted) return;
        setPost(response.data);
      } catch (err) {
        if (!isMounted) return;
        console.error('Error loading blog:', err);
        if (err.response && err.response.status === 404) {
          setError('Blog post not found.');
        } else {
          setError('Unable to load this blog post.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchPost();

    return () => {
      isMounted = false;
    };
  }, [slug]);

  const publishedDate = post?.published_at
    ? new Date(post.published_at).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    : null;

  return (
    <div className="bg-slate-50 dark:bg-slate-900 min-h-screen">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center text-accent-600 dark:text-accent-400 font-semibold hover:underline"
        >
          <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back
        </button>

        {loading ? (
          <div className="mt-8 space-y-4">
            <div className="h-10 w-2/3 bg-slate-200 dark:bg-slate-700 animate-pulse rounded" />
            <div className="h-6 w-1/3 bg-slate-200 dark:bg-slate-700 animate-pulse rounded" />
            <div className="h-80 bg-slate-200 dark:bg-slate-700 animate-pulse rounded-xl" />
            <div className="space-y-3">
              {[...Array(6)].map((_, idx) => (
                <div key={idx} className="h-4 bg-slate-200 dark:bg-slate-700 animate-pulse rounded" />
              ))}
            </div>
          </div>
        ) : error ? (
          <div className="card p-6 mt-8">
            <p className="text-red-600 dark:text-red-400">{error}</p>
            <Link to="/blogs" className="mt-4 inline-block text-accent-600 dark:text-accent-400 hover:underline">
              Go to all blogs
            </Link>
          </div>
        ) : post ? (
          <article className="mt-8 card p-6 md:p-10">
            <h1 className="mt-2 text-3xl md:text-4xl font-bold text-primary-900 dark:text-white">
              {post.title}
            </h1>
            {publishedDate && (
              <p className="mt-2 text-sm text-primary-500 dark:text-primary-400">Published on {publishedDate}</p>
            )}

            {post.hero_image_url && (
              <img
                src={post.hero_image_url}
                alt={post.title}
                className="mt-6 w-full h-80 object-cover rounded-xl"
              />
            )}

            <div
              className="prose prose-slate dark:prose-invert max-w-none mt-8"
              dangerouslySetInnerHTML={{ __html: post.content }}
            />
          </article>
        ) : null}
      </div>
    </div>
  );
}
