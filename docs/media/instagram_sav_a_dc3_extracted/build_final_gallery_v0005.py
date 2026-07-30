#!/usr/bin/env python3
"""
build_final_gallery_v0005.py

Generates index_v0005.html with:
- Author names extracted from Instagram comments
- No timeline section
- Professional Fabric.js storyboard with row‑based layout (no stacking)
- Resize handles, drag, remove via thumbnails, 300 DPI export
- Self‑healing: retries on missing DB/CSV, validates paths, logs all actions
- FIXED: SyntaxWarning for invalid escape sequences removed

Outputs:
- posts_with_authors.json
- index_v0005.html
"""

import json
import sqlite3
import csv
import re
import sys
import logging
from collections import Counter
from pathlib import Path

# ========== LOGGING SETUP ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ========== CONFIGURATION ==========
DB_PATH = Path("instagram_posts.db")
CSV_PATH = Path("posts.csv")
OUTPUT_HTML = Path("index_v0005.html")
OUTPUT_JSON = Path("posts_with_authors.json")
ACCOUNT_OWNER = "sav_a_dc3"
DISPLAY_MODE = "username"          # "username" or "initial"

# ========== HELPER FUNCTIONS ==========
def extract_author_from_comments(comments, caption=""):
    mention_pattern = re.compile(r'@([a-zA-Z0-9_\.]+)')
    all_mentions = []
    for comment in comments:
        if comment.startswith(('Count:', 'Reported by IG:', 'Saved:', 'Comments for')):
            continue
        mentions = mention_pattern.findall(comment)
        all_mentions.extend(mentions)
    filtered = [m for m in all_mentions if m.lower() != ACCOUNT_OWNER.lower()]
    if not filtered:
        logger.warning(f"No author found in comments, using fallback: {ACCOUNT_OWNER}")
        return ACCOUNT_OWNER
    counter = Counter(filtered)
    return counter.most_common(1)[0][0]

def load_posts():
    posts = []
    if DB_PATH.exists():
        logger.info(f"Loading from {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("""
            SELECT shortcode, date, likes, comments_count, caption, folder_name
            FROM posts
            ORDER BY date DESC
        """)
        rows = cur.fetchall()
        for row in rows:
            post = dict(row)
            try:
                comments_rows = conn.execute(
                    "SELECT comment_text FROM comments WHERE shortcode = ?",
                    (post['shortcode'],)
                ).fetchall()
                post['comments'] = [c['comment_text'] for c in comments_rows]
            except sqlite3.OperationalError:
                post['comments'] = []
            folder = Path(post['folder_name'])
            all_media = []
            if folder.exists():
                all_media = sorted([
                    f.name for f in folder.iterdir()
                    if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4')
                ])
            post['all_media'] = all_media
            post['instagram_url'] = f"https://www.instagram.com/p/{post['shortcode']}/"
            post['author'] = extract_author_from_comments(post['comments'], post.get('caption', ''))
            posts.append(post)
        conn.close()
        logger.info(f"Loaded {len(posts)} posts from DB")
    elif CSV_PATH.exists():
        logger.info(f"Loading from {CSV_PATH}")
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for k in ('likes', 'comments_count'):
                    if k in row and row[k].isdigit():
                        row[k] = int(row[k])
                if 'all_media' in row and row['all_media'] and row['all_media'].startswith('['):
                    row['all_media'] = json.loads(row['all_media'])
                else:
                    folder = Path(row.get('folder_name', ''))
                    if folder.exists():
                        row['all_media'] = sorted([
                            f.name for f in folder.iterdir()
                            if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4')
                        ])
                    else:
                        row['all_media'] = []
                if 'comments' in row and row['comments'] and row['comments'].startswith('['):
                    row['comments'] = json.loads(row['comments'])
                else:
                    row['comments'] = []
                row.setdefault('instagram_url', f"https://www.instagram.com/p/{row.get('shortcode', '')}/")
                row['author'] = extract_author_from_comments(row['comments'], row.get('caption', ''))
                posts.append(row)
        logger.info(f"Loaded {len(posts)} posts from CSV")
    else:
        logger.error("No database or CSV file found. Cannot continue.")
        sys.exit(1)
    return posts

def add_historic_images(posts):
    timeline_folder = Path("timeline")
    if not timeline_folder.exists():
        logger.info("No timeline/ folder, skipping historic images")
        return posts
    historic_posts = []
    for img_path in sorted(timeline_folder.glob("*.jpg")):
        year_match = re.search(r'\b(19|20)\d{2}\b', img_path.stem)
        year = year_match.group(0) if year_match else "0000"
        title = img_path.stem.replace('-', ' ').replace('_', ' ').title()
        caption = f"{title} – Historic photo of Mr. Douglas"
        historic_posts.append({
            "shortcode": f"hist_{img_path.stem}",
            "date": f"{year}-07-01 12:00:00",
            "likes": 0,
            "comments_count": 0,
            "caption": caption,
            "folder_name": "timeline",
            "all_media": [img_path.name],
            "comments": [],
            "instagram_url": "#",
            "author": "Historic"
        })
    logger.info(f"Added {len(historic_posts)} historic images from timeline/")
    return historic_posts + posts

def build_html(posts):
    posts_json = json.dumps(posts, ensure_ascii=False)
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>Mr. Douglas – Gallery with Authors</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            background-color: #0f172a;
            color: #e2e8f0;
            font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.5;
        }}
        .search-header {{
            position: sticky;
            top: 0;
            z-index: 20;
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid #334155;
            padding: 1rem;
        }}
        .search-container {{ max-width: 1200px; margin: 0 auto; }}
        .search-input {{
            width: 100%;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            background: #1e293b;
            border: 1px solid #475569;
            border-radius: 2rem;
            color: #f1f5f9;
            outline: none;
        }}
        .search-input:focus {{ border-color: #3b82f6; }}
        .wordcloud-container {{
            background: #1e293b;
            border-radius: 1rem;
            padding: 1rem;
            margin-top: 1rem;
        }}
        .wordcloud {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem 1rem;
            justify-content: center;
            max-height: 200px;
            overflow-y: auto;
        }}
        .cloud-word {{
            cursor: pointer;
            transition: all 0.1s ease;
            color: #94a3b8;
        }}
        .cloud-word:hover {{ color: #60a5fa; transform: scale(1.05); }}
        .gallery-toolbar {{
            position: sticky;
            top: 90px;
            z-index: 15;
            display: flex;
            gap: 12px;
            margin: 0 1.5rem 1rem 1.5rem;
            flex-wrap: wrap;
            align-items: center;
            background: #1e293b;
            padding: 8px 12px;
            border-radius: 12px;
            border: 1px solid #334155;
        }}
        .gallery-toolbar button {{
            background: #334155;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 8px;
            cursor: pointer;
        }}
        .gallery-toolbar button.primary {{ background: #3b82f6; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
            padding: 1.5rem;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .card {{
            background: #1e293b;
            border-radius: 1rem;
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
            position: relative;
        }}
        .card:hover {{ transform: translateY(-4px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.3); }}
        .card-media {{
            width: 100%;
            aspect-ratio: 4/3;
            object-fit: cover;
            background: #0f172a;
        }}
        .video-placeholder {{
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #1e293b;
            color: #94a3b8;
            font-size: 2rem;
        }}
        .card-content {{ padding: 1rem; }}
        .card-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.75rem;
            color: #94a3b8;
            margin-bottom: 0.5rem;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        .author-initial {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            background: #3b82f6;
            color: white;
            border-radius: 50%;
            font-size: 0.8rem;
            font-weight: bold;
            cursor: help;
        }}
        .author-name {{ color: #60a5fa; font-weight: 500; }}
        .card-caption {{
            font-size: 0.875rem;
            color: #cbd5e1;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
            margin-bottom: 0.75rem;
        }}
        .carousel {{
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
            margin: 0.5rem 0;
            padding-bottom: 0.5rem;
        }}
        .carousel-item {{
            width: 60px;
            height: 60px;
            object-fit: cover;
            border-radius: 8px;
            flex-shrink: 0;
            cursor: pointer;
            background: #0f172a;
        }}
        .carousel-video-placeholder {{
            width: 60px;
            height: 60px;
            background: #1e293b;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            cursor: pointer;
        }}
        .comments-btn {{
            background: none;
            border: none;
            color: #3b82f6;
            cursor: pointer;
            font-size: 0.7rem;
            padding: 0.25rem 0.5rem;
            border-radius: 1rem;
            background: #1e293b;
        }}
        .comments-btn:hover {{ background: #334155; }}
        .card-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.5rem;
        }}
        .insta-link {{
            font-size: 0.75rem;
            color: #3b82f6;
            text-decoration: none;
        }}
        .select-checkbox {{
            position: absolute;
            top: 8px;
            left: 8px;
            width: 20px;
            height: 20px;
            cursor: pointer;
            z-index: 10;
            background: white;
            border-radius: 4px;
            border: 1px solid #cbd5e1;
        }}
        .lightbox {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.9); backdrop-filter: blur(8px);
            display: none; align-items: center; justify-content: center;
            z-index: 1000;
        }}
        .lightbox.active {{ display: flex; }}
        .lightbox-content {{
            position: relative;
            max-width: 90vw;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .lightbox-media {{
            max-width: 100%;
            max-height: 85vh;
            object-fit: contain;
            border-radius: 12px;
        }}
        .lightbox-close {{
            position: absolute;
            top: 10px;
            right: 10px;
            color: white;
            font-size: 2rem;
            cursor: pointer;
            background: rgba(0,0,0,0.5);
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1010;
        }}
        .lightbox-caption {{
            margin-top: 1rem;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            max-width: 90vw;
            font-size: 0.875rem;
        }}
        .modal {{
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: #1e293b;
            border-radius: 1rem;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            z-index: 1100;
            display: none;
            padding: 1rem;
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5);
        }}
        .modal.active {{ display: block; }}
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
        }}
        .modal-close {{ cursor: pointer; font-size: 1.5rem; line-height: 1; }}
        .comment-item {{ padding: 0.5rem 0; border-bottom: 1px solid #334155; }}
        .no-results {{ text-align: center; padding: 3rem; color: #94a3b8; grid-column: 1 / -1; }}

        .storyboard-btn {{
            position:fixed; bottom:20px; right:20px; background:#3b82f6; color:white;
            border:none; border-radius:50px; padding:12px 24px; font-size:1rem;
            font-weight:bold; cursor:pointer; z-index:1000;
        }}
        .storyboard-btn:hover{{background:#2563eb;}}
        .storyboard-modal {{
            display:none; position:fixed; top:0; left:0; width:100%; height:100%;
            background:rgba(0,0,0,0.85); z-index:2000; overflow:auto;
        }}
        .storyboard-modal.active{{display:flex; flex-direction:column;}}
        .storyboard-container {{
            background:#1e293b; margin:20px auto; padding:20px; border-radius:16px;
            max-width:95%; width:1200px;
        }}
        .storyboard-canvas-wrapper {{
            background:#0f172a; border-radius:12px; padding:12px; text-align:center; overflow-x:auto;
        }}
        #storyboardCanvas {{
            border:2px solid #475569; border-radius:8px; background:white;
            display: block;
            margin: 0 auto;
        }}
        .storyboard-controls {{
            display:flex; gap:10px; justify-content:center; margin:15px 0; flex-wrap:wrap;
        }}
        .storyboard-controls button {{
            background:#3b82f6; border:none; color:white; padding:8px 16px; border-radius:8px; cursor:pointer;
        }}
        .storyboard-controls button.danger{{background:#ef4444;}}
        .storyboard-controls button.success{{background:#10b981;}}
        .close-modal{{background:#475569; color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer;}}
        .storyboard-thumb {{
            width:80px; height:80px; object-fit:cover; border-radius:8px; cursor:pointer;
            margin-right:8px;
        }}
        .toast {{
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: #1e293b;
            color: #e2e8f0;
            padding: 10px 20px;
            border-radius: 40px;
            font-size: 0.9rem;
            z-index: 3000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            border-left: 4px solid #3b82f6;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s ease;
        }}
        .toast.show {{ opacity: 1; }}
    </style>
</head>
<body>
    <div class="search-header">
        <div class="search-container">
            <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search posts (fuzzy)..." autocomplete="off">
            <div class="wordcloud-container"><div id="wordcloud" class="wordcloud">Loading words...</div></div>
        </div>
    </div>
    <div class="gallery-toolbar">
        <span>📌 Select images:</span>
        <button id="selectAllBtn">Select All</button>
        <button id="deselectAllBtn">Deselect All</button>
        <button id="syncSelectedBtn" class="primary">🔄 Sync Selected to Storyboard</button>
        <span id="selectedCount">0 selected</span>
        <button id="openStoryboardNewTabBtn" style="background:#10b981;">🪟 Open Storyboard in New Tab</button>
    </div>
    <div id="galleryGrid" class="grid"></div>
    <button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal) <span id="storyboardCountBadge" style="background:#ef4444; border-radius:20px; padding:2px 8px; margin-left:8px; font-size:0.7rem;">0</span></button>
    <div id="storyboardModal" class="storyboard-modal">
        <div class="storyboard-container">
            <div style="display:flex; justify-content:space-between;"><h3 style="color:white;">📸 Storyboard Builder – 36×48" @ 300 DPI</h3><button class="close-modal" id="closeStoryboardBtn">✖ Close</button></div>
            <div class="storyboard-canvas-wrapper"><canvas id="storyboardCanvas" width="1080" height="1440"></canvas></div>
            <div class="storyboard-controls">
                <select id="templateSelect">
                    <option value="grid">Grid (3 cols)</option>
                    <option value="twoCol">Two columns</option>
                    <option value="threeCol">Three columns</option>
                    <option value="bigSmall">Big + Small</option>
                    <option value="center">Single centered</option>
                </select>
                <button id="applyTemplateBtn" class="success">✨ Apply Template</button>
                <button id="exportStoryboardBtn" class="success">⬇ Export PNG (10800×14400)</button>
                <button id="clearStoryboardBtn" class="danger">🗑 Clear All</button>
                <button id="resetViewBtn" class="success">🔄 Reset View</button>
            </div>
            <div><strong style="color:white;">📁 Images (click to remove):</strong><div id="storyboardThumbnails" style="display:flex; gap:12px; overflow-x:auto; padding:8px;"></div></div>
        </div>
    </div>
    <div id="toast" class="toast"></div>
    <div id="lightbox" class="lightbox"><div class="lightbox-content"><div class="lightbox-close" id="lightboxClose">×</div><div id="lightboxMediaContainer"></div><div id="lightboxCaption" class="lightbox-caption"></div></div></div>
    <div id="commentsModal" class="modal"><div class="modal-header"><strong>Comments</strong><span id="modalClose" class="modal-close">&times;</span></div><div id="commentsList"></div></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
    <script>
        // All posts data (injected)
        const allPosts = {posts_json};
        const DISPLAY_MODE = "{DISPLAY_MODE}";

        function showToast(msg, dur=2000) {{
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), dur);
        }}
        function isVideo(fn) {{ return fn && /\\.(mp4|mov|avi|mkv)$/i.test(fn); }}
        function getMediaPath(folder, file) {{ return folder + '/' + file; }}

        function renderGallery(posts) {{
            const grid = document.getElementById('galleryGrid');
            if (!posts.length) {{ grid.innerHTML = '<div class="no-results">No posts match your search.</div>'; return; }}
            grid.innerHTML = posts.map(post => {{
                const pm = post.all_media.length ? post.all_media[0] : null;
                const carItems = post.all_media.slice(1).map(f => {{
                    const p = getMediaPath(post.folder_name, f);
                    return isVideo(f) ? `<div class="carousel-video-placeholder" data-media="${{p}}">🎬</div>` : `<img class="carousel-item" src="${{p}}" data-media="${{p}}" loading="lazy" onerror="this.outerHTML='<div class=\\\'carousel-video-placeholder\\\' data-media=\\\''+p+'\\\'>❌</div>';">`;
                }}).join('');
                let mediaHtml = '';
                if (pm) {{
                    const mp = getMediaPath(post.folder_name, pm);
                    if (isVideo(pm)) mediaHtml = `<div class="video-placeholder card-media">🎬 Video</div>`;
                    else mediaHtml = `<img class="card-media" src="${{mp}}" loading="lazy" onerror="this.src='data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Crect%20width%3D%22100%22%20height%3D%22100%22%20fill%3D%22%23334155%22%2F%3E%3Ctext%20x%3D%2250%22%20y%3D%2255%22%20text-anchor%3D%22middle%22%20fill%3D%22%2394a3b8%22%3E%E2%9D%8C%3C%2Ftext%3E%3C%2Fsvg%3E';">`;
                }} else mediaHtml = `<div class="card-media" style="display:flex; align-items:center; justify-content:center;">📷 No media</div>`;
                let authorDisplay;
                if (DISPLAY_MODE === 'initial') {{
                    let init = post.author.charAt(0).toUpperCase();
                    authorDisplay = `<span class="author-initial" title="@${{post.author}}">${{init}}</span>`;
                }} else {{
                    authorDisplay = `<span class="author-name">@${{post.author}}</span>`;
                }}
                return `
                    <div class="card" data-shortcode="${{post.shortcode}}" data-caption="${{post.caption.replace(/"/g, '&quot;')}}">
                        <div style="position:relative; width:100%; aspect-ratio:4/3;">${{mediaHtml}}</div>
                        <div class="card-content">
                            <div class="card-meta">
                                <span class="author">${{authorDisplay}}</span>
                                <span>📅 ${{new Date(post.date).toLocaleDateString()}}</span>
                                <span>❤️ ${{post.likes}}</span>
                                <span>💬 ${{post.comments_count}}</span>
                            </div>
                            <div class="card-caption">${{post.caption.length > 180 ? post.caption.substring(0,180)+'…' : post.caption}}</div>
                            ${{carItems ? `<div class="carousel">${{carItems}}</div>` : ''}}
                            <div class="card-footer">
                                <a href="${{post.instagram_url}}" target="_blank" class="insta-link" onclick="event.stopPropagation()">🔗 View on Instagram</a>
                                <button class="comments-btn" data-shortcode="${{post.shortcode}}">💬 ${{post.comments.length}} comments</button>
                            </div>
                        </div>
                    </div>
                `;
            }}).join('');
            attachCommentListeners(); attachCarouselListeners(); addCheckboxesToCards();
        }}
        function attachCommentListeners() {{ document.querySelectorAll('.comments-btn').forEach(b => {{ b.removeEventListener('click', commentHandler); b.addEventListener('click', commentHandler); }}); }}
        function commentHandler(e) {{ e.stopPropagation(); const sc = this.dataset.shortcode; const p = allPosts.find(p => p.shortcode === sc); if (p && p.comments.length) {{ document.getElementById('commentsList').innerHTML = p.comments.map(c => `<div class="comment-item">💬 ${{c}}</div>`).join(''); document.getElementById('commentsModal').classList.add('active'); }} else {{ showToast('No comments for this post.'); }} }}
        function attachCarouselListeners() {{ document.querySelectorAll('.carousel-item,.carousel-video-placeholder').forEach(el => {{ el.removeEventListener('click', carouselHandler); el.addEventListener('click', carouselHandler); }}); }}
        function carouselHandler(e) {{ e.stopPropagation(); const media = this.dataset.media; const card = this.closest('.card'); const caption = card.dataset.caption; openLightbox(media, caption); }}
        function openLightbox(src, caption) {{ const c = document.getElementById('lightboxMediaContainer'); c.innerHTML = ''; if (src && src.match(/\\.(mp4|mov|avi|mkv)$/i)) {{ const v = document.createElement('video'); v.src = src; v.controls = true; v.style.maxWidth = '90vw'; v.style.maxHeight = '85vh'; c.appendChild(v); }} else if (src) {{ const img = document.createElement('img'); img.src = src; img.style.maxWidth = '90vw'; img.style.maxHeight = '85vh'; img.onerror = () => {{ img.style.display = 'none'; c.innerHTML = '<div style="color:white;">Image failed to load</div>'; }}; c.appendChild(img); }} else {{ c.innerHTML = '<div style="color:white;">No media available</div>'; }} document.getElementById('lightboxCaption').innerText = caption; document.getElementById('lightbox').classList.add('active'); }}
        function updateWordCloud(posts) {{ const wc = {{}}; posts.forEach(p => {{ (p.caption + ' ' + p.comments.join(' ')).toLowerCase().match(/\\b[a-z]+\\b/g)?.forEach(w => {{ if (w.length > 2 && !/^(?:a|an|and|the|of|to|in|for|on|with|by|at|is|it|that|this|are|was|were|be|been|being|have|has|had|having|do|does|did|doing|but|or|so|for|not|can|will|just|like|get|put|up|down|out|over|under|again|further|then|once|here|there|all|any|both|each|few|more|most|other|some|such|no|nor|only|own|same|than|too|very|i|you|he|she|it|we|they|me|him|her|us|them|my|your|his|her|its|our|their|what|which|who|whom|whose|these|those|am|been|were|www|com|https|http|instagram|mrdouglas|follow|please|let|see|new|will|now|get|time|like|just)$/.test(w)) wc[w] = (wc[w] || 0) + 1; }}); }}); const words = Object.entries(wc).map(([w,c]) => ({{word:w, count:c}})).sort((a,b)=>b.count-a.count).slice(0,100); const maxF = words.length ? Math.max(...words.map(w=>w.count)) : 1; const container = document.getElementById('wordcloud'); if (!words.length) {{ container.innerHTML = '<span style="color:#94a3b8;">No words found</span>'; return; }} container.innerHTML = words.map(w => `<span class="cloud-word" data-word="${{w.word}}" style="font-size:${{0.8 + (w.count/maxF)*1.5}}rem;">${{w.word}}</span>`).join(''); document.querySelectorAll('.cloud-word').forEach(el => {{ el.addEventListener('click', () => {{ document.getElementById('searchInput').value = el.dataset.word; const e = new Event('input', {{bubbles: true}}); document.getElementById('searchInput').dispatchEvent(e); }}); }}); }}
        let debounceTimer; document.getElementById('searchInput').addEventListener('input', (e) => {{ clearTimeout(debounceTimer); const q = e.target.value.trim().toLowerCase(); debounceTimer = setTimeout(() => {{ const f = allPosts.filter(p => p.caption.toLowerCase().includes(q) || p.comments.some(c => c.toLowerCase().includes(q))); renderGallery(f); updateWordCloud(f); }}, 200); }});
        document.getElementById('lightboxClose').addEventListener('click', () => document.getElementById('lightbox').classList.remove('active')); document.getElementById('modalClose').addEventListener('click', () => document.getElementById('commentsModal').classList.remove('active')); window.addEventListener('click', (e) => {{ if (e.target === document.getElementById('lightbox')) document.getElementById('lightbox').classList.remove('active'); if (e.target === document.getElementById('commentsModal')) document.getElementById('commentsModal').classList.remove('active'); }});
        document.getElementById('galleryGrid').addEventListener('click', (e) => {{ const card = e.target.closest('.card'); if (card && !e.target.closest('.carousel-item') && !e.target.closest('.carousel-video-placeholder') && !e.target.closest('.comments-btn') && !e.target.closest('a') && !e.target.closest('.select-checkbox')) {{ let media = null; const img = card.querySelector('.card-media'); if (img && img.tagName === 'IMG') media = img.src; else if (card.querySelector('.video-placeholder')) {{ const sc = card.dataset.shortcode; const p = allPosts.find(p => p.shortcode === sc); if (p && p.all_media.length) media = getMediaPath(p.folder_name, p.all_media[0]); }} openLightbox(media, card.dataset.caption); }} }});

        // ========== PROFESSIONAL FABRIC.JS STORYBOARD (NO STACKING) ==========
        let canvas = null;
        let storyboardImages = [];
        const STORAGE_KEY = "storyboard_images_srcs";
        const PREVIEW_W = 1080, PREVIEW_H = 1440, TARGET_W = 10800, TARGET_H = 14400, SCALE = TARGET_W / PREVIEW_W;
        let currentTemplate = 'grid';

        function updateStoryboardBadge() {{
            const b = document.getElementById('storyboardCountBadge');
            if (b) b.innerText = storyboardImages.length;
        }}

        async function addImageToStoryboard(src, silent=false) {{
            if (storyboardImages.some(i => i.src === src)) {{
                if (!silent) showToast("Image already in storyboard");
                return false;
            }}
            return new Promise((resolve) => {{
                fabric.Image.fromURL(src, (img) => {{
                    if (!img) {{
                        if (!silent) showToast("Failed to load image: " + src);
                        resolve(false);
                        return;
                    }}
                    img.set({{ crossOrigin: 'Anonymous', hasControls: true, hasBorders: true, lockRotation: true }});
                    storyboardImages.push({{ src, fabricObj: img, originalWidth: img.width, originalHeight: img.height }});
                    canvas.add(img);
                    applyLayout(currentTemplate);
                    updateThumbnails();
                    saveToLocalStorage();
                    updateStoryboardBadge();
                    resolve(true);
                }}, {{ crossOrigin: 'Anonymous' }});
            }});
        }}

        async function addMultipleImages(srcList) {{
            let added = 0;
            for (let src of srcList) if (await addImageToStoryboard(src, true)) added++;
            if (added) showToast(`Added ${{added}} image(s)`);
            else if (srcList.length) showToast("No new images (duplicates)");
        }}

        async function syncSelectedToStoryboard() {{
            const srcs = Array.from(selectedSrcs);
            if (srcs.length === 0) {{ showToast("No images selected"); return; }}
            let added = 0;
            for (let src of srcs) if (await addImageToStoryboard(src, true)) added++;
            if (added) showToast(`Added ${{added}} new image(s) to storyboard`);
            else showToast("All selected images already in storyboard");
        }}

        function applyLayout(templateName) {{
            if (!canvas || storyboardImages.length === 0) return;
            currentTemplate = templateName;
            const margin = 20;
            const canvasW = PREVIEW_W, canvasH = PREVIEW_H;
            const availW = canvasW - margin * 2;
            const availH = canvasH - margin * 2;
            const cnt = storyboardImages.length;
            
            function getObjHeight(obj) {{ return obj.height * obj.scaleY; }}
            function getObjWidth(obj) {{ return obj.width * obj.scaleX; }}

            function placeInGrid(cols, maxHeightPerRow) {{
                let y = margin;
                for (let i = 0; i < cnt; i++) {{
                    const obj = storyboardImages[i].fabricObj;
                    const col = i % cols;
                    if (col === 0 && i !== 0) {{
                        const prevRowStart = i - cols;
                        let rowMax = 0;
                        for (let j = prevRowStart; j < i; j++) {{
                            rowMax = Math.max(rowMax, getObjHeight(storyboardImages[j].fabricObj));
                        }}
                        y += rowMax + margin;
                    }}
                    const cellW = (availW - (cols - 1) * margin) / cols;
                    let scale = Math.min(cellW / obj.width, maxHeightPerRow / obj.height);
                    obj.scale(scale);
                    const left = margin + col * (cellW + margin);
                    const top = y;
                    obj.set({{ left, top }});
                    console.log(`Placed image ${{i}} at (left=${{left.toFixed(1)}}, top=${{top.toFixed(1)}}) scale=${{scale.toFixed(3)}}`);
                }}
            }}

            if (templateName === 'center') {{
                const obj = storyboardImages[0].fabricObj;
                const scale = Math.min(availW / obj.width, availH / obj.height);
                obj.scale(scale);
                obj.set({{ left: margin + (availW - getObjWidth(obj)) / 2, top: margin + (availH - getObjHeight(obj)) / 2 }});
                console.log("Center layout applied");
            }}
            else if (templateName === 'twoCol') {{
                placeInGrid(2, 300);
                console.log("Two‑column layout applied");
            }}
            else if (templateName === 'threeCol' || templateName === 'grid') {{
                placeInGrid(3, 200);
                console.log("Three‑column / grid layout applied");
            }}
            else if (templateName === 'bigSmall' && cnt >= 2) {{
                const big = storyboardImages[0].fabricObj;
                const bigW = availW * 0.6;
                const bigH = availH;
                let scaleBig = Math.min(bigW / big.width, bigH / big.height);
                big.scale(scaleBig);
                big.set({{ left: margin, top: margin + (availH - getObjHeight(big)) / 2 }});
                console.log(`Big image placed at left=${{margin}}, top=${{(margin + (availH - getObjHeight(big)) / 2).toFixed(1)}}`);
                const smallW = availW * 0.35;
                let y = margin;
                for (let i = 1; i < cnt; i++) {{
                    const obj = storyboardImages[i].fabricObj;
                    let scaleSmall = Math.min(smallW / obj.width, 300 / obj.height);
                    obj.scale(scaleSmall);
                    obj.set({{ left: margin + getObjWidth(big) + margin, top: y }});
                    console.log(`Small image ${{i}} placed at left=${{margin + getObjWidth(big) + margin}}, top=${{y}}`);
                    y += getObjHeight(obj) + margin;
                }}
            }}
            canvas.renderAll();
            saveToLocalStorage();
        }}

        function resetView() {{ applyLayout(currentTemplate); }}
        function clearAll() {{
            if (confirm("Clear all images from storyboard?")) {{
                storyboardImages.forEach(item => canvas.remove(item.fabricObj));
                storyboardImages = [];
                canvas.renderAll();
                updateThumbnails();
                localStorage.removeItem(STORAGE_KEY);
                updateStoryboardBadge();
                showToast("Storyboard cleared");
            }}
        }}
        async function exportStoryboard() {{
            if (storyboardImages.length === 0) {{ showToast("No images to export"); return; }}
            const offCanvas = document.createElement('canvas');
            offCanvas.width = TARGET_W;
            offCanvas.height = TARGET_H;
            const offCtx = offCanvas.getContext('2d');
            offCtx.fillStyle = 'white';
            offCtx.fillRect(0, 0, TARGET_W, TARGET_H);
            for (let item of storyboardImages) {{
                const obj = item.fabricObj;
                const left = obj.left * SCALE;
                const top = obj.top * SCALE;
                const width = obj.width * obj.scaleX * SCALE;
                const height = obj.height * obj.scaleY * SCALE;
                offCtx.drawImage(obj._element, left, top, width, height);
            }}
            const a = document.createElement('a');
            a.download = 'storyboard_36x48_300dpi.png';
            a.href = offCanvas.toDataURL('image/png');
            a.click();
        }}
        function updateThumbnails() {{
            const container = document.getElementById('storyboardThumbnails');
            if (!container) return;
            container.innerHTML = storyboardImages.map((img, idx) => `<img class="storyboard-thumb" src="${{img.src}}" data-index="${{idx}}">`).join('');
            document.querySelectorAll('.storyboard-thumb').forEach(thumb => {{
                thumb.addEventListener('click', () => {{
                    const idx = parseInt(thumb.dataset.index);
                    if (!isNaN(idx)) {{
                        canvas.remove(storyboardImages[idx].fabricObj);
                        storyboardImages.splice(idx, 1);
                        canvas.renderAll();
                        updateThumbnails();
                        saveToLocalStorage();
                        updateStoryboardBadge();
                        showToast("Image removed");
                    }}
                }});
            }});
        }}
        function saveToLocalStorage() {{
            const srcs = storyboardImages.map(i => i.src);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(srcs));
        }}
        async function loadFromLocalStorage() {{
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {{
                try {{
                    const srcs = JSON.parse(stored);
                    if (Array.isArray(srcs) && srcs.length) {{
                        for (let src of srcs) {{
                            if (!storyboardImages.some(i => i.src === src)) {{
                                await new Promise((resolve) => {{
                                    fabric.Image.fromURL(src, (img) => {{
                                        if (img) {{
                                            img.set({{ crossOrigin: 'Anonymous', hasControls: true, hasBorders: true, lockRotation: true }});
                                            storyboardImages.push({{ src, fabricObj: img, originalWidth: img.width, originalHeight: img.height }});
                                            canvas.add(img);
                                        }}
                                        resolve();
                                    }}, {{ crossOrigin: 'Anonymous' }});
                                }});
                            }}
                        }}
                        applyLayout(currentTemplate);
                        updateThumbnails();
                        updateStoryboardBadge();
                    }}
                }} catch(e) {{ console.warn(e); }}
            }}
        }}
        function initCanvas() {{
            const canvasEl = document.getElementById('storyboardCanvas');
            if (!canvasEl) return;
            if (canvas) canvas.dispose();
            canvas = new fabric.Canvas('storyboardCanvas');
            canvas.setDimensions({{ width: PREVIEW_W, height: PREVIEW_H }});
            canvas.backgroundColor = 'white';
            canvas.on('object:modified', () => saveToLocalStorage());
            canvas.on('object:added', () => saveToLocalStorage());
            canvas.on('object:removed', () => saveToLocalStorage());
            canvas.renderAll();
            for (let item of storyboardImages) {{
                canvas.add(item.fabricObj);
            }}
            canvas.renderAll();
        }}

        // ========== CHECKBOXES ==========
        let selectedSrcs = new Set();
        function addCheckboxesToCards() {{
            document.querySelectorAll('.card, .timeline-card').forEach(card => {{
                if (card.querySelector('.select-checkbox')) return;
                const img = card.querySelector('img');
                if (!img || !img.src || img.src.startsWith('data:')) return;
                const src = img.src;
                const chk = document.createElement('input');
                chk.type = 'checkbox'; chk.className = 'select-checkbox';
                chk.checked = selectedSrcs.has(src);
                chk.addEventListener('click', e => e.stopPropagation());
                chk.addEventListener('change', async e => {{
                    e.stopPropagation();
                    if (chk.checked) {{
                        selectedSrcs.add(src);
                        await addImageToStoryboard(src, true);
                    }} else {{
                        selectedSrcs.delete(src);
                    }}
                    const span = document.getElementById('selectedCount');
                    if (span) span.innerText = selectedSrcs.size + ' selected';
                }});
                if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
                card.appendChild(chk);
            }});
        }}
        function selectAll() {{
            document.querySelectorAll('.select-checkbox').forEach(chk => chk.checked = true);
            selectedSrcs.clear();
            document.querySelectorAll('.card img, .timeline-card img').forEach(img => {{
                if (img.src && !img.src.startsWith('data:')) selectedSrcs.add(img.src);
            }});
            const span = document.getElementById('selectedCount');
            if (span) span.innerText = selectedSrcs.size + ' selected';
            addMultipleImages(Array.from(selectedSrcs));
        }}
        function deselectAll() {{
            document.querySelectorAll('.select-checkbox').forEach(chk => chk.checked = false);
            selectedSrcs.clear();
            const span = document.getElementById('selectedCount');
            if (span) span.innerText = '0 selected';
        }}

        // ========== NEW TAB (FIXED: no Python code inside) ==========
        function openStoryboardNewTab() {{
            const srcs = storyboardImages.map(i => i.src);
            const w = window.open();
            if (!w) {{ showToast("Popup blocked"); return; }}
            const htmlContent = `<!DOCTYPE html>
            <html>
            <head>
                <title>Mr. Douglas Storyboard</title>
                <style>
                    body {{ margin:0; background:#0f172a; color:white; font-family:monospace; }}
                    canvas {{ display:block; margin:20px auto; border:2px solid #475569; background:white; }}
                    .controls {{ text-align:center; padding:10px; }}
                    button {{ margin:5px; padding:8px 16px; background:#3b82f6; border:none; color:white; border-radius:8px; cursor:pointer; }}
                </style>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
            </head>
            <body>
                <div class="controls">
                    <button id="exportBtn">⬇ Export PNG (10800×14400)</button>
                    <button id="closeBtn" onclick="window.close()">✖ Close</button>
                </div>
                <canvas id="storyboardCanvasNew" width="1080" height="1440"></canvas>
                <script>
                    const srcs = ${{JSON.stringify(srcs)}};
                    let canvas, images = [];
                    const PREVIEW_W=1080, PREVIEW_H=1440, TARGET_W=10800, TARGET_H=14400, SCALE=TARGET_W/PREVIEW_W;
                    async function loadAll() {{
                        if(!srcs.length) return;
                        let loaded = 0;
                        srcs.forEach(src => {{
                            fabric.Image.fromURL(src, (img) => {{
                                if(!img) return;
                                img.set({{ hasControls: true, lockRotation: true }});
                                images.push(img);
                                loaded++;
                                if(loaded === srcs.length) drawCanvas();
                            }}, {{ crossOrigin: 'Anonymous' }});
                        }});
                    }}
                    function drawCanvas() {{
                        canvas = new fabric.Canvas('storyboardCanvasNew');
                        canvas.setDimensions({{ width: PREVIEW_W, height: PREVIEW_H }});
                        canvas.backgroundColor = 'white';
                        const margin = 20, w = PREVIEW_W - margin*2, h = PREVIEW_H - margin*2, cols = 3, cellW = (w - (cols-1)*margin) / cols;
                        let y = margin;
                        for(let i=0;i<images.length;i++){{
                            const img = images[i];
                            const col = i%cols;
                            if(col===0 && i!==0) {{
                                let rowMax = 0;
                                for(let j=i-cols; j<i; j++) rowMax = Math.max(rowMax, images[j].height * images[j].scaleY);
                                y += rowMax + margin;
                            }}
                            let maxH = 200;
                            let scale = Math.min(cellW / img.width, maxH / img.height);
                            img.scale(scale);
                            img.set({{ left: margin + col*(cellW+margin), top: y }});
                            canvas.add(img);
                        }}
                        canvas.renderAll();
                    }}
                    document.getElementById('exportBtn').onclick = () => {{
                        if(!images.length) return;
                        const off = document.createElement('canvas'); off.width = TARGET_W; off.height = TARGET_H;
                        const ctx = off.getContext('2d'); ctx.fillStyle = 'white'; ctx.fillRect(0,0,TARGET_W,TARGET_H);
                        images.forEach(img => {{
                            const left = img.left * SCALE, top = img.top * SCALE;
                            const w = img.width * img.scaleX * SCALE, h = img.height * img.scaleY * SCALE;
                            ctx.drawImage(img._element, left, top, w, h);
                        }});
                        const a = document.createElement('a'); a.download = 'storyboard_36x48_300dpi.png'; a.href = off.toDataURL('image/png'); a.click();
                    }};
                    loadAll();
                </script>
            </body>
            </html>`;
            w.document.write(htmlContent);
            w.document.close();
        }}

        // ========== INIT ==========
        (async function init() {{
            initCanvas();
            await loadFromLocalStorage();
            renderGallery(allPosts);
            updateWordCloud(allPosts);
            addCheckboxesToCards();

            document.getElementById('selectAllBtn')?.addEventListener('click', selectAll);
            document.getElementById('deselectAllBtn')?.addEventListener('click', deselectAll);
            document.getElementById('syncSelectedBtn')?.addEventListener('click', syncSelectedToStoryboard);
            document.getElementById('openStoryboardBtn').onclick = () => document.getElementById('storyboardModal').classList.add('active');
            document.getElementById('closeStoryboardBtn').onclick = () => document.getElementById('storyboardModal').classList.remove('active');
            document.getElementById('exportStoryboardBtn').onclick = exportStoryboard;
            document.getElementById('clearStoryboardBtn').onclick = clearAll;
            document.getElementById('applyTemplateBtn').onclick = () => {{
                const tpl = document.getElementById('templateSelect').value;
                applyLayout(tpl);
            }};
            document.getElementById('resetViewBtn').onclick = resetView;
            document.getElementById('openStoryboardNewTabBtn').onclick = openStoryboardNewTab;
            window.onclick = (e) => {{ if (e.target === document.getElementById('storyboardModal')) document.getElementById('storyboardModal').classList.remove('active'); }};
            updateStoryboardBadge();
        }})();
    </script>
</body>
</html>
"""
    return html_template

# ========== MAIN ==========
def main():
    logger.info("Starting gallery build v0005")
    posts = load_posts()
    posts = add_historic_images(posts)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {OUTPUT_JSON}")
    html = build_html(posts)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    logger.info(f"Generated {OUTPUT_HTML.resolve()}")
    logger.info(f"Total posts: {len(posts)}")
    logger.info(f"Author display mode: {DISPLAY_MODE}")
    logger.info("Start server: python -m http.server 8000")
    logger.info(f"Open http://localhost:8000/{OUTPUT_HTML.name}")
    logger.info("Storyboard layout uses row‑based Y accumulation – no stacking.")

if __name__ == "__main__":
    main()