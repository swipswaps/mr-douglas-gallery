import { useEffect, useState } from 'react';
import { Post } from './types';
import ThreeScene from './components/ThreeScene';
import LayoutEditor from './components/LayoutEditor';

const API_URL = import.meta.env.VITE_API_URL || '';

function App() {
  const [mode, setMode] = useState<"gallery" | "layout">("gallery");
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        const url = API_URL ? `${API_URL}/api/posts` : import.meta.env.BASE_URL + 'posts.json';
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

  return (
    <>
      <div style={{ position: "fixed", bottom: "20px", left: "20px", zIndex: 1000, background: "rgba(0,0,0,0.7)", padding: "10px 15px", borderRadius: "8px", color: "white", fontSize: "14px", pointerEvents: "none" }} data-testid="ui-overlay">
        <div style={{ pointerEvents: "auto", marginBottom: "8px" }}>
          <button onClick={() => setMode(mode === "gallery" ? "layout" : "gallery")} style={{ background: "#E1306C", border: "none", color: "white", padding: "4px 12px", borderRadius: "4px", cursor: "pointer", pointerEvents: "auto" }}>
            {mode === "gallery" ? "Switch to Layout Editor" : "Back to Gallery"}
          </button>
        </div>
        <div>🖱️ Click a card to view full image &amp; Instagram post</div>
        <div style={{ marginTop: "4px", fontSize: "12px", opacity: 0.8 }}>🔄 Drag to rotate · Scroll to zoom</div>
        <button
          onClick={() => {
            const canvas = document.querySelector("canvas");
            if (canvas) {
              canvas.dispatchEvent(new Event("toggle-autorotate"));
            }
          }}
          style={{ pointerEvents: "auto", marginTop: "6px", background: "#E1306C", border: "none", color: "white", padding: "4px 12px", borderRadius: "4px", cursor: "pointer" }}
        >
          Toggle Auto-Rotate
        </button>
      </div>
      {mode === "gallery" ? <ThreeScene posts={posts} /> : <LayoutEditor posts={posts} onBack={() => setMode("gallery")} />}
    </>
  );
}

export default App;
