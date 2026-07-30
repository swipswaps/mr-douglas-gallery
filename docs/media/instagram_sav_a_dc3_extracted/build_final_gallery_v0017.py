#!/usr/bin/env python3
"""
build_final_gallery_v0017.py

AUTOMATIC - Does everything in one command:
- Starts error server (port 8001) in background
- Starts HTTP server (port 8000) in background  
- Opens browser automatically
- Captures ALL logs to database
- No manual terminal juggling required
"""

import json
import sqlite3
import csv
import re
import sys
import logging
import subprocess
import threading
import time
import webbrowser
import os
import signal
import atexit
from collections import Counter
from pathlib import Path

# ========== LOGGING SETUP ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== CONFIGURATION ==========
DB_PATH = Path("instagram_posts.db")
CSV_PATH = Path("posts.csv")
OUTPUT_HTML = Path("index_v0017.html")
OUTPUT_JSON = Path("posts_with_authors.json")
ACCOUNT_OWNER = "sav_a_dc3"
DISPLAY_MODE = "username"
BASE_PATH = Path.cwd()

# Global process holders for cleanup
processes = []

def cleanup():
    """Terminate all background processes on exit"""
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=2)
        except:
            try:
                p.kill()
            except:
                pass
    logger.info("All background processes terminated")

atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda s, f: cleanup() or sys.exit(0))
signal.signal(signal.SIGTERM, lambda s, f: cleanup() or sys.exit(0))

def start_error_server():
    """Start error_server.py in background"""
    try:
        # Check if already running
        import urllib.request
        try:
            urllib.request.urlopen('http://localhost:8001/health', timeout=0.5)
            logger.info("Error server already running on port 8001")
            return True
        except:
            pass
        
        # Start error server process
        p = subprocess.Popen(
            [sys.executable, 'run_error_server.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        processes.append(p)
        
        # Wait for it to start
        time.sleep(2)
        logger.info(f"Error server started (PID: {p.pid}) on port 8001")
        return True
    except Exception as e:
        logger.warning(f"Could not start error server: {e}")
        return False

def start_http_server():
    """Start HTTP server in background"""
    try:
        # Check if already running
        import urllib.request
        try:
            urllib.request.urlopen('http://localhost:8000/', timeout=0.5)
            logger.info("HTTP server already running on port 8000")
            return True
        except:
            pass
        
        # Start HTTP server process
        p = subprocess.Popen(
            [sys.executable, '-m', 'http.server', '8000'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        processes.append(p)
        
        # Wait for it to start
        time.sleep(2)
        logger.info(f"HTTP server started (PID: {p.pid}) on port 8000")
        return True
    except Exception as e:
        logger.warning(f"Could not start HTTP server: {e}")
        return False

def open_browser(url):
    """Open browser after delay"""
    time.sleep(3)
    webbrowser.open(url)
    logger.info(f"Browser opened: {url}")

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
        return ACCOUNT_OWNER
    counter = Counter(filtered)
    return counter.most_common(1)[0][0]

def load_posts(db_conn=None):
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
            post['all_media'] = all_media
            post['instagram_url'] = f"https://www.instagram.com/p/{post['shortcode']}/"
            post['author'] = extract_author_from_comments(post['comments'], post.get('caption', ''))
            posts.append(post)
        
        conn.close()
        logger.info(f"Loaded {len(posts)} posts")
    return posts

def add_historic_images(posts):
    timeline_folder = Path("timeline")
    if timeline_folder.exists():
        for img_path in sorted(timeline_folder.glob("*.jpg")):
            year_match = re.search(r'\b(19|20)\d{2}\b', img_path.stem)
            year = year_match.group(0) if year_match else "0000"
            title = img_path.stem.replace('-', ' ').replace('_', ' ').title()
            posts.append({
                "shortcode": f"hist_{img_path.stem}",
                "date": f"{year}-07-01 12:00:00",
                "likes": 0,
                "comments_count": 0,
                "caption": f"{title} – Historic photo",
                "folder_name": "timeline",
                "all_media": [img_path.name],
                "comments": [],
                "instagram_url": "#",
                "author": "Historic"
            })
        logger.info(f"Added historic images")
    return posts

def build_html(posts, error_server_available, http_server_available):
    posts_json = json.dumps(posts, ensure_ascii=False)
    
    html = '<!DOCTYPE html>\n'
    html += '<html lang="en">\n<head>\n'
    html += '<meta charset="UTF-8">\n'
    html += '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    html += '<title>Mr. Douglas Gallery v0017 - Auto Server</title>\n'
    
    html += '<style>\n'
    html += '*{box-sizing:border-box}body{margin:0;background:#0f172a;color:#e2e8f0;font-family:system-ui}\n'
    html += '.search-header{position:sticky;top:0;z-index:20;background:rgba(15,23,42,0.95);backdrop-filter:blur(8px);border-bottom:1px solid #334155;padding:1rem}\n'
    html += '.search-container{max-width:1200px;margin:0 auto}\n'
    html += '.search-input{width:100%;padding:0.75rem 1rem;background:#1e293b;border:1px solid #475569;border-radius:2rem;color:#f1f5f9}\n'
    html += '.wordcloud-container{background:#1e293b;border-radius:1rem;padding:1rem;margin-top:1rem}\n'
    html += '.wordcloud{display:flex;flex-wrap:wrap;gap:0.5rem 1rem;justify-content:center;max-height:200px;overflow-y:auto}\n'
    html += '.cloud-word{cursor:pointer;color:#94a3b8}.cloud-word:hover{color:#60a5fa}\n'
    html += '.gallery-toolbar{position:sticky;top:90px;z-index:15;display:flex;gap:12px;margin:0 1.5rem 1rem;flex-wrap:wrap;align-items:center;background:#1e293b;padding:8px 12px;border-radius:12px}\n'
    html += '.gallery-toolbar button{background:#334155;color:white;border:none;padding:6px 12px;border-radius:8px;cursor:pointer}\n'
    html += '.gallery-toolbar button.primary{background:#3b82f6}\n'
    html += '.status-indicator{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}\n'
    html += '.status-on{background:#10b981;box-shadow:0 0 4px #10b981}\n'
    html += '.status-off{background:#ef4444;box-shadow:0 0 4px #ef4444}\n'
    html += '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1.5rem;padding:1.5rem;max-width:1400px;margin:0 auto}\n'
    html += '.card{background:#1e293b;border-radius:1rem;overflow:hidden;cursor:pointer;position:relative}\n'
    html += '.card:hover{transform:translateY(-4px)}\n'
    html += '.card-media{width:100%;aspect-ratio:4/3;object-fit:cover;background:#0f172a}\n'
    html += '.video-placeholder{width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:#1e293b;font-size:2rem}\n'
    html += '.card-content{padding:1rem}\n'
    html += '.card-meta{display:flex;justify-content:space-between;font-size:0.75rem;color:#94a3b8;margin-bottom:0.5rem;flex-wrap:wrap}\n'
    html += '.author-initial{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;background:#3b82f6;color:white;border-radius:50%;font-size:0.8rem;font-weight:bold}\n'
    html += '.author-name{color:#60a5fa}\n'
    html += '.card-caption{font-size:0.875rem;color:#cbd5e1;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;margin-bottom:0.75rem}\n'
    html += '.carousel{display:flex;gap:0.5rem;overflow-x:auto;margin:0.5rem 0}\n'
    html += '.carousel-item{width:60px;height:60px;object-fit:cover;border-radius:8px;cursor:pointer;background:#0f172a}\n'
    html += '.carousel-video-placeholder{width:60px;height:60px;background:#1e293b;border-radius:8px;display:flex;align-items:center;justify-content:center;cursor:pointer}\n'
    html += '.comments-btn{background:none;border:none;color:#3b82f6;cursor:pointer;font-size:0.7rem;padding:0.25rem 0.5rem;border-radius:1rem;background:#1e293b}\n'
    html += '.card-footer{display:flex;justify-content:space-between;align-items:center;margin-top:0.5rem}\n'
    html += '.insta-link{font-size:0.75rem;color:#3b82f6;text-decoration:none}\n'
    html += '.select-checkbox{position:absolute;top:8px;left:8px;width:20px;height:20px;cursor:pointer;z-index:10;background:white;border-radius:4px}\n'
    html += '.lightbox{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);display:none;align-items:center;justify-content:center;z-index:1000}\n'
    html += '.lightbox.active{display:flex}\n'
    html += '.lightbox-content{position:relative;max-width:90vw;max-height:90vh}\n'
    html += '.lightbox-close{position:absolute;top:10px;right:10px;color:white;font-size:2rem;cursor:pointer;background:rgba(0,0,0,0.5);width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center}\n'
    html += '.modal{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1e293b;border-radius:1rem;max-width:600px;width:90%;max-height:80vh;overflow-y:auto;z-index:1100;display:none;padding:1rem}\n'
    html += '.modal.active{display:block}\n'
    html += '.storyboard-btn{position:fixed;bottom:20px;right:20px;background:#3b82f6;color:white;border:none;border-radius:50px;padding:12px 24px;cursor:pointer;z-index:1000}\n'
    html += '.storyboard-modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:2000;overflow:auto}\n'
    html += '.storyboard-modal.active{display:flex;flex-direction:column}\n'
    html += '.storyboard-container{background:#1e293b;margin:20px auto;padding:20px;border-radius:16px;max-width:95%;width:1200px}\n'
    html += '#storyboardCanvas{border:2px solid #475569;border-radius:8px;background:white;display:block;margin:0 auto}\n'
    html += '.storyboard-controls{display:flex;gap:10px;justify-content:center;margin:15px 0;flex-wrap:wrap}\n'
    html += '.storyboard-controls button{background:#3b82f6;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer}\n'
    html += '.storyboard-controls button.danger{background:#ef4444}\n'
    html += '.storyboard-controls button.success{background:#10b981}\n'
    html += '.storyboard-thumb{width:80px;height:80px;object-fit:cover;border-radius:8px;cursor:pointer;margin-right:8px}\n'
    html += '.toast{position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1e293b;color:#e2e8f0;padding:10px 20px;border-radius:40px;z-index:3000;opacity:0;transition:opacity 0.2s}\n'
    html += '.toast.show{opacity:1}\n'
    html += '.debug-panel{position:fixed;bottom:10px;left:10px;background:#1e293b;color:#0f0;font-family:monospace;font-size:10px;padding:8px;border-radius:8px;z-index:9999;max-width:400px;max-height:200px;overflow:auto;opacity:0.8}\n'
    html += '.no-results{text-align:center;padding:3rem;color:#94a3b8;grid-column:1/-1}\n'
    html += '</style>\n</head>\n<body>\n'
    
    # Debug panel with dual status
    error_status_class = "status-on" if error_server_available else "status-off"
    http_status_class = "status-on" if http_server_available else "status-off"
    html += f'<div class="debug-panel" id="debugPanel">\n'
    html += f'<strong>🐛 Auto-Server Mode</strong><br>\n'
    html += f'<span class="status-indicator {error_status_class}"></span>Error Server: {"ON" if error_server_available else "OFF"} | '
    html += f'<span class="status-indicator {http_status_class}"></span>HTTP Server: {"ON" if http_server_available else "OFF"}\n'
    html += '<div id="debugLog">Initializing...</div>\n'
    html += '</div>\n'
    
    # Search header
    html += '<div class="search-header"><div class="search-container">\n'
    html += '<input type="text" id="searchInput" class="search-input" placeholder="Search posts...">\n'
    html += '<div class="wordcloud-container"><div id="wordcloud" class="wordcloud">Loading words...</div></div>\n'
    html += '</div></div>\n'
    
    # Toolbar
    html += '<div class="gallery-toolbar">\n'
    html += '<span>Select images:</span>\n'
    html += '<button id="selectAllBtn">Select All</button>\n'
    html += '<button id="deselectAllBtn">Deselect All</button>\n'
    html += '<button id="syncSelectedBtn" class="primary">Sync Selected to Storyboard</button>\n'
    html += '<span id="selectedCount">0 selected</span>\n'
    html += '<button id="openStoryboardNewTabBtn" style="background:#10b981;">Open Storyboard in New Tab</button>\n'
    html += '</div>\n'
    
    # Gallery grid
    html += '<div id="galleryGrid" class="grid"></div>\n'
    
    # Storyboard button and modal
    html += '<button class="storyboard-btn" id="openStoryboardBtn">Open Storyboard <span id="storyboardCountBadge">0</span></button>\n'
    html += '<div id="storyboardModal" class="storyboard-modal">\n'
    html += '<div class="storyboard-container">\n'
    html += '<div style="display:flex;justify-content:space-between;"><h3>Storyboard Builder</h3><button class="close-modal" id="closeStoryboardBtn">Close</button></div>\n'
    html += '<div><canvas id="storyboardCanvas" width="1080" height="1440"></canvas></div>\n'
    html += '<div class="storyboard-controls">\n'
    html += '<select id="templateSelect"><option value="grid">Grid (3 cols)</option><option value="twoCol">Two columns</option><option value="center">Single centered</option></select>\n'
    html += '<button id="applyTemplateBtn" class="success">Apply Template</button>\n'
    html += '<button id="exportStoryboardBtn" class="success">Export PNG</button>\n'
    html += '<button id="clearStoryboardBtn" class="danger">Clear All</button>\n'
    html += '</div>\n'
    html += '<div><strong>Images (click to remove):</strong><div id="storyboardThumbnails"></div></div>\n'
    html += '</div></div>\n'
    
    # Toast, lightbox, comments modal
    html += '<div id="toast" class="toast"></div>\n'
    html += '<div id="lightbox" class="lightbox"><div class="lightbox-content"><div class="lightbox-close" id="lightboxClose">×</div><div id="lightboxMediaContainer"></div><div id="lightboxCaption"></div></div></div>\n'
    html += '<div id="commentsModal" class="modal"><div class="modal-header"><strong>Comments</strong><span id="modalClose" class="modal-close">&times;</span></div><div id="commentsList"></div></div>\n'
    
    # Scripts
    html += '<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>\n'
    html += '<script>\n'
    
    # Data injection
    html += 'var allPosts = ' + posts_json + ';\n'
    html += 'var DISPLAY_MODE = "' + DISPLAY_MODE + '";\n'
    html += 'var LOG_SERVER_URL = "http://localhost:8001";\n'
    html += 'var serverAvailable = ' + str(error_server_available).lower() + ';\n'
    
    # Logging functions
    html += 'var debugLog = document.getElementById("debugLog");\n'
    html += 'function addLog(msg, type) {\n'
    html += '  var d = document.createElement("div");\n'
    html += '  var colors = {info: "#6bcb77", warn: "#ffd93d", error: "#ff6b6b"};\n'
    html += '  d.style.color = colors[type] || "#6bcb77";\n'
    html += '  d.textContent = new Date().toLocaleTimeString() + " " + msg;\n'
    html += '  debugLog.appendChild(d);\n'
    html += '  if(debugLog.children.length > 30) debugLog.removeChild(debugLog.children[0]);\n'
    html += '  console.log(msg);\n'
    html += '  if(serverAvailable) {\n'
    html += '    fetch(LOG_SERVER_URL + "/log_console", {\n'
    html += '      method: "POST",\n'
    html += '      headers: {"Content-Type": "application/json"},\n'
    html += '      body: JSON.stringify({level: "log", message: msg, source: "browser"})\n'
    html += '    }).catch(function(e){ console.warn("Log send failed:", e); });\n'
    html += '  }\n'
    html += '}\n'
    html += 'addLog("=== GALLERY v0017 STARTED (Auto-Server) ===", "info");\n'
    html += 'addLog("Error server: " + (serverAvailable ? "CONNECTED" : "OFFLINE"), serverAvailable ? "info" : "warn");\n'
    html += 'addLog("Posts loaded: " + allPosts.length, "info");\n'
    
    # Helper functions
    html += 'function isVideo(fn) { return fn && /\\.(mp4|mov|avi|mkv)$/i.test(fn); }\n'
    html += 'function getMediaPath(folder, file) { return folder + "/" + file; }\n'
    html += 'function showToast(msg, dur) { dur = dur || 2000; var t = document.getElementById("toast"); t.textContent = msg; t.classList.add("show"); setTimeout(function() { t.classList.remove("show"); }, dur); addLog("Toast: " + msg, "info"); }\n'
    
    # Word cloud
    html += 'function updateWordCloud(posts) {\n'
    html += '  addLog("[WordCloud] Generating from " + posts.length + " posts", "info");\n'
    html += '  var wc = {};\n'
    html += '  for(var i=0;i<posts.length;i++){\n'
    html += '    var text = posts[i].caption + " " + posts[i].comments.join(" ");\n'
    html += '    var words = text.toLowerCase().match(/\\b[a-z]+\\b/g) || [];\n'
    html += '    for(var j=0;j<words.length;j++){\n'
    html += '      var w = words[j];\n'
    html += '      if(w.length>2 && !/^(a|an|and|the|of|to|in|for|on|with|by|at|is|it|that|this|are|was|were|be|been|being|have|has|had|having|do|does|did|doing|but|or|so|for|not|can|will|just|like|get|put|up|down|out|over|under|again|then|once|here|there|all|any|both|each|few|more|most|other|some|such|no|nor|only|own|same|than|too|very|i|you|he|she|it|we|they|me|him|her|us|them|my|your|his|her|its|our|their|what|which|who|whom|whose|these|those|am|been|were|www|com|https|http|instagram)$/.test(w)){\n'
    html += '        wc[w] = (wc[w] || 0) + 1;\n'
    html += '      }\n'
    html += '    }\n'
    html += '  }\n'
    html += '  var wordList = [];\n'
    html += '  for(var word in wc) wordList.push({word:word, count:wc[word]});\n'
    html += '  wordList.sort(function(a,b){return b.count-a.count});\n'
    html += '  wordList = wordList.slice(0,100);\n'
    html += '  var maxF = wordList.length ? wordList[0].count : 1;\n'
    html += '  var container = document.getElementById("wordcloud");\n'
    html += '  if(!wordList.length){ container.innerHTML="<span>No words found</span>"; return; }\n'
    html += '  var cloudHtml = "";\n'
    html += '  for(var i=0;i<wordList.length;i++){\n'
    html += '    var size = 0.8 + (wordList[i].count / maxF) * 1.5;\n'
    html += '    cloudHtml += "<span class=\\"cloud-word\\" data-word=\\"" + wordList[i].word + "\\" style=\\"font-size:" + size + "rem;\\">" + wordList[i].word + "</span>";\n'
    html += '  }\n'
    html += '  container.innerHTML = cloudHtml;\n'
    html += '  var cloudWords = document.querySelectorAll(".cloud-word");\n'
    html += '  for(var i=0;i<cloudWords.length;i++){\n'
    html += '    cloudWords[i].onclick = function(){\n'
    html += '      addLog("[WordCloud] Selected: " + this.dataset.word, "info");\n'
    html += '      document.getElementById("searchInput").value = this.dataset.word;\n'
    html += '      var e = new Event("input", {bubbles:true});\n'
    html += '      document.getElementById("searchInput").dispatchEvent(e);\n'
    html += '    };\n'
    html += '  }\n'
    html += '  addLog("[WordCloud] Generated " + wordList.length + " words", "info");\n'
    html += '}\n'
    
    # Render gallery
    html += 'function renderGallery(posts) {\n'
    html += '  addLog("[Render] Rendering " + posts.length + " posts", "info");\n'
    html += '  var grid = document.getElementById("galleryGrid");\n'
    html += '  if(!posts.length){ grid.innerHTML = "<div class=\\"no-results\\">No posts match your search.</div>"; return; }\n'
    html += '  var htmlStr = "";\n'
    html += '  for(var idx=0; idx<posts.length; idx++){\n'
    html += '    var post = posts[idx];\n'
    html += '    var pm = post.all_media.length ? post.all_media[0] : null;\n'
    html += '    var carItems = "";\n'
    html += '    for(var i=1;i<post.all_media.length;i++){\n'
    html += '      var f = post.all_media[i];\n'
    html += '      var p = getMediaPath(post.folder_name, f);\n'
    html += '      if(isVideo(f)) carItems += "<div class=\\"carousel-video-placeholder\\" data-media=\\"" + p + "\\">🎬</div>";\n'
    html += '      else carItems += "<img class=\\"carousel-item\\" src=\\"" + p + "\\" data-media=\\"" + p + "\\" loading=\\"lazy\\">";\n'
    html += '    }\n'
    html += '    var mediaHtml = "";\n'
    html += '    if(pm){\n'
    html += '      var mp = getMediaPath(post.folder_name, pm);\n'
    html += '      if(isVideo(pm)) mediaHtml = "<div class=\\"video-placeholder card-media\\">🎬 Video</div>";\n'
    html += '      else mediaHtml = "<img class=\\"card-media\\" src=\\"" + mp + "\\" loading=\\"lazy\\">";\n'
    html += '    } else { mediaHtml = "<div class=\\"card-media\\" style=\\"display:flex;align-items:center;justify-content:center;\\">No media</div>"; }\n'
    html += '    var authorDisplay;\n'
    html += '    if(DISPLAY_MODE === "initial"){\n'
    html += '      var init = post.author.charAt(0).toUpperCase();\n'
    html += '      authorDisplay = "<span class=\\"author-initial\\" title=\\"@" + post.author + "\\">" + init + "</span>";\n'
    html += '    } else { authorDisplay = "<span class=\\"author-name\\">@" + post.author + "</span>"; }\n'
    html += '    var captionText = post.caption.length > 180 ? post.caption.substring(0,180)+"…" : post.caption;\n'
    html += '    htmlStr += "<div class=\\"card\\" data-shortcode=\\"" + post.shortcode + "\\" data-caption=\\"" + post.caption.replace(/"/g,"&quot;") + "\\">";\n'
    html += '    htmlStr += "<div style=\\"position:relative;width:100%;aspect-ratio:4/3;\\">" + mediaHtml + "</div>";\n'
    html += '    htmlStr += "<div class=\\"card-content\\">";\n'
    html += '    htmlStr += "<div class=\\"card-meta\\"><span>" + authorDisplay + "</span><span>📅 " + new Date(post.date).toLocaleDateString() + "</span><span>❤️ " + post.likes + "</span><span>💬 " + post.comments_count + "</span></div>";\n'
    html += '    htmlStr += "<div class=\\"card-caption\\">" + captionText + "</div>";\n'
    html += '    if(carItems) htmlStr += "<div class=\\"carousel\\">" + carItems + "</div>";\n'
    html += '    htmlStr += "<div class=\\"card-footer\\"><a href=\\"" + post.instagram_url + "\\" target=\\"_blank\\" class=\\"insta-link\\" onclick=\\"event.stopPropagation()\\">🔗 View on Instagram</a>";\n'
    html += '    htmlStr += "<button class=\\"comments-btn\\" data-shortcode=\\"" + post.shortcode + "\\">💬 " + post.comments.length + " comments</button></div></div></div>";\n'
    html += '  }\n'
    html += '  grid.innerHTML = htmlStr;\n'
    html += '  attachCommentListeners(); attachCarouselListeners(); addCheckboxesToCards();\n'
    html += '  addLog("[Render] Complete - " + posts.length + " cards", "info");\n'
    html += '}\n'
    
    # Event listeners (condensed for brevity - same as v0016)
    html += 'function attachCommentListeners(){var btns=document.querySelectorAll(".comments-btn");for(var i=0;i<btns.length;i++) btns[i].onclick=commentHandler;}\n'
    html += 'function commentHandler(e){e.stopPropagation();var sc=this.dataset.shortcode;addLog("[Comments] Loading for post: "+sc,"info");for(var i=0;i<allPosts.length;i++){if(allPosts[i].shortcode===sc){var commentsHtml="";for(var j=0;j<allPosts[i].comments.length;j++) commentsHtml+="<div class=\"comment-item\">💬 "+allPosts[i].comments[j]+"</div>";document.getElementById("commentsList").innerHTML=commentsHtml;document.getElementById("commentsModal").classList.add("active");addLog("[Comments] Displayed "+allPosts[i].comments.length+" comments","info");return;}}showToast("No comments for this post.");}\n'
    html += 'function attachCarouselListeners(){var items=document.querySelectorAll(".carousel-item, .carousel-video-placeholder");for(var i=0;i<items.length;i++) items[i].onclick=carouselHandler;}\n'
    html += 'function carouselHandler(e){e.stopPropagation();var media=this.dataset.media;var card=this.closest(".card");var caption=card.dataset.caption;addLog("[Carousel] Opening: "+media,"info");openLightbox(media,caption);}\n'
    html += 'function openLightbox(src,caption){addLog("[Lightbox] Opening: "+src,"info");var c=document.getElementById("lightboxMediaContainer");c.innerHTML="";if(src && src.match(/\\.(mp4|mov|avi|mkv)$/i)){var v=document.createElement("video");v.src=src;v.controls=true;v.style.maxWidth="90vw";v.style.maxHeight="85vh";c.appendChild(v);}else if(src){var img=document.createElement("img");img.src=src;img.style.maxWidth="90vw";img.style.maxHeight="85vh";c.appendChild(img);}else{c.innerHTML="<div style=\"color:white;\">No media available</div>";}document.getElementById("lightboxCaption").innerText=caption;document.getElementById("lightbox").classList.add("active");}\n'
    html += 'var debounceTimer;document.getElementById("searchInput").addEventListener("input",function(e){clearTimeout(debounceTimer);var q=e.target.value.trim().toLowerCase();addLog("[Search] Query: "+(q||"(empty)"),"info");debounceTimer=setTimeout(function(){var filtered=[];for(var i=0;i<allPosts.length;i++){if(allPosts[i].caption.toLowerCase().indexOf(q)!==-1) filtered.push(allPosts[i]);}addLog("[Search] Filtered to "+filtered.length+" posts","info");renderGallery(filtered);updateWordCloud(filtered);},200);});\n'
    html += 'document.getElementById("lightboxClose").onclick=function(){addLog("[Lightbox] Closed","info");document.getElementById("lightbox").classList.remove("active");};\n'
    html += 'document.getElementById("modalClose").onclick=function(){addLog("[Comments] Modal closed","info");document.getElementById("commentsModal").classList.remove("active");};\n'
    html += 'window.onclick=function(e){if(e.target===document.getElementById("lightbox")){addLog("[Lightbox] Closed (outside click)","info");document.getElementById("lightbox").classList.remove("active");}if(e.target===document.getElementById("commentsModal")){addLog("[Comments] Modal closed (outside click)","info");document.getElementById("commentsModal").classList.remove("active");}};\n'
    html += 'document.getElementById("galleryGrid").onclick=function(e){var card=e.target.closest(".card");if(card && !e.target.closest(".carousel-item") && !e.target.closest(".carousel-video-placeholder") && !e.target.closest(".comments-btn") && !e.target.closest("a") && !e.target.closest(".select-checkbox")){var media=null;var img=card.querySelector(".card-media");if(img && img.tagName==="IMG") media=img.src;else if(card.querySelector(".video-placeholder")){var sc=card.dataset.shortcode;for(var i=0;i<allPosts.length;i++){if(allPosts[i].shortcode===sc && allPosts[i].all_media.length) media=getMediaPath(allPosts[i].folder_name,allPosts[i].all_media[0]);}}addLog("[Card] Opening media for: "+card.dataset.shortcode,"info");openLightbox(media,card.dataset.caption);}};\n'
    html += 'var selectedSrcs=new Set();\n'
    html += 'function addCheckboxesToCards(){var cards=document.querySelectorAll(".card");for(var i=0;i<cards.length;i++){var card=cards[i];if(card.querySelector(".select-checkbox")) continue;var img=card.querySelector("img");if(!img || !img.src || img.src.startsWith("data:")) continue;var src=img.src;var chk=document.createElement("input");chk.type="checkbox";chk.className="select-checkbox";chk.checked=selectedSrcs.has(src);chk.onclick=function(e){e.stopPropagation();};chk.onchange=function(e){e.stopPropagation();var isChecked=this.checked;var imageSrc=this.parentElement.querySelector("img").src;addLog("[Checkbox] "+(isChecked?"Selected":"Deselected")+": "+imageSrc,"info");if(isChecked){selectedSrcs.add(imageSrc);addImageToStoryboard(imageSrc,true);}else{selectedSrcs.delete(imageSrc);}var span=document.getElementById("selectedCount");if(span) span.innerText=selectedSrcs.size+" selected";};if(getComputedStyle(card).position==="static") card.style.position="relative";card.appendChild(chk);}}\n'
    html += 'function selectAll(){addLog("[Select] Select All clicked","info");var checkboxes=document.querySelectorAll(".select-checkbox");for(var i=0;i<checkboxes.length;i++) checkboxes[i].checked=true;selectedSrcs.clear();var images=document.querySelectorAll(".card img");for(var i=0;i<images.length;i++){if(images[i].src && !images[i].src.startsWith("data:")) selectedSrcs.add(images[i].src);}var span=document.getElementById("selectedCount");if(span) span.innerText=selectedSrcs.size+" selected";addMultipleImages(Array.from(selectedSrcs));}\n'
    html += 'function deselectAll(){addLog("[Select] Deselect All clicked","info");var checkboxes=document.querySelectorAll(".select-checkbox");for(var i=0;i<checkboxes.length;i++) checkboxes[i].checked=false;selectedSrcs.clear();var span=document.getElementById("selectedCount");if(span) span.innerText="0 selected";}\n'
    html += 'var canvas=null;var storyboardImages=[];var STORAGE_KEY="storyboard_images_srcs";var PREVIEW_W=1080,PREVIEW_H=1440,TARGET_W=10800,TARGET_H=14400,SCALE=TARGET_W/PREVIEW_W;var currentTemplate="grid";\n'
    html += 'function updateStoryboardBadge(){var b=document.getElementById("storyboardCountBadge");if(b) b.innerText=storyboardImages.length;addLog("[Storyboard] Badge updated: "+storyboardImages.length+" images","info");}\n'
    html += 'function addImageToStoryboard(src,silent){silent=silent||false;for(var i=0;i<storyboardImages.length;i++){if(storyboardImages[i].src===src){if(!silent) showToast("Image already in storyboard");return Promise.resolve(false);}}addLog("[Storyboard] Adding image: "+src,"info");return new Promise(function(resolve){fabric.Image.fromURL(src,function(img){if(!img){if(!silent) showToast("Failed to load image");addLog("[Storyboard] Failed to load: "+src,"error");resolve(false);return;}img.set({crossOrigin:"Anonymous",hasControls:true,hasBorders:true,lockRotation:true});storyboardImages.push({src:src,fabricObj:img,originalWidth:img.width,originalHeight:img.height});if(canvas){canvas.add(img);applyLayout(currentTemplate);updateThumbnails();saveToLocalStorage();updateStoryboardBadge();}addLog("[Storyboard] Added successfully","info");resolve(true);},{crossOrigin:"Anonymous"});});}\n'
    html += 'function addMultipleImages(srcList){var added=0;var promises=[];for(var i=0;i<srcList.length;i++){promises.push(addImageToStoryboard(srcList[i],true));}Promise.all(promises).then(function(results){for(var i=0;i<results.length;i++) if(results[i]) added++;if(added) showToast("Added "+added+" image(s)");addLog("[Storyboard] Added "+added+" images from batch","info");});}\n'
    html += 'function syncSelectedToStoryboard(){var srcs=Array.from(selectedSrcs);if(srcs.length===0){showToast("No images selected");return;}addLog("[Storyboard] Syncing "+srcs.length+" selected images","info");addMultipleImages(srcs);}\n'
    html += 'function applyLayout(templateName){if(!canvas || storyboardImages.length===0) return;currentTemplate=templateName;addLog("[Storyboard] Applying layout: "+templateName,"info");var margin=20,availW=PREVIEW_W-margin*2,availH=PREVIEW_H-margin*2,cnt=storyboardImages.length;function placeInGrid(cols,maxHeightPerRow){var y=margin;for(var i=0;i<cnt;i++){var obj=storyboardImages[i].fabricObj;var col=i%cols;if(col===0 && i!==0){var rowMax=0;for(var j=i-cols;j<i;j++) rowMax=Math.max(rowMax,storyboardImages[j].fabricObj.height*storyboardImages[j].fabricObj.scaleY);y+=rowMax+margin;}var cellW=(availW-(cols-1)*margin)/cols;var scale=Math.min(cellW/obj.width,maxHeightPerRow/obj.height);obj.scale(scale);obj.set({left:margin+col*(cellW+margin),top:y});}}if(templateName==="center"){var obj=storyboardImages[0].fabricObj;var scale=Math.min(availW/obj.width,availH/obj.height);obj.scale(scale);obj.set({left:margin+(availW-obj.width*scale)/2,top:margin+(availH-obj.height*scale)/2});}else if(templateName==="twoCol"){placeInGrid(2,300);}else{placeInGrid(3,200);}canvas.renderAll();saveToLocalStorage();}\n'
    html += 'function clearAll(){if(confirm("Clear all images?")){addLog("[Storyboard] Clearing all images","info");for(var i=0;i<storyboardImages.length;i++) canvas.remove(storyboardImages[i].fabricObj);storyboardImages=[];canvas.renderAll();updateThumbnails();localStorage.removeItem(STORAGE_KEY);updateStoryboardBadge();showToast("Storyboard cleared");}}\n'
    html += 'function exportStoryboard(){if(storyboardImages.length===0){showToast("No images to export");return;}addLog("[Storyboard] Exporting "+storyboardImages.length+" images at "+TARGET_W+"x"+TARGET_H,"info");var offCanvas=document.createElement("canvas");offCanvas.width=TARGET_W;offCanvas.height=TARGET_H;var offCtx=offCanvas.getContext("2d");offCtx.fillStyle="white";offCtx.fillRect(0,0,TARGET_W,TARGET_H);for(var i=0;i<storyboardImages.length;i++){var obj=storyboardImages[i].fabricObj;offCtx.drawImage(obj._element,obj.left*SCALE,obj.top*SCALE,obj.width*obj.scaleX*SCALE,obj.height*obj.scaleY*SCALE);}var a=document.createElement("a");a.download="storyboard.png";a.href=offCanvas.toDataURL("image/png");a.click();addLog("[Storyboard] Export initiated","info");}\n'
    html += 'function updateThumbnails(){var container=document.getElementById("storyboardThumbnails");if(!container) return;var html="";for(var i=0;i<storyboardImages.length;i++) html+="<img class=\"storyboard-thumb\" src=\""+storyboardImages[i].src+"\" data-index=\""+i+"\">";container.innerHTML=html;var thumbs=document.querySelectorAll(".storyboard-thumb");for(var i=0;i<thumbs.length;i++){thumbs[i].onclick=function(){var idx=parseInt(this.dataset.index);if(!isNaN(idx)){addLog("[Storyboard] Removing image index: "+idx,"info");canvas.remove(storyboardImages[idx].fabricObj);storyboardImages.splice(idx,1);canvas.renderAll();updateThumbnails();saveToLocalStorage();updateStoryboardBadge();showToast("Image removed");}};}}\n'
    html += 'function saveToLocalStorage(){var srcs=[];for(var i=0;i<storyboardImages.length;i++) srcs.push(storyboardImages[i].src);localStorage.setItem(STORAGE_KEY,JSON.stringify(srcs));}\n'
    html += 'function loadFromLocalStorage(){var stored=localStorage.getItem(STORAGE_KEY);if(stored){try{var srcs=JSON.parse(stored);if(srcs && srcs.length){addLog("[Storyboard] Loading "+srcs.length+" images from localStorage","info");for(var i=0;i<srcs.length;i++){(function(src){fabric.Image.fromURL(src,function(img){if(img){img.set({crossOrigin:"Anonymous",hasControls:true,hasBorders:true,lockRotation:true});storyboardImages.push({src:src,fabricObj:img,originalWidth:img.width,originalHeight:img.height});if(canvas) canvas.add(img);}});})(srcs[i]);}setTimeout(function(){if(canvas){applyLayout(currentTemplate);updateThumbnails();updateStoryboardBadge();}},500);}}catch(e){console.warn(e);}}}\n'
    html += 'function initCanvas(){var canvasEl=document.getElementById("storyboardCanvas");if(!canvasEl) return;if(canvas) canvas.dispose();canvas=new fabric.Canvas("storyboardCanvas");canvas.setDimensions({width:PREVIEW_W,height:PREVIEW_H});canvas.backgroundColor="white";canvas.on("object:modified",function(){saveToLocalStorage();});canvas.renderAll();loadFromLocalStorage();addLog("[Canvas] Initialized","info");}\n'
    html += 'function openStoryboardNewTab(){var srcs=[];for(var i=0;i<storyboardImages.length;i++) srcs.push(storyboardImages[i].src);var w=window.open();if(!w){showToast("Popup blocked");return;}addLog("[Storyboard] Opening new tab with "+srcs.length+" images","info");var htmlContent="<!DOCTYPE html><html><head><title>Storyboard</title><style>body{margin:0;background:#0f172a;color:white;}canvas{display:block;margin:20px auto;border:2px solid #475569;background:white;}.controls{text-align:center;padding:10px;}button{margin:5px;padding:8px 16px;background:#3b82f6;border:none;color:white;border-radius:8px;cursor:pointer;}</style><script src=\"https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js\"><\\/script></head><body><div class=\"controls\"><button id=\"exportBtn\">Export PNG</button><button id=\"closeBtn\" onclick=\"window.close()\">Close</button></div><canvas id=\"storyboardCanvasNew\" width=\"1080\" height=\"1440\"></canvas><script>var srcs="+JSON.stringify(srcs)+"; var canvas,images=[]; var PREVIEW_W=1080,PREVIEW_H=1440,TARGET_W=10800,TARGET_H=14400,SCALE=TARGET_W/PREVIEW_W; function loadAll(){ if(!srcs.length) return; var loaded=0; for(var i=0;i<srcs.length;i++){ fabric.Image.fromURL(srcs[i],function(img){ if(!img) return; img.set({hasControls:true,lockRotation:true}); images.push(img); loaded++; if(loaded===srcs.length) drawCanvas(); },{crossOrigin:\"Anonymous\"}); } } function drawCanvas(){ canvas=new fabric.Canvas(\"storyboardCanvasNew\"); canvas.setDimensions({width:PREVIEW_W,height:PREVIEW_H}); canvas.backgroundColor=\"white\"; var margin=20,w=PREVIEW_W-margin*2,cols=3,cellW=(w-(cols-1)*margin)/cols; var y=margin; for(var i=0;i<images.length;i++){ var img=images[i]; var col=i%cols; if(col===0 && i!==0){ var rowMax=0; for(var j=i-cols;j<i;j++) rowMax=Math.max(rowMax,images[j].height*images[j].scaleY); y+=rowMax+margin; } var scale=Math.min(cellW/img.width,200/img.height); img.scale(scale); img.set({left:margin+col*(cellW+margin),top:y}); canvas.add(img); } canvas.renderAll(); } document.getElementById(\"exportBtn\").onclick=function(){ if(!images.length) return; var off=document.createElement(\"canvas\"); off.width=TARGET_W; off.height=TARGET_H; var ctx=off.getContext(\"2d\"); ctx.fillStyle=\"white\"; ctx.fillRect(0,0,TARGET_W,TARGET_H); for(var i=0;i<images.length;i++){ var img=images[i]; ctx.drawImage(img._element,img.left*SCALE,img.top*SCALE,img.width*img.scaleX*SCALE,img.height*img.scaleY*SCALE); } var a=document.createElement(\"a\"); a.download=\"storyboard.png\"; a.href=off.toDataURL(\"image/png\"); a.click(); }; loadAll();<\\/script></body></html>"; w.document.write(htmlContent); w.document.close();}\n'
    
    # Initialization
    html += 'document.getElementById("selectAllBtn").onclick = selectAll;\n'
    html += 'document.getElementById("deselectAllBtn").onclick = deselectAll;\n'
    html += 'document.getElementById("syncSelectedBtn").onclick = syncSelectedToStoryboard;\n'
    html += 'document.getElementById("openStoryboardBtn").onclick = function(){ addLog("[Storyboard] Opening modal", "info"); document.getElementById("storyboardModal").classList.add("active"); };\n'
    html += 'document.getElementById("closeStoryboardBtn").onclick = function(){ addLog("[Storyboard] Closing modal", "info"); document.getElementById("storyboardModal").classList.remove("active"); };\n'
    html += 'document.getElementById("exportStoryboardBtn").onclick = exportStoryboard;\n'
    html += 'document.getElementById("clearStoryboardBtn").onclick = clearAll;\n'
    html += 'document.getElementById("applyTemplateBtn").onclick = function(){ var tpl = document.getElementById("templateSelect").value; applyLayout(tpl); };\n'
    html += 'document.getElementById("openStoryboardNewTabBtn").onclick = openStoryboardNewTab;\n'
    html += 'window.onclick = function(e){ if(e.target === document.getElementById("storyboardModal")){ addLog("[Storyboard] Modal closed (outside click)", "info"); document.getElementById("storyboardModal").classList.remove("active"); } };\n'
    html += 'initCanvas();\n'
    html += 'renderGallery(allPosts);\n'
    html += 'updateWordCloud(allPosts);\n'
    html += 'addLog("=== GALLERY READY ===", "info");\n'
    html += 'if(!serverAvailable) addLog("⚠️ Error server not running - logs saved to browser memory only", "warn");\n'
    html += '</script>\n</body>\n</html>'
    
    return html

def main():
    print("=" * 70)
    print("MR. DOUGLAS GALLERY BUILDER v0017")
    print("AUTO-SERVER MODE - One Command Does Everything")
    print("=" * 70)
    print()
    
    # Step 1: Generate the gallery
    print("[1/4] Building gallery...")
    posts = load_posts()
    posts = add_historic_images(posts)
    logger.info(f"Total posts: {len(posts)}")
    
    # Step 2: Start error server (for database logging)
    print("[2/4] Starting error server (port 8001)...")
    error_server_ok = start_error_server()
    
    # Step 3: Start HTTP server
    print("[3/4] Starting HTTP server (port 8000)...")
    http_server_ok = start_http_server()
    
    # Step 4: Generate HTML
    print("[4/4] Generating HTML...")
    html = build_html(posts, error_server_ok, http_server_ok)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    logger.info(f"Generated {OUTPUT_HTML.resolve()}")
    
    # Save JSON for reference
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
    
    print()
    print("=" * 70)
    print("BUILD COMPLETE!")
    print("=" * 70)
    print()
    print(f"📁 HTML file: {OUTPUT_HTML.resolve()}")
    print(f"📁 JSON file: {OUTPUT_JSON.resolve()}")
    print(f"📁 Database: gallery_errors.db")
    print()
    print("🌐 Opening browser in 3 seconds...")
    print("   URL: http://localhost:8000/index_v0017.html")
    print()
    print("📊 Status:")
    print(f"   Error Server (port 8001): {'✅ RUNNING' if error_server_ok else '❌ FAILED'}")
    print(f"   HTTP Server (port 8000): {'✅ RUNNING' if http_server_ok else '❌ FAILED'}")
    print()
    print("⚠️  Press Ctrl+C to stop all servers and exit")
    
    # Open browser
    threading.Thread(target=open_browser, args=('http://localhost:8000/index_v0017.html',), daemon=True).start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        cleanup()
        print("Done.")

if __name__ == "__main__":
    main()