#!/usr/bin/env python3
"""
IG Grab to 3D D3+Three Gallery – Fixed thumbnails, right-click, click detection
"""

import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from PIL import Image

# ---------- Thumbnail generation with verbose output ----------
def generate_thumbnail(src_path, dst_path, max_width=400, quality=70):
    try:
        with Image.open(src_path) as img:
            if img.width > max_width:
                ratio = max_width / img.width
                new_size = (max_width, int(img.height * ratio))
                img.thumbnail(new_size, Image.Resampling.LANCZOS)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(dst_path, quality=quality, optimize=True)
        print(f"  ✅ Thumbnail created: {dst_path}")
        return True
    except Exception as e:
        print(f"  ❌ Thumbnail failed for {src_path}: {e}")
        return False

# ---------- Parse IG Grab data (unchanged) ----------
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
        if not line or line.startswith('Comments for') or line.startswith('Count:') or line.startswith('Reported by') or line.startswith('Saved:'):
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

def scan_ig_grab_folder(base_dir):
    base_path = Path(base_dir).resolve()
    posts = []
    thumb_dir = base_path / 'thumbs'
    thumb_dir.mkdir(exist_ok=True)
    print("Generating thumbnails (this may take a moment)...")
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

        # Create thumbnail
        src_full = base_path / data['primary_media']
        if src_full.exists() and src_full.suffix.lower() in ('.jpg','.jpeg','.png','.gif','.webp'):
            thumb_rel = Path('thumbs') / data['primary_media']
            thumb_full = base_path / thumb_rel
            if not thumb_full.exists():
                generate_thumbnail(src_full, thumb_full, max_width=400, quality=70)
            data['thumb_media'] = str(thumb_rel)
        else:
            data['thumb_media'] = data['primary_media']
        posts.append(data)
    posts.sort(key=lambda x: x.get('iso_date', ''))
    return posts

# ---------- HTML generation with fixed right-click, click logging ----------
def generate_html(posts, model_path='models/scene.gltf'):
    posts_json = json.dumps(posts, indent=2)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Mr. Douglas 3D Gallery | D3 Layout + Aircraft Model</title>
    <style>
        body {{ margin: 0; overflow: hidden; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        #info {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 8px 15px;
            border-radius: 8px;
            pointer-events: none;
            z-index: 10;
            font-size: 14px;
            backdrop-filter: blur(5px);
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
        .lightbox {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.95); backdrop-filter: blur(8px);
            display: none; align-items: center; justify-content: center;
            z-index: 2000;
        }}
        .lightbox.active {{ display: flex; }}
        .lightbox-content {{ position: relative; max-width: 90vw; max-height: 90vh; }}
        .lightbox-media {{
            max-width: 100%; max-height: 90vh; object-fit: contain; border-radius: 12px;
        }}
        .lightbox-close {{
            position: absolute; top: -40px; right: 0; color: white; font-size: 32px;
            cursor: pointer; background: none; border: none;
        }}
        .lightbox-nav {{
            position: absolute; top: 50%; transform: translateY(-50%);
            background: rgba(0,0,0,0.6); color: white; border: none;
            font-size: 36px; cursor: pointer; padding: 10px 20px; border-radius: 50%;
            transition: background 0.2s;
        }}
        .lightbox-nav:hover {{ background: rgba(0,0,0,0.9); }}
        .lightbox-prev {{ left: 20px; }}
        .lightbox-next {{ right: 20px; }}
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
        <strong>✈️ Mr. Douglas 3D Gallery</strong> | Aircraft model + {len(posts)} restoration images<br>
        🖱️ Drag to orbit • Scroll to zoom • <strong>Right‑click canvas</strong> for browser screenshot
    </div>
    <div class="controls-note">
        Click any image for full‑screen slideshow (← → arrows)
    </div>

    <div id="lightbox" class="lightbox">
        <div class="lightbox-content">
            <button id="lb-close" class="lightbox-close">&times;</button>
            <button id="lb-prev" class="lightbox-nav lightbox-prev">‹</button>
            <button id="lb-next" class="lightbox-nav lightbox-next">›</button>
            <div id="lb-media-container"></div>
            <div id="lb-caption" class="lightbox-caption"></div>
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
    <script src="https://d3js.org/d3.v7.min.js"></script>

    <script type="module">
        import * as THREE from 'three';
        import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
        import {{ GLTFLoader }} from 'three/addons/loaders/GLTFLoader.js';

        const postsData = {posts_json};
        console.log(`Loaded ${{postsData.length}} posts`);

        // --- Setup scene ---
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x050b1a);
        scene.fog = new THREE.FogExp2(0x050b1a, 0.008);

        const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(5, 3, 8);
        camera.lookAt(0, 0, 0);

        const renderer = new THREE.WebGLRenderer({{ antialias: true, preserveDrawingBuffer: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        document.body.appendChild(renderer.domElement);

        // Explicitly allow right-click on canvas
        renderer.domElement.addEventListener('contextmenu', (e) => {{
            // do nothing – let browser show context menu
            console.log('Right-click on canvas (allowed)');
        }});

        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.autoRotate = false;
        controls.enableZoom = true;
        controls.zoomSpeed = 1.2;

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404060);
        scene.add(ambientLight);
        const mainLight = new THREE.DirectionalLight(0xffffff, 1.2);
        mainLight.position.set(3, 5, 2);
        mainLight.castShadow = true;
        scene.add(mainLight);
        const fillLight = new THREE.DirectionalLight(0x88aaff, 0.5);
        fillLight.position.set(-2, 1, -3);
        scene.add(fillLight);
        const backLight = new THREE.PointLight(0xffaa66, 0.3);
        backLight.position.set(0, 2, -4);
        scene.add(backLight);

        // --- Load aircraft model ---
        const modelUrl = '{model_path}';
        let modelGroup = new THREE.Group();
        const loader = new GLTFLoader();
        loader.load(modelUrl,
            (gltf) => {{
                modelGroup = gltf.scene;
                modelGroup.traverse((child) => {{
                    if (child.isMesh) {{
                        child.castShadow = true;
                        child.receiveShadow = true;
                    }}
                }});
                modelGroup.scale.set(0.5, 0.5, 0.5);
                modelGroup.position.set(0, -0.8, 0);
                scene.add(modelGroup);
                console.log('✅ Aircraft model loaded');
            }},
            (xhr) => {{ console.log(`Model loading: ${{(xhr.loaded/xhr.total)*100}}%`); }},
            (error) => {{
                console.error('❌ Model load error:', error);
                // Fallback cube
                const geometry = new THREE.BoxGeometry(1.5, 1.5, 1.5);
                const material = new THREE.MeshStandardMaterial({{ color: 0xff6600, emissive: 0x442200 }});
                const cube = new THREE.Mesh(geometry, material);
                cube.castShadow = true;
                cube.position.set(0, 0, 0);
                scene.add(cube);
                console.warn('Using fallback cube');
            }}
        );

        // --- D3 layout: cylindrical distribution ---
        const count = postsData.length;
        const radius = 4.8;
        const heightRange = 2.8;
        const angles = d3.range(count).map(i => (i / count) * Math.PI * 2);
        const heights = d3.scaleLinear().domain([0, count-1]).range([-heightRange, heightRange]);
        const positions = [];
        for (let i = 0; i < count; i++) {{
            const angle = angles[i];
            const x = Math.sin(angle) * radius;
            const z = Math.cos(angle) * radius;
            const y = heights(i);
            positions.push(new THREE.Vector3(x, y, z));
        }}

        // --- Create image planes using thumbnails ---
        const imageGroup = new THREE.Group();
        const planeWidth = 1.6;
        const planeHeight = 1.2;

        postsData.forEach((post, idx) => {{
            const url = post.thumb_media || post.primary_media;
            const texture = new THREE.TextureLoader().load(url,
                () => console.log(`Loaded: ${{url}}`),
                undefined,
                (err) => console.error(`Failed to load texture: ${{url}}`, err)
            );
            const material = new THREE.MeshStandardMaterial({{ map: texture, side: THREE.DoubleSide }});
            const geometry = new THREE.PlaneGeometry(planeWidth, planeHeight);
            const mesh = new THREE.Mesh(geometry, material);
            mesh.position.copy(positions[idx]);
            mesh.userData = {{
                post: post,
                originalPos: positions[idx].clone()
            }};
            imageGroup.add(mesh);
        }});
        scene.add(imageGroup);
        console.log(`Created ${{imageGroup.children.length}} image planes`);

        // --- Billboard: make each plane face the camera ---
        function updateBillboards() {{
            imageGroup.children.forEach(plane => {{
                plane.lookAt(camera.position);
            }});
        }}

        // --- Slideshow lightbox (reused from working version) ---
        const lightbox = document.getElementById('lightbox');
        const mediaContainer = document.getElementById('lb-media-container');
        const captionDiv = document.getElementById('lb-caption');
        let currentMediaList = [];
        let currentMediaIndex = 0;
        let currentCaption = '';

        function isVideo(url) {{
            return url && url.match(/\\.(mp4|mov|avi|mkv)$/i);
        }}

        function updateLightboxMedia() {{
            mediaContainer.innerHTML = '';
            const mediaUrl = currentMediaList[currentMediaIndex];
            if (isVideo(mediaUrl)) {{
                const video = document.createElement('video');
                video.src = mediaUrl;
                video.controls = true;
                video.className = 'lightbox-media';
                video.style.maxWidth = '90vw';
                video.style.maxHeight = '90vh';
                mediaContainer.appendChild(video);
                video.play().catch(e => console.log('autoplay blocked, click to play'));
            }} else {{
                const img = document.createElement('img');
                img.src = mediaUrl;
                img.className = 'lightbox-media';
                mediaContainer.appendChild(img);
            }}
            captionDiv.innerHTML = currentCaption + `<br><span style="font-size:0.8rem;">[${{currentMediaIndex+1}} / ${{currentMediaList.length}}]</span>`;
        }}

        function openLightbox(mediaList, caption, startIndex = 0) {{
            if (!mediaList.length) return;
            currentMediaList = mediaList;
            currentCaption = caption;
            currentMediaIndex = Math.min(startIndex, mediaList.length - 1);
            updateLightboxMedia();
            lightbox.classList.add('active');
            document.body.style.overflow = 'hidden';
        }}

        function closeLightbox() {{
            lightbox.classList.remove('active');
            document.body.style.overflow = '';
        }}

        function nextMedia() {{
            if (currentMediaList.length) {{
                currentMediaIndex = (currentMediaIndex + 1) % currentMediaList.length;
                updateLightboxMedia();
            }}
        }}
        function prevMedia() {{
            if (currentMediaList.length) {{
                currentMediaIndex = (currentMediaIndex - 1 + currentMediaList.length) % currentMediaList.length;
                updateLightboxMedia();
            }}
        }}

        document.getElementById('lb-close').addEventListener('click', closeLightbox);
        document.getElementById('lb-prev').addEventListener('click', prevMedia);
        document.getElementById('lb-next').addEventListener('click', nextMedia);
        lightbox.addEventListener('click', (e) => {{ if (e.target === lightbox) closeLightbox(); }});
        document.addEventListener('keydown', (e) => {{
            if (!lightbox.classList.contains('active')) return;
            if (e.key === 'Escape') closeLightbox();
            if (e.key === 'ArrowLeft') prevMedia();
            if (e.key === 'ArrowRight') nextMedia();
        }});

        // --- Raycaster for clicking on planes ---
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();

        function onMouseClick(event) {{
            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(imageGroup.children);
            if (intersects.length > 0) {{
                const clicked = intersects[0].object;
                if (clicked.userData && clicked.userData.post) {{
                    console.log('Clicked post:', clicked.userData.post.shortcode);
                    openLightbox(clicked.userData.post.all_media, clicked.userData.post.caption, 0);
                }}
            }}
        }}
        window.addEventListener('click', onMouseClick, false);

        // --- Animation loop ---
        function animate() {{
            requestAnimationFrame(animate);
            updateBillboards();
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
    parser = argparse.ArgumentParser(description='Build 3D D3+Three gallery from IG Grab folder')
    parser.add_argument('folder', default='.', help='IG Grab extracted folder')
    parser.add_argument('--model', default='models/scene.gltf', help='Path to glTF model (relative to folder)')
    parser.add_argument('--output', default=None, help='Output HTML filename')
    args = parser.parse_args()

    base_dir = Path(args.folder).resolve()
    if not base_dir.exists():
        print(f"Error: folder '{base_dir}' does not exist.")
        return

    print(f"Scanning {base_dir} ...")
    posts = scan_ig_grab_folder(base_dir)
    print(f"Found {len(posts)} posts.")

    if args.output is None:
        out_path = base_dir / '3d_d3_fixed.html'
    else:
        out_path = Path(args.output)

    html = generate_html(posts, model_path=args.model)
    out_path.write_text(html, encoding='utf-8')
    print(f"✅ Gallery saved to {out_path.resolve()}")
    print("\n➡️ To view, serve the folder with:")
    print(f"   cd {base_dir}")
    print("   python -m http.server 8000")
    print("   Then open http://localhost:8000/3d_d3_fixed.html")
    print("\n📌 If thumbnails are still missing, check the 'thumbs' folder inside.")
    print("   Right-click on canvas should now work. Click any image to open slideshow.\n")

if __name__ == '__main__':
    main()