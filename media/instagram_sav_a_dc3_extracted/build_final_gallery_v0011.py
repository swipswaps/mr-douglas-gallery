#!/usr/bin/env python3
"""
build_final_gallery_v0011.py

Single file version with:
- Proper JSON injection using json.dumps
- No broken template strings
- Console logging that actually works
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
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ========== CONFIGURATION ==========
DB_PATH = Path("instagram_posts.db")
CSV_PATH = Path("posts.csv")
OUTPUT_HTML = Path("index_v0011.html")
OUTPUT_JSON = Path("posts_with_authors.json")
ACCOUNT_OWNER = "sav_a_dc3"
DISPLAY_MODE = "username"

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
        cur = conn.execute("SELECT shortcode, date, likes, comments_count, caption, folder_name FROM posts ORDER BY date DESC")
        rows = cur.fetchall()
        for row in rows:
            post = dict(row)
            try:
                comments_rows = conn.execute("SELECT comment_text FROM comments WHERE shortcode = ?", (post['shortcode'],)).fetchall()
                post['comments'] = [c['comment_text'] for c in comments_rows]
            except sqlite3.OperationalError:
                post['comments'] = []
            folder = Path(post['folder_name'])
            all_media = []
            if folder.exists():
                all_media = sorted([f.name for f in folder.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4')])
                logger.debug(f"Folder {post['folder_name']}: found {len(all_media)} media files")
            else:
                logger.warning(f"Folder does NOT exist: {post['folder_name']}")
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
                        row['all_media'] = sorted([f.name for f in folder.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4')])
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
    # Properly serialize posts to JSON
    posts_json = json.dumps(posts, ensure_ascii=False)
    
    # Build HTML as a single string using string concatenation for clarity
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mr. Douglas – Gallery</title>
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; background-color: #0f172a; color: #e2e8f0; font-family: system-ui, sans-serif; }
        .search-header { position: sticky; top: 0; z-index: 20; background: rgba(15,23,42,0.95); backdrop-filter: blur(8px); border-bottom: 1px solid #334155; padding: 1rem; }
        .search-container { max-width: 1200px; margin: 0 auto; }
        .search-input { width: 100%; padding: 0.75rem 1rem; background: #1e293b; border: 1px solid #475569; border-radius: 2rem; color: #f1f5f9; }
        .wordcloud-container { background: #1e293b; border-radius: 1rem; padding: 1rem; margin-top: 1rem; }
        .wordcloud { display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; justify-content: center; max-height: 200px; overflow-y: auto; }
        .cloud-word { cursor: pointer; color: #94a3b8; }
        .cloud-word:hover { color: #60a5fa; }
        .gallery-toolbar { position: sticky; top: 90px; z-index: 15; display: flex; gap: 12px; margin: 0 1.5rem 1rem; flex-wrap: wrap; align-items: center; background: #1e293b; padding: 8px 12px; border-radius: 12px; }
        .gallery-toolbar button { background: #334155; color: white; border: none; padding: 6px 12px; border-radius: 8px; cursor: pointer; }
        .gallery-toolbar button.primary { background: #3b82f6; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; padding: 1.5rem; max-width: 1400px; margin: 0 auto; }
        .card { background: #1e293b; border-radius: 1rem; overflow: hidden; cursor: pointer; position: relative; }
        .card:hover { transform: translateY(-4px); }
        .card-media { width: 100%; aspect-ratio: 4/3; object-fit: cover; background: #0f172a; }
        .card-content { padding: 1rem; }
        .card-meta { display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; flex-wrap: wrap; }
        .author-name { color: #60a5fa; }
        .card-caption { font-size: 0.875rem; color: #cbd5e1; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 0.75rem; }
        .carousel { display: flex; gap: 0.5rem; overflow-x: auto; margin: 0.5rem 0; }
        .carousel-item { width: 60px; height: 60px; object-fit: cover; border-radius: 8px; cursor: pointer; background: #0f172a; }
        .comments-btn { background: none; border: none; color: #3b82f6; cursor: pointer; font-size: 0.7rem; padding: 0.25rem 0.5rem; border-radius: 1rem; background: #1e293b; }
        .card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem; }
        .insta-link { font-size: 0.75rem; color: #3b82f6; text-decoration: none; }
        .select-checkbox { position: absolute; top: 8px; left: 8px; width: 20px; height: 20px; cursor: pointer; z-index: 10; background: white; border-radius: 4px; }
        .lightbox { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); display: none; align-items: center; justify-content: center; z-index: 1000; }
        .lightbox.active { display: flex; }
        .lightbox-content { position: relative; max-width: 90vw; max-height: 90vh; }
        .lightbox-close { position: absolute; top: 10px; right: 10px; color: white; font-size: 2rem; cursor: pointer; background: rgba(0,0,0,0.5); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .modal { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #1e293b; border-radius: 1rem; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; z-index: 1100; display: none; padding: 1rem; }
        .modal.active { display: block; }
        .storyboard-btn { position: fixed; bottom: 20px; right: 20px; background: #3b82f6; color: white; border: none; border-radius: 50px; padding: 12px 24px; cursor: pointer; z-index: 1000; }
        .storyboard-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 2000; overflow: auto; }
        .storyboard-modal.active { display: flex; flex-direction: column; }
        .storyboard-container { background: #1e293b; margin: 20px auto; padding: 20px; border-radius: 16px; max-width: 95%; width: 1200px; }
        #storyboardCanvas { border: 2px solid #475569; border-radius: 8px; background: white; display: block; margin: 0 auto; }
        .storyboard-controls { display: flex; gap: 10px; justify-content: center; margin: 15px 0; flex-wrap: wrap; }
        .storyboard-controls button { background: #3b82f6; border: none; color: white; padding: 8px 16px; border-radius: 8px; cursor: pointer; }
        .storyboard-controls button.danger { background: #ef4444; }
        .storyboard-controls button.success { background: #10b981; }
        .toast { position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); background: #1e293b; color: #e2e8f0; padding: 10px 20px; border-radius: 40px; z-index: 3000; opacity: 0; transition: opacity 0.2s; }
        .toast.show { opacity: 1; }
        .debug-panel { position: fixed; bottom: 10px; left: 10px; background: #1e293b; color: #0f0; font-family: monospace; font-size: 10px; padding: 8px; border-radius: 8px; z-index: 9999; max-width: 400px; max-height: 200px; overflow: auto; opacity: 0.8; }
        .no-results { text-align: center; padding: 3rem; color: #94a3b8; grid-column: 1 / -1; }
    </style>
</head>
<body>
    <div class="debug-panel" id="debugPanel">
        <strong>🐛 Debug Active</strong><br>
        <div id="debugLog">Initializing...</div>
    </div>
    <div class="search-header">
        <div class="search-container">
            <input type="text" id="searchInput" class="search-input" placeholder="Search posts...">
            <div class="wordcloud-container"><div id="wordcloud" class="wordcloud">Loading words...</div></div>
        </div>
    </div>
    <div class="gallery-toolbar">
        <span>Select images:</span>
        <button id="selectAllBtn">Select All</button>
        <button id="deselectAllBtn">Deselect All</button>
        <button id="syncSelectedBtn" class="primary">Sync Selected to Storyboard</button>
        <span id="selectedCount">0 selected</span>
        <button id="openStoryboardNewTabBtn" style="background:#10b981;">Open Storyboard in New Tab</button>
    </div>
    <div id="galleryGrid" class="grid"></div>
    <button class="storyboard-btn" id="openStoryboardBtn">Open Storyboard <span id="storyboardCountBadge">0</span></button>
    <div id="storyboardModal" class="storyboard-modal">
        <div class="storyboard-container">
            <div style="display:flex; justify-content:space-between;"><h3>Storyboard Builder</h3><button class="close-modal" id="closeStoryboardBtn">Close</button></div>
            <div><canvas id="storyboardCanvas" width="1080" height="1440"></canvas></div>
            <div class="storyboard-controls">
                <select id="templateSelect">
                    <option value="grid">Grid (3 cols)</option>
                    <option value="twoCol">Two columns</option>
                    <option value="center">Single centered</option>
                </select>
                <button id="applyTemplateBtn" class="success">Apply Template</button>
                <button id="exportStoryboardBtn" class="success">Export PNG</button>
                <button id="clearStoryboardBtn" class="danger">Clear All</button>
            </div>
            <div><strong>Images (click to remove):</strong><div id="storyboardThumbnails"></div></div>
        </div>
    </div>
    <div id="toast" class="toast"></div>
    <div id="lightbox" class="lightbox"><div class="lightbox-content"><div class="lightbox-close" id="lightboxClose">×</div><div id="lightboxMediaContainer"></div><div id="lightboxCaption"></div></div></div>
    <div id="commentsModal" class="modal"><div class="modal-header"><strong>Comments</strong><span id="modalClose" class="modal-close">&times;</span></div><div id="commentsList"></div></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
    <script>
        // Simple debug logger
        var debugLog = document.getElementById('debugLog');
        function log(msg) {
            var div = document.createElement('div');
            div.textContent = new Date().toLocaleTimeString() + ' ' + msg;
            debugLog.appendChild(div);
            if (debugLog.children.length > 20) debugLog.removeChild(debugLog.children[0]);
            console.log(msg);
        }
        
        log('=== GALLERY STARTING ===');
        
        // Posts data
        var allPosts = ''' + posts_json + ''';
        var DISPLAY_MODE = "''' + DISPLAY_MODE + '''";
        
        log('Posts loaded: ' + allPosts.length);
        
        function getMediaPath(folder, file) {
            var path = folder + '/' + file;
            log('[Path] ' + path);
            return path;
        }
        
        function renderGallery(posts) {
            log('[Render] Rendering ' + posts.length + ' posts');
            var grid = document.getElementById('galleryGrid');
            if (!grid) { log('[ERROR] galleryGrid not found'); return; }
            if (!posts.length) { 
                grid.innerHTML = '<div class="no-results">No posts match your search.</div>';
                return;
            }
            
            var html = '';
            for (var i = 0; i < posts.length; i++) {
                var post = posts[i];
                log('[Render] Post ' + i + ': ' + post.shortcode);
                
                var pm = post.all_media && post.all_media.length ? post.all_media[0] : null;
                var mediaHtml = '';
                if (pm) {
                    var mp = getMediaPath(post.folder_name, pm);
                    mediaHtml = '<img class="card-media" src="' + mp + '" loading="lazy" onerror="log(\'[ERROR] Failed: ' + mp + '\')">';
                } else {
                    mediaHtml = '<div class="card-media">No media</div>';
                }
                
                var authorDisplay = '<span class="author-name">@' + (post.author || 'unknown') + '</span>';
                var captionText = post.caption ? (post.caption.length > 180 ? post.caption.substring(0,180) + '…' : post.caption) : '';
                
                html += '<div class="card" data-shortcode="' + (post.shortcode || '') + '" data-caption="' + (post.caption || '').replace(/"/g, '&quot;') + '">';
                html += '<div style="position:relative; width:100%; aspect-ratio:4/3;">' + mediaHtml + '</div>';
                html += '<div class="card-content">';
                html += '<div class="card-meta"><span>' + authorDisplay + '</span><span>' + new Date(post.date).toLocaleDateString() + '</span><span>' + (post.likes || 0) + ' likes</span><span>' + (post.comments_count || 0) + ' comments</span></div>';
                html += '<div class="card-caption">' + captionText + '</div>';
                html += '<div class="card-footer"><a href="' + (post.instagram_url || '#') + '" target="_blank" class="insta-link">View on Instagram</a>';
                html += '<button class="comments-btn" data-shortcode="' + (post.shortcode || '') + '">' + (post.comments ? post.comments.length : 0) + ' comments</button></div></div></div>';
            }
            
            grid.innerHTML = html;
            log('[Render] Complete - ' + posts.length + ' cards created');
        }
        
        // Initial render
        log('Calling renderGallery...');
        renderGallery(allPosts);
        log('=== GALLERY READY ===');
    </script>
</body>
</html>'''
    
    return html

def main():
    print("=" * 60)
    print("MR. DOUGLAS GALLERY BUILDER v0011")
    print("=" * 60)
    
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
    
    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    print(f"\nStart server: python -m http.server 8000")
    print(f"Open: http://localhost:8000/{OUTPUT_HTML.name}")
    print("\nCheck the debug panel in bottom-left corner for logs")

if __name__ == "__main__":
    main()