import { Canvas } from '@react-three/fiber';
import { OrbitControls, Image, Environment } from '@react-three/drei';
import { useState } from 'react';
import { Post } from '../types';
import PostModal from './PostModal';

// Enable debug logging - use any to avoid TypeScript error
(window as any).__DEBUG_ACTIVE__ = true;

interface Props {
  posts: Post[];
}

export default function ThreeScene({ posts }: Props) {
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);

  // Use first media item as thumbnail
  const thumbnails = posts
    .map((post) => ({
      id: post.id,
      src: post.media[0] || '',
      post,
    }))
    .filter((t) => t.src); // skip posts without media

  const total = thumbnails.length;

  if (total === 0) {
    return <div style={{ color: 'white' }}>No thumbnails</div>;
  }

  // Arrange in a spiral
  const radius = 10;
  const positions = thumbnails.map((_, i) => {
    const angle = (i / total) * Math.PI * 6; // 3 full turns
    const x = radius * Math.cos(angle);
    const z = radius * Math.sin(angle);
    const y = (i / total) * 10 - 5;
    return [x, y, z] as [number, number, number];
  });

  // Debug: log thumbnail info on mount
  console.log('[DEBUG] ThreeScene mounted with', total, 'thumbnails');
  console.log('[DEBUG] Thumbnail positions:', positions);

  const handleImageClick = (post: Post) => {
    console.log('[DEBUG] Image clicked:', {
      postId: post.id,
      caption: post.caption?.substring(0, 50),
      mediaCount: post.media.length,
      thumbnail: post.media[0],
    });
    console.log('[DEBUG] Current selection:', selectedPost?.id || 'none');
    setSelectedPost(post);
  };

  return (
    <>
      <Canvas camera={{ position: [0, 0, 18], fov: 60 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 10, 5]} intensity={1} />
        <Environment preset="city" />
        <OrbitControls enableZoom={true} enablePan={true} autoRotate={true} autoRotateSpeed={0.5} />
        {thumbnails.map((thumb, i) => (
          <Image
            key={thumb.id}
            url={thumb.src}
            position={positions[i]}
            scale={1.8}
            onClick={() => handleImageClick(thumb.post)}
          />
        ))}
      </Canvas>
      {selectedPost && (
        <PostModal
          post={selectedPost}
          onClose={() => {
            console.log('[DEBUG] Modal closed for post:', selectedPost.id);
            setSelectedPost(null);
          }}
        />
      )}
    </>
  );
}
