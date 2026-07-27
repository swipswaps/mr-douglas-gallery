#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FINAL GALLERY BUILDER – WITH AUTHOR NAMES, NO TIMELINE, STORYBOARD + CHECKBOXES
================================================================================
Reads Instagram data from instagram_posts.db (or posts.csv), extracts author
names from comment mentions, and generates a standalone HTML gallery with:
- Author name (or initial icon) displayed on each post card
- No timeline section (removed completely)
- Checkbox selection on all images
- Storyboard builder (36x48" @300 DPI export)
- Search + word cloud + lightbox + comments modal

Usage: python build_final_gallery_with_authors.py
Output: index_final_with_authors.html
"""

import json
import sqlite3
import csv
import re
from collections import Counter
from pathlib import Path
import html

# ========== CONFIGURATION ==========
DB_PATH = Path("instagram_posts.db")
CSV_PATH = Path("posts.csv")
OUTPUT_HTML = Path("index_final_with_authors.html")
OUTPUT_JSON = Path("posts_with_authors.json")
ACCOUNT_OWNER = "sav_a_dc3"               # Fallback author
DISPLAY_MODE = "username"                 # "username" or "initial" – show full @name or circle with first letter

# ========== HELPER: extract author from comments ==========
def extract_author_from_comments(comments, post_caption=""):
    """
    Heuristic: find the most frequent @username in comments that is NOT
    the account owner. Assumes the post author is mentioned in comments
    (common when exporter includes @username in comment strings).
    Returns a username string without '@'.
    """
    mention_pattern = re.compile(r'@([a-zA-Z0-9_\.]+)')
    all_mentions = []
    for comment in comments:
        # Skip metadata lines that contain no user mentions
        if comment.startswith(('Count:', 'Reported by IG:', 'Saved:', 'Comments for')):
            continue
        mentions = mention_pattern.findall(comment)
        all_mentions.extend(mentions)

    # Filter out the account owner
    filtered = [m for m in all_mentions if m.lower() != ACCOUNT_OWNER.lower()]
    if not filtered:
        return ACCOUNT_OWNER

    # Return the most frequent mention
    counter = Counter(filtered)
    return counter.most_common(1)[0][0]

def get_author_display(username):
    """Return display string and optional initial."""
    if DISPLAY_MODE == "initial":
        initial = username[0].upper() if username else "?"
        return f'<span class="author-initial" title="@{username}">{initial}</span>'
    else:
        return f'<span class="author-name">@{username}</span>'

# ========== 1. LOAD POSTS ==========
posts = []

if DB_PATH.exists():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("""
        SELECT shortcode, date, likes, comments_count, caption, folder_name
        FROM posts
        ORDER BY date DESC
    """)
    for row in cur:
        post = dict(row)
        # Load comments from separate comments table (if exists)
        try:
            comments_rows = conn.execute(
                "SELECT comment_text FROM comments WHERE shortcode = ?",
                (post['shortcode'],)
            ).fetchall()
            post['comments'] = [c['comment_text'] for c in comments_rows]
        except sqlite3.OperationalError:
            # No comments table – use empty list
            post['comments'] = []
        # Load media list from folder
        folder = Path(post['folder_name'])
        all_media = []
        if folder.exists():
            all_media = sorted([
                f.name for f in folder.iterdir()
                if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4')
            ])
        post['all_media'] = all_media
        post['instagram_url'] = f"https://www.instagram.com/p/{post['shortcode']}/"
        # Extract author from comments
        post['author'] = extract_author_from_comments(post['comments'], post.get('caption', ''))
        posts.append(post)
    conn.close()
    print(f"✅ Loaded {len(posts)} posts from {DB_PATH}")
elif CSV_PATH.exists():
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            for k in ('likes', 'comments_count'):
                if k in row and row[k].isdigit():
                    row[k] = int(row[k])
            # Parse all_media JSON
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
            # Parse comments JSON
            if 'comments' in row and row['comments'] and row['comments'].startswith('['):
                row['comments'] = json.loads(row['comments'])
            else:
                row['comments'] = []
            # Ensure instagram_url
            row.setdefault('instagram_url', f"https://www.instagram.com/p/{row.get('shortcode', '')}/")
            row['author'] = extract_author_from_comments(row['comments'], row.get('caption', ''))
            posts.append(row)
    print(f"✅ Loaded {len(posts)} posts from {CSV_PATH}")
else:
    print("❌ No database or CSV found. Please run import_ig_grab_to_db.py first.")
    exit(1)

# ========== 2. (OPTIONAL) ADD HISTORIC IMAGES FROM /timeline/ ==========
# (these will appear as extra cards, with author "Historic")
timeline_folder = Path("timeline")
if timeline_folder.exists():
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
    # Prepend historic posts (appear first)
    posts = historic_posts + posts
    print(f"✅ Added {len(historic_posts)} historic images from timeline/")

# ========== 3. SAVE POSTS.JSON (for reference) ==========
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(posts, f, indent=2, ensure_ascii=False)
print(f"💾 Saved {OUTPUT_JSON}")

# ========== 4. GENERATE HTML WITH AUTHOR DISPLAY, NO TIMELINE, STORYBOARD ==========
posts_json = json.dumps(posts, ensure_ascii=False)

html_content = f"""<!DOCTYPE html>
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
            display: flex;
            gap: 12px;
            margin: 0 1.5rem 1rem 1.5rem;
            flex-wrap: wrap;
            align-items: center;
            background: #1e293b;
            padding: 8px 12px;
            border-radius: 12px;
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

        /* Storyboard styles */
        .storyboard-btn{{
            position:fixed; bottom:20px; right:20px; background:#3b82f6; color:white;
            border:none; border-radius:50px; padding:12px 24px; font-size:1rem;
            font-weight:bold; cursor:pointer; z-index:1000;
        }}
        .storyboard-btn:hover{{background:#2563eb;}}
        .storyboard-modal{{
            display:none; position:fixed; top:0; left:0; width:100%; height:100%;
            background:rgba(0,0,0,0.85); z-index:2000; overflow:auto;
        }}
        .storyboard-modal.active{{display:flex; flex-direction:column;}}
        .storyboard-container{{
            background:#1e293b; margin:20px auto; padding:20px; border-radius:16px;
            max-width:95%; width:1200px;
        }}
        .storyboard-canvas-wrapper{{
            background:#0f172a; border-radius:12px; padding:12px; text-align:center; overflow-x:auto;
        }}
        #storyboardCanvas{{
            border:2px solid #475569; border-radius:8px; background:white;
        }}
        .storyboard-controls{{
            display:flex; gap:10px; justify-content:center; margin:15px 0; flex-wrap:wrap;
        }}
        .storyboard-controls button{{
            background:#3b82f6; border:none; color:white; padding:8px 16px; border-radius:8px; cursor:pointer;
        }}
        .storyboard-controls button.danger{{background:#ef4444;}}
        .storyboard-controls button.success{{background:#10b981;}}
        .close-modal{{background:#475569; color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer;}}
        .storyboard-thumb{{
            width:80px; height:80px; object-fit:cover; border-radius:8px; cursor:pointer;
        }}
    </style>
</head>
<body>
    <div class="search-header">
        <div class="search-container">
            <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search posts (fuzzy)..." autocomplete="off">
            <div class="wordcloud-container">
                <div id="wordcloud" class="wordcloud">Loading words...</div>
            </div>
        </div>
    </div>

    <div class="gallery-toolbar">
        <span>📌 Select images:</span>
        <button id="selectAllBtn">Select All</button>
        <button id="deselectAllBtn">Deselect All</button>
        <button id="addSelectedBtn" class="primary">➕ Add Selected to Storyboard</button>
        <span id="selectedCount">0 selected</span>
    </div>

    <div id="galleryGrid" class="grid"></div>

    <button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (36x48")</button>

    <div id="storyboardModal" class="storyboard-modal">
        <div class="storyboard-container">
            <div style="display:flex; justify-content:space-between;">
                <h3 style="color:white;">📸 Storyboard Builder – 36×48" @ 300 DPI</h3>
                <button class="close-modal" id="closeStoryboardBtn">✖ Close</button>
            </div>
            <div class="storyboard-canvas-wrapper">
                <canvas id="storyboardCanvas" width="1080" height="1440"></canvas>
            </div>
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
            </div>
            <div>
                <strong style="color:white;">📁 Images (click to remove):</strong>
                <div id="storyboardThumbnails" style="display:flex; gap:12px; overflow-x:auto; padding:8px;"></div>
            </div>
        </div>
    </div>

    <!-- Lightbox -->
    <div id="lightbox" class="lightbox">
        <div class="lightbox-content">
            <div class="lightbox-close" id="lightboxClose">×</div>
            <div id="lightboxMediaContainer"></div>
            <div id="lightboxCaption" class="lightbox-caption"></div>
        </div>
    </div>

    <!-- Comments Modal -->
    <div id="commentsModal" class="modal">
        <div class="modal-header">
            <strong>Comments</strong>
            <span id="modalClose" class="modal-close">&times;</span>
        </div>
        <div id="commentsList"></div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
    <script>
        // All posts with author field
        const allPosts = {posts_json};

        // Helper functions
        function isVideo(filename) {{
            return filename && /\\.(mp4|mov|avi|mkv)$/i.test(filename);
        }}
        function getMediaPath(folderName, fileName) {{
            return `${{folderName}}/${{fileName}}`;
        }}

        function renderGallery(posts) {{
            const grid = document.getElementById('galleryGrid');
            if (!posts.length) {{
                grid.innerHTML = '<div class="no-results">No posts match your search.</div>';
                return;
            }}
            grid.innerHTML = posts.map(post => {{
                const primaryMedia = post.all_media.length ? post.all_media[0] : null;
                const carouselItems = post.all_media.slice(1).map(f => {{
                    const path = getMediaPath(post.folder_name, f);
                    if (isVideo(f)) return `<div class="carousel-video-placeholder" data-media="${{path}}">🎬</div>`;
                    return `<img class="carousel-item" src="${{path}}" data-media="${{path}}" loading="lazy" onerror="this.outerHTML='<div class=\\\'carousel-video-placeholder\\\' data-media=\\\''+path+'\\\'>❌</div>';">`;
                }}).join('');
                let mediaHtml = '';
                if (primaryMedia) {{
                    const mediaPath = getMediaPath(post.folder_name, primaryMedia);
                    if (isVideo(primaryMedia)) mediaHtml = `<div class="video-placeholder card-media">🎬 Video</div>`;
                    else mediaHtml = `<img class="card-media" src="${{mediaPath}}" loading="lazy" onerror="this.src='data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Crect%20width%3D%22100%22%20height%3D%22100%22%20fill%3D%22%23334155%22%2F%3E%3Ctext%20x%3D%2250%22%20y%3D%2255%22%20text-anchor%3D%22middle%22%20fill%3D%22%2394a3b8%22%3E%E2%9D%8C%3C%2Ftext%3E%3C%2Fsvg%3E';">`;
                }} else mediaHtml = `<div class="card-media" style="display:flex; align-items:center; justify-content:center;">📷 No media</div>`;

                // Author display (username or initial)
                let authorDisplay;
                if ('{DISPLAY_MODE}' === 'initial') {{
                    let initial = post.author.charAt(0).toUpperCase();
                    authorDisplay = `<span class="author-initial" title="@${{post.author}}">${{initial}}</span>`;
                }} else {{
                    authorDisplay = `<span class="author-name">@${{post.author}}</span>`;
                }}

                return `
                    <div class="card" data-shortcode="${{post.shortcode}}" data-caption="${{post.caption.replace(/"/g, '&quot;')}}">
                        <div style="position:relative; width:100%; aspect-ratio:4/3;">
                            ${{mediaHtml}}
                        </div>
                        <div class="card-content">
                            <div class="card-meta">
                                <span class="author">${{authorDisplay}}</span>
                                <span>📅 ${{new Date(post.date).toLocaleDateString()}}</span>
                                <span>❤️ ${{post.likes}}</span>
                                <span>💬 ${{post.comments_count}}</span>
                            </div>
                            <div class="card-caption">${{post.caption.length > 180 ? post.caption.substring(0,180)+'…' : post.caption}}</div>
                            ${{carouselItems ? `<div class="carousel">${{carouselItems}}</div>` : ''}}
                            <div class="card-footer">
                                <a href="${{post.instagram_url}}" target="_blank" class="insta-link" onclick="event.stopPropagation()">🔗 View on Instagram</a>
                                <button class="comments-btn" data-shortcode="${{post.shortcode}}">💬 ${{post.comments.length}} comments</button>
                            </div>
                        </div>
                    </div>
                `;
            }}).join('');

            // Attach comment button listeners
            document.querySelectorAll('.comments-btn').forEach(btn => {{
                btn.addEventListener('click', (e) => {{
                    e.stopPropagation();
                    const shortcode = btn.dataset.shortcode;
                    const post = allPosts.find(p => p.shortcode === shortcode);
                    if (post && post.comments.length) {{
                        const modal = document.getElementById('commentsModal');
                        const listDiv = document.getElementById('commentsList');
                        listDiv.innerHTML = post.comments.map(c => `<div class="comment-item">💬 ${{c}}</div>`).join('');
                        modal.classList.add('active');
                    }} else {{
                        alert('No comments for this post.');
                    }}
                }});
            }});

            // Carousel click
            document.querySelectorAll('.carousel-item, .carousel-video-placeholder').forEach(el => {{
                el.addEventListener('click', (e) => {{
                    e.stopPropagation();
                    const media = el.dataset.media;
                    const card = el.closest('.card');
                    const caption = card.dataset.caption;
                    openLightbox(media, caption);
                }});
            }});

            // Add checkboxes to newly rendered cards
            addCheckboxesToCards();
        }}

        function openLightbox(src, caption) {{
            const container = document.getElementById('lightboxMediaContainer');
            container.innerHTML = '';
            if (src && src.match(/\\.(mp4|mov|avi|mkv)$/i)) {{
                const v = document.createElement('video');
                v.src = src; v.controls = true;
                v.style.maxWidth = '90vw'; v.style.maxHeight = '85vh';
                container.appendChild(v);
            }} else if (src) {{
                const img = document.createElement('img');
                img.src = src;
                img.style.maxWidth = '90vw'; img.style.maxHeight = '85vh';
                img.onerror = () => {{ img.style.display = 'none'; container.innerHTML = '<div style="color:white;">Image failed to load</div>'; }};
                container.appendChild(img);
            }} else {{
                container.innerHTML = '<div style="color:white;">No media available</div>';
            }}
            document.getElementById('lightboxCaption').innerText = caption;
            document.getElementById('lightbox').classList.add('active');
        }}

        // Word cloud and search (same as before)
        function updateWordCloud(posts) {{
            const wordCount = {{}};
            posts.forEach(post => {{
                (post.caption + ' ' + post.comments.join(' ')).toLowerCase().match(/\\b[a-z]+\\b/g)?.forEach(w => {{
                    if (w.length > 2 && !/^(?:a|an|and|the|of|to|in|for|on|with|by|at|is|it|that|this|are|was|were|be|been|being|have|has|had|having|do|does|did|doing|but|or|so|for|not|can|will|just|like|get|put|up|down|out|over|under|again|further|then|once|here|there|all|any|both|each|few|more|most|other|some|such|no|nor|only|own|same|than|too|very|i|you|he|she|it|we|they|me|him|her|us|them|my|your|his|her|its|our|their|what|which|who|whom|whose|these|those|am|been|were|www|com|https|http|instagram|mrdouglas|follow|please|let|see|new|will|now|get|time|like|just)$/.test(w)) wordCount[w] = (wordCount[w] || 0) + 1;
                }});
            }});
            const words = Object.entries(wordCount).map(([w,c]) => ({{word:w, count:c}})).sort((a,b)=>b.count-a.count).slice(0,100);
            const maxF = words.length ? Math.max(...words.map(w=>w.count)) : 1;
            const container = document.getElementById('wordcloud');
            if (!words.length) {{ container.innerHTML = '<span style="color:#94a3b8;">No words found</span>'; return; }}
            container.innerHTML = words.map(w => `<span class="cloud-word" data-word="${{w.word}}" style="font-size:${{0.8 + (w.count/maxF)*1.5}}rem;">${{w.word}}</span>`).join('');
            document.querySelectorAll('.cloud-word').forEach(el => {{
                el.addEventListener('click', () => {{
                    document.getElementById('searchInput').value = el.dataset.word;
                    const event = new Event('input', {{ bubbles: true }});
                    document.getElementById('searchInput').dispatchEvent(event);
                }});
            }});
        }}

        let debounceTimer;
        document.getElementById('searchInput').addEventListener('input', (e) => {{
            clearTimeout(debounceTimer);
            const query = e.target.value.trim().toLowerCase();
            debounceTimer = setTimeout(() => {{
                const filtered = allPosts.filter(p => p.caption.toLowerCase().includes(query) || p.comments.some(c => c.toLowerCase().includes(query)));
                renderGallery(filtered);
                updateWordCloud(filtered);
            }}, 200);
        }});

        // Close lightbox/modal
        document.getElementById('lightboxClose').addEventListener('click', () => document.getElementById('lightbox').classList.remove('active'));
        document.getElementById('modalClose').addEventListener('click', () => document.getElementById('commentsModal').classList.remove('active'));
        window.addEventListener('click', (e) => {{
            if (e.target === document.getElementById('lightbox')) document.getElementById('lightbox').classList.remove('active');
            if (e.target === document.getElementById('commentsModal')) document.getElementById('commentsModal').classList.remove('active');
        }});

        // Click on card main media to open lightbox
        document.getElementById('galleryGrid').addEventListener('click', (e) => {{
            const card = e.target.closest('.card');
            if (card && !e.target.closest('.carousel-item') && !e.target.closest('.carousel-video-placeholder') && !e.target.closest('.comments-btn') && !e.target.closest('a')) {{
                let media = null;
                const img = card.querySelector('.card-media');
                if (img && img.tagName === 'IMG') media = img.src;
                else if (card.querySelector('.video-placeholder')) {{
                    const shortcode = card.dataset.shortcode;
                    const post = allPosts.find(p => p.shortcode === shortcode);
                    if (post && post.all_media.length) media = getMediaPath(post.folder_name, post.all_media[0]);
                }}
                openLightbox(media, card.dataset.caption);
            }}
        }});

        // ========== STORYBOARD (same as working version) ==========
        let storyboardImages = [], displayCanvas = null;
        const PREVIEW_W = 1080, PREVIEW_H = 1440, TARGET_W = 10800, TARGET_H = 14400, SCALE = TARGET_W / PREVIEW_W;
        const imgCache = new Map();

        function loadImage(src) {{
            if (imgCache.has(src)) return Promise.resolve(imgCache.get(src));
            return new Promise((resolve, reject) => {{
                const img = new Image(); img.crossOrigin = "Anonymous";
                img.onload = () => {{ imgCache.set(src, img); resolve(img); }};
                img.onerror = reject; img.src = src;
            }});
        }}

        async function addImageToStoryboard(src, silent=false) {{
            if (storyboardImages.some(i => i.src === src)) {{ if (!silent) alert("Image already in storyboard"); return false; }}
            try {{
                const imgEl = await loadImage(src);
                const aspect = imgEl.width / imgEl.height;
                const defW = 200, defH = defW / aspect;
                const newItem = {{
                    src, imgElement: imgEl, width: imgEl.width, height: imgEl.height,
                    left: 50, top: 50, scaleX: defW / imgEl.width, scaleY: defH / imgEl.height, fabricObject: null
                }};
                storyboardImages.push(newItem);
                if (displayCanvas) {{
                    const fimg = new fabric.Image(imgEl, {{ left: 50, top: 50, scaleX: defW / imgEl.width, scaleY: defH / imgEl.height, hasControls: true, lockRotation: true }});
                    newItem.fabricObject = fimg;
                    displayCanvas.add(fimg);
                    displayCanvas.renderAll();
                }}
                updateStoryboardThumbnails();
                return true;
            }} catch(e) {{ if (!silent) alert("Failed: " + e.message); return false; }}
        }}

        async function addMultipleImages(srcList) {{
            let added = 0;
            for (let src of srcList) if (await addImageToStoryboard(src, true)) added++;
            if (added) alert(`Added ${{added}} image(s)`);
            else if (srcList.length) alert("No new images (duplicates)");
            if (added) applyTemplate('grid');
        }}

        function updateStoryboardThumbnails() {{
            const container = document.getElementById('storyboardThumbnails');
            if (!container) return;
            container.innerHTML = storyboardImages.map((img, idx) => `<img class="storyboard-thumb" src="${{img.src}}" data-index="${{idx}}">`).join('');
            document.querySelectorAll('.storyboard-thumb').forEach(thumb => {{
                thumb.addEventListener('click', () => {{
                    const idx = parseInt(thumb.dataset.index);
                    if (!isNaN(idx)) {{
                        if (displayCanvas && storyboardImages[idx].fabricObject) displayCanvas.remove(storyboardImages[idx].fabricObject);
                        storyboardImages.splice(idx, 1);
                        displayCanvas?.renderAll();
                        updateStoryboardThumbnails();
                    }}
                }});
            }});
        }}

        function applyTemplate(templateName) {{
            if (!displayCanvas || storyboardImages.length === 0) return;
            const cnt = storyboardImages.length, margin = 20, w = PREVIEW_W - margin*2, h = PREVIEW_H - margin*2;
            if (templateName === 'center') {{
                for (let i=0; i<cnt; i++) {{
                    const item = storyboardImages[i], img = item.imgElement;
                    const sc = Math.min((w*0.8)/img.width, (h*0.8)/img.height);
                    const drawW = img.width*sc, drawH = img.height*sc;
                    const left = margin + (w-drawW)/2, top = margin + (h-drawH)/2;
                    item.left = left; item.top = top; item.scaleX = sc; item.scaleY = sc;
                    item.fabricObject?.set({{ left, top, scaleX: sc, scaleY: sc }});
                }}
            }} else if (templateName === 'twoCol') {{
                const cols = 2, cellW = (w - (cols-1)*margin) / cols;
                for (let i=0; i<cnt; i++) {{
                    const row = Math.floor(i/cols), col = i%cols, item = storyboardImages[i], img = item.imgElement;
                    let drawW = cellW, drawH = drawW / (img.width/img.height);
                    if (drawH > PREVIEW_H/3) {{ drawH = PREVIEW_H/3; drawW = drawH * (img.width/img.height); }}
                    const left = margin + col*(cellW+margin), top = margin + row*(drawH+margin);
                    item.left = left; item.top = top; item.scaleX = drawW/img.width; item.scaleY = drawH/img.height;
                    item.fabricObject?.set({{ left, top, scaleX: item.scaleX, scaleY: item.scaleY }});
                }}
            }} else if (templateName === 'bigSmall' && cnt >= 2) {{
                const big = storyboardImages[0], bigImg = big.imgElement;
                const bigW = w*0.6, bigH = h, bigSc = Math.min(bigW/bigImg.width, bigH/bigImg.height);
                const bigDrawW = bigImg.width*bigSc, bigDrawH = bigImg.height*bigSc;
                big.left = margin; big.top = margin + (h-bigDrawH)/2; big.scaleX = bigSc; big.scaleY = bigSc;
                big.fabricObject?.set({{ left: big.left, top: big.top, scaleX: bigSc, scaleY: bigSc }});
                let y = margin;
                for (let i=1; i<cnt; i++) {{
                    const item = storyboardImages[i], img = item.imgElement;
                    let drawW = w*0.35, drawH = drawW / (img.width/img.height);
                    if (drawH > (h/(cnt-1))-margin) drawH = (h/(cnt-1))-margin;
                    item.left = margin + bigDrawW + margin; item.top = y;
                    item.scaleX = drawW/img.width; item.scaleY = drawH/img.height;
                    item.fabricObject?.set({{ left: item.left, top: item.top, scaleX: item.scaleX, scaleY: item.scaleY }});
                    y += drawH + margin;
                }}
            }} else {{ // default grid 3 cols
                const cols = 3, cellW = (w - (cols-1)*margin) / cols;
                for (let i=0; i<cnt; i++) {{
                    const row = Math.floor(i/cols), col = i%cols, item = storyboardImages[i], img = item.imgElement;
                    let drawW = cellW, drawH = drawW / (img.width/img.height);
                    if (drawH > 200) {{ drawH = 200; drawW = drawH * (img.width/img.height); }}
                    const left = margin + col*(cellW+margin), top = margin + row*(drawH+margin);
                    item.left = left; item.top = top; item.scaleX = drawW/img.width; item.scaleY = drawH/img.height;
                    item.fabricObject?.set({{ left, top, scaleX: item.scaleX, scaleY: item.scaleY }});
                }}
            }}
            displayCanvas.renderAll();
        }}

        async function exportStoryboard() {{
            if (!storyboardImages.length) {{ alert("No images"); return; }}
            const off = document.createElement('canvas'); off.width = TARGET_W; off.height = TARGET_H;
            const ctx = off.getContext('2d'); ctx.fillStyle = 'white'; ctx.fillRect(0,0,TARGET_W,TARGET_H);
            for (let item of storyboardImages) {{
                try {{
                    const img = item.imgElement;
                    const left = (item.left||0)*SCALE, top = (item.top||0)*SCALE;
                    const w = img.width * (item.scaleX||1) * SCALE, h = img.height * (item.scaleY||1) * SCALE;
                    ctx.drawImage(img, left, top, w, h);
                }} catch(e) {{}}
            }}
            const a = document.createElement('a'); a.download = 'storyboard_36x48_300dpi.png'; a.href = off.toDataURL('image/png'); a.click();
        }}

        function clearAll() {{ if (confirm("Clear all?")) {{ storyboardImages = []; displayCanvas?.clear(); displayCanvas?.renderAll(); updateStoryboardThumbnails(); }} }}
        function initCanvas() {{
            const canvas = document.getElementById('storyboardCanvas');
            if (!canvas) return;
            displayCanvas = new fabric.Canvas('storyboardCanvas');
            displayCanvas.setDimensions({{ width: PREVIEW_W, height: PREVIEW_H }});
            displayCanvas.on('object:modified', (e) => {{
                const obj = e.target;
                const idx = storyboardImages.findIndex(i => i.fabricObject === obj);
                if (idx !== -1) {{
                    storyboardImages[idx].left = obj.left; storyboardImages[idx].top = obj.top;
                    storyboardImages[idx].scaleX = obj.scaleX; storyboardImages[idx].scaleY = obj.scaleY;
                }}
            }});
            displayCanvas.renderAll(); updateStoryboardThumbnails();
        }}

        // ========== CHECKBOXES FOR IMAGE SELECTION ==========
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
                chk.addEventListener('change', () => {{
                    if (chk.checked) selectedSrcs.add(src);
                    else selectedSrcs.delete(src);
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
        }}
        function deselectAll() {{
            document.querySelectorAll('.select-checkbox').forEach(chk => chk.checked = false);
            selectedSrcs.clear();
            const span = document.getElementById('selectedCount');
            if (span) span.innerText = '0 selected';
        }}
        function addSelected() {{
            const srcs = Array.from(selectedSrcs);
            if (srcs.length === 0) {{ alert("No images selected"); return; }}
            addMultipleImages(srcs);
        }}

        // ========== INITIALIZATION ==========
        function waitForFabricAndStart() {{
            if (typeof fabric !== 'undefined') {{
                initCanvas();
                renderGallery(allPosts);
                updateWordCloud(allPosts);
                addCheckboxesToCards();
                document.getElementById('selectAllBtn')?.addEventListener('click', selectAll);
                document.getElementById('deselectAllBtn')?.addEventListener('click', deselectAll);
                document.getElementById('addSelectedBtn')?.addEventListener('click', addSelected);
                document.getElementById('openStoryboardBtn').onclick = () => document.getElementById('storyboardModal').classList.add('active');
                document.getElementById('closeStoryboardBtn').onclick = () => document.getElementById('storyboardModal').classList.remove('active');
                document.getElementById('exportStoryboardBtn').onclick = exportStoryboard;
                document.getElementById('clearStoryboardBtn').onclick = clearAll;
                document.getElementById('applyTemplateBtn').onclick = () => {{ const tpl = document.getElementById('templateSelect').value; applyTemplate(tpl); }};
                window.onclick = (e) => {{ if (e.target === document.getElementById('storyboardModal')) document.getElementById('storyboardModal').classList.remove('active'); }};
            }} else {{
                setTimeout(waitForFabricAndStart, 200);
            }}
        }}
        waitForFabricAndStart();
    </script>
</body>
</html>
"""

# Write the final HTML file
with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n✅ Gallery generated: {OUTPUT_HTML.resolve()}")
print(f"   Total posts included: {len(posts)}")
print(f"   Author display mode: {DISPLAY_MODE}")
print("\n💡 Start server: python -m http.server 8000")
print(f"   Then open http://localhost:8000/{OUTPUT_HTML.name}")
print("\n📌 Features:")
print("   - Author names extracted from comments (most frequent @mention)")
print("   - Display as @username or initial circle (change DISPLAY_MODE variable)")
print("   - No timeline section")
print("   - Image checkboxes + storyboard builder (36x48\" @300 DPI)")
print("   - Search, word cloud, lightbox, comments modal")