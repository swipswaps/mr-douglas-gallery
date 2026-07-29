import { Post } from '../types';

export default function PostModal({ post, onClose }: { post: Post; onClose: () => void }) {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        background: 'rgba(0,0,0,0.85)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000,
        padding: '1rem',
        cursor: 'pointer',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#222',
          padding: '2rem',
          maxWidth: '90vw',
          maxHeight: '90vh',
          overflow: 'auto',
          borderRadius: '8px',
          color: 'white',
          cursor: 'default',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3>{post.date}</h3>
        <p>{post.caption}</p>
        {post.url && (
          <div style={{ marginTop: '0.5rem' }}>
            <a href={post.url} target="_blank" rel="noopener noreferrer" 
               style={{ color: '#E1306C', textDecoration: 'underline' }}>
              🔗 View on Instagram
            </a>
          </div>
        )}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {post.media.map((src, idx) => {
            if (src.endsWith('.mp4') || src.endsWith('.webm')) {
              return <video key={idx} src={import.meta.env.BASE_URL + src} controls style={{ maxWidth: '100%', maxHeight: '400px' }} />;
            } else {
              return <img key={idx} src={import.meta.env.BASE_URL + src} alt={`${post.id}-${idx}`} style={{ maxWidth: '100%', maxHeight: '400px', objectFit: 'contain' }} />;
            }
          })}
        </div>
        {post.comments.length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            <h4>Comments</h4>
            {post.comments.map((c, i) => <p key={i} style={{ margin: '0.2rem 0' }}>• {c}</p>)}
          </div>
        )}
        <button
          onClick={onClose}
          style={{ marginTop: '1rem', padding: '0.5rem 1rem', background: '#555', border: 'none', color: 'white', borderRadius: '4px', cursor: 'pointer' }}
        >
          Close
        </button>
      </div>
    </div>
  );
}
