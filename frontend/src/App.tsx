import { useEffect, useState } from 'react';
import { Post } from './types';
import ThreeScene from './components/ThreeScene';

const API_URL = import.meta.env.VITE_API_URL || '';

function App() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        const url = API_URL ? `${API_URL}/api/posts` : '/posts.json';
        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to fetch posts');
        const data = await res.json();
        setPosts(data);
      } catch (err) {
        console.error(err);
        setPosts([]);
      } finally {
        setLoading(false);
      }
    };
    fetchPosts();
  }, []);

  if (loading) return <div style={{ color: 'white', padding: '2rem' }}>Loading gallery…</div>;
  if (posts.length === 0) return <div style={{ color: 'white', padding: '2rem' }}>No posts found.</div>;

  return <ThreeScene posts={posts} />;
}

export default App;
