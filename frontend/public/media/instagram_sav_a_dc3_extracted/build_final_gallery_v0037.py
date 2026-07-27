#!/usr/bin/env python3
"""
build_final_gallery_v0037.py - COMPLIANT WITH ALL FEATURES + LOGGING
Based on working v0031 baseline with added canvas suite, persistence, and complete logging
"""

import json
import sqlite3
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
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path("instagram_posts.db")
OUTPUT_HTML = Path("index_v0037.html")
ACCOUNT_OWNER = "sav_a_dc3"

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

atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda s, f: cleanup() or sys.exit(0))
signal.signal(signal.SIGTERM, lambda s, f: cleanup() or sys.exit(0))

def load_posts():
    posts = []
    if DB_PATH.exists():
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
            mention_pattern = re.compile(r'@([a-zA-Z0-9_\.]+)')
            all_mentions = []
            for comment in post['comments']:
                if not comment.startswith(('Count:', 'Reported by IG:', 'Saved:', 'Comments for')):
                    mentions = mention_pattern.findall(comment)
                    all_mentions.extend(mentions)
            filtered = [m for m in all_mentions if m.lower() != ACCOUNT_OWNER.lower()]
            post['author'] = filtered[0] if filtered else ACCOUNT_OWNER
            posts.append(post)
        conn.close()
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
    return posts

def build_html(posts):
    # Direct inline JSON (working method from v0031)
    posts_json = json.dumps(posts, ensure_ascii=False)
    print(f"JSON size: {len(posts_json)} bytes for {len(posts)} posts")
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mr. Douglas Gallery v0037 - Complete with Canvas Suite</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0f172a;color:#e2e8f0;font-family:system-ui}
.search-header{position:sticky;top:0;z-index:20;background:rgba(15,23,42,0.95);backdrop-filter:blur(8px);border-bottom:1px solid #334155;padding:1rem}
.search-container{max-width:1200px;margin:0 auto}
.search-input{width:100%;padding:0.75rem 1rem;background:#1e293b;border:1px solid #475569;border-radius:2rem;color:#f1f5f9;font-size:1rem}
.gallery-toolbar{position:sticky;top:90px;z-index:15;display:flex;gap:12px;margin:0 1.5rem 1rem;flex-wrap:wrap;align-items:center;background:#1e293b;padding:8px 12px;border-radius:12px}
.gallery-toolbar button{background:#334155;color:white;border:none;padding:6px 12px;border-radius:8px;cursor:pointer}
.gallery-toolbar button.primary{background:#3b82f6}
.gallery-toolbar button.warning{background:#f59e0b}
.gallery-toolbar button.success{background:#10b981}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1.5rem;padding:1.5rem;max-width:1400px;margin:0 auto}
.card{background:#1e293b;border-radius:1rem;overflow:hidden;cursor:pointer;position:relative;transition:transform 0.2s}
.card:hover{transform:translateY(-4px)}
.card-media{width:100%;aspect-ratio:4/3;object-fit:cover;background:#0f172a}
.card-content{padding:1rem}
.card-meta{display:flex;justify-content:space-between;font-size:0.75rem;color:#94a3b8;margin-bottom:0.5rem;flex-wrap:wrap}
.author-name{color:#60a5fa}
.card-caption{font-size:0.875rem;color:#cbd5e1;margin-bottom:0.75rem;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.select-checkbox{position:absolute;top:8px;left:8px;width:20px;height:20px;cursor:pointer;z-index:10}
.carousel{display:flex;gap:0.5rem;overflow-x:auto;margin:0.5rem 0;padding-bottom:4px}
.carousel-item{width:60px;height:60px;object-fit:cover;border-radius:8px;cursor:pointer;background:#0f172a}
.carousel-video-item{width:60px;height:60px;background:#1e293b;border-radius:8px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:20px}
.comments-btn{background:none;border:none;color:#3b82f6;cursor:pointer;font-size:0.7rem;padding:0.25rem 0.5rem;border-radius:1rem;background:#1e293b}
.comments-btn:hover{background:#3b82f6;color:white}
.card-footer{display:flex;justify-content:space-between;align-items:center;margin-top:0.5rem}
.insta-link{font-size:0.75rem;color:#3b82f6;text-decoration:none}
.storyboard-modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:2000;overflow:auto}
.storyboard-modal.active{display:flex;flex-direction:column}
.storyboard-container{background:#1e293b;margin:20px auto;padding:20px;border-radius:16px;max-width:95%;width:1200px}
#storyboardCanvas{border:2px solid #475569;border-radius:8px;background:white;display:block;margin:0 auto}
.storyboard-controls{display:flex;gap:10px;justify-content:center;margin:15px 0;flex-wrap:wrap}
.storyboard-controls button{background:#3b82f6;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer}
.storyboard-thumb{width:80px;height:80px;object-fit:cover;border-radius:8px;cursor:pointer;margin-right:8px}
.toast{position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1e293b;color:#e2e8f0;padding:10px 20px;border-radius:40px;z-index:3000;opacity:0;transition:opacity 0.2s;pointer-events:none}
.toast.show{opacity:1}
.debug-panel{position:fixed;bottom:10px;right:10px;background:#1e293b;color:#0f0;font-family:monospace;font-size:10px;padding:8px;border-radius:8px;z-index:9999;max-width:500px;max-height:300px;overflow:auto;opacity:0.95}
.debug-header{display:flex;justify-content:space-between;margin-bottom:5px;background:#334155;padding:4px 8px;border-radius:4px}
.debug-close{color:#ef4444;cursor:pointer;margin-left:10px}
.debug-save{color:#10b981;cursor:pointer;margin-right:10px}
.image-status{font-size:9px;border-top:1px solid #334155;margin-top:5px;padding-top:5px}
.lightbox{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.95);display:none;align-items:center;justify-content:center;z-index:10000}
.lightbox.active{display:flex}
.lightbox-content{position:relative;max-width:90vw;max-height:90vh}
.lightbox-media{max-width:90vw;max-height:85vh;object-fit:contain}
.lightbox-close{position:absolute;top:-40px;right:-40px;color:white;font-size:2rem;cursor:pointer;background:rgba(0,0,0,0.5);width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center}
.lightbox-close:hover{background:#ef4444}
.lightbox-caption{position:absolute;bottom:-60px;left:0;right:0;color:white;text-align:center;padding:10px;background:rgba(0,0,0,0.7);border-radius:8px;font-size:14px}
.lightbox-nav{position:absolute;top:50%;transform:translateY(-50%);background:rgba(0,0,0,0.5);color:white;border:none;font-size:2rem;cursor:pointer;padding:10px 15px;border-radius:50%;z-index:10001}
.lightbox-nav:hover{background:rgba(0,0,0,0.8)}
.lightbox-prev{left:20px}
.lightbox-next{right:20px}
.modal{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1e293b;border-radius:1rem;max-width:600px;width:90%;max-height:80vh;overflow-y:auto;z-index:11000;display:none;padding:1rem}
.modal.active{display:block}
.modal-header{display:flex;justify-content:space-between;margin-bottom:1rem;padding-bottom:0.5rem;border-bottom:1px solid #475569}
.modal-close{color:#ef4444;cursor:pointer;font-size:1.5rem;line-height:1}
.comment-item{padding:8px 12px;margin:4px 0;background:#0f172a;border-radius:8px;word-wrap:break-word}
.canvas-toolbar{display:flex;gap:8px;margin:10px 0;flex-wrap:wrap;border-top:1px solid #475569;padding-top:10px}
.canvas-toolbar button{background:#8b5cf6;border:none;color:white;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px}
.canvas-toolbar button:hover{background:#7c3aed}
</style>
</head>
<body>

<div class="debug-panel" id="debugPanel">
    <div class="debug-header">
        <strong>🔍 Debug Console</strong>
        <span>
            <span id="debugSaveBtn" class="debug-save">💾</span>
            <span id="debugCloseBtn" class="debug-close">✕</span>
        </span>
    </div>
    <div id="debugLog"></div>
    <div id="imageStatusLog" class="image-status"></div>
</div>

<div class="search-header">
    <div class="search-container">
        <input type="text" id="searchInput" class="search-input" placeholder="Search posts...">
    </div>
</div>

<div class="gallery-toolbar">
    <span>Select images:</span>
    <button id="selectAllBtn">Select All</button>
    <button id="deselectAllBtn">Deselect All</button>
    <button id="syncSelectedBtn" class="primary">📋 Sync to Storyboard</button>
    <button id="openStoryboardBtn" class="success">🎬 Open Storyboard <span id="storyboardCountBadge">0</span></button>
    <button id="checkMissingBtn" class="warning">🔍 Check Missing</button>
    <span id="selectedCount">0 selected</span>
</div>

<div id="galleryGrid" class="grid"></div>

<div id="storyboardModal" class="storyboard-modal">
    <div class="storyboard-container">
        <div style="display:flex;justify-content:space-between;">
            <h3>Storyboard Builder - Complete Canvas Suite</h3>
            <button id="closeStoryboardBtn" style="background:#ef4444;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer">Close</button>
        </div>
        <div class="storyboard-controls">
            <div style="display:flex;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
                <label>Background:</label>
                <select id="bgColorSelect">
                    <option value="#ffffff">White</option>
                    <option value="#0f172a">Dark Blue</option>
                    <option value="#1e293b">Slate</option>
                    <option value="#f5f5f0">Cream</option>
                    <option value="#1a1a2e">Deep Navy</option>
                    <option value="#2d2d2d">Charcoal</option>
                </select>
                <label>Logo SVG:</label>
                <input type="file" id="logoUpload" accept="image/svg+xml">
                <button id="addLogoBtn" style="background:#10b981;border:none;color:white;padding:4px 12px;border-radius:4px">Add Logo</button>
                <button id="removeLogoBtn" style="background:#ef4444;border:none;color:white;padding:4px 12px;border-radius:4px">Remove Logo</button>
            </div>
            <select id="templateSelect">
                <option value="grid">Grid (3 cols)</option>
                <option value="center">Single centered</option>
                <option value="masonry">Masonry</option>
            </select>
            <button id="applyTemplateBtn">Apply Template</button>
            <button id="exportStoryboardBtn" class="primary">📸 Export 300 DPI PNG</button>
            <button id="clearStoryboardBtn">Clear Canvas</button>
        </div>
        <canvas id="storyboardCanvas" width="1080" height="1440"></canvas>
        <div><strong>Images (click to remove):</strong>
            <div id="storyboardThumbnails" style="display:flex;gap:12px;overflow-x:auto;padding:8px;"></div>
        </div>
        <div class="canvas-toolbar" id="canvasToolbar">
            <button id="drawModeBtn">✏️ Draw</button>
            <button id="addTextBtn">📝 Text</button>
            <button id="addRectBtn">⬜ Rect</button>
            <button id="addCircleBtn">● Circle</button>
            <button id="addTriangleBtn">▲ Triangle</button>
            <button id="grayscaleBtn">⚫ Grayscale</button>
            <button id="sepiaBtn">🟤 Sepia</button>
            <button id="brightnessBtn">☀️ Brightness</button>
            <button id="contrastBtn">◐ Contrast</button>
            <button id="removeFiltersBtn">⟳ Reset Filter</button>
            <button id="bringFrontBtn">⬆️ Bring Front</button>
            <button id="sendBackBtn">⬇️ Send Back</button>
            <button id="duplicateBtn">📑 Duplicate</button>
            <button id="clearCanvasBtn" style="background:#ef4444;">🗑️ Clear All</button>
        </div>
    </div>
</div>

<div id="toast" class="toast"></div>

<div id="lightbox" class="lightbox">
    <button class="lightbox-nav lightbox-prev">‹</button>
    <div class="lightbox-content">
        <div id="lightboxCloseBtn" class="lightbox-close">×</div>
        <div id="lightboxMediaContainer"></div>
        <div id="lightboxCaption" class="lightbox-caption"></div>
    </div>
    <button class="lightbox-nav lightbox-next">›</button>
</div>

<div id="commentsModal" class="modal">
    <div class="modal-header">
        <strong>💬 Comments</strong>
        <span id="commentsModalClose" class="modal-close">&times;</span>
    </div>
    <div id="commentsList"></div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
<script>
// ============================================================================
// PATH: index_v0037.html (top of script section)
// WHAT: Complete log capture system - captures console, errors, rejections
// WHY: Without capture, errors are invisible in production; localStorage provides persistence across reloads
//
// MENTAL MODEL BEFORE: console.error writes to browser console only; user never sees; errors lost on reload
// MENTAL MODEL AFTER: All console output captured to array, localStorage backup, exportable to file
//
// FAILURE MODE: If capture fails, check browser console for errors; debug panel may remain empty
//
// VERIFIES WITH: Open browser console (F12), see "=== LOG CAPTURE SYSTEM ACTIVE ===";
//   Click any button, see captured log in debug panel; Click 💾, download logs file with timestamp
//
// Source (Tier 2): MDN Web API Console: https://developer.mozilla.org/en-US/docs/Web/API/console
// ============================================================================

// ========== COMPLETE LOG CAPTURE SYSTEM ==========
var capturedLogs = [];
var originalConsole = {
    log: console.log,
    error: console.error,
    warn: console.warn,
    info: console.info
};

function addToCapturedLog(level, args) {
    var timestamp = new Date().toISOString();
    var msg = Array.from(args).join(' ');
    var logEntry = { timestamp: timestamp, level: level, message: msg };
    capturedLogs.push(logEntry);
    if (capturedLogs.length > 1000) capturedLogs.shift();
    try {
        localStorage.setItem('gallery_captured_logs', JSON.stringify(capturedLogs.slice(-500)));
    } catch(e) {}
}

console.log = function() { addToCapturedLog('LOG', arguments); originalConsole.log.apply(console, arguments); };
console.error = function() { addToCapturedLog('ERROR', arguments); originalConsole.error.apply(console, arguments); };
console.warn = function() { addToCapturedLog('WARN', arguments); originalConsole.warn.apply(console, arguments); };
console.info = function() { addToCapturedLog('INFO', arguments); originalConsole.info.apply(console, arguments); };

window.addEventListener('error', function(e) {
    var errorMsg = e.message + ' at ' + e.filename + ':' + e.lineno;
    capturedLogs.push({ timestamp: new Date().toISOString(), level: 'UNCAUGHT', message: errorMsg, stack: e.error?.stack });
    var debugDiv = document.getElementById('debugLog');
    if (debugDiv) {
        var entry = document.createElement('div');
        entry.textContent = new Date().toLocaleTimeString() + ' [UNCAUGHT] ' + errorMsg;
        entry.style.color = '#ef4444';
        debugDiv.appendChild(entry);
    }
    return false;
});

window.addEventListener('unhandledrejection', function(e) {
    var reasonMsg = e.reason?.message || String(e.reason);
    capturedLogs.push({ timestamp: new Date().toISOString(), level: 'REJECTION', message: reasonMsg });
    var debugDiv = document.getElementById('debugLog');
    if (debugDiv) {
        var entry = document.createElement('div');
        entry.textContent = new Date().toLocaleTimeString() + ' [REJECTION] ' + reasonMsg;
        entry.style.color = '#f59e0b';
        debugDiv.appendChild(entry);
    }
});

function exportCapturedLogs() {
    var logsText = capturedLogs.map(function(l) { return l.timestamp + ' [' + l.level + '] ' + l.message; }).join('\\n');
    var blob = new Blob([logsText], {type: 'text/plain'});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'gallery_complete_logs_' + new Date().toISOString().slice(0,19).replace(/:/g, '-') + '.txt';
    a.click();
    URL.revokeObjectURL(a.href);
}

try {
    var savedLogs = localStorage.getItem('gallery_captured_logs');
    if (savedLogs) {
        var previous = JSON.parse(savedLogs);
        capturedLogs = previous.concat(capturedLogs);
        console.log('Loaded ' + previous.length + ' previous logs from storage');
    }
} catch(e) {}

console.log('=== LOG CAPTURE SYSTEM ACTIVE ===');

// Global error handler
window.onerror = function(msg, url, line, col, error) {
    var errorMsg = "ERROR: " + msg + " at line " + line;
    console.error(errorMsg);
    var debugDiv = document.getElementById("debugLog");
    if(debugDiv) {
        var entry = document.createElement("div");
        entry.textContent = new Date().toLocaleTimeString() + " [ERROR] " + errorMsg;
        entry.style.color = "#ef4444";
        debugDiv.appendChild(entry);
    }
    return false;
};

console.log("=== GALLERY v0037 STARTING ===");

var allPosts = ''' + posts_json + ''';
console.log("Posts loaded:", allPosts.length);

var allLogs = [];
var failedImages = {};
var loadedImages = {};
var currentLightboxIndex = 0;
var currentLightboxMedia = [];
var selectedSrcs = new Set();
var canvas = null;
var storyboardImages = [];
var currentLogo = null;
var isDrawingMode = false;
var PREVIEW_W = 1080;
var PREVIEW_H = 1440;
var TARGET_W = 10800;
var TARGET_H = 14400;
var SCALE = TARGET_W / PREVIEW_W;
var STORAGE_KEYS = {
    IMAGES: 'storyboard_images_data_v2',
    BG: 'storyboard_bg_color_v2',
    TEMPLATE: 'storyboard_template_v2'
};

function addLog(msg, type) {
    var timestamp = new Date().toLocaleTimeString();
    var prefix = type === "error" ? "[ERROR] " : (type === "success" ? "[OK] " : "[INFO] ");
    var color = type === "error" ? "#ef4444" : (type === "success" ? "#10b981" : "#60a5fa");
    var fullMsg = timestamp + " " + prefix + msg;
    var logDiv = document.getElementById("debugLog");
    if(logDiv) {
        var entry = document.createElement("div");
        entry.textContent = fullMsg;
        entry.style.color = color;
        logDiv.appendChild(entry);
        entry.scrollIntoView();
    }
    console.log(fullMsg);
    allLogs.push(fullMsg);
    if(allLogs.length > 500) allLogs.shift();
}

function saveLogs() {
    if(allLogs.length === 0) { addLog("No logs to save", "error"); return; }
    exportCapturedLogs();
    addLog("Saved " + allLogs.length + " logs", "success");
}

function showToast(msg, isError) {
    var t = document.getElementById("toast");
    if(t) {
        t.textContent = msg;
        t.classList.add("show");
        setTimeout(function() { t.classList.remove("show"); }, 2000);
    }
    addLog(msg, isError ? "error" : "success");
}

function getMediaPath(folder, file) {
    return folder + "/" + file;
}

function isVideo(filename) {
    if(!filename) return false;
    var ext = filename.toLowerCase();
    return ext.endsWith(".mp4") || ext.endsWith(".mov") || ext.endsWith(".avi") || ext.endsWith(".mkv");
}

// ============================================================================
// PATH: index_v0037.html (lightbox functions)
// WHAT: Event delegation for gallery clicks, proper lightbox with navigation
// WHY: Direct onclick handlers lost when grid.innerHTML = '' during pagination/search
//
// MENTAL MODEL BEFORE: each card has onclick listener; on search, grid.innerHTML clears, listeners lost
// MENTAL MODEL AFTER: single listener on parent container; uses event.target.closest() to find card
//
// FAILURE MODE: If clicks don't open lightbox, check galleryGrid has event listener; console shows "Lightbox opened"
//
// VERIFIES WITH: Click any image card, lightbox opens with navigation arrows; console shows "Lightbox opened with X items"
//
// Source (Tier 2): MDN Event Delegation: https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Building_blocks/Events#event_delegation
// ============================================================================

function openLightbox(mediaItems, startIndex, caption) {
    currentLightboxMedia = mediaItems;
    currentLightboxIndex = startIndex;
    var captionDiv = document.getElementById("lightboxCaption");
    if(captionDiv) captionDiv.textContent = caption || "";
    showLightboxMedia(currentLightboxIndex);
    var lightbox = document.getElementById("lightbox");
    if(lightbox) lightbox.classList.add("active");
    addLog("Lightbox opened with " + mediaItems.length + " items", "info");
}

function showLightboxMedia(index) {
    var container = document.getElementById("lightboxMediaContainer");
    var media = currentLightboxMedia[index];
    if(!media || !container) return;
    container.innerHTML = "";
    if(isVideo(media.url)) {
        var video = document.createElement("video");
        video.src = media.url;
        video.controls = true;
        video.style.maxWidth = "90vw";
        video.style.maxHeight = "85vh";
        video.className = "lightbox-media";
        container.appendChild(video);
    } else {
        var img = document.createElement("img");
        img.src = media.url;
        img.style.maxWidth = "90vw";
        img.style.maxHeight = "85vh";
        img.className = "lightbox-media";
        img.onload = function() { console.log('Lightbox image loaded:', media.url.split('/').pop()); };
        img.onerror = function() { console.error('Lightbox image failed:', media.url); };
        container.appendChild(img);
    }
}

function closeLightbox() {
    var lightbox = document.getElementById("lightbox");
    if(lightbox) lightbox.classList.remove("active");
    addLog("Lightbox closed", "info");
}

function prevLightbox() {
    if(currentLightboxMedia.length === 0) return;
    currentLightboxIndex = (currentLightboxIndex - 1 + currentLightboxMedia.length) % currentLightboxMedia.length;
    showLightboxMedia(currentLightboxIndex);
}

function nextLightbox() {
    if(currentLightboxMedia.length === 0) return;
    currentLightboxIndex = (currentLightboxIndex + 1) % currentLightboxMedia.length;
    showLightboxMedia(currentLightboxIndex);
}

function showComments(shortcode) {
    addLog("Loading comments for: " + shortcode, "info");
    var post = null;
    for(var i=0;i<allPosts.length;i++) {
        if(allPosts[i].shortcode === shortcode) {
            post = allPosts[i];
            break;
        }
    }
    var commentsList = document.getElementById("commentsList");
    if(!commentsList) return;
    if(!post || !post.comments || post.comments.length === 0) {
        commentsList.innerHTML = "<div style='text-align:center;padding:20px;'>No comments</div>";
    } else {
        var html = "";
        for(var i=0;i<post.comments.length;i++) {
            var safeComment = post.comments[i].replace(/</g, '&lt;').replace(/>/g, '&gt;');
            html += "<div class='comment-item'>💬 " + safeComment + "</div>";
        }
        commentsList.innerHTML = html;
        addLog("Displayed " + post.comments.length + " comments", "success");
    }
    var modal = document.getElementById("commentsModal");
    if(modal) modal.classList.add("active");
}

function trackImageLoad(img) {
    var src = img.src;
    if(!loadedImages[src]) {
        loadedImages[src] = true;
        delete failedImages[src];
        addLog("✓ " + src.split('/').pop(), "success");
        updateImageStatus();
    }
}

function trackImageError(img) {
    var src = img.src;
    if(!failedImages[src]) {
        failedImages[src] = true;
        delete loadedImages[src];
        addLog("✗ FAILED: " + src.split('/').pop(), "error");
        updateImageStatus();
    }
}

function updateImageStatus() {
    var total = Object.keys(failedImages).length + Object.keys(loadedImages).length;
    var failedCount = Object.keys(failedImages).length;
    var statusDiv = document.getElementById("imageStatusLog");
    if(!statusDiv) return;
    var html = '<div>📊 ' + total + ' total | <span style="color:#10b981">' + Object.keys(loadedImages).length + ' loaded</span> | <span style="color:#ef4444">' + failedCount + ' failed</span></div>';
    if(failedCount > 0) {
        var failList = Object.keys(failedImages).slice(0,3);
        html += '<div style="color:#ef4444">Failed: ' + failList.map(function(s){return s.split('/').pop();}).join(', ') + (failedCount > 3 ? '...' : '') + '</div>';
    }
    statusDiv.innerHTML = html;
}

function renderGallery(posts) {
    addLog("Rendering " + posts.length + " posts", "info");
    var grid = document.getElementById("galleryGrid");
    if(!grid) return;
    if(!posts.length) {
        grid.innerHTML = "<div style='text-align:center;padding:3rem;'>No posts match.</div>";
        return;
    }
    var htmlStr = "";
    for(var idx=0; idx<posts.length; idx++){
        var post = posts[idx];
        var firstMedia = post.all_media && post.all_media.length ? post.all_media[0] : null;
        var mediaPath = firstMedia ? getMediaPath(post.folder_name, firstMedia) : "";
        var isVideoPost = firstMedia && isVideo(firstMedia);
        
        var mediaArray = [];
        if(post.all_media) {
            for(var i=0;i<post.all_media.length;i++) {
                mediaArray.push({
                    url: getMediaPath(post.folder_name, post.all_media[i]),
                    type: isVideo(post.all_media[i]) ? "video" : "image"
                });
            }
        }
        var mediaArrayJson = JSON.stringify(mediaArray).replace(/"/g, '&quot;');
        
        var carouselHtml = "";
        if(post.all_media && post.all_media.length > 1) {
            carouselHtml = "<div class='carousel'>";
            for(var i=0;i<post.all_media.length;i++) {
                var mediaFile = post.all_media[i];
                var mediaUrl = getMediaPath(post.folder_name, mediaFile);
                if(isVideo(mediaFile)) {
                    carouselHtml += "<div class='carousel-video-item' data-url='" + mediaUrl + "'>🎬</div>";
                } else {
                    carouselHtml += "<img class='carousel-item' src='" + mediaUrl + "' data-url='" + mediaUrl + "' loading='lazy'>";
                }
            }
            carouselHtml += "</div>";
        }
        
        var mediaHtml = "";
        if(firstMedia) {
            if(isVideoPost) {
                mediaHtml = "<div style='position:relative;background:#0f172a;display:flex;align-items:center;justify-content:center;height:100%;min-height:200px;'>🎬 VIDEO</div>";
            } else {
                mediaHtml = "<img class='card-media' src='" + mediaPath + "' loading='lazy' onload='trackImageLoad(this)' onerror='trackImageError(this)'>";
            }
        } else {
            mediaHtml = "<div class='card-media'>No media</div>";
        }
        
        var shortCaption = post.caption ? (post.caption.length > 120 ? post.caption.substring(0,120) + "..." : post.caption) : "";
        
        htmlStr += "<div class='card' data-shortcode='" + post.shortcode + "' data-media='" + mediaArrayJson + "' data-caption='" + (post.caption || "").replace(/"/g, '&quot;') + "'>";
        htmlStr += "<div style='position:relative;width:100%;aspect-ratio:4/3;'>" + mediaHtml + "</div>";
        htmlStr += "<div class='card-content'>";
        htmlStr += "<div class='card-meta'><span class='author-name'>@" + post.author + "</span><span>📅 " + new Date(post.date).toLocaleDateString() + "</span><span>❤️ " + post.likes + "</span></div>";
        if(shortCaption) htmlStr += "<div class='card-caption'>" + shortCaption.replace(/</g, '&lt;').replace(/>/g, '&gt;') + "</div>";
        if(carouselHtml) htmlStr += carouselHtml;
        htmlStr += "<div class='card-footer'>";
        htmlStr += "<a href='" + post.instagram_url + "' target='_blank' class='insta-link' onclick='event.stopPropagation()'>🔗 Instagram</a>";
        htmlStr += "<button class='comments-btn' data-shortcode='" + post.shortcode + "'>💬 " + (post.comments ? post.comments.length : 0) + "</button>";
        htmlStr += "</div></div></div>";
    }
    grid.innerHTML = htmlStr;
    
    // Event delegation for card clicks
    var galleryGrid = document.getElementById('galleryGrid');
    if (galleryGrid) {
        galleryGrid.removeEventListener('click', gridClickHandler);
        galleryGrid.addEventListener('click', gridClickHandler);
    }
    
    document.querySelectorAll(".carousel-item, .carousel-video-item").forEach(function(item) {
        item.onclick = function(e) {
            e.stopPropagation();
            var card = this.closest(".card");
            var mediaData = JSON.parse(card.dataset.media);
            var url = this.dataset.url;
            var index = 0;
            for(var j=0;j<mediaData.length;j++) {
                if(mediaData[j].url === url) {
                    index = j;
                    break;
                }
            }
            openLightbox(mediaData, index, card.dataset.caption);
        };
    });
    
    document.querySelectorAll(".comments-btn").forEach(function(btn) {
        btn.onclick = function(e) {
            e.stopPropagation();
            showComments(this.dataset.shortcode);
        };
    });
    
    addCheckboxesToCards();
}

function gridClickHandler(e) {
    var card = e.target.closest('.card');
    if (!card) return;
    
    if (e.target.closest('.select-checkbox') || 
        e.target.closest('.comments-btn') || 
        e.target.closest('.insta-link') ||
        e.target.closest('.carousel-item') ||
        e.target.closest('.carousel-video-item')) {
        return;
    }
    
    var mediaData = card.dataset.media;
    if (mediaData) {
        try {
            var mediaArray = JSON.parse(mediaData);
            if (mediaArray && mediaArray.length) {
                openLightbox(mediaArray, 0, card.dataset.caption || '');
            }
        } catch(err) {
            console.error('Failed to parse media data:', err);
        }
    }
}

function addCheckboxesToCards() {
    var cards = document.querySelectorAll(".card");
    addLog("Adding checkboxes to " + cards.length + " cards", "info");
    for(var i=0;i<cards.length;i++){
        if(cards[i].querySelector(".select-checkbox")) continue;
        var img = cards[i].querySelector("img");
        if(!img || !img.src) continue;
        var chk = document.createElement("input");
        chk.type = "checkbox";
        chk.className = "select-checkbox";
        chk.dataset.src = img.src;
        chk.onclick = function(e) { e.stopPropagation(); };
        chk.onchange = function(e) {
            e.stopPropagation();
            var src = this.dataset.src;
            if(this.checked){
                if(!selectedSrcs.has(src)) {
                    selectedSrcs.add(src);
                    addImageToStoryboard(src);
                }
            } else {
                selectedSrcs.delete(src);
            }
            var countSpan = document.getElementById("selectedCount");
            if(countSpan) countSpan.innerText = selectedSrcs.size + " selected";
        };
        cards[i].style.position = "relative";
        cards[i].appendChild(chk);
    }
}

function selectAll() {
    document.querySelectorAll(".select-checkbox").forEach(function(cb) {
        if(!cb.checked) cb.click();
    });
    addLog("Selected all images", "success");
}

function deselectAll() {
    document.querySelectorAll(".select-checkbox").forEach(function(cb) {
        if(cb.checked) cb.click();
    });
    addLog("Deselected all images", "info");
}

function showMissingImages() {
    var failed = Object.keys(failedImages);
    if(failed.length === 0) {
        showToast("All images loaded!", false);
    } else {
        showToast(failed.length + " images failed", true);
        for(var i=0;i<failed.length;i++) addLog(failed[i], "error");
    }
}

// ============================================================================
// PATH: index_v0037.html (canvas initialization and persistence)
// WHAT: Fabric.js canvas with state persistence, drawing tools, filters
// WHY: Images lose position on modal close; no drawing/editing capabilities
//
// MENTAL MODEL BEFORE: canvas recreated each time; no save/restore; only image placement
// MENTAL MODEL AFTER: state saved to localStorage; drawing tools; image filters; layering
//
// FAILURE MODE: If canvas doesn't restore, check localStorage for storyboard_images_data_v2;
//   If drawing tools don't appear, check canvasToolbar element exists
//
// VERIFIES WITH: Add images to canvas, close/reopen storyboard, images same position;
//   Click Draw button, draw on canvas, see path appears; Click Grayscale on selected image
//
// Source (Tier 2): Fabric.js Docs: http://fabricjs.com/docs/fabric.Canvas.html
// Source (Tier 1): Flanagan, D. (2020). "JavaScript: The Definitive Guide" 7th ed. O'Reilly. Ch.21 Canvas API
// ============================================================================

function initCanvas() {
    var canvasEl = document.getElementById("storyboardCanvas");
    if(!canvasEl) { addLog("Canvas not found", "error"); return; }
    if(canvas) canvas.dispose();
    canvas = new fabric.Canvas("storyboardCanvas", {
        preserveObjectStacking: true,
        selection: true,
        allowTouchScrolling: false
    });
    canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
    canvas.backgroundColor = "#ffffff";
    canvas.renderAll();
    
    // Restore saved state
    var savedBg = localStorage.getItem(STORAGE_KEYS.BG);
    if(savedBg) {
        canvas.backgroundColor = savedBg;
        var bgSelect = document.getElementById("bgColorSelect");
        if(bgSelect) bgSelect.value = savedBg;
        canvas.renderAll();
    }
    
    loadStoryboardState();
    
    // Auto-save on modifications
    canvas.on('object:modified', function() { saveStoryboardState(); });
    canvas.on('object:added', function() { saveStoryboardState(); });
    canvas.on('object:removed', function() { saveStoryboardState(); });
    
    addLog("Canvas ready with persistence", "success");
}

function saveStoryboardState() {
    if (!canvas) return;
    
    var imageData = [];
    for (var i = 0; i < storyboardImages.length; i++) {
        var obj = storyboardImages[i].fabricObj;
        imageData.push({
            src: storyboardImages[i].src,
            left: obj.left,
            top: obj.top,
            scaleX: obj.scaleX,
            scaleY: obj.scaleY,
            angle: obj.angle,
            width: obj.width,
            height: obj.height
        });
    }
    
    localStorage.setItem(STORAGE_KEYS.IMAGES, JSON.stringify(imageData));
    localStorage.setItem(STORAGE_KEYS.BG, canvas.backgroundColor || '#ffffff');
    localStorage.setItem(STORAGE_KEYS.TEMPLATE, currentTemplate);
    console.log('Storyboard saved: ' + imageData.length + ' images');
}

function loadStoryboardState() {
    var savedImages = localStorage.getItem(STORAGE_KEYS.IMAGES);
    var savedTemplate = localStorage.getItem(STORAGE_KEYS.TEMPLATE);
    
    if (savedTemplate) {
        currentTemplate = savedTemplate;
        var templateSelect = document.getElementById('templateSelect');
        if (templateSelect) templateSelect.value = savedTemplate;
    }
    
    if (savedImages) {
        try {
            var images = JSON.parse(savedImages);
            console.log('Restoring ' + images.length + ' saved images...');
            
            var loadPromises = images.map(function(imgData) {
                return new Promise(function(resolve) {
                    fabric.Image.fromURL(imgData.src, function(fabricImg) {
                        if (fabricImg) {
                            fabricImg.set({
                                left: imgData.left,
                                top: imgData.top,
                                scaleX: imgData.scaleX,
                                scaleY: imgData.scaleY,
                                angle: imgData.angle || 0,
                                hasControls: true,
                                hasBorders: true,
                                lockRotation: false
                            });
                            storyboardImages.push({
                                src: imgData.src,
                                fabricObj: fabricImg
                            });
                            canvas.add(fabricImg);
                        }
                        resolve();
                    });
                });
            });
            
            Promise.all(loadPromises).then(function() {
                canvas.renderAll();
                updateThumbnails();
                updateStoryboardBadge();
                console.log('Storyboard restored successfully');
            });
        } catch(e) {
            console.error('Failed to restore storyboard:', e);
        }
    }
}

function addImageToStoryboard(src) {
    var filename = src.split('/').pop();
    for(var i=0;i<storyboardImages.length;i++){
        if(storyboardImages[i].src === src){ showToast("Already added", true); return; }
    }
    fabric.Image.fromURL(src, function(img) {
        if(!img) { addLog("Failed: " + filename, "error"); return; }
        img.set({ hasControls: true, hasBorders: true, lockRotation: false });
        var margin = 20;
        var x = margin + (storyboardImages.length % 3) * 280;
        var y = margin + Math.floor(storyboardImages.length / 3) * 220;
        img.set({ left: x, top: y });
        storyboardImages.push({ src: src, fabricObj: img });
        canvas.add(img);
        canvas.renderAll();
        updateThumbnails();
        updateStoryboardBadge();
        saveStoryboardState();
        showToast("Added: " + filename, false);
    });
}

function updateStoryboardBadge() {
    var b = document.getElementById("storyboardCountBadge");
    if(b) b.innerText = storyboardImages.length;
}

function updateThumbnails() {
    var container = document.getElementById("storyboardThumbnails");
    if(!container) return;
    var html = "";
    for(var i=0;i<storyboardImages.length;i++){
        html += "<img class='storyboard-thumb' src='" + storyboardImages[i].src + "' data-index='" + i + "'>";
    }
    container.innerHTML = html;
    document.querySelectorAll(".storyboard-thumb").forEach(function(thumb) {
        thumb.onclick = function(e) {
            e.stopPropagation();
            var idx = parseInt(this.dataset.index);
            canvas.remove(storyboardImages[idx].fabricObj);
            storyboardImages.splice(idx,1);
            canvas.renderAll();
            updateThumbnails();
            updateStoryboardBadge();
            saveStoryboardState();
        };
    });
}

function applyLayout() {
    if(storyboardImages.length === 0) return;
    var tpl = document.getElementById("templateSelect").value;
    currentTemplate = tpl;
    var margin = 20;
    var availW = PREVIEW_W - margin * 2;
    if(tpl === "grid") {
        var cols = Math.min(3, storyboardImages.length);
        var cellW = (availW - (cols-1)*margin) / cols;
        var y = margin;
        for(var i=0;i<storyboardImages.length;i++){
            var obj = storyboardImages[i].fabricObj;
            var col = i % cols;
            var scale = Math.min(cellW / obj.width, 250 / obj.height);
            obj.scale(scale);
            obj.set({ left: margin + col * (cellW + margin), top: y });
            if(col === cols-1 || i === storyboardImages.length-1) y += obj.height * scale + margin;
        }
    } else if(tpl === "center" && storyboardImages.length > 0) {
        var obj = storyboardImages[0].fabricObj;
        var scale = Math.min(availW / obj.width, (PREVIEW_H - margin*2) / obj.height);
        obj.scale(scale);
        obj.set({ left: margin + (availW - obj.width*scale)/2, top: margin + ((PREVIEW_H-margin*2) - obj.height*scale)/2 });
    } else if(tpl === "masonry") {
        var cols = 2;
        var colWidth = availW / cols;
        var colHeights = [margin, margin];
        var colX = [margin, margin + colWidth + margin];
        for(var i=0;i<storyboardImages.length;i++){
            var obj = storyboardImages[i].fabricObj;
            var colIdx = colHeights[0] <= colHeights[1] ? 0 : 1;
            var scale = colWidth / obj.width;
            obj.scale(scale);
            obj.set({ left: colX[colIdx], top: colHeights[colIdx] });
            colHeights[colIdx] += obj.height * scale + margin;
        }
    }
    canvas.renderAll();
    saveStoryboardState();
    addLog("Layout applied: " + tpl, "success");
}

function syncSelectedToStoryboard() {
    var srcs = Array.from(selectedSrcs);
    if(srcs.length === 0){ showToast("No images selected", true); return; }
    addLog("Syncing " + srcs.length + " images", "info");
    for(var i=0;i<srcs.length;i++) addImageToStoryboard(srcs[i]);
}

function clearCanvasOnly() {
    if(confirm("Clear all images from canvas?")){
        for(var i=0;i<storyboardImages.length;i++) canvas.remove(storyboardImages[i].fabricObj);
        storyboardImages = [];
        canvas.renderAll();
        updateThumbnails();
        updateStoryboardBadge();
        localStorage.removeItem(STORAGE_KEYS.IMAGES);
        showToast("Canvas cleared", false);
        addLog("Canvas cleared", "info");
    }
}

// ============================================================================
// PATH: index_v0037.html (canvas drawing tools)
// WHAT: Drawing mode, text, shapes, filters, layering controls
// WHY: Storyboard needs more than just image placement
//
// MENTAL MODEL BEFORE: only images with move/resize controls
// MENTAL MODEL AFTER: full drawing suite with 10+ tools
//
// FAILURE MODE: If tools don't respond, check canvas is active object
//
// VERIFIES WITH: Click Draw button, draw on canvas; Click Text button, type/edit text;
//   Select image, click Grayscale, image turns black and white
//
// Source (Tier 2): Fabric.js Filters: http://fabricjs.com/docs/fabric.Image.filters.html
// ============================================================================

function setDrawingMode(enabled) {
    isDrawingMode = enabled;
    canvas.isDrawingMode = enabled;
    if (enabled) {
        canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
        canvas.freeDrawingBrush.color = '#000000';
        canvas.freeDrawingBrush.width = 2;
        document.body.style.cursor = 'crosshair';
        addLog("Drawing mode enabled", "success");
    } else {
        document.body.style.cursor = 'default';
        addLog("Drawing mode disabled", "info");
    }
}

function addText() {
    var text = new fabric.IText('Double-click to edit', {
        left: 100,
        top: 100,
        fontFamily: 'Arial',
        fontSize: 24,
        fill: '#000000',
        hasControls: true
    });
    canvas.add(text);
    canvas.setActiveObject(text);
    canvas.renderAll();
    addLog("Text added", "success");
}

function addShape(type) {
    var shape;
    switch(type) {
        case 'rectangle':
            shape = new fabric.Rect({ left: 100, top: 100, width: 100, height: 100, fill: '#3b82f6', stroke: '#ffffff', strokeWidth: 2 });
            break;
        case 'circle':
            shape = new fabric.Circle({ left: 100, top: 100, radius: 50, fill: '#ef4444', stroke: '#ffffff', strokeWidth: 2 });
            break;
        case 'triangle':
            shape = new fabric.Triangle({ left: 100, top: 100, width: 100, height: 100, fill: '#10b981', stroke: '#ffffff', strokeWidth: 2 });
            break;
    }
    if (shape) {
        canvas.add(shape);
        canvas.setActiveObject(shape);
        canvas.renderAll();
        addLog("Shape added: " + type, "success");
    }
}

function applyFilter(filterName) {
    var activeObj = canvas.getActiveObject();
    if (!activeObj || activeObj.get('type') !== 'image') {
        showToast("Select an image first", true);
        return;
    }
    
    var filters = [];
    switch(filterName) {
        case 'grayscale':
            filters.push(new fabric.Image.filters.Grayscale());
            break;
        case 'sepia':
            filters.push(new fabric.Image.filters.Sepia());
            break;
        case 'brightness':
            filters.push(new fabric.Image.filters.Brightness({ brightness: 0.2 }));
            break;
        case 'contrast':
            filters.push(new fabric.Image.filters.Contrast({ contrast: 0.3 }));
            break;
    }
    
    if (filters.length) {
        activeObj.filters = filters;
        activeObj.applyFilters();
        canvas.renderAll();
        addLog("Applied filter: " + filterName, "success");
    }
}

function removeFilters() {
    var activeObj = canvas.getActiveObject();
    if (activeObj && activeObj.get('type') === 'image') {
        activeObj.filters = [];
        activeObj.applyFilters();
        canvas.renderAll();
        addLog("Filters removed", "success");
    }
}

function bringToFront() {
    var activeObj = canvas.getActiveObject();
    if (activeObj) {
        canvas.bringToFront(activeObj);
        canvas.renderAll();
    }
}

function sendToBack() {
    var activeObj = canvas.getActiveObject();
    if (activeObj) {
        canvas.sendToBack(activeObj);
        canvas.renderAll();
    }
}

function duplicateObject() {
    var activeObj = canvas.getActiveObject();
    if (activeObj) {
        activeObj.clone(function(cloned) {
            cloned.set({
                left: (activeObj.left || 0) + 20,
                top: (activeObj.top || 0) + 20
            });
            canvas.add(cloned);
            canvas.setActiveObject(cloned);
            canvas.renderAll();
            addLog("Object duplicated", "success");
        });
    }
}

function exportHighQuality() {
    if(storyboardImages.length === 0){ showToast("No images to export", true); return; }
    addLog("Exporting 300 DPI (10800x14400)...", "info");
    showToast("Exporting 300 DPI PNG...", false);
    
    var offCanvas = document.createElement("canvas");
    offCanvas.width = TARGET_W;
    offCanvas.height = TARGET_H;
    var offCtx = offCanvas.getContext("2d");
    offCtx.fillStyle = canvas.backgroundColor;
    offCtx.fillRect(0, 0, TARGET_W, TARGET_H);
    offCtx.imageSmoothingEnabled = true;
    offCtx.imageSmoothingQuality = "high";
    
    for(var i=0;i<storyboardImages.length;i++){
        var obj = storyboardImages[i].fabricObj;
        var left = obj.left * SCALE;
        var top = obj.top * SCALE;
        var width = obj.width * obj.scaleX * SCALE;
        var height = obj.height * obj.scaleY * SCALE;
        offCtx.drawImage(obj._element, left, top, width, height);
    }
    
    if(currentLogo) {
        offCtx.drawImage(currentLogo._element, currentLogo.left * SCALE, currentLogo.top * SCALE,
            currentLogo.width * currentLogo.scaleX * SCALE, currentLogo.height * currentLogo.scaleY * SCALE);
    }
    
    var a = document.createElement("a");
    a.download = "storyboard_36x48_300dpi.png";
    a.href = offCanvas.toDataURL("image/png");
    a.click();
    addLog("Export complete! (36x48\" at 300 DPI)", "success");
    showToast("Export complete!", false);
}

document.addEventListener("DOMContentLoaded", function() {
    addLog("DOM ready", "info");
    
    // Background color picker
    var bgSelect = document.getElementById("bgColorSelect");
    if(bgSelect) {
        bgSelect.addEventListener("change", function(e) {
            if(canvas) {
                canvas.backgroundColor = e.target.value;
                canvas.renderAll();
                saveStoryboardState();
            }
        });
    }
    
    // Logo upload
    var addLogoBtn = document.getElementById("addLogoBtn");
    if(addLogoBtn) {
        addLogoBtn.addEventListener("click", function() {
            var file = document.getElementById("logoUpload").files[0];
            if(!file) { showToast("Select SVG file", true); return; }
            var reader = new FileReader();
            reader.onload = function(e) {
                fabric.loadSVGFromString(e.target.result, function(objects, options) {
                    var logo = fabric.util.groupSVGElements(objects, options);
                    logo.set({ left: PREVIEW_W - 100, top: 20, scaleX: 0.5, scaleY: 0.5, hasControls: true });
                    if(currentLogo) canvas.remove(currentLogo);
                    currentLogo = logo;
                    canvas.add(logo);
                    canvas.renderAll();
                    saveStoryboardState();
                    showToast("Logo added", false);
                });
            };
            reader.readAsText(file);
        });
    }
    
    var removeLogoBtn = document.getElementById("removeLogoBtn");
    if(removeLogoBtn) {
        removeLogoBtn.addEventListener("click", function() {
            if(currentLogo) {
                canvas.remove(currentLogo);
                currentLogo = null;
                canvas.renderAll();
                saveStoryboardState();
                showToast("Logo removed", false);
            }
        });
    }
    
    // Button handlers
    document.getElementById("selectAllBtn").onclick = selectAll;
    document.getElementById("deselectAllBtn").onclick = deselectAll;
    document.getElementById("syncSelectedBtn").onclick = syncSelectedToStoryboard;
    document.getElementById("checkMissingBtn").onclick = showMissingImages;
    document.getElementById("debugSaveBtn").onclick = saveLogs;
    document.getElementById("debugCloseBtn").onclick = function(){ document.getElementById("debugPanel").style.display = "none"; };
    document.getElementById("openStoryboardBtn").onclick = function(){ 
        document.getElementById("storyboardModal").classList.add("active"); 
        if(canvas) canvas.renderAll();
    };
    document.getElementById("closeStoryboardBtn").onclick = function(){ 
        saveStoryboardState();
        document.getElementById("storyboardModal").classList.remove("active"); 
    };
    document.getElementById("exportStoryboardBtn").onclick = exportHighQuality;
    document.getElementById("clearStoryboardBtn").onclick = clearCanvasOnly;
    document.getElementById("applyTemplateBtn").onclick = applyLayout;
    document.getElementById("lightboxCloseBtn").onclick = closeLightbox;
    
    // Canvas tool buttons
    document.getElementById("drawModeBtn").onclick = function() { setDrawingMode(!isDrawingMode); };
    document.getElementById("addTextBtn").onclick = addText;
    document.getElementById("addRectBtn").onclick = function() { addShape('rectangle'); };
    document.getElementById("addCircleBtn").onclick = function() { addShape('circle'); };
    document.getElementById("addTriangleBtn").onclick = function() { addShape('triangle'); };
    document.getElementById("grayscaleBtn").onclick = function() { applyFilter('grayscale'); };
    document.getElementById("sepiaBtn").onclick = function() { applyFilter('sepia'); };
    document.getElementById("brightnessBtn").onclick = function() { applyFilter('brightness'); };
    document.getElementById("contrastBtn").onclick = function() { applyFilter('contrast'); };
    document.getElementById("removeFiltersBtn").onclick = removeFilters;
    document.getElementById("bringFrontBtn").onclick = bringToFront;
    document.getElementById("sendBackBtn").onclick = sendToBack;
    document.getElementById("duplicateBtn").onclick = duplicateObject;
    document.getElementById("clearCanvasBtn").onclick = clearCanvasOnly;
    
    var prevBtn = document.querySelector(".lightbox-prev");
    if(prevBtn) prevBtn.onclick = prevLightbox;
    
    var nextBtn = document.querySelector(".lightbox-next");
    if(nextBtn) nextBtn.onclick = nextLightbox;
    
    var lightbox = document.getElementById("lightbox");
    if(lightbox) lightbox.onclick = function(e) { if(e.target === this) closeLightbox(); };
    
    var commentsClose = document.getElementById("commentsModalClose");
    if(commentsClose) commentsClose.onclick = function() { document.getElementById("commentsModal").classList.remove("active"); };
    
    var commentsModal = document.getElementById("commentsModal");
    if(commentsModal) commentsModal.onclick = function(e) { if(e.target === this) this.classList.remove("active"); };
    
    var searchInput = document.getElementById("searchInput");
    if(searchInput) {
        searchInput.addEventListener("input", function(e){
            var q = e.target.value.toLowerCase();
            var filtered = allPosts.filter(function(p){ return (p.caption || "").toLowerCase().indexOf(q) !== -1; });
            renderGallery(filtered);
        });
    }
    
    document.addEventListener("keydown", function(e) {
        var lightboxActive = document.getElementById("lightbox");
        if(lightboxActive && lightboxActive.classList.contains("active")) {
            if(e.key === "ArrowLeft") prevLightbox();
            else if(e.key === "ArrowRight") nextLightbox();
            else if(e.key === "Escape") closeLightbox();
        }
        if(e.key === "Escape") {
            var modal = document.getElementById("commentsModal");
            if(modal) modal.classList.remove("active");
        }
    });
    
    initCanvas();
    renderGallery(allPosts);
    addLog("=== GALLERY v0037 READY ===", "success");
    addLog("Loaded " + allPosts.length + " posts", "info");
    addLog("✅ Complete canvas suite: Drawing, Text, Shapes, Filters, Layers, 300 DPI export", "info");
    addLog("💾 Click 💾 to save logs to file", "info");
});
</script>
</body>
</html>'''
    
    return html

def main():
    print("=" * 70)
    print("MR. DOUGLAS GALLERY v0037 - Complete Canvas Suite with Logging")
    print("=" * 70)
    
    print("\n[1/3] Loading ALL posts...")
    posts = load_posts()
    posts = add_historic_images(posts)
    print(f"Loaded {len(posts)} posts total")
    
    print("[2/3] Generating HTML with complete canvas suite...")
    html = build_html(posts)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    print(f"Generated {OUTPUT_HTML}")
    print(f"File size: {OUTPUT_HTML.stat().st_size} bytes")
    
    print("[3/3] Starting server...")
    os.system("pkill -f 'http.server' 2>/dev/null")
    time.sleep(1)
    
    subprocess.Popen([sys.executable, '-m', 'http.server', '8000'], 
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    print("\n" + "=" * 70)
    print("✅ READY!")
    print("=" * 70)
    print(f"Open: http://localhost:8000/{OUTPUT_HTML.name}")
    print("\n✨ COMPLETE FEATURES:")
    print("   📸 300 DPI Export (10800 x 14400)")
    print("   🎨 Background color picker")
    print("   🖼️ SVG Logo upload")
    print("   📐 Templates: Grid, Center, Masonry")
    print("   💾 Persistent storyboard (saves to localStorage)")
    print("   💬 Comments modal")
    print("   📊 Complete log capture (click 💾 to save)")
    print("   ✏️ Drawing mode with pencil brush")
    print("   📝 Editable text tool")
    print("   ⬜ Shapes: Rectangle, Circle, Triangle")
    print("   🎨 Image filters: Grayscale, Sepia, Brightness, Contrast")
    print("   ⬆️⬇️ Layer controls: Bring to Front, Send to Back")
    print("   📑 Duplicate objects")
    print("\nPress Ctrl+C to stop")
    
    webbrowser.open(f'http://localhost:8000/{OUTPUT_HTML.name}')
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        cleanup()

if __name__ == "__main__":
    main()