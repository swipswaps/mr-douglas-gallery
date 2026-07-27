#!/usr/bin/env python3
"""
build_final_gallery_v0009.py

Generates index_v0009.html with:
- Complete error logging to SQLite database
- Automatic browser console error capture via fetch() to local endpoint
- Embedded JavaScript error handler that sends all console messages to server
- Image path validation with database logging
- Step-by-step execution logging

Outputs:
- posts_with_authors.json
- index_v0009.html
- gallery_errors.db (SQLite database with all errors)
- execution_log.txt (plain text log)
"""

import json
import sqlite3
import csv
import re
import sys
import logging
import threading
import webbrowser
import time
from datetime import datetime
from collections import Counter
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# ========== DATABASE SETUP ==========
DB_LOG_PATH = Path("gallery_errors.db")

def init_error_db():
    """Initialize SQLite database for error logging"""
    conn = sqlite3.connect(DB_LOG_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS execution_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            step_name TEXT,
            status TEXT,
            message TEXT,
            details TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_validation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            folder_name TEXT,
            image_name TEXT,
            full_path TEXT,
            exists INTEGER,
            error_message TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS browser_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            error_type TEXT,
            error_message TEXT,
            source TEXT,
            lineno INTEGER,
            colno INTEGER,
            stack_trace TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS browser_console_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            log_level TEXT,
            message TEXT,
            source_info TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_load_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            image_url TEXT,
            success INTEGER,
            error_message TEXT,
            http_status INTEGER
        )
    ''')
    
    conn.commit()
    return conn

def log_step(conn, step_name, status, message, details=""):
    """Log a step to the database"""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO execution_log (timestamp, step_name, status, message, details)
        VALUES (?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), step_name, status, message, details))
    conn.commit()
    print(f"[{step_name}] {status}: {message}")

def validate_image_path(conn, folder_name, image_name, base_path):
    """Validate that an image exists and log the result"""
    full_path = base_path / folder_name / image_name
    exists = full_path.exists()
    
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO image_validation (timestamp, folder_name, image_name, full_path, exists, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        folder_name,
        image_name,
        str(full_path),
        1 if exists else 0,
        "" if exists else f"File not found: {full_path}"
    ))
    conn.commit()
    
    return exists

# ========== ERROR COLLECTION HTTP SERVER ==========
class ErrorCollectionHandler(BaseHTTPRequestHandler):
    """HTTP handler that receives browser error logs"""
    
    conn = None
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logs"""
        pass
    
    def do_POST(self):
        """Handle POST requests from browser error logging"""
        if self.path == '/log_error':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                error_data = json.loads(post_data.decode('utf-8'))
                
                if ErrorCollectionHandler.conn:
                    cursor = ErrorCollectionHandler.conn.cursor()
                    cursor.execute('''
                        INSERT INTO browser_errors (timestamp, error_type, error_message, source, lineno, colno, stack_trace)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        datetime.now().isoformat(),
                        error_data.get('type', 'unknown'),
                        error_data.get('message', ''),
                        error_data.get('source', ''),
                        error_data.get('lineno', 0),
                        error_data.get('colno', 0),
                        error_data.get('stack', '')
                    ))
                    ErrorCollectionHandler.conn.commit()
                    print(f"[Browser Error] {error_data.get('type')}: {error_data.get('message', '')[:100]}")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
                
            except Exception as e:
                print(f"Error processing browser log: {e}")
                self.send_response(500)
                self.end_headers()
        
        elif self.path == '/log_console':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                log_data = json.loads(post_data.decode('utf-8'))
                
                if ErrorCollectionHandler.conn:
                    cursor = ErrorCollectionHandler.conn.cursor()
                    cursor.execute('''
                        INSERT INTO browser_console_logs (timestamp, log_level, message, source_info)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        datetime.now().isoformat(),
                        log_data.get('level', 'log'),
                        log_data.get('message', ''),
                        log_data.get('source', '')
                    ))
                    ErrorCollectionHandler.conn.commit()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
                
            except Exception as e:
                self.send_response(500)
                self.end_headers()
        
        elif self.path == '/log_image':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                image_data = json.loads(post_data.decode('utf-8'))
                
                if ErrorCollectionHandler.conn:
                    cursor = ErrorCollectionHandler.conn.cursor()
                    cursor.execute('''
                        INSERT INTO image_load_attempts (timestamp, image_url, success, error_message, http_status)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        datetime.now().isoformat(),
                        image_data.get('url', ''),
                        1 if image_data.get('success') else 0,
                        image_data.get('error', ''),
                        image_data.get('status', 0)
                    ))
                    ErrorCollectionHandler.conn.commit()
                
                self.send_response(200)
                self.end_headers()
                
            except Exception as e:
                self.send_response(500)
                self.end_headers()
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_error_server(conn, port=8001):
    """Start the error collection HTTP server"""
    ErrorCollectionHandler.conn = conn
    server = HTTPServer(('localhost', port), ErrorCollectionHandler)
    print(f"[Error Server] Listening on http://localhost:{port}")
    server.serve_forever()

# ========== MAIN SCRIPT ==========
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('execution_log.txt', mode='w')
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = Path("instagram_posts.db")
CSV_PATH = Path("posts.csv")
OUTPUT_HTML = Path("index_v0009.html")
OUTPUT_JSON = Path("posts_with_authors.json")
ACCOUNT_OWNER = "sav_a_dc3"
DISPLAY_MODE = "username"
BASE_PATH = Path.cwd()

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

def load_posts(conn):
    posts = []
    if DB_PATH.exists():
        logger.info(f"Loading from {DB_PATH}")
        log_step(conn, "DB_LOAD", "START", f"Loading from {DB_PATH}")
        
        conn_sqlite = sqlite3.connect(DB_PATH)
        conn_sqlite.row_factory = sqlite3.Row
        cur = conn_sqlite.execute("SELECT shortcode, date, likes, comments_count, caption, folder_name FROM posts ORDER BY date DESC")
        rows = cur.fetchall()
        
        for row in rows:
            post = dict(row)
            try:
                comments_rows = conn_sqlite.execute("SELECT comment_text FROM comments WHERE shortcode = ?", (post['shortcode'],)).fetchall()
                post['comments'] = [c['comment_text'] for c in comments_rows]
            except sqlite3.OperationalError:
                post['comments'] = []
            
            folder = Path(post['folder_name'])
            all_media = []
            if folder.exists():
                all_media = sorted([f.name for f in folder.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4')])
                logger.debug(f"Folder {post['folder_name']}: found {len(all_media)} media files")
                
                # Validate each image path
                for media_file in all_media:
                    validate_image_path(conn, post['folder_name'], media_file, BASE_PATH)
            else:
                logger.warning(f"Folder does NOT exist: {post['folder_name']}")
                log_step(conn, "IMAGE_VALIDATION", "WARNING", f"Folder missing: {post['folder_name']}")
            
            post['all_media'] = all_media
            post['instagram_url'] = f"https://www.instagram.com/p/{post['shortcode']}/"
            post['author'] = extract_author_from_comments(post['comments'], post.get('caption', ''))
            posts.append(post)
        
        conn_sqlite.close()
        logger.info(f"Loaded {len(posts)} posts from DB")
        log_step(conn, "DB_LOAD", "COMPLETE", f"Loaded {len(posts)} posts")
        
    elif CSV_PATH.exists():
        logger.info(f"Loading from {CSV_PATH}")
        log_step(conn, "CSV_LOAD", "START", f"Loading from {CSV_PATH}")
        
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
                        for media_file in row['all_media']:
                            validate_image_path(conn, row.get('folder_name', ''), media_file, BASE_PATH)
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
        log_step(conn, "CSV_LOAD", "COMPLETE", f"Loaded {len(posts)} posts")
        
    else:
        logger.error("No database or CSV file found. Cannot continue.")
        log_step(conn, "LOAD", "ERROR", "No database or CSV file found")
        sys.exit(1)
    
    return posts

def add_historic_images(posts, conn):
    timeline_folder = Path("timeline")
    if not timeline_folder.exists():
        logger.info("No timeline/ folder, skipping historic images")
        log_step(conn, "HISTORIC", "SKIP", "No timeline folder")
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
        validate_image_path(conn, "timeline", img_path.name, BASE_PATH)
    
    logger.info(f"Added {len(historic_posts)} historic images from timeline/")
    log_step(conn, "HISTORIC", "COMPLETE", f"Added {len(historic_posts)} historic images")
    return historic_posts + posts

def build_html(posts, conn):
    posts_json = json.dumps(posts, ensure_ascii=False)
    
    log_step(conn, "HTML_BUILD", "START", f"Building HTML with {len(posts)} posts")
    
    # HTML template with embedded error logging JavaScript
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mr. Douglas – Gallery with Error Logging</title>
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
        <strong>🐛 Error Logger Active</strong><br>
        <div id="debugLog"></div>
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
        // Error logging endpoint
        const ERROR_ENDPOINT = 'http://localhost:8001/log_error';
        const CONSOLE_ENDPOINT = 'http://localhost:8001/log_console';
        const IMAGE_ENDPOINT = 'http://localhost:8001/log_image';
        
        // Override console methods to capture all logs
        const originalConsole = {
            log: console.log,
            error: console.error,
            warn: console.warn,
            info: console.info,
            debug: console.debug
        };
        
        function sendToServer(endpoint, data) {
            try {
                fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                }).catch(e => originalConsole.error('Failed to send log:', e));
            } catch(e) {}
        }
        
        function addToDebugPanel(msg, type) {
            const panel = document.getElementById('debugLog');
            if (panel) {
                const entry = document.createElement('div');
                entry.style.color = type === 'error' ? '#ff6b6b' : (type === 'warn' ? '#ffd93d' : '#6bcb77');
                entry.textContent = new Date().toLocaleTimeString() + ' ' + msg;
                panel.appendChild(entry);
                if (panel.children.length > 20) panel.removeChild(panel.children[0]);
            }
        }
        
        console.log = function(...args) {
            const msg = args.join(' ');
            addToDebugPanel(msg, 'info');
            sendToServer(CONSOLE_ENDPOINT, { level: 'log', message: msg, source: 'console.log' });
            originalConsole.log.apply(console, args);
        };
        
        console.error = function(...args) {
            const msg = args.join(' ');
            addToDebugPanel(msg, 'error');
            sendToServer(ERROR_ENDPOINT, { type: 'error', message: msg, source: 'console.error' });
            originalConsole.error.apply(console, args);
        };
        
        console.warn = function(...args) {
            const msg = args.join(' ');
            addToDebugPanel(msg, 'warn');
            sendToServer(CONSOLE_ENDPOINT, { level: 'warn', message: msg, source: 'console.warn' });
            originalConsole.warn.apply(console, args);
        };
        
        // Global error handler
        window.onerror = function(message, source, lineno, colno, error) {
            console.error(`Global Error: ${message} at ${source}:${lineno}:${colno}`);
            sendToServer(ERROR_ENDPOINT, {
                type: 'uncaught',
                message: message,
                source: source,
                lineno: lineno,
                colno: colno,
                stack: error ? error.stack : ''
            });
            return false;
        };
        
        // Image load error tracking
        function trackImageLoad(imgElement, src) {
            imgElement.onerror = function() {
                console.error(`Image failed to load: ${src}`);
                sendToServer(IMAGE_ENDPOINT, { url: src, success: false, error: 'load_failed' });
            };
            imgElement.onload = function() {
                console.log(`Image loaded successfully: ${src}`);
                sendToServer(IMAGE_ENDPOINT, { url: src, success: true });
            };
        }
        
        console.log("=== GALLERY INITIALIZATION STARTED ===");
        console.log("Error logging enabled - sending to port 8001");
        
        const allPosts = """ + posts_json + """;
        const DISPLAY_MODE = \"""" + DISPLAY_MODE + """\";
        
        console.log(`Loaded ${allPosts.length} posts`);
        
        function showToast(msg, dur) {
            dur = dur || 2000;
            var t = document.getElementById('toast');
            t.textContent = msg;
            t.classList.add('show');
            setTimeout(function() { t.classList.remove('show'); }, dur);
        }
        
        function getMediaPath(folder, file) {
            const path = folder + '/' + file;
            console.log(`[Media Path] ${path}`);
            return path;
        }
        
        function renderGallery(posts) {
            console.log(`[Render] Rendering ${posts.length} posts`);
            var grid = document.getElementById('galleryGrid');
            if (!posts.length) { 
                grid.innerHTML = '<div class="no-results">No posts match your search.</div>'; 
                console.warn('[Render] No posts to display');
                return; 
            }
            
            var html = '';
            for (var idx = 0; idx < posts.length; idx++) {
                var post = posts[idx];
                console.log(`[Render] Processing post ${idx}: ${post.shortcode} - folder: ${post.folder_name}`);
                
                var pm = post.all_media.length ? post.all_media[0] : null;
                var carItems = '';
                
                for (var i = 1; i < post.all_media.length; i++) {
                    var f = post.all_media[i];
                    var p = getMediaPath(post.folder_name, f);
                    carItems += '<img class="carousel-item" src="' + p + '" data-media="' + p + '" loading="lazy">';
                }
                
                var mediaHtml = '';
                if (pm) {
                    var mp = getMediaPath(post.folder_name, pm);
                    console.log(`[Render] Main image path: ${mp}`);
                    mediaHtml = '<img class="card-media" src="' + mp + '" loading="lazy" onerror="console.error(\'Main image failed: ' + mp + '\');">';
                } else {
                    mediaHtml = '<div class="card-media" style="display:flex; align-items:center; justify-content:center;">No media</div>';
                    console.warn(`[Render] No media for post ${post.shortcode}`);
                }
                
                var authorDisplay = '<span class="author-name">@' + post.author + '</span>';
                var captionText = post.caption.length > 180 ? post.caption.substring(0,180) + '…' : post.caption;
                
                html += '<div class="card" data-shortcode="' + post.shortcode + '" data-caption="' + post.caption.replace(/"/g, '&quot;') + '">';
                html += '<div style="position:relative; width:100%; aspect-ratio:4/3;">' + mediaHtml + '</div>';
                html += '<div class="card-content">';
                html += '<div class="card-meta"><span>' + authorDisplay + '</span><span>' + new Date(post.date).toLocaleDateString() + '</span><span>' + post.likes + ' likes</span><span>' + post.comments_count + ' comments</span></div>';
                html += '<div class="card-caption">' + captionText + '</div>';
                if (carItems) html += '<div class="carousel">' + carItems + '</div>';
                html += '<div class="card-footer"><a href="' + post.instagram_url + '" target="_blank" class="insta-link">View on Instagram</a>';
                html += '<button class="comments-btn" data-shortcode="' + post.shortcode + '">' + post.comments.length + ' comments</button></div></div></div>';
            }
            
            grid.innerHTML = html;
            console.log('[Render] Gallery rendering complete');
            attachCommentListeners();
            attachCarouselListeners();
            addCheckboxesToCards();
        }
        
        function attachCommentListeners() {
            var btns = document.querySelectorAll('.comments-btn');
            console.log(`[Attach] Found ${btns.length} comment buttons`);
            for (var i = 0; i < btns.length; i++) {
                btns[i].onclick = commentHandler;
            }
        }
        
        function commentHandler(e) {
            e.stopPropagation();
            var sc = this.dataset.shortcode;
            for (var i = 0; i < allPosts.length; i++) {
                if (allPosts[i].shortcode === sc) {
                    var commentsHtml = '';
                    for (var j = 0; j < allPosts[i].comments.length; j++) {
                        commentsHtml += '<div class="comment-item">' + allPosts[i].comments[j] + '</div>';
                    }
                    document.getElementById('commentsList').innerHTML = commentsHtml;
                    document.getElementById('commentsModal').classList.add('active');
                    return;
                }
            }
            showToast('No comments for this post.');
        }
        
        function attachCarouselListeners() {
            var items = document.querySelectorAll('.carousel-item');
            console.log(`[Attach] Found ${items.length} carousel items`);
            for (var i = 0; i < items.length; i++) {
                items[i].onclick = carouselHandler;
                // Track image loads
                trackImageLoad(items[i], items[i].src);
            }
        }
        
        function carouselHandler(e) {
            e.stopPropagation();
            var media = this.dataset.media;
            var card = this.closest('.card');
            var caption = card.dataset.caption;
            openLightbox(media, caption);
        }
        
        function openLightbox(src, caption) {
            console.log(`[Lightbox] Opening: ${src}`);
            var c = document.getElementById('lightboxMediaContainer');
            c.innerHTML = '';
            var img = document.createElement('img');
            img.src = src;
            img.style.maxWidth = '90vw';
            img.style.maxHeight = '85vh';
            trackImageLoad(img, src);
            c.appendChild(img);
            document.getElementById('lightboxCaption').innerText = caption;
            document.getElementById('lightbox').classList.add('active');
        }
        
        function updateWordCloud(posts) {
            console.log(`[WordCloud] Generating from ${posts.length} posts`);
            var wc = {};
            for (var i = 0; i < posts.length; i++) {
                var text = posts[i].caption + ' ' + posts[i].comments.join(' ');
                var words = text.toLowerCase().match(/\\b[a-z]+\\b/g) || [];
                for (var j = 0; j < words.length; j++) {
                    var w = words[j];
                    if (w.length > 2 && !/^(a|an|and|the|of|to|in|for|on|with|by|at|is|it|that|this|are|was|were|be|been|being|have|has|had|having|do|does|did|doing|but|or|so|for|not|can|will|just|like|get|put|up|down|out|over|under|again|then|once|here|there|all|any|both|each|few|more|most|other|some|such|no|nor|only|own|same|than|too|very|i|you|he|she|it|we|they|me|him|her|us|them|my|your|his|her|its|our|their|what|which|who|whom|whose|these|those|am|been|were|www|com|https|http|instagram)$/.test(w)) {
                        wc[w] = (wc[w] || 0) + 1;
                    }
                }
            }
            var wordList = [];
            for (var word in wc) { wordList.push({word: word, count: wc[word]}); }
            wordList.sort(function(a,b) { return b.count - a.count; });
            wordList = wordList.slice(0, 100);
            var maxF = wordList.length ? wordList[0].count : 1;
            var container = document.getElementById('wordcloud');
            if (!wordList.length) { container.innerHTML = '<span>No words found</span>'; return; }
            var cloudHtml = '';
            for (var i = 0; i < wordList.length; i++) {
                var size = 0.8 + (wordList[i].count / maxF) * 1.5;
                cloudHtml += '<span class="cloud-word" data-word="' + wordList[i].word + '" style="font-size:' + size + 'rem;">' + wordList[i].word + '</span>';
            }
            container.innerHTML = cloudHtml;
            var cloudWords = document.querySelectorAll('.cloud-word');
            for (var i = 0; i < cloudWords.length; i++) {
                cloudWords[i].onclick = function() {
                    document.getElementById('searchInput').value = this.dataset.word;
                    var e = new Event('input', {bubbles: true});
                    document.getElementById('searchInput').dispatchEvent(e);
                };
            }
            console.log(`[WordCloud] Generated ${wordList.length} words`);
        }
        
        var debounceTimer;
        document.getElementById('searchInput').addEventListener('input', function(e) {
            clearTimeout(debounceTimer);
            var q = e.target.value.trim().toLowerCase();
            debounceTimer = setTimeout(function() {
                var filtered = [];
                for (var i = 0; i < allPosts.length; i++) {
                    if (allPosts[i].caption.toLowerCase().indexOf(q) !== -1) {
                        filtered.push(allPosts[i]);
                    }
                }
                console.log(`[Search] Filtered to ${filtered.length} posts for query: "${q}"`);
                renderGallery(filtered);
                updateWordCloud(filtered);
            }, 200);
        });
        
        document.getElementById('lightboxClose').onclick = function() { document.getElementById('lightbox').classList.remove('active'); };
        document.getElementById('modalClose').onclick = function() { document.getElementById('commentsModal').classList.remove('active'); };
        window.onclick = function(e) {
            if (e.target === document.getElementById('lightbox')) document.getElementById('lightbox').classList.remove('active');
            if (e.target === document.getElementById('commentsModal')) document.getElementById('commentsModal').classList.remove('active');
        };
        
        document.getElementById('galleryGrid').onclick = function(e) {
            var card = e.target.closest('.card');
            if (card && !e.target.closest('.carousel-item') && !e.target.closest('.comments-btn') && !e.target.closest('a')) {
                var media = null;
                var img = card.querySelector('.card-media');
                if (img && img.tagName === 'IMG') media = img.src;
                openLightbox(media, card.dataset.caption);
            }
        };
        
        // Storyboard (simplified for debugging)
        var canvas = null;
        var storyboardImages = [];
        var STORAGE_KEY = "storyboard_images_srcs";
        var PREVIEW_W = 1080, PREVIEW_H = 1440, TARGET_W = 10800, TARGET_H = 14400, SCALE = TARGET_W / PREVIEW_W;
        var currentTemplate = 'grid';
        var selectedSrcs = new Set();
        
        function updateStoryboardBadge() {
            var b = document.getElementById('storyboardCountBadge');
            if (b) b.innerText = storyboardImages.length;
        }
        
        function addImageToStoryboard(src, silent) {
            silent = silent || false;
            for (var i = 0; i < storyboardImages.length; i++) {
                if (storyboardImages[i].src === src) {
                    if (!silent) showToast("Image already in storyboard");
                    return Promise.resolve(false);
                }
            }
            console.log(`[Storyboard] Adding image: ${src}`);
            return new Promise(function(resolve) {
                fabric.Image.fromURL(src, function(img) {
                    if (!img) {
                        console.error(`[Storyboard] Failed to load image: ${src}`);
                        if (!silent) showToast("Failed to load image");
                        resolve(false);
                        return;
                    }
                    img.set({ crossOrigin: 'Anonymous', hasControls: true, hasBorders: true, lockRotation: true });
                    storyboardImages.push({ src: src, fabricObj: img, originalWidth: img.width, originalHeight: img.height });
                    if (canvas) {
                        canvas.add(img);
                        applyLayout(currentTemplate);
                        updateThumbnails();
                        saveToLocalStorage();
                        updateStoryboardBadge();
                    }
                    resolve(true);
                }, { crossOrigin: 'Anonymous' });
            });
        }
        
        function addMultipleImages(srcList) {
            var added = 0;
            var promises = [];
            for (var i = 0; i < srcList.length; i++) {
                promises.push(addImageToStoryboard(srcList[i], true));
            }
            Promise.all(promises).then(function(results) {
                for (var i = 0; i < results.length; i++) if (results[i]) added++;
                if (added) showToast("Added " + added + " image(s)");
            });
        }
        
        function syncSelectedToStoryboard() {
            var srcs = Array.from(selectedSrcs);
            if (srcs.length === 0) { showToast("No images selected"); return; }
            addMultipleImages(srcs);
        }
        
        function applyLayout(templateName) {
            if (!canvas || storyboardImages.length === 0) return;
            currentTemplate = templateName;
            var margin = 20;
            var availW = PREVIEW_W - margin * 2;
            var availH = PREVIEW_H - margin * 2;
            var cnt = storyboardImages.length;
            
            function getObjHeight(obj) { return obj.height * obj.scaleY; }
            function getObjWidth(obj) { return obj.width * obj.scaleX; }
            
            function placeInGrid(cols, maxHeightPerRow) {
                var y = margin;
                for (var i = 0; i < cnt; i++) {
                    var obj = storyboardImages[i].fabricObj;
                    var col = i % cols;
                    if (col === 0 && i !== 0) {
                        var rowMax = 0;
                        for (var j = i - cols; j < i; j++) {
                            rowMax = Math.max(rowMax, getObjHeight(storyboardImages[j].fabricObj));
                        }
                        y += rowMax + margin;
                    }
                    var cellW = (availW - (cols - 1) * margin) / cols;
                    var scale = Math.min(cellW / obj.width, maxHeightPerRow / obj.height);
                    obj.scale(scale);
                    var left = margin + col * (cellW + margin);
                    var top = y;
                    obj.set({ left: left, top: top });
                }
            }
            
            if (templateName === 'center') {
                var obj = storyboardImages[0].fabricObj;
                var scale = Math.min(availW / obj.width, availH / obj.height);
                obj.scale(scale);
                obj.set({ left: margin + (availW - getObjWidth(obj)) / 2, top: margin + (availH - getObjHeight(obj)) / 2 });
            } else if (templateName === 'twoCol') {
                placeInGrid(2, 300);
            } else {
                placeInGrid(3, 200);
            }
            canvas.renderAll();
            saveToLocalStorage();
        }
        
        function clearAll() {
            if (confirm("Clear all images from storyboard?")) {
                for (var i = 0; i < storyboardImages.length; i++) {
                    canvas.remove(storyboardImages[i].fabricObj);
                }
                storyboardImages = [];
                canvas.renderAll();
                updateThumbnails();
                localStorage.removeItem(STORAGE_KEY);
                updateStoryboardBadge();
                showToast("Storyboard cleared");
            }
        }
        
        function exportStoryboard() {
            if (storyboardImages.length === 0) { showToast("No images to export"); return; }
            var offCanvas = document.createElement('canvas');
            offCanvas.width = TARGET_W;
            offCanvas.height = TARGET_H;
            var offCtx = offCanvas.getContext('2d');
            offCtx.fillStyle = 'white';
            offCtx.fillRect(0, 0, TARGET_W, TARGET_H);
            for (var i = 0; i < storyboardImages.length; i++) {
                var obj = storyboardImages[i].fabricObj;
                var left = obj.left * SCALE;
                var top = obj.top * SCALE;
                var width = obj.width * obj.scaleX * SCALE;
                var height = obj.height * obj.scaleY * SCALE;
                offCtx.drawImage(obj._element, left, top, width, height);
            }
            var a = document.createElement('a');
            a.download = 'storyboard.png';
            a.href = offCanvas.toDataURL('image/png');
            a.click();
        }
        
        function updateThumbnails() {
            var container = document.getElementById('storyboardThumbnails');
            if (!container) return;
            var html = '';
            for (var i = 0; i < storyboardImages.length; i++) {
                html += '<img class="storyboard-thumb" src="' + storyboardImages[i].src + '" data-index="' + i + '" style="width:80px; height:80px; object-fit:cover; border-radius:8px; cursor:pointer; margin-right:8px;">';
            }
            container.innerHTML = html;
            var thumbs = document.querySelectorAll('.storyboard-thumb');
            for (var i = 0; i < thumbs.length; i++) {
                thumbs[i].onclick = function() {
                    var idx = parseInt(this.dataset.index);
                    if (!isNaN(idx)) {
                        canvas.remove(storyboardImages[idx].fabricObj);
                        storyboardImages.splice(idx, 1);
                        canvas.renderAll();
                        updateThumbnails();
                        saveToLocalStorage();
                        updateStoryboardBadge();
                        showToast("Image removed");
                    }
                };
            }
        }
        
        function saveToLocalStorage() {
            var srcs = [];
            for (var i = 0; i < storyboardImages.length; i++) srcs.push(storyboardImages[i].src);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(srcs));
        }
        
        function loadFromLocalStorage() {
            var stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                try {
                    var srcs = JSON.parse(stored);
                    if (srcs && srcs.length) {
                        var promises = [];
                        for (var i = 0; i < srcs.length; i++) {
                            (function(src) {
                                promises.push(new Promise(function(resolve) {
                                    fabric.Image.fromURL(src, function(img) {
                                        if (img) {
                                            img.set({ crossOrigin: 'Anonymous', hasControls: true, hasBorders: true, lockRotation: true });
                                            storyboardImages.push({ src: src, fabricObj: img, originalWidth: img.width, originalHeight: img.height });
                                            if (canvas) canvas.add(img);
                                        }
                                        resolve();
                                    }, { crossOrigin: 'Anonymous' });
                                }));
                            })(srcs[i]);
                        }
                        Promise.all(promises).then(function() {
                            if (canvas) {
                                applyLayout(currentTemplate);
                                updateThumbnails();
                                updateStoryboardBadge();
                            }
                        });
                    }
                } catch(e) { console.warn(e); }
            }
        }
        
        function initCanvas() {
            var canvasEl = document.getElementById('storyboardCanvas');
            if (!canvasEl) return;
            if (canvas) canvas.dispose();
            canvas = new fabric.Canvas('storyboardCanvas');
            canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
            canvas.backgroundColor = 'white';
            canvas.on('object:modified', function() { saveToLocalStorage(); });
            canvas.on('object:added', function() { saveToLocalStorage(); });
            canvas.on('object:removed', function() { saveToLocalStorage(); });
            canvas.renderAll();
            for (var i = 0; i < storyboardImages.length; i++) {
                canvas.add(storyboardImages[i].fabricObj);
            }
            canvas.renderAll();
            console.log('[Canvas] Initialized');
        }
        
        function addCheckboxesToCards() {
            var cards = document.querySelectorAll('.card');
            console.log(`[Checkbox] Adding to ${cards.length} cards`);
            for (var i = 0; i < cards.length; i++) {
                var card = cards[i];
                if (card.querySelector('.select-checkbox')) continue;
                var img = card.querySelector('img');
                if (!img || !img.src || img.src.startsWith('data:')) continue;
                var src = img.src;
                var chk = document.createElement('input');
                chk.type = 'checkbox';
                chk.className = 'select-checkbox';
                chk.checked = selectedSrcs.has(src);
                chk.onclick = function(e) { e.stopPropagation(); };
                chk.onchange = function(e) {
                    e.stopPropagation();
                    var isChecked = this.checked;
                    var imageSrc = this.parentElement.querySelector('img').src;
                    if (isChecked) {
                        selectedSrcs.add(imageSrc);
                        addImageToStoryboard(imageSrc, true);
                    } else {
                        selectedSrcs.delete(imageSrc);
                    }
                    var span = document.getElementById('selectedCount');
                    if (span) span.innerText = selectedSrcs.size + ' selected';
                };
                if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
                card.appendChild(chk);
            }
        }
        
        function selectAll() {
            var checkboxes = document.querySelectorAll('.select-checkbox');
            for (var i = 0; i < checkboxes.length; i++) checkboxes[i].checked = true;
            selectedSrcs.clear();
            var images = document.querySelectorAll('.card img');
            for (var i = 0; i < images.length; i++) {
                if (images[i].src && !images[i].src.startsWith('data:')) selectedSrcs.add(images[i].src);
            }
            var span = document.getElementById('selectedCount');
            if (span) span.innerText = selectedSrcs.size + ' selected';
            addMultipleImages(Array.from(selectedSrcs));
        }
        
        function deselectAll() {
            var checkboxes = document.querySelectorAll('.select-checkbox');
            for (var i = 0; i < checkboxes.length; i++) checkboxes[i].checked = false;
            selectedSrcs.clear();
            var span = document.getElementById('selectedCount');
            if (span) span.innerText = '0 selected';
        }
        
        function openStoryboardNewTab() {
            var srcs = [];
            for (var i = 0; i < storyboardImages.length; i++) srcs.push(storyboardImages[i].src);
            var w = window.open();
            if (!w) { showToast("Popup blocked"); return; }
            var htmlContent = '<!DOCTYPE html><html><head><title>Storyboard</title><style>body{margin:0;background:#0f172a;color:white;}canvas{display:block;margin:20px auto;border:2px solid #475569;background:white;}.controls{text-align:center;padding:10px;}button{margin:5px;padding:8px 16px;background:#3b82f6;border:none;color:white;border-radius:8px;cursor:pointer;}</style><script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"><\/script></head><body><div class="controls"><button id="exportBtn">Export PNG</button><button id="closeBtn" onclick="window.close()">Close</button></div><canvas id="storyboardCanvasNew" width="1080" height="1440"></canvas><script>var srcs = ' + JSON.stringify(srcs) + ';
                var canvas, images = [];
                var PREVIEW_W=1080, PREVIEW_H=1440, TARGET_W=10800, TARGET_H=14400, SCALE=TARGET_W/PREVIEW_W;
                function loadAll() {
                    if(!srcs.length) return;
                    var loaded = 0;
                    for(var i=0;i<srcs.length;i++) {
                        fabric.Image.fromURL(srcs[i], function(img) {
                            if(!img) return;
                            img.set({ hasControls: true, lockRotation: true });
                            images.push(img);
                            loaded++;
                            if(loaded === srcs.length) drawCanvas();
                        }, { crossOrigin: "Anonymous" });
                    }
                }
                function drawCanvas() {
                    canvas = new fabric.Canvas("storyboardCanvasNew");
                    canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
                    canvas.backgroundColor = "white";
                    var margin = 20, w = PREVIEW_W - margin*2, cols = 3, cellW = (w - (cols-1)*margin) / cols;
                    var y = margin;
                    for(var i=0;i<images.length;i++) {
                        var img = images[i];
                        var col = i%cols;
                        if(col===0 && i!==0) {
                            var rowMax = 0;
                            for(var j=i-cols; j<i; j++) rowMax = Math.max(rowMax, images[j].height * images[j].scaleY);
                            y += rowMax + margin;
                        }
                        var scale = Math.min(cellW / img.width, 200 / img.height);
                        img.scale(scale);
                        img.set({ left: margin + col*(cellW+margin), top: y });
                        canvas.add(img);
                    }
                    canvas.renderAll();
                }
                document.getElementById("exportBtn").onclick = function() {
                    if(!images.length) return;
                    var off = document.createElement("canvas");
                    off.width = TARGET_W;
                    off.height = TARGET_H;
                    var ctx = off.getContext("2d");
                    ctx.fillStyle = "white";
                    ctx.fillRect(0,0,TARGET_W,TARGET_H);
                    for(var i=0;i<images.length;i++) {
                        var img = images[i];
                        var left = img.left * SCALE;
                        var top = img.top * SCALE;
                        var w = img.width * img.scaleX * SCALE;
                        var h = img.height * img.scaleY * SCALE;
                        ctx.drawImage(img._element, left, top, w, h);
                    }
                    var a = document.createElement("a");
                    a.download = "storyboard.png";
                    a.href = off.toDataURL("image/png");
                    a.click();
                };
                loadAll();<\/script></body></html>';
            w.document.write(htmlContent);
            w.document.close();
        }
        
        (function init() {
            console.log('[Init] Starting initialization');
            initCanvas();
            loadFromLocalStorage();
            renderGallery(allPosts);
            updateWordCloud(allPosts);
            addCheckboxesToCards();
            
            document.getElementById('selectAllBtn').onclick = selectAll;
            document.getElementById('deselectAllBtn').onclick = deselectAll;
            document.getElementById('syncSelectedBtn').onclick = syncSelectedToStoryboard;
            document.getElementById('openStoryboardBtn').onclick = function() { document.getElementById('storyboardModal').classList.add('active'); };
            document.getElementById('closeStoryboardBtn').onclick = function() { document.getElementById('storyboardModal').classList.remove('active'); };
            document.getElementById('exportStoryboardBtn').onclick = exportStoryboard;
            document.getElementById('clearStoryboardBtn').onclick = clearAll;
            document.getElementById('applyTemplateBtn').onclick = function() {
                var tpl = document.getElementById('templateSelect').value;
                applyLayout(tpl);
            };
            document.getElementById('openStoryboardNewTabBtn').onclick = openStoryboardNewTab;
            window.onclick = function(e) {
                if (e.target === document.getElementById('storyboardModal')) document.getElementById('storyboardModal').classList.remove('active');
            };
            updateStoryboardBadge();
            console.log('[Init] Initialization complete');
            showToast('Gallery loaded - check debug panel for errors');
        })();
    </script>
</body>
</html>"""
    
    log_step(conn, "HTML_BUILD", "COMPLETE", f"HTML built successfully")
    return html_template

def extract_logs_from_db(conn):
    """Extract all logs from database and save to text files"""
    cursor = conn.cursor()
    
    # Extract execution logs
    cursor.execute("SELECT * FROM execution_log ORDER BY id")
    execution_logs = cursor.fetchall()
    
    with open('execution_log_export.txt', 'w') as f:
        f.write("=== EXECUTION LOGS ===\n")
        for log in execution_logs:
            f.write(f"{log[1]} | {log[2]} | {log[3]} | {log[4]} | {log[5]}\n")
    
    # Extract image validation logs
    cursor.execute("SELECT * FROM image_validation ORDER BY id")
    image_logs = cursor.fetchall()
    
    with open('image_validation_export.txt', 'w') as f:
        f.write("=== IMAGE VALIDATION LOGS ===\n")
        for log in image_logs:
            f.write(f"{log[1]} | {log[2]} | {log[3]} | EXISTS:{log[5]} | {log[6]}\n")
    
    # Count failed images
    cursor.execute("SELECT COUNT(*) FROM image_validation WHERE exists = 0")
    failed_count = cursor.fetchone()[0]
    
    print(f"\n=== LOG EXTRACTION COMPLETE ===")
    print(f"Execution logs: {len(execution_logs)} entries")
    print(f"Image validations: {len(image_logs)} entries")
    print(f"Failed images: {failed_count}")
    print(f"\nExported to:")
    print(f"  - execution_log_export.txt")
    print(f"  - image_validation_export.txt")
    print(f"  - gallery_errors.db (SQLite database)")
    
    return failed_count

def main():
    print("=" * 60)
    print("MR. DOUGLAS GALLERY BUILDER v0009")
    print("With Automatic Error Logging")
    print("=" * 60)
    
    # Initialize database
    conn = init_error_db()
    log_step(conn, "START", "INFO", "Gallery build started")
    
    # Load posts
    posts = load_posts(conn)
    posts = add_historic_images(posts, conn)
    
    # Save JSON
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {OUTPUT_JSON}")
    log_step(conn, "JSON_SAVE", "COMPLETE", f"Saved {OUTPUT_JSON}")
    
    # Build HTML
    html = build_html(posts, conn)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    logger.info(f"Generated {OUTPUT_HTML.resolve()}")
    log_step(conn, "HTML_SAVE", "COMPLETE", f"Generated {OUTPUT_HTML}")
    
    # Final summary
    logger.info(f"Total posts: {len(posts)}")
    logger.info(f"Author display mode: {DISPLAY_MODE}")
    log_step(conn, "COMPLETE", "INFO", f"Build complete. Total posts: {len(posts)}")
    
    # Extract logs
    failed_images = extract_logs_from_db(conn)
    
    # Close database
    conn.close()
    
    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    print(f"\nTo view the gallery:")
    print(f"1. Start the main HTTP server: python -m http.server 8000")
    print(f"2. Start the error collection server: python -c \"from build_final_gallery_v0009 import start_error_server, init_error_db; import threading; conn = init_error_db(); threading.Thread(target=start_error_server, args=(conn, 8001), daemon=True).start(); input('Error server running. Press Enter to stop...')\"")
    print(f"3. Open: http://localhost:8000/{OUTPUT_HTML.name}")
    print(f"\nError logs are saved to:")
    print(f"  - gallery_errors.db (SQLite)")
    print(f"  - execution_log_export.txt")
    print(f"  - image_validation_export.txt")
    print(f"\nFailed images found: {failed_images}")
    
    if failed_images > 0:
        print(f"\n⚠️ WARNING: {failed_images} images failed validation. Check image_validation_export.txt")

if __name__ == "__main__":
    main()