#!/usr/bin/env python3
"""
IG Grab to Three.js 3D Gallery – FAST with thumbnails
Generates thumbnails and uses them for 3D textures.
"""

import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime

# Try to import PIL for thumbnail generation
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def generate_thumbnail(src_path, dst_path, max_width=500, quality=75):
    """Create a thumbnail image at dst_path."""
    if not HAS_PIL:
        return False
    try:
        with Image.open(src_path) as img:
            if img.width > max_width:
                ratio = max_width / img.width
                new_size = (max_width, int(img.height * ratio))
                img.thumbnail(new_size, Image.Resampling.LANCZOS)
            # Ensure the output directory exists
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(dst_path, quality=quality, optimize=True)
        return True
    except Exception as e:
        print(f"Warning: Could not create thumbnail for {src_path}: {e}")
        return False

def parse_info_txt(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    data = {}
    data['url'] = re.search(r'URL: (.+)', content).group(1) if re.search(r'URL: (.+)', content) else ''
    data['date'] = re.search(r'Date: (.+)', content).group(1) if re.search(r'Date: (.+)', content) else ''
    data['type'] = re.search(r'Type: (.+)', content).group(1) if re.search(r'Type: (.+)', content) else ''
    data['likes'] = int(re.search(r'Likes: (\d+)', content).group(1)) if re.search(r'Likes: (\d+)', content) else 0
    data['comments'] = int(re.search(r'Comments: (\d+)', content).group(1)) if re.search(r'Comments: (\d+)', content) else 0
    data['location'] = re.search(r'Location: (.+)', content).group(1) if re.search(r'Location: (.+)', content) else ''
    data['items'] = int(re.search(r'Items: (\d+)', content).group(1)) if re.search(r'Items: (\d+)', content) else 0
    caption_match = re.search(r'Caption:\n(.*?)(?=\n\n|$)', content, re.DOTALL)
    data['caption'] = caption_match.group(1).strip() if caption_match else ''
    shortcode_match = re.search(r'/p/([^/]+)/', data['url'])
    data['shortcode'] = shortcode_match.group(1) if shortcode_match else ''
    data['instagram_url'] = f"https://www.instagram.com/p/{data['shortcode']}/" if data['shortcode'] else ''
    try:
        dt = datetime.strptime(data['date'], '%m/%d/%Y %I:%M:%S%p')
        data['iso_date'] = dt.isoformat()
    except:
        data['iso_date'] = data['date']
    return data

def parse_comments_txt(filepath):
    comments = []
    if not os.path.exists(filepath):
        return comments
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith('Comments for') or line.startswith('Count:') or line.startswith('Reported by') or line.startswith('Saved:'):
            i += 1
            continue
        match = re.match(r'\[(.+?)\]\s+@(\w+)', line)
        if match:
            date_str = match.group(1)
            username = match.group(2)
            i += 1
            text_lines = []
            while i < len(lines):
                next_line = lines[i].strip()
                if re.match(r'\[.+?\]\s+@\w+', next_line) or next_line.startswith('Comments for') or next_line.startswith('Count:') or next_line.startswith('Reported by') or next_line.startswith('Saved:'):
                    break
                if next_line and not next_line.startswith('--'):
                    text_lines.append(next_line)
                i += 1
            text = ' '.join(text_lines).strip()
            if text:
                comments.append({'username': username, 'date': date_str, 'text': text})
        else:
            i += 1
    return comments

def find_media_files(folder):
    media_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.avi', '.mkv'}
    media_files = []
    for f in folder.iterdir():
        if f.suffix.lower() in media_extensions:
            rel_path = f.relative_to(folder.parent)
            media_files.append(str(rel_path))
    return sorted(media_files)

def scan_ig_grab_folder(base_dir, generate_thumbs=True):
    base_path = Path(base_dir).resolve()
    if not base_path.exists():
        raise FileNotFoundError(f"Folder not found: {base_path}")
    posts = []
    # Thumbnail directory
    thumb_dir = base_path / 'thumbs'
    if generate_thumbs and HAS_PIL:
        thumb_dir.mkdir(exist_ok=True)
        print(f"📸 Thumbnails will be saved to {thumb_dir}")
    elif generate_thumbs and not HAS_PIL:
        print("⚠️ Pillow not installed. Install with `pip install Pillow` to enable thumbnails (faster loading).")
        print("   Falling back to original images (slow).")

    for subdir in sorted(base_path.iterdir()):
        if not subdir.is_dir():
            continue
        info_file = subdir / 'info.txt'
        if not info_file.exists():
            continue
        data = parse_info_txt(info_file)
        if not data.get('shortcode'):
            continue
        data['folder_name'] = subdir.name
        data['comments_list'] = parse_comments_txt(subdir / 'comments.txt')
        data['media_files'] = find_media_files(subdir)
        if not data['media_files']:
            continue
        data['primary_media'] = data['media_files'][0]
        data['all_media'] = data['media_files']

        # Create thumbnail for primary media if it's an image
        if generate_thumbs and HAS_PIL and data['primary_media'].lower().endswith(('.jpg','.jpeg','.png','.gif','.webp')):
            src_full = base_path / data['primary_media']
            if src_full.exists():
                # Thumbnail filename: same relative path but inside thumbs/
                thumb_rel = Path('thumbs') / data['primary_media']
                thumb_full = base_path / thumb_rel
                if not thumb_full.exists():
                    generate_thumbnail(src_full, thumb_full, max_width=400, quality=70)
                data['thumb_media'] = str(thumb_rel)
            else:
                data['thumb_media'] = data['primary_media']
        else:
            # For videos or if Pillow missing, keep original
            data['thumb_media'] = data['primary_media']

        posts.append(data)
    posts.sort(key=lambda x: x.get('iso_date', ''))
    return posts

def generate_html(posts, style='grid'):
    posts_json = json.dumps(posts, indent=2)

    style_desc = {
        'grid': "Grid wall – pictures arranged in rows",
        'carousel': "Circular carousel – drag to spin",
        'particles': "Floating particle cloud – images move gently"
    }.get(style, "3D Gallery")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mr. Douglas 3D | {style.capitalize()} (Fast)</title>
    <style>
        body {{ margin: 0; overflow: hidden; font-family: 'Inter', sans-serif; }}
        #info {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 10px 15px;
            border-radius: 8px;
            backdrop-filter: blur(5px);
            pointer-events: none;
            z-index: 10;
            font-size: 14px;
        }}
        .controls-note {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(0,0,0,0.6);
            color: #ccc;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
            pointer-events: none;
            z-index: 10;
        }}
        .warning {{
            position: absolute;
            bottom: 20px;
            right: 20px;
            background: rgba(255,100,0,0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: bold;
            pointer-events: none;
            z-index: 20;
            max-width: 300px;
            text-align: center;
        }}
        .lightbox {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.9); backdrop-filter: blur(8px);
            display: flex; align-items: center; justify-content: center;
            z-index: 1000; visibility: hidden; opacity: 0;
            transition: visibility 0.2s, opacity 0.2s;
        }}
        .lightbox.active {{ visibility: visible; opacity: 1; }}
        .lightbox-content {{ max-width: 90vw; max-height: 90vh; position: relative; }}
        .lightbox-img {{ max-width: 100%; max-height: 90vh; object-fit: contain; border-radius: 12px; }}
        .lightbox-close {{ position: absolute; top: -40px; right: 0; color: white; font-size: 32px; cursor: pointer; background: none; border: none; }}
        .lightbox-caption {{
            position: absolute; bottom: -60px; left: 0; right: 0;
            background: rgba(0,0,0,0.7); color: white; padding: 12px;
            border-radius: 8px; text-align: center; max-height: 150px; overflow-y: auto;
        }}
        canvas {{ outline: none; }}
    </style>
</head>
<body>
    <div id="info">
        <h1>✈️ Mr. Douglas | {style.capitalize()} 3D (Thumbnails)</h1>
        <p>{style_desc}</p>
    </div>
    <div class="controls-note">
        🖱️ Drag to rotate • Scroll to zoom • Right‑click for browser menu<br>
        🖼️ Click image for details + full‑res photo
    </div>
    <div id="server-warning" class="warning" style="display:none;">
        ⚠️ Images not loading? Use a local HTTP server.<br>
        <code>python -m http.server 8000</code>
    </div>

    <div id="lightbox" class="lightbox">
        <div class="lightbox-content">
            <button id="lightbox-close" class="lightbox-close">&times;</button>
            <img id="lightbox-img" class="lightbox-img" src="">
            <div id="lightbox-caption" class="lightbox-caption"></div>
        </div>
    </div>

    <script type="importmap">
        {{
            "imports": {{
                "three": "https://unpkg.com/three@0.128.0/build/three.module.js",
                "three/addons/": "https://unpkg.com/three@0.128.0/examples/jsm/"
            }}
        }}
    </script>

    <script type="module">
        import * as THREE from 'three';
        import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

        const posts = {posts_json};
        const styleType = '{style}';
        if (window.location.protocol === 'file:') {{
            document.getElementById('server-warning').style.display = 'block';
        }}

        // Lightbox using full‑resolution original media
        const lightbox = document.getElementById('lightbox');
        const lightboxImg = document.getElementById('lightbox-img');
        const lightboxCaption = document.getElementById('lightbox-caption');
        const closeLightbox = () => {{
            lightbox.classList.remove('active');
            document.body.style.overflow = '';
        }};
        document.getElementById('lightbox-close').addEventListener('click', closeLightbox);
        lightbox.addEventListener('click', (e) => {{ if (e.target === lightbox) closeLightbox(); }});

        function openLightbox(post) {{
            lightboxImg.src = post.primary_media;  // original high‑res image
            let captionHtml = `<strong>${{post.caption.length > 200 ? post.caption.substring(0,200)+'…' : post.caption}}</strong><br>
                               📅 ${{post.date}} &nbsp; ❤️ ${{post.likes}} &nbsp; 💬 ${{post.comments}}<br>
                               <a href="${{post.instagram_url}}" target="_blank" style="color:#3b82f6;">View on Instagram →</a>`;
            if (post.location) captionHtml += `<br>📍 ${{post.location}}`;
            lightboxCaption.innerHTML = captionHtml;
            lightbox.classList.add('active');
            document.body.style.overflow = 'hidden';
        }}

        // Three.js setup
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0a1030);
        scene.fog = new THREE.FogExp2(0x0a1030, 0.008);

        const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(0, 2, 12);
        const renderer = new THREE.WebGLRenderer({{ antialias: true, preserveDrawingBuffer: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        document.body.appendChild(renderer.domElement);

        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.autoRotate = (styleType === 'carousel');
        controls.autoRotateSpeed = 1.2;
        controls.enableZoom = true;
        controls.zoomSpeed = 1.2;

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404060);
        scene.add(ambientLight);
        const dirLight = new THREE.DirectionalLight(0xffffff, 1);
        dirLight.position.set(2, 5, 3);
        scene.add(dirLight);
        const fillLight = new THREE.DirectionalLight(0x88aaff, 0.5);
        fillLight.position.set(-2, 1, -3);
        scene.add(fillLight);

        function createImagePlane(url, width, height, post) {{
            const geometry = new THREE.PlaneGeometry(width, height);
            const texture = new THREE.TextureLoader().load(url);
            const material = new THREE.MeshStandardMaterial({{ map: texture, side: THREE.DoubleSide }});
            const mesh = new THREE.Mesh(geometry, material);
            mesh.userData = {{ post }};
            return mesh;
        }}

        let imageGroup;

        if (styleType === 'grid') {{
            imageGroup = new THREE.Group();
            const cols = 6;
            const rows = Math.ceil(posts.length / cols);
            const spacingX = 2.2;
            const spacingY = 2.2;
            const w = 2.0;
            const h = 1.5;
            posts.forEach((post, idx) => {{
                const col = idx % cols;
                const row = Math.floor(idx / cols);
                const x = (col - cols/2) * spacingX;
                const y = -(row - rows/2) * spacingY;
                const plane = createImagePlane(post.thumb_media || post.primary_media, w, h, post);
                plane.position.set(x, y, 0);
                imageGroup.add(plane);
            }});
            scene.add(imageGroup);
            camera.position.set(0, 0, 12);
            controls.target.set(0, 0, 0);
        }}
        else if (styleType === 'carousel') {{
            imageGroup = new THREE.Group();
            const radius = 5;
            const count = posts.length;
            const w = 2.0;
            const h = 1.5;
            for (let i = 0; i < count; i++) {{
                const angle = (i / count) * Math.PI * 2;
                const x = Math.sin(angle) * radius;
                const z = Math.cos(angle) * radius;
                const plane = createImagePlane(posts[i].thumb_media || posts[i].primary_media, w, h, posts[i]);
                plane.position.set(x, 0, z);
                plane.lookAt(0, 0, 0);
                imageGroup.add(plane);
            }}
            scene.add(imageGroup);
            camera.position.set(0, 2, 10);
            controls.target.set(0, 0, 0);
        }}
        else if (styleType === 'particles') {{
            imageGroup = new THREE.Group();
            const w = 1.2;
            const h = 0.9;
            const bounds = 7;
            posts.forEach((post) => {{
                const x = (Math.random() - 0.5) * bounds * 2;
                const y = (Math.random() - 0.5) * bounds * 0.6;
                const z = (Math.random() - 0.5) * bounds;
                const plane = createImagePlane(post.thumb_media || post.primary_media, w, h, post);
                plane.position.set(x, y, z);
                plane.userData.originalPos = new THREE.Vector3(x, y, z);
                plane.userData.floatSpeed = 0.003 + Math.random() * 0.008;
                plane.userData.floatPhase = Math.random() * Math.PI * 2;
                imageGroup.add(plane);
            }});
            scene.add(imageGroup);
            camera.position.set(0, 2, 14);
        }}

        // Raycaster for clicks
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        function onMouseClick(event) {{
            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(imageGroup.children, true);
            if (intersects.length > 0) {{
                let clicked = intersects[0].object;
                while (clicked && !clicked.userData?.post) clicked = clicked.parent;
                if (clicked && clicked.userData?.post) openLightbox(clicked.userData.post);
            }}
        }}
        window.addEventListener('click', onMouseClick, false);

        let time = 0;
        function animate() {{
            requestAnimationFrame(animate);
            time += 0.016;
            if (styleType === 'particles') {{
                imageGroup.children.forEach(child => {{
                    if (child.userData.originalPos) {{
                        const orig = child.userData.originalPos;
                        const speed = child.userData.floatSpeed;
                        const phase = child.userData.floatPhase;
                        child.position.y = orig.y + Math.sin(time * speed + phase) * 0.08;
                        child.position.x = orig.x + Math.cos(time * 0.6 + phase) * 0.04;
                    }}
                }});
            }}
            controls.update();
            renderer.render(scene, camera);
        }}
        animate();

        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
    </script>
</body>
</html>"""
    return html

def main():
    parser = argparse.ArgumentParser(description='Build fast 3D gallery from IG Grab folder (with thumbnails)')
    parser.add_argument('folder', help='Path to IG Grab extracted folder')
    parser.add_argument('--style', choices=['grid', 'carousel', 'particles'], default='grid',
                        help='3D presentation style')
    parser.add_argument('--no-thumbs', action='store_true',
                        help='Disable thumbnail generation (use original images, slow)')
    parser.add_argument('-o', '--output', default=None)
    args = parser.parse_args()

    base_dir = Path(args.folder).resolve()
    if not base_dir.exists():
        print(f"Error: folder '{base_dir}' does not exist.")
        return

    print(f"Scanning: {base_dir}")
    posts = scan_ig_grab_folder(base_dir, generate_thumbs=not args.no_thumbs)
    print(f"Found {len(posts)} posts.")
    if not posts:
        print("No valid posts found.")
        return

    if args.output is None:
        output_path = base_dir / f'index_3d_{args.style}_fast.html'
    else:
        output_path = Path(args.output)

    html_content = generate_html(posts, style=args.style)
    output_path.write_text(html_content, encoding='utf-8')
    print(f"✅ Fast 3D gallery saved to {output_path.resolve()}")
    print(f"Style: {args.style}")
    print("\n⚠️ IMPORTANT: You MUST serve this folder with a local HTTP server:")
    print(f"   cd {base_dir}")
    print("   python -m http.server 8000")
    print("   Then open http://localhost:8000/ and click on the generated HTML file.")
    print("\n📸 Thumbnails were created in the 'thumbs' folder – they are tiny and load instantly.")
    print("   The lightbox still shows the full‑resolution images on click.\n")

if __name__ == '__main__':
    main()