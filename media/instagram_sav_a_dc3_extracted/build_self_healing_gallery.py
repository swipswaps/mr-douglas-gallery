#!/usr/bin/env python3
"""
Build a self‑healing gallery HTML file with embedded data and debug output.
"""

import json
import sqlite3
import csv
from pathlib import Path
import re

DB_PATH = Path("instagram_posts.db")
CSV_PATH = Path("posts.csv")
TIMELINE_DIR = Path("timeline")
OUTPUT_HTML = Path("index_debug.html")   # new name to avoid confusion

posts = []

if DB_PATH.exists():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM posts ORDER BY date DESC")
    for row in cur:
        post = dict(row)
        for field in ['comments', 'all_media']:
            if field in post and isinstance(post[field], str) and post[field].startswith('['):
                try:
                    post[field] = json.loads(post[field])
                except:
                    post[field] = []
        posts.append(post)
    conn.close()
    print(f"Loaded {len(posts)} posts from {DB_PATH}")
else:
    print("No database found.")
    exit(1)

historic_posts = []
if TIMELINE_DIR.exists():
    for img_path in TIMELINE_DIR.glob("*.jpg"):
        year_match = re.search(r'\b(19|20)\d{2}\b', img_path.stem)
        year = year_match.group(0) if year_match else "0000"
        title = img_path.stem.replace('-', ' ').replace('_', ' ').title()
        caption = f"{title} – Historic photo"
        historic_posts.append({
            "shortcode": f"hist_{img_path.stem}",
            "date": f"{year}-07-01 12:00:00",
            "likes": 0,
            "comments_count": 0,
            "caption": caption,
            "folder_name": "timeline",
            "all_media": [img_path.name],
            "comments": [],
            "instagram_url": "#"
        })
    print(f"Added {len(historic_posts)} historic images")

all_posts = historic_posts + posts
print(f"Total posts: {len(all_posts)}")

# Convert to JSON with proper escaping
json_data = json.dumps(all_posts, ensure_ascii=False, indent=2)

# HTML template with debug panel
html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Mr. Douglas Gallery (Debug)</title>
    <style>
        * { box-sizing: border-box; }
        body { background: #0f172a; color: #e2e8f0; font-family: system-ui, sans-serif; margin: 0; padding: 1rem; }
        .debug { background: #1e293b; border: 1px solid #ef4444; padding: 1rem; margin-bottom: 1rem; border-radius: 8px; white-space: pre-wrap; font-family: monospace; font-size: 0.8rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; margin-top: 1rem; }
        .card { background: #1e293b; border-radius: 0.5rem; overflow: hidden; position: relative; }
        .card img { width: 100%; aspect-ratio: 4/3; object-fit: cover; }
        .search-header { position: sticky; top: 0; background: rgba(15,23,42,0.95); padding: 1rem; }
        .search-input { width: 100%; padding: 0.5rem; background: #1e293b; border: none; border-radius: 2rem; color: white; }
        .wordcloud { background: #1e293b; border-radius: 1rem; padding: 0.5rem; margin-top: 0.5rem; display: flex; flex-wrap: wrap; gap: 0.5rem; }
        .gallery-toolbar { display: flex; gap: 12px; margin: 1rem 0; flex-wrap: wrap; align-items: center; background: #1e293b; padding: 8px; border-radius: 12px; }
        .select-checkbox { position: absolute; top: 8px; left: 8px; width: 20px; height: 20px; z-index: 10; }
        .storyboard-btn { position: fixed; bottom: 20px; right: 20px; background: #3b82f6; border: none; border-radius: 50px; padding: 12px 24px; cursor: pointer; z-index: 1000; }
    </style>
</head>
<body>
    <div class="search-header">
        <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search...">
        <div id="wordcloud" class="wordcloud">Loading words...</div>
    </div>
    <div class="gallery-toolbar">
        <span>📌 Select images:</span>
        <button id="selectAllBtn">Select All</button>
        <button id="deselectAllBtn">Deselect All</button>
        <button id="addSelectedBtn">➕ Add Selected to Storyboard</button>
        <span id="selectedCount">0 selected</span>
    </div>
    <div id="galleryGrid" class="grid"></div>
    <button id="openStoryboardBtn" class="storyboard-btn">🎨 Storyboard</button>

    <!-- Debug panel -->
    <div id="debugPanel" class="debug" style="display:none;"></div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
    <script>
        // === DEBUG LOGGING ===
        const debugDiv = document.getElementById('debugPanel');
        function log(msg, isError = false) {
            console.log(msg);
            if (debugDiv) {
                debugDiv.style.display = 'block';
                debugDiv.innerHTML += `<div style="color:${isError ? '#f87171' : '#86efac'}">> ${msg}</div>`;
            }
        }
        log('Script started');

        // === EMBEDDED DATA ===
        let allPosts;
        try {
            allPosts = EMBEDDED_POSTS_PLACEHOLDER;
            log(`Loaded ${allPosts.length} posts`);
        } catch(e) {
            log(`ERROR parsing posts: ${e.message}`, true);
            allPosts = [];
        }

        // === Helper functions ===
        function isVideo(f) { return f && /\\.(mp4|mov|avi|mkv)$/i.test(f); }
        function getMediaPath(folder, file) { return `${folder}/${file}`; }

        function renderGallery(posts) {
            log(`Rendering ${posts.length} posts`);
            const grid = document.getElementById('galleryGrid');
            if (!posts.length) { grid.innerHTML = '<div>No posts</div>'; return; }
            try {
                grid.innerHTML = posts.map(post => {
                    const primary = post.all_media && post.all_media.length ? post.all_media[0] : null;
                    let mediaHtml = '';
                    if (primary) {
                        const path = getMediaPath(post.folder_name, primary);
                        if (isVideo(primary)) mediaHtml = `<div class="video-placeholder">🎬</div>`;
                        else mediaHtml = `<img class="card-media" src="${path}" loading="lazy" onerror="this.src='data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Crect%20width%3D%22100%22%20height%3D%22100%22%20fill%3D%22%23334155%22%2F%3E%3Ctext%20x%3D%2250%22%20y%3D%2255%22%20text-anchor%3D%22middle%22%20fill%3D%22%2394a3b8%22%3E%E2%9D%8C%3C%2Ftext%3E%3C%2Fsvg%3E';">`;
                    } else mediaHtml = `<div>📷 No media</div>`;
                    return `<div class="card" data-shortcode="${post.shortcode}">${mediaHtml}<div class="card-content">${post.caption.substring(0,100)}</div></div>`;
                }).join('');
            } catch(e) {
                log(`ERROR in renderGallery: ${e.message}`, true);
                grid.innerHTML = `<div class="debug">Render failed: ${e.message}</div>`;
            }
        }

        function updateWordCloud(posts) {
            // simplified for now
            const container = document.getElementById('wordcloud');
            container.innerHTML = '<span>Word cloud placeholder</span>';
        }

        // === Initialize ===
        try {
            renderGallery(allPosts);
            updateWordCloud(allPosts);
            log('Initial render complete');
        } catch(e) {
            log(`Initial render error: ${e.message}`, true);
        }

        // Add minimal storyboard buttons (to prove JS works)
        document.getElementById('openStoryboardBtn').onclick = () => alert('Storyboard placeholder – check console');
    </script>
</body>
</html>
"""

# Replace placeholder with JSON data
final_html = html_template.replace("EMBEDDED_POSTS_PLACEHOLDER", json_data)

# Write file
OUTPUT_HTML.write_text(final_html, encoding='utf-8')
print(f"✅ Debug gallery saved as {OUTPUT_HTML}")
print("Start server: python -m http.server 8000")
print(f"Open http://localhost:8000/{OUTPUT_HTML.name}")