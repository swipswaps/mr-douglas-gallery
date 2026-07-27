#!/usr/bin/env python3
"""
build_final_gallery_v0021.py

WORKING v0013 GALLERY + PROFESSIONAL STORYBOARD WITH LANCZOS UPSCALING

Features:
- Gallery displays images correctly (v0013 base)
- Storyboard with high-quality Lanczos image scaling
- Background color picker
- SVG logo upload
- Multiple layout templates (grid, twoCol, center, masonry, polaroid, timeline)
- Dual export (300 DPI print + web preview)
- LocalStorage persistence
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path("instagram_posts.db")
CSV_PATH = Path("posts.csv")
OUTPUT_HTML = Path("index_v0021.html")
OUTPUT_JSON = Path("posts_with_authors.json")
ACCOUNT_OWNER = "sav_a_dc3"
DISPLAY_MODE = "username"

processes = []

def cleanup():
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
    try:
        import urllib.request
        try:
            urllib.request.urlopen('http://localhost:8001/health', timeout=0.5)
            logger.info("Error server already running")
            return True
        except:
            pass
        p = subprocess.Popen([sys.executable, 'run_error_server.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(p)
        time.sleep(2)
        logger.info(f"Error server started (PID: {p.pid})")
        return True
    except Exception as e:
        logger.warning(f"Could not start error server: {e}")
        return False

def start_http_server():
    try:
        import urllib.request
        try:
            urllib.request.urlopen('http://localhost:8000/', timeout=0.5)
            logger.info("HTTP server already running")
            return True
        except:
            pass
        p = subprocess.Popen([sys.executable, '-m', 'http.server', '8000'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(p)
        time.sleep(2)
        logger.info(f"HTTP server started (PID: {p.pid})")
        return True
    except Exception as e:
        logger.warning(f"Could not start HTTP server: {e}")
        return False

def open_browser(url):
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

def build_html(posts):
    posts_json = json.dumps(posts, ensure_ascii=False)
    
    html = '<!DOCTYPE html>\n'
    html += '<html lang="en">\n<head>\n'
    html += '<meta charset="UTF-8">\n'
    html += '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    html += '<title>Mr. Douglas Gallery v0021 - Lanczos Scaling</title>\n'
    
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
    
    html += '<div class="debug-panel" id="debugPanel"><strong>🐛 Debug Active</strong><br><div id="debugLog"></div></div>\n'
    html += '<div class="search-header"><div class="search-container">\n'
    html += '<input type="text" id="searchInput" class="search-input" placeholder="Search posts...">\n'
    html += '<div class="wordcloud-container"><div id="wordcloud" class="wordcloud">Loading words...</div></div>\n</div></div>\n'
    
    html += '<div class="gallery-toolbar">\n'
    html += '<span>Select images:</span>\n'
    html += '<button id="selectAllBtn">Select All</button>\n'
    html += '<button id="deselectAllBtn">Deselect All</button>\n'
    html += '<button id="syncSelectedBtn" class="primary">Sync Selected to Storyboard</button>\n'
    html += '<span id="selectedCount">0 selected</span>\n'
    html += '<button id="openStoryboardNewTabBtn" style="background:#10b981;">Open Storyboard in New Tab</button>\n</div>\n'
    
    html += '<div id="galleryGrid" class="grid"></div>\n'
    
    html += '<button class="storyboard-btn" id="openStoryboardBtn">Open Storyboard <span id="storyboardCountBadge">0</span></button>\n'
    html += '<div id="storyboardModal" class="storyboard-modal">\n'
    html += '<div class="storyboard-container">\n'
    html += '<div style="display:flex;justify-content:space-between;"><h3>Storyboard Builder</h3><button class="close-modal" id="closeStoryboardBtn">Close</button></div>\n'
    html += '<div class="storyboard-controls" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:15px">\n'
    html += '<label style="color:white;font-size:12px">Background:</label>\n'
    html += '<select id="bgColorSelect" style="background:#334155;color:white;border:none;padding:4px 8px;border-radius:4px">\n'
    html += '<option value="#ffffff">White</option>\n'
    html += '<option value="#0f172a">Dark Blue</option>\n'
    html += '<option value="#1e293b">Slate</option>\n'
    html += '<option value="#f5f5f0">Cream</option>\n'
    html += '<option value="#1a1a2e">Deep Navy</option>\n'
    html += '<option value="#2d2d2d">Charcoal</option>\n'
    html += '</select>\n'
    html += '<label style="color:white;font-size:12px">Logo SVG:</label>\n'
    html += '<input type="file" id="logoUpload" accept="image/svg+xml" style="background:#334155;color:white;border:none;padding:4px 8px;border-radius:4px;font-size:12px">\n'
    html += '<button id="addLogoBtn" style="background:#10b981;border:none;color:white;padding:4px 12px;border-radius:4px;cursor:pointer">Add Logo</button>\n'
    html += '<button id="removeLogoBtn" style="background:#ef4444;border:none;color:white;padding:4px 12px;border-radius:4px;cursor:pointer">Remove Logo</button>\n'
    html += '</div>\n'
    html += '<div><canvas id="storyboardCanvas" width="1080" height="1440"></canvas></div>\n'
    html += '<div class="storyboard-controls">\n'
    html += '<select id="templateSelect">\n'
    html += '<option value="grid">Grid (3 cols)</option>\n'
    html += '<option value="twoCol">Two columns</option>\n'
    html += '<option value="center">Single centered</option>\n'
    html += '<option value="masonry">Masonry Collage</option>\n'
    html += '<option value="polaroid">Polaroid Stack</option>\n'
    html += '<option value="timeline">Timeline Cascade</option>\n'
    html += '</select>\n'
    html += '<button id="applyTemplateBtn" class="success">Apply Template</button>\n'
    html += '<button id="exportStoryboardBtn" class="success">Export PNG (10800×14400)</button>\n'
    html += '<button id="exportWebBtn" class="success">Export Web Preview</button>\n'
    html += '<button id="clearStoryboardBtn" class="danger">Clear All</button>\n'
    html += '<button id="resetViewBtn" class="success">Reset View</button>\n'
    html += '</div>\n'
    html += '<div><strong>Images (click to remove):</strong><div id="storyboardThumbnails" style="display:flex;gap:12px;overflow-x:auto;padding:8px;"></div></div>\n'
    html += '</div></div>\n'
    
    html += '<div id="toast" class="toast"></div>\n'
    html += '<div id="lightbox" class="lightbox"><div class="lightbox-content"><div class="lightbox-close" id="lightboxClose">×</div><div id="lightboxMediaContainer"></div><div id="lightboxCaption"></div></div></div>\n'
    html += '<div id="commentsModal" class="modal"><div class="modal-header"><strong>Comments</strong><span id="modalClose" class="modal-close">&times;</span></div><div id="commentsList"></div></div>\n'
    
    html += '<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>\n'
    html += '<script>\n'
    html += 'var allPosts = ' + posts_json + ';\n'
    html += 'var DISPLAY_MODE = "' + DISPLAY_MODE + '";\n'
    html += 'var debugLog = document.getElementById("debugLog");\n'
    html += 'function addLog(msg) { var d = document.createElement("div"); d.textContent = new Date().toLocaleTimeString() + " " + msg; debugLog.appendChild(d); if(debugLog.children.length>30) debugLog.removeChild(debugLog.children[0]); console.log(msg); }\n'
    html += 'addLog("=== GALLERY v0021 STARTED ===");\n'
    html += 'addLog("Posts loaded: " + allPosts.length);\n'
    
    # Helper functions
    html += 'function isVideo(fn) { return fn && /\\\\.(mp4|mov|avi|mkv)$/i.test(fn); }\n'
    html += 'function getMediaPath(folder, file) { return folder + "/" + file; }\n'
    html += 'function showToast(msg, dur) { dur = dur || 2000; var t = document.getElementById("toast"); t.textContent = msg; t.classList.add("show"); setTimeout(function() { t.classList.remove("show"); }, dur); addLog("Toast: " + msg); }\n'
    
    # Word cloud
    html += 'function updateWordCloud(posts) {\n'
    html += '  addLog("[WordCloud] Generating from " + posts.length + " posts");\n'
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
    html += '      addLog("[WordCloud] Selected: " + this.dataset.word);\n'
    html += '      document.getElementById("searchInput").value = this.dataset.word;\n'
    html += '      var e = new Event("input", {bubbles:true});\n'
    html += '      document.getElementById("searchInput").dispatchEvent(e);\n'
    html += '    };\n'
    html += '  }\n'
    html += '  addLog("[WordCloud] Generated " + wordList.length + " words");\n'
    html += '}\n'
    
    # Gallery render (v0013 working)
    html += 'function renderGallery(posts) {\n'
    html += '  addLog("[Render] Rendering " + posts.length + " posts");\n'
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
    html += '  addLog("[Render] Complete - " + posts.length + " cards");\n'
    html += '}\n'
    
    # Event listeners
    html += 'function attachCommentListeners(){\n'
    html += '  var btns = document.querySelectorAll(".comments-btn");\n'
    html += '  for(var i=0;i<btns.length;i++) btns[i].onclick = commentHandler;\n'
    html += '}\n'
    html += 'function commentHandler(e){\n'
    html += '  e.stopPropagation(); var sc = this.dataset.shortcode;\n'
    html += '  addLog("[Comments] Loading for post: " + sc);\n'
    html += '  for(var i=0;i<allPosts.length;i++){\n'
    html += '    if(allPosts[i].shortcode === sc){\n'
    html += '      var commentsHtml = "";\n'
    html += '      for(var j=0;j<allPosts[i].comments.length;j++) commentsHtml += "<div class=\\"comment-item\\">💬 " + allPosts[i].comments[j] + "</div>";\n'
    html += '      document.getElementById("commentsList").innerHTML = commentsHtml;\n'
    html += '      document.getElementById("commentsModal").classList.add("active");\n'
    html += '      addLog("[Comments] Displayed " + allPosts[i].comments.length + " comments");\n'
    html += '      return;\n'
    html += '    }\n'
    html += '  }\n'
    html += '  showToast("No comments for this post.");\n'
    html += '}\n'
    html += 'function attachCarouselListeners(){\n'
    html += '  var items = document.querySelectorAll(".carousel-item, .carousel-video-placeholder");\n'
    html += '  for(var i=0;i<items.length;i++) items[i].onclick = carouselHandler;\n'
    html += '}\n'
    html += 'function carouselHandler(e){\n'
    html += '  e.stopPropagation(); var media = this.dataset.media; var card = this.closest(".card"); var caption = card.dataset.caption;\n'
    html += '  addLog("[Carousel] Opening: " + media);\n'
    html += '  openLightbox(media, caption);\n'
    html += '}\n'
    html += 'function openLightbox(src, caption){\n'
    html += '  addLog("[Lightbox] Opening: " + src);\n'
    html += '  var c = document.getElementById("lightboxMediaContainer"); c.innerHTML = "";\n'
    html += '  if(src && src.match(/\\.(mp4|mov|avi|mkv)$/i)){\n'
    html += '    var v = document.createElement("video"); v.src = src; v.controls = true; v.style.maxWidth = "90vw"; v.style.maxHeight = "85vh"; c.appendChild(v);\n'
    html += '  } else if(src){\n'
    html += '    var img = document.createElement("img"); img.src = src; img.style.maxWidth = "90vw"; img.style.maxHeight = "85vh"; c.appendChild(img);\n'
    html += '  } else { c.innerHTML = "<div style=\\"color:white;\\">No media available</div>"; }\n'
    html += '  document.getElementById("lightboxCaption").innerText = caption;\n'
    html += '  document.getElementById("lightbox").classList.add("active");\n'
    html += '}\n'
    html += 'var debounceTimer;\n'
    html += 'document.getElementById("searchInput").addEventListener("input", function(e){\n'
    html += '  clearTimeout(debounceTimer);\n'
    html += '  var q = e.target.value.trim().toLowerCase();\n'
    html += '  addLog("[Search] Query: " + (q || "(empty)"));\n'
    html += '  debounceTimer = setTimeout(function(){\n'
    html += '    var filtered = [];\n'
    html += '    for(var i=0;i<allPosts.length;i++){\n'
    html += '      if(allPosts[i].caption.toLowerCase().indexOf(q) !== -1) filtered.push(allPosts[i]);\n'
    html += '    }\n'
    html += '    addLog("[Search] Filtered to " + filtered.length + " posts");\n'
    html += '    renderGallery(filtered);\n'
    html += '    updateWordCloud(filtered);\n'
    html += '  }, 200);\n'
    html += '});\n'
    html += 'document.getElementById("lightboxClose").onclick = function(){ addLog("[Lightbox] Closed"); document.getElementById("lightbox").classList.remove("active"); };\n'
    html += 'document.getElementById("modalClose").onclick = function(){ addLog("[Comments] Modal closed"); document.getElementById("commentsModal").classList.remove("active"); };\n'
    html += 'window.onclick = function(e){\n'
    html += '  if(e.target === document.getElementById("lightbox")){ addLog("[Lightbox] Closed (outside click)"); document.getElementById("lightbox").classList.remove("active"); }\n'
    html += '  if(e.target === document.getElementById("commentsModal")){ addLog("[Comments] Modal closed (outside click)"); document.getElementById("commentsModal").classList.remove("active"); }\n'
    html += '};\n'
    html += 'document.getElementById("galleryGrid").onclick = function(e){\n'
    html += '  var card = e.target.closest(".card");\n'
    html += '  if(card && !e.target.closest(".carousel-item") && !e.target.closest(".carousel-video-placeholder") && !e.target.closest(".comments-btn") && !e.target.closest("a") && !e.target.closest(".select-checkbox")){\n'
    html += '    var media = null;\n'
    html += '    var img = card.querySelector(".card-media");\n'
    html += '    if(img && img.tagName === "IMG") media = img.src;\n'
    html += '    else if(card.querySelector(".video-placeholder")){\n'
    html += '      var sc = card.dataset.shortcode;\n'
    html += '      for(var i=0;i<allPosts.length;i++){\n'
    html += '        if(allPosts[i].shortcode === sc && allPosts[i].all_media.length) media = getMediaPath(allPosts[i].folder_name, allPosts[i].all_media[0]);\n'
    html += '      }\n'
    html += '    }\n'
    html += '    addLog("[Card] Opening media for: " + card.dataset.shortcode);\n'
    html += '    openLightbox(media, card.dataset.caption);\n'
    html += '  }\n'
    html += '};\n'
    html += 'var selectedSrcs = new Set();\n'
    html += 'function addCheckboxesToCards(){\n'
    html += '  var cards = document.querySelectorAll(".card");\n'
    html += '  for(var i=0;i<cards.length;i++){\n'
    html += '    var card = cards[i];\n'
    html += '    if(card.querySelector(".select-checkbox")) continue;\n'
    html += '    var img = card.querySelector("img");\n'
    html += '    if(!img || !img.src || img.src.startsWith("data:")) continue;\n'
    html += '    var src = img.src;\n'
    html += '    var chk = document.createElement("input");\n'
    html += '    chk.type = "checkbox"; chk.className = "select-checkbox";\n'
    html += '    chk.checked = selectedSrcs.has(src);\n'
    html += '    chk.onclick = function(e){ e.stopPropagation(); };\n'
    html += '    chk.onchange = function(e){\n'
    html += '      e.stopPropagation();\n'
    html += '      var isChecked = this.checked;\n'
    html += '      var imageSrc = this.parentElement.querySelector("img").src;\n'
    html += '      addLog("[Checkbox] " + (isChecked ? "Selected" : "Deselected") + ": " + imageSrc);\n'
    html += '      if(isChecked){ selectedSrcs.add(imageSrc); addImageToStoryboard(imageSrc, true); }\n'
    html += '      else{ selectedSrcs.delete(imageSrc); }\n'
    html += '      var span = document.getElementById("selectedCount");\n'
    html += '      if(span) span.innerText = selectedSrcs.size + " selected";\n'
    html += '    };\n'
    html += '    if(getComputedStyle(card).position === "static") card.style.position = "relative";\n'
    html += '    card.appendChild(chk);\n'
    html += '  }\n'
    html += '}\n'
    html += 'function selectAll(){\n'
    html += '  addLog("[Select] Select All clicked");\n'
    html += '  var checkboxes = document.querySelectorAll(".select-checkbox");\n'
    html += '  for(var i=0;i<checkboxes.length;i++) checkboxes[i].checked = true;\n'
    html += '  selectedSrcs.clear();\n'
    html += '  var images = document.querySelectorAll(".card img");\n'
    html += '  for(var i=0;i<images.length;i++){\n'
    html += '    if(images[i].src && !images[i].src.startsWith("data:")) selectedSrcs.add(images[i].src);\n'
    html += '  }\n'
    html += '  var span = document.getElementById("selectedCount");\n'
    html += '  if(span) span.innerText = selectedSrcs.size + " selected";\n'
    html += '  addMultipleImages(Array.from(selectedSrcs));\n'
    html += '}\n'
    html += 'function deselectAll(){\n'
    html += '  addLog("[Select] Deselect All clicked");\n'
    html += '  var checkboxes = document.querySelectorAll(".select-checkbox");\n'
    html += '  for(var i=0;i<checkboxes.length;i++) checkboxes[i].checked = false;\n'
    html += '  selectedSrcs.clear();\n'
    html += '  var span = document.getElementById("selectedCount");\n'
    html += '  if(span) span.innerText = "0 selected";\n'
    html += '}\n'
    
    # ========== HIGH-QUALITY FABRIC.JS STORYBOARD WITH LANCZOS ==========
    html += '// ========== HIGH-QUALITY STORYBOARD WITH LANCZOS ==========\n'
    html += 'var canvas = null;\n'
    html += 'var storyboardImages = [];\n'
    html += 'var STORAGE_KEY = "storyboard_images_srcs";\n'
    html += 'var PREVIEW_W = 1080, PREVIEW_H = 1440;\n'
    html += 'var TARGET_W = 10800, TARGET_H = 14400;\n'
    html += 'var SCALE = TARGET_W / PREVIEW_W;\n'
    html += 'var currentTemplate = "grid";\n'
    html += 'var currentLogo = null;\n'
    html += '\n'
    html += 'function initCanvas() {\n'
    html += '  var canvasEl = document.getElementById("storyboardCanvas");\n'
    html += '  if (!canvasEl) return;\n'
    html += '  if (canvas) canvas.dispose();\n'
    html += '  canvas = new fabric.Canvas("storyboardCanvas", {\n'
    html += '    enableRetinaScaling: true,\n'
    html += '    imageSmoothingEnabled: true,\n'
    html += '    imageSmoothingQuality: "high"\n'
    html += '  });\n'
    html += '  canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });\n'
    html += '  canvas.backgroundColor = "#ffffff";\n'
    html += '  var ctx = canvas.getContext("2d");\n'
    html += '  if (ctx) { ctx.imageSmoothingQuality = "high"; }\n'
    html += '  canvas.on("object:modified", function() { saveToLocalStorage(); });\n'
    html += '  canvas.renderAll();\n'
    html += '  loadFromLocalStorage();\n'
    html += '  addLog("[Canvas] Initialized");\n'
    html += '}\n'
    html += '\n'
    html += 'function lanczosKernel(x, a) {\n'
    html += '  a = a || 3;\n'
    html += '  if (x === 0) return 1;\n'
    html += '  if (Math.abs(x) >= a) return 0;\n'
    html += '  var pi = Math.PI;\n'
    html += '  var pix = pi * x;\n'
    html += '  var pixA = pi * x / a;\n'
    html += '  return (Math.sin(pix) * Math.sin(pixA)) / (pix * pixA);\n'
    html += '}\n'
    html += '\n'
    html += 'function lanczosResample(sourceCanvas, targetWidth, targetHeight) {\n'
    html += '  var source = sourceCanvas.getContext("2d").getImageData(0, 0, sourceCanvas.width, sourceCanvas.height);\n'
    html += '  var sourceWidth = sourceCanvas.width;\n'
    html += '  var sourceHeight = sourceCanvas.height;\n'
    html += '  var targetCanvas = document.createElement("canvas");\n'
    html += '  targetCanvas.width = targetWidth;\n'
    html += '  targetCanvas.height = targetHeight;\n'
    html += '  var targetCtx = targetCanvas.getContext("2d");\n'
    html += '  var targetData = targetCtx.createImageData(targetWidth, targetHeight);\n'
    html += '  var scaleX = sourceWidth / targetWidth;\n'
    html += '  var scaleY = sourceHeight / targetHeight;\n'
    html += '  for (var y = 0; y < targetHeight; y++) {\n'
    html += '    var sy = y * scaleY;\n'
    html += '    var syInt = Math.floor(sy);\n'
    html += '    var syFrac = sy - syInt;\n'
    html += '    for (var x = 0; x < targetWidth; x++) {\n'
    html += '      var sx = x * scaleX;\n'
    html += '      var sxInt = Math.floor(sx);\n'
    html += '      var sxFrac = sx - sxInt;\n'
    html += '      var r = 0, g = 0, b = 0, a_total = 0;\n'
    html += '      var weightTotal = 0;\n'
    html += '      for (var dy = -3; dy <= 3; dy++) {\n'
    html += '        var sampleY = syInt + dy;\n'
    html += '        if (sampleY < 0 || sampleY >= sourceHeight) continue;\n'
    html += '        var lanczosY = lanczosKernel((syFrac - dy) / scaleY, 3);\n'
    html += '        for (var dx = -3; dx <= 3; dx++) {\n'
    html += '          var sampleX = sxInt + dx;\n'
    html += '          if (sampleX < 0 || sampleX >= sourceWidth) continue;\n'
    html += '          var lanczosX = lanczosKernel((sxFrac - dx) / scaleX, 3);\n'
    html += '          var weight = lanczosX * lanczosY;\n'
    html += '          var idx = (sampleY * sourceWidth + sampleX) * 4;\n'
    html += '          r += source.data[idx] * weight;\n'
    html += '          g += source.data[idx + 1] * weight;\n'
    html += '          b += source.data[idx + 2] * weight;\n'
    html += '          a_total += source.data[idx + 3] * weight;\n'
    html += '          weightTotal += weight;\n'
    html += '        }\n'
    html += '      }\n'
    html += '      var targetIdx = (y * targetWidth + x) * 4;\n'
    html += '      targetData.data[targetIdx] = r / weightTotal;\n'
    html += '      targetData.data[targetIdx + 1] = g / weightTotal;\n'
    html += '      targetData.data[targetIdx + 2] = b / weightTotal;\n'
    html += '      targetData.data[targetIdx + 3] = a_total / weightTotal;\n'
    html += '    }\n'
    html += '  }\n'
    html += '  targetCtx.putImageData(targetData, 0, 0);\n'
    html += '  return targetCanvas;\n'
    html += '}\n'
    html += '\n'
    html += 'function addImageToStoryboard(src, silent) {\n'
    html += '  silent = silent || false;\n'
    html += '  for (var i = 0; i < storyboardImages.length; i++) {\n'
    html += '    if (storyboardImages[i].src === src) {\n'
    html += '      if (!silent) showToast("Image already in storyboard");\n'
    html += '      return Promise.resolve(false);\n'
    html += '    }\n'
    html += '  }\n'
    html += '  addLog("[Storyboard] Adding image: " + src);\n'
    html += '  return new Promise(function(resolve) {\n'
    html += '    var tempImg = new Image();\n'
    html += '    tempImg.crossOrigin = "Anonymous";\n'
    html += '    tempImg.onload = function() {\n'
    html += '      var sourceWidth = tempImg.width;\n'
    html += '      var sourceHeight = tempImg.height;\n'
    html += '      var targetWidth = PREVIEW_W * 0.33;\n'
    html += '      var finalImageDataURL = src;\n'
    html += '      if (sourceWidth < targetWidth || sourceHeight < targetHeight) {\n'
    html += '        addLog("[Image] Pre-upscaling from " + sourceWidth + "x" + sourceHeight);\n'
    html += '        var sourceCanvas = document.createElement("canvas");\n'
    html += '        sourceCanvas.width = sourceWidth;\n'
    html += '        sourceCanvas.height = sourceHeight;\n'
    html += '        var ctx = sourceCanvas.getContext("2d");\n'
    html += '        ctx.drawImage(tempImg, 0, 0);\n'
    html += '        var upscaleTargetWidth = targetWidth * 2;\n'
    html += '        var upscaleTargetHeight = (sourceHeight / sourceWidth) * upscaleTargetWidth;\n'
    html += '        var upscaledCanvas = lanczosResample(sourceCanvas, upscaleTargetWidth, upscaleTargetHeight);\n'
    html += '        finalImageDataURL = upscaledCanvas.toDataURL("image/png");\n'
    html += '        addLog("[Image] Upscaled to " + upscaleTargetWidth + "x" + upscaleTargetHeight);\n'
    html += '      }\n'
    html += '      fabric.Image.fromURL(finalImageDataURL, function(img) {\n'
    html += '        if (!img) {\n'
    html += '          if (!silent) showToast("Failed to load image");\n'
    html += '          resolve(false);\n'
    html += '          return;\n'
    html += '        }\n'
    html += '        img.set({\n'
    html += '          crossOrigin: "Anonymous",\n'
    html += '          hasControls: true,\n'
    html += '          hasBorders: true,\n'
    html += '          lockRotation: true,\n'
    html += '          minScaleLimit: 0.1,\n'
    html += '          maxScaleLimit: 2.0\n'
    html += '        });\n'
    html += '        storyboardImages.push({\n'
    html += '          src: src,\n'
    html += '          fabricObj: img,\n'
    html += '          originalWidth: sourceWidth,\n'
    html += '          originalHeight: sourceHeight\n'
    html += '        });\n'
    html += '        canvas.add(img);\n'
    html += '        applyLayout(currentTemplate);\n'
    html += '        updateThumbnails();\n'
    html += '        saveToLocalStorage();\n'
    html += '        updateStoryboardBadge();\n'
    html += '        resolve(true);\n'
    html += '      }, { crossOrigin: "Anonymous" });\n'
    html += '    };\n'
    html += '    tempImg.src = src;\n'
    html += '  });\n'
    html += '}\n'
    html += '\n'
    html += 'function addMultipleImages(srcList) {\n'
    html += '  var added = 0;\n'
    html += '  var promises = [];\n'
    html += '  for (var i = 0; i < srcList.length; i++) {\n'
    html += '    promises.push(addImageToStoryboard(srcList[i], true));\n'
    html += '  }\n'
    html += '  Promise.all(promises).then(function(results) {\n'
    html += '    for (var i = 0; i < results.length; i++) if (results[i]) added++;\n'
    html += '    if (added) showToast("Added " + added + " image(s)");\n'
    html += '  });\n'
    html += '}\n'
    html += '\n'
    html += 'function syncSelectedToStoryboard() {\n'
    html += '  var srcs = Array.from(selectedSrcs);\n'
    html += '  if (srcs.length === 0) { showToast("No images selected"); return; }\n'
    html += '  addMultipleImages(srcs);\n'
    html += '}\n'
    html += '\n'
    html += 'function updateStoryboardBadge() {\n'
    html += '  var b = document.getElementById("storyboardCountBadge");\n'
    html += '  if (b) b.innerText = storyboardImages.length;\n'
    html += '}\n'
    html += '\n'
    html += 'function applyLayout(templateName) {\n'
    html += '  if (!canvas || storyboardImages.length === 0) return;\n'
    html += '  currentTemplate = templateName;\n'
    html += '  addLog("[Storyboard] Applying layout: " + templateName);\n'
    html += '  var margin = 20;\n'
    html += '  var availW = PREVIEW_W - margin * 2;\n'
    html += '  var cnt = storyboardImages.length;\n'
    html += '  function getObjHeight(obj) { return obj.height * obj.scaleY; }\n'
    html += '  function placeInGrid(cols, maxHeightPerRow) {\n'
    html += '    var y = margin;\n'
    html += '    for (var i = 0; i < cnt; i++) {\n'
    html += '      var obj = storyboardImages[i].fabricObj;\n'
    html += '      var col = i % cols;\n'
    html += '      if (col === 0 && i !== 0) {\n'
    html += '        var rowMax = 0;\n'
    html += '        for (var j = i - cols; j < i; j++) {\n'
    html += '          rowMax = Math.max(rowMax, getObjHeight(storyboardImages[j].fabricObj));\n'
    html += '        }\n'
    html += '        y += rowMax + margin;\n'
    html += '      }\n'
    html += '      var cellW = (availW - (cols - 1) * margin) / cols;\n'
    html += '      var scale = Math.min(cellW / obj.width, maxHeightPerRow / obj.height);\n'
    html += '      obj.scale(scale);\n'
    html += '      obj.set({ left: margin + col * (cellW + margin), top: y });\n'
    html += '    }\n'
    html += '  }\n'
    html += '  function placeInMasonry(cols) {\n'
    html += '    var columnHeights = [];\n'
    html += '    var columnX = [];\n'
    html += '    for (var c = 0; c < cols; c++) {\n'
    html += '      columnHeights[c] = margin;\n'
    html += '      columnX[c] = margin + c * (availW / cols);\n'
    html += '    }\n'
    html += '    var colWidth = availW / cols;\n'
    html += '    for (var i = 0; i < cnt; i++) {\n'
    html += '      var obj = storyboardImages[i].fabricObj;\n'
    html += '      var shortestCol = 0;\n'
    html += '      for (var c = 1; c < cols; c++) {\n'
    html += '        if (columnHeights[c] < columnHeights[shortestCol]) shortestCol = c;\n'
    html += '      }\n'
    html += '      var scale = colWidth / obj.width;\n'
    html += '      obj.scale(scale);\n'
    html += '      obj.set({ left: columnX[shortestCol], top: columnHeights[shortestCol] });\n'
    html += '      columnHeights[shortestCol] += getObjHeight(obj) + margin;\n'
    html += '    }\n'
    html += '  }\n'
    html += '  function placeInPolaroid() {\n'
    html += '    var centerX = PREVIEW_W / 2;\n'
    html += '    var centerY = PREVIEW_H / 2;\n'
    html += '    var baseScale = 0.4;\n'
    html += '    for (var i = 0; i < cnt; i++) {\n'
    html += '      var obj = storyboardImages[i].fabricObj;\n'
    html += '      var angle = (i - cnt/2) * 5;\n'
    html += '      var scale = baseScale * (1 - i * 0.05);\n'
    html += '      obj.scale(scale);\n'
    html += '      obj.set({ left: centerX - (obj.width * scale) / 2, top: centerY - (obj.height * scale) / 2, angle: angle });\n'
    html += '    }\n'
    html += '  }\n'
    html += '  function placeInTimeline() {\n'
    html += '    var x = margin;\n'
    html += '    var y = margin;\n'
    html += '    var rowHeight = 150;\n'
    html += '    for (var i = 0; i < cnt; i++) {\n'
    html += '      var obj = storyboardImages[i].fabricObj;\n'
    html += '      var scale = rowHeight / obj.height;\n'
    html += '      obj.scale(scale);\n'
    html += '      obj.set({ left: x, top: y });\n'
    html += '      x += (obj.width * scale) + margin;\n'
    html += '      if (x + (obj.width * scale) > PREVIEW_W - margin) {\n'
    html += '        x = margin;\n'
    html += '        y += rowHeight + margin;\n'
    html += '      }\n'
    html += '    }\n'
    html += '  }\n'
    html += '  function placeTwoColumn() {\n'
    html += '    var leftImages = [];\n'
    html += '    var rightImages = [];\n'
    html += '    for (var i = 0; i < cnt; i++) {\n'
    html += '      if (i % 2 === 0) leftImages.push(storyboardImages[i]);\n'
    html += '      else rightImages.push(storyboardImages[i]);\n'
    html += '    }\n'
    html += '    var colWidth = (availW - margin) / 2;\n'
    html += '    var leftY = margin;\n'
    html += '    for (var i = 0; i < leftImages.length; i++) {\n'
    html += '      var obj = leftImages[i].fabricObj;\n'
    html += '      var scale = colWidth / obj.width;\n'
    html += '      obj.scale(scale);\n'
    html += '      obj.set({ left: margin, top: leftY });\n'
    html += '      leftY += getObjHeight(obj) + margin;\n'
    html += '    }\n'
    html += '    var rightY = margin;\n'
    html += '    for (var i = 0; i < rightImages.length; i++) {\n'
    html += '      var obj = rightImages[i].fabricObj;\n'
    html += '      var scale = colWidth / obj.width;\n'
    html += '      obj.scale(scale);\n'
    html += '      obj.set({ left: margin + colWidth + margin, top: rightY });\n'
    html += '      rightY += getObjHeight(obj) + margin;\n'
    html += '    }\n'
    html += '  }\n'
    html += '  function placeCenter() {\n'
    html += '    var obj = storyboardImages[0].fabricObj;\n'
    html += '    var scale = Math.min(availW / obj.width, (PREVIEW_H - margin * 2) / obj.height);\n'
    html += '    obj.scale(scale);\n'
    html += '    obj.set({ left: margin + (availW - obj.width * scale) / 2, top: margin + ((PREVIEW_H - margin * 2) - obj.height * scale) / 2 });\n'
    html += '  }\n'
    html += '  if (templateName === "grid") { placeInGrid(3, 200); }\n'
    html += '  else if (templateName === "twoCol") { placeTwoColumn(); }\n'
    html += '  else if (templateName === "center") { placeCenter(); }\n'
    html += '  else if (templateName === "masonry") { placeInMasonry(3); }\n'
    html += '  else if (templateName === "polaroid") { placeInPolaroid(); }\n'
    html += '  else if (templateName === "timeline") { placeInTimeline(); }\n'
    html += '  else { placeInGrid(3, 200); }\n'
    html += '  canvas.renderAll();\n'
    html += '  saveToLocalStorage();\n'
    html += '}\n'
    html += '\n'
    html += 'function clearAll() {\n'
    html += '  if (confirm("Clear all images from storyboard?")) {\n'
    html += '    for (var i = 0; i < storyboardImages.length; i++) {\n'
    html += '      canvas.remove(storyboardImages[i].fabricObj);\n'
    html += '    }\n'
    html += '    storyboardImages = [];\n'
    html += '    canvas.renderAll();\n'
    html += '    updateThumbnails();\n'
    html += '    localStorage.removeItem(STORAGE_KEY);\n'
    html += '    updateStoryboardBadge();\n'
    html += '    showToast("Storyboard cleared");\n'
    html += '  }\n'
    html += '}\n'
    html += '\n'
    html += 'function resetView() { applyLayout(currentTemplate); }\n'
    html += '\n'
    html += 'function exportStoryboard() {\n'
    html += '  if (storyboardImages.length === 0) { showToast("No images to export"); return; }\n'
    html += '  addLog("[Export] Starting high-quality export");\n'
    html += '  var offCanvas = document.createElement("canvas");\n'
    html += '  offCanvas.width = TARGET_W;\n'
    html += '  offCanvas.height = TARGET_H;\n'
    html += '  var offCtx = offCanvas.getContext("2d");\n'
    html += '  offCtx.fillStyle = canvas.backgroundColor;\n'
    html += '  offCtx.fillRect(0, 0, TARGET_W, TARGET_H);\n'
    html += '  offCtx.imageSmoothingEnabled = true;\n'
    html += '  offCtx.imageSmoothingQuality = "high";\n'
    html += '  for (var i = 0; i < storyboardImages.length; i++) {\n'
    html += '    var obj = storyboardImages[i].fabricObj;\n'
    html += '    var left = obj.left * SCALE;\n'
    html += '    var top = obj.top * SCALE;\n'
    html += '    var width = obj.width * obj.scaleX * SCALE;\n'
    html += '    var height = obj.height * obj.scaleY * SCALE;\n'
    html += '    offCtx.drawImage(obj._element, left, top, width, height);\n'
    html += '  }\n'
    html += '  if (currentLogo) {\n'
    html += '    offCtx.drawImage(currentLogo._element, currentLogo.left * SCALE, currentLogo.top * SCALE,\n'
    html += '      currentLogo.width * currentLogo.scaleX * SCALE, currentLogo.height * currentLogo.scaleY * SCALE);\n'
    html += '  }\n'
    html += '  var a = document.createElement("a");\n'
    html += '  a.download = "storyboard_36x48_300dpi.png";\n'
    html += '  a.href = offCanvas.toDataURL("image/png");\n'
    html += '  a.click();\n'
    html += '  addLog("[Export] Complete");\n'
    html += '}\n'
    html += '\n'
    html += 'function exportWebPreview() {\n'
    html += '  if (storyboardImages.length === 0) { showToast("No images to export"); return; }\n'
    html += '  var offCanvas = document.createElement("canvas");\n'
    html += '  offCanvas.width = PREVIEW_W;\n'
    html += '  offCanvas.height = PREVIEW_H;\n'
    html += '  var offCtx = offCanvas.getContext("2d");\n'
    html += '  offCtx.fillStyle = canvas.backgroundColor;\n'
    html += '  offCtx.fillRect(0, 0, PREVIEW_W, PREVIEW_H);\n'
    html += '  for (var i = 0; i < storyboardImages.length; i++) {\n'
    html += '    var obj = storyboardImages[i].fabricObj;\n'
    html += '    offCtx.drawImage(obj._element, obj.left, obj.top, obj.width * obj.scaleX, obj.height * obj.scaleY);\n'
    html += '  }\n'
    html += '  if (currentLogo) {\n'
    html += '    offCtx.drawImage(currentLogo._element, currentLogo.left, currentLogo.top,\n'
    html += '      currentLogo.width * currentLogo.scaleX, currentLogo.height * currentLogo.scaleY);\n'
    html += '  }\n'
    html += '  var a = document.createElement("a");\n'
    html += '  a.download = "storyboard_preview.png";\n'
    html += '  a.href = offCanvas.toDataURL("image/png");\n'
    html += '  a.click();\n'
    html += '}\n'
    html += '\n'
    html += 'function updateThumbnails() {\n'
    html += '  var container = document.getElementById("storyboardThumbnails");\n'
    html += '  if (!container) return;\n'
    html += '  var html = "";\n'
    html += '  for (var i = 0; i < storyboardImages.length; i++) {\n'
    html += '    html += "<img class=\\"storyboard-thumb\\" src=\\"" + storyboardImages[i].src + "\\" data-index=\\"" + i + "\\">";\n'
    html += '  }\n'
    html += '  container.innerHTML = html;\n'
    html += '  var thumbs = document.querySelectorAll(".storyboard-thumb");\n'
    html += '  for (var i = 0; i < thumbs.length; i++) {\n'
    html += '    thumbs[i].onclick = function() {\n'
    html += '      var idx = parseInt(this.dataset.index);\n'
    html += '      if (!isNaN(idx)) {\n'
    html += '        canvas.remove(storyboardImages[idx].fabricObj);\n'
    html += '        storyboardImages.splice(idx, 1);\n'
    html += '        canvas.renderAll();\n'
    html += '        updateThumbnails();\n'
    html += '        saveToLocalStorage();\n'
    html += '        updateStoryboardBadge();\n'
    html += '        showToast("Image removed");\n'
    html += '      }\n'
    html += '    };\n'
    html += '  }\n'
    html += '}\n'
    html += '\n'
    html += 'function saveToLocalStorage() {\n'
    html += '  var srcs = [];\n'
    html += '  for (var i = 0; i < storyboardImages.length; i++) srcs.push(storyboardImages[i].src);\n'
    html += '  localStorage.setItem(STORAGE_KEY, JSON.stringify(srcs));\n'
    html += '  localStorage.setItem("storyboard_bg_color", canvas.backgroundColor);\n'
    html += '}\n'
    html += '\n'
    html += 'function loadFromLocalStorage() {\n'
    html += '  var stored = localStorage.getItem(STORAGE_KEY);\n'
    html += '  var savedBg = localStorage.getItem("storyboard_bg_color");\n'
    html += '  if (savedBg && canvas) {\n'
    html += '    canvas.backgroundColor = savedBg;\n'
    html += '    document.getElementById("bgColorSelect").value = savedBg;\n'
    html += '  }\n'
    html += '  if (stored) {\n'
    html += '    try {\n'
    html += '      var srcs = JSON.parse(stored);\n'
    html += '      if (srcs && srcs.length) {\n'
    html += '        for (var i = 0; i < srcs.length; i++) {\n'
    html += '          addImageToStoryboard(srcs[i], true);\n'
    html += '        }\n'
    html += '      }\n'
    html += '    } catch(e) { console.warn(e); }\n'
    html += '  }\n'
    html += '}\n'
    html += '\n'
    html += 'function openStoryboardNewTab() {\n'
    html += '  var srcs = [];\n'
    html += '  for (var i = 0; i < storyboardImages.length; i++) srcs.push(storyboardImages[i].src);\n'
    html += '  var w = window.open();\n'
    html += '  if (!w) { showToast("Popup blocked"); return; }\n'
    html += '  w.document.write("<html><head><title>Storyboard</title><style>body{margin:0;background:#0f172a;color:white;}canvas{display:block;margin:20px auto;border:2px solid #475569;background:white;}</style><script src=\\"https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js\\"><\\/script></head><body><canvas id=\\"c\\" width=\\"1080\\" height=\\"1440\\"></canvas><script>var srcs="+JSON.stringify(srcs)+"; var canvas,imgs=[]; var PREVIEW_W=1080,PREVIEW_H=1440,TARGET_W=10800,TARGET_H=14400,SCALE=TARGET_W/PREVIEW_W; function loadAll(){ if(!srcs.length) return; var loaded=0; for(var i=0;i<srcs.length;i++){ fabric.Image.fromURL(srcs[i],function(img){ if(!img) return; img.set({hasControls:true}); imgs.push(img); loaded++; if(loaded===srcs.length) drawCanvas(); },{crossOrigin:\\"Anonymous\\"}); } } function drawCanvas(){ canvas=new fabric.Canvas(\\"c\\"); canvas.setDimensions({width:PREVIEW_W,height:PREVIEW_H}); canvas.backgroundColor=\\"white\\"; var margin=20,w=PREVIEW_W-margin*2,cols=3,cellW=(w-(cols-1)*margin)/cols; var y=margin; for(var i=0;i<imgs.length;i++){ var img=imgs[i]; var col=i%cols; if(col===0 && i!==0){ var rowMax=0; for(var j=i-cols;j<i;j++) rowMax=Math.max(rowMax,imgs[j].height*imgs[j].scaleY); y+=rowMax+margin; } var scale=Math.min(cellW/img.width,200/img.height); img.scale(scale); img.set({left:margin+col*(cellW+margin),top:y}); canvas.add(img); } canvas.renderAll(); } loadAll();<\\/script></body></html>");\n'
    html += '  w.document.close();\n'
    html += '}\n'
    html += '\n'
    html += 'document.getElementById("bgColorSelect").addEventListener("change", function(e) {\n'
    html += '  canvas.backgroundColor = e.target.value;\n'
    html += '  canvas.renderAll();\n'
    html += '  saveToLocalStorage();\n'
    html += '});\n'
    html += '\n'
    html += 'document.getElementById("addLogoBtn").addEventListener("click", function() {\n'
    html += '  var file = document.getElementById("logoUpload").files[0];\n'
    html += '  if (!file) { showToast("Select an SVG file first"); return; }\n'
    html += '  var reader = new FileReader();\n'
    html += '  reader.onload = function(e) {\n'
    html += '    fabric.loadSVGFromString(e.target.result, function(objects, options) {\n'
    html += '      var logo = fabric.util.groupSVGElements(objects, options);\n'
    html += '      logo.set({ left: PREVIEW_W - 100, top: 20, scaleX: 0.5, scaleY: 0.5, hasControls: true });\n'
    html += '      if (currentLogo) canvas.remove(currentLogo);\n'
    html += '      currentLogo = logo;\n'
    html += '      canvas.add(logo);\n'
    html += '      canvas.renderAll();\n'
    html += '      saveToLocalStorage();\n'
    html += '    });\n'
    html += '  };\n'
    html += '  reader.readAsText(file);\n'
    html += '});\n'
    html += '\n'
    html += 'document.getElementById("removeLogoBtn").addEventListener("click", function() {\n'
    html += '  if (currentLogo) {\n'
    html += '    canvas.remove(currentLogo);\n'
    html += '    currentLogo = null;\n'
    html += '    canvas.renderAll();\n'
    html += '    saveToLocalStorage();\n'
    html += '  }\n'
    html += '});\n'
    html += '\n'
    html += 'document.getElementById("selectAllBtn").onclick = selectAll;\n'
    html += 'document.getElementById("deselectAllBtn").onclick = deselectAll;\n'
    html += 'document.getElementById("syncSelectedBtn").onclick = syncSelectedToStoryboard;\n'
    html += 'document.getElementById("openStoryboardBtn").onclick = function(){ document.getElementById("storyboardModal").classList.add("active"); };\n'
    html += 'document.getElementById("closeStoryboardBtn").onclick = function(){ document.getElementById("storyboardModal").classList.remove("active"); };\n'
    html += 'document.getElementById("exportStoryboardBtn").onclick = exportStoryboard;\n'
    html += 'document.getElementById("exportWebBtn").onclick = exportWebPreview;\n'
    html += 'document.getElementById("clearStoryboardBtn").onclick = clearAll;\n'
    html += 'document.getElementById("applyTemplateBtn").onclick = function(){ var tpl = document.getElementById("templateSelect").value; applyLayout(tpl); };\n'
    html += 'document.getElementById("resetViewBtn").onclick = resetView;\n'
    html += 'document.getElementById("openStoryboardNewTabBtn").onclick = openStoryboardNewTab;\n'
    html += 'window.onclick = function(e){ if(e.target === document.getElementById("storyboardModal")){ document.getElementById("storyboardModal").classList.remove("active"); } };\n'
    html += '\n'
    html += 'initCanvas();\n'
    html += 'renderGallery(allPosts);\n'
    html += 'updateWordCloud(allPosts);\n'
    html += 'addLog("=== GALLERY READY ===");\n'
    html += '</script>\n</body>\n</html>'
    
    return html

def main():
    print("=" * 70)
    print("MR. DOUGLAS GALLERY BUILDER v0021")
    print("Working Gallery + Lanczos High-Quality Scaling")
    print("=" * 70)
    print()
    
    print("[1/4] Building gallery...")
    posts = load_posts()
    posts = add_historic_images(posts)
    logger.info(f"Total posts: {len(posts)}")
    
    print("[2/4] Starting error server (port 8001)...")
    error_server_ok = start_error_server()
    
    print("[3/4] Starting HTTP server (port 8000)...")
    http_server_ok = start_http_server()
    
    print("[4/4] Generating HTML...")
    html = build_html(posts)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    logger.info(f"Generated {OUTPUT_HTML.resolve()}")
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
    
    print()
    print("=" * 70)
    print("BUILD COMPLETE!")
    print("=" * 70)
    print()
    print(f"📁 HTML: {OUTPUT_HTML.resolve()}")
    print()
    print("🌐 Opening browser...")
    print("   http://localhost:8000/index_v0021.html")
    print()
    print("📊 Status:")
    print(f"   Error Server (8001): {'✅' if error_server_ok else '❌'}")
    print(f"   HTTP Server (8000): {'✅' if http_server_ok else '❌'}")
    print()
    print("✨ FEATURES:")
    print("   - Background color picker")
    print("   - SVG logo upload")
    print("   - Multiple layout templates")
    print("   - Lanczos high-quality image scaling (prevents pixelation)")
    print("   - Dual export (300 DPI print + web preview)")
    print()
    print("⚠️  Press Ctrl+C to stop all servers")
    
    threading.Thread(target=open_browser, args=('http://localhost:8000/index_v0021.html',), daemon=True).start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        cleanup()
        print("Done.")

if __name__ == "__main__":
    main()