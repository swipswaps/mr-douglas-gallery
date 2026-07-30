#!/usr/bin/env python3
"""
build_final_gallery_v0033.py - 300 DPI Export + Top Bar Storyboard Button
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
from datetime import datetime
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path("instagram_posts.db")
OUTPUT_HTML = Path("index_v0033.html")
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
    posts_json = json.dumps(posts, ensure_ascii=False)
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mr. Douglas Gallery v0033 - 300 DPI Export</title>
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
.video-thumbnail{position:relative;width:100%;aspect-ratio:4/3;background:#0f172a;display:flex;align-items:center;justify-content:center;cursor:pointer}
.video-thumbnail video{width:100%;height:100%;object-fit:cover}
.video-thumbnail .play-overlay{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.7);color:white;font-size:48px;width:80px;height:80px;border-radius:50%;display:flex;align-items:center;justify-content:center;pointer-events:none}
.video-thumbnail .duration{position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,0.7);color:white;padding:2px 6px;border-radius:4px;font-size:11px;pointer-events:none}
.card-content{padding:1rem}
.card-meta{display:flex;justify-content:space-between;font-size:0.75rem;color:#94a3b8;margin-bottom:0.5rem;flex-wrap:wrap}
.author-name{color:#60a5fa}
.card-caption{font-size:0.875rem;color:#cbd5e1;margin-bottom:0.75rem;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.select-checkbox{position:absolute;top:8px;left:8px;width:20px;height:20px;cursor:pointer;z-index:10}
.carousel{display:flex;gap:0.5rem;overflow-x:auto;margin:0.5rem 0;padding-bottom:4px}
.carousel-item{width:60px;height:60px;object-fit:cover;border-radius:8px;cursor:pointer;background:#0f172a}
.carousel-video-item{position:relative;width:60px;height:60px;border-radius:8px;cursor:pointer;overflow:hidden}
.carousel-video-item video{width:100%;height:100%;object-fit:cover}
.carousel-video-item .play-icon{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:20px;text-shadow:0 0 2px black}
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
            <h3>Storyboard Builder - 300 DPI Export (10800 x 14400)</h3>
            <button id="closeStoryboardBtn" style="background:#ef4444;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer">Close</button>
        </div>
        <div class="storyboard-controls">
            <select id="templateSelect">
                <option value="grid">Grid (3 cols)</option>
                <option value="center">Single centered</option>
                <option value="masonry">Masonry</option>
            </select>
            <button id="applyTemplateBtn">Apply Template</button>
            <button id="exportStoryboardBtn" class="primary">📸 Export 300 DPI PNG</button>
            <button id="clearStoryboardBtn">Clear All</button>
        </div>
        <canvas id="storyboardCanvas" width="1080" height="1440"></canvas>
        <div><strong>Images (click to remove):</strong>
            <div id="storyboardThumbnails" style="display:flex;gap:12px;overflow-x:auto;padding:8px;"></div>
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

console.log("=== GALLERY v0033 STARTING ===");

var allPosts = ''' + posts_json + ''';
var allLogs = [];
var failedImages = {};
var loadedImages = {};
var currentLightboxIndex = 0;
var currentLightboxMedia = [];
var selectedSrcs = new Set();
var canvas = null;
var storyboardImages = [];
var PREVIEW_W = 1080;
var PREVIEW_H = 1440;
var TARGET_W = 10800;   // 10x scale for 300 DPI (36 inches * 300 DPI)
var TARGET_H = 14400;   // 48 inches * 300 DPI
var SCALE = TARGET_W / PREVIEW_W;

function addLog(msg, type) {
    var timestamp = new Date().toLocaleTimeString();
    var prefix = "";
    var color = "#10b981";
    if(type === "error") {
        prefix = "[ERROR] ";
        color = "#ef4444";
    } else if(type === "warning") {
        prefix = "[WARN] ";
        color = "#f59e0b";
    } else if(type === "success") {
        prefix = "[OK] ";
        color = "#10b981";
    } else {
        prefix = "[INFO] ";
        color = "#60a5fa";
    }
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
    if(allLogs.length === 0) {
        addLog("No logs to save yet", "warning");
        return;
    }
    var logsText = allLogs.join("\\n");
    var blob = new Blob([logsText], {type: "text/plain"});
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "gallery_logs_" + new Date().toISOString().slice(0,19).replace(/:/g, "-") + ".txt";
    a.click();
    URL.revokeObjectURL(a.href);
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

// Lightbox functions
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
        video.play();
    } else {
        var img = document.createElement("img");
        img.src = media.url;
        img.style.maxWidth = "90vw";
        img.style.maxHeight = "85vh";
        img.className = "lightbox-media";
        container.appendChild(img);
    }
}

function closeLightbox() {
    var lightbox = document.getElementById("lightbox");
    if(lightbox) lightbox.classList.remove("active");
    var container = document.getElementById("lightboxMediaContainer");
    if(container) container.innerHTML = "";
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

// Comments
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

// Image tracking
function trackImageLoad(img) {
    var src = img.src;
    if(!loadedImages[src]) {
        loadedImages[src] = true;
        delete failedImages[src];
        addLog("Loaded: " + src.split('/').pop(), "success");
        updateImageStatus();
    }
}

function trackImageError(img) {
    var src = img.src;
    if(!failedImages[src]) {
        failedImages[src] = true;
        delete loadedImages[src];
        addLog("FAILED: " + src.split('/').pop(), "error");
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

// Render gallery with video thumbnails
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
        var firstMedia = post.all_media.length ? post.all_media[0] : null;
        var mediaPath = firstMedia ? getMediaPath(post.folder_name, firstMedia) : "";
        var isVideoPost = firstMedia && isVideo(firstMedia);
        
        var mediaArray = [];
        for(var i=0;i<post.all_media.length;i++) {
            mediaArray.push({
                url: getMediaPath(post.folder_name, post.all_media[i]),
                type: isVideo(post.all_media[i]) ? "video" : "image"
            });
        }
        var mediaArrayJson = JSON.stringify(mediaArray).replace(/"/g, '&quot;');
        
        var mediaHtml = "";
        if(firstMedia) {
            if(isVideoPost) {
                mediaHtml = "<div class='video-thumbnail' data-video-url='" + mediaPath + "'>";
                mediaHtml += "<video preload='metadata' muted playsinline>";
                mediaHtml += "<source src='" + mediaPath + "' type='video/mp4'>";
                mediaHtml += "</video>";
                mediaHtml += "<div class='play-overlay'>▶</div>";
                mediaHtml += "<div class='duration' id='duration-" + idx + "'>Loading...</div>";
                mediaHtml += "</div>";
            } else {
                mediaHtml = "<img class='card-media' src='" + mediaPath + "' loading='lazy' onload='trackImageLoad(this)' onerror='trackImageError(this)'>";
            }
        } else {
            mediaHtml = "<div class='card-media'>No media</div>";
        }
        
        var carouselHtml = "";
        if(post.all_media.length > 1) {
            carouselHtml = "<div class='carousel'>";
            for(var i=0;i<post.all_media.length;i++) {
                var mediaFile = post.all_media[i];
                var mediaUrl = getMediaPath(post.folder_name, mediaFile);
                if(isVideo(mediaFile)) {
                    carouselHtml += "<div class='carousel-video-item' data-url='" + mediaUrl + "'>";
                    carouselHtml += "<video preload='metadata' muted playsinline>";
                    carouselHtml += "<source src='" + mediaUrl + "' type='video/mp4'>";
                    carouselHtml += "</video>";
                    carouselHtml += "<div class='play-icon'>▶</div>";
                    carouselHtml += "</div>";
                } else {
                    carouselHtml += "<img class='carousel-item' src='" + mediaUrl + "' data-url='" + mediaUrl + "' loading='lazy'>";
                }
            }
            carouselHtml += "</div>";
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
        htmlStr += "<button class='comments-btn' data-shortcode='" + post.shortcode + "'>💬 " + post.comments.length + "</button>";
        htmlStr += "</div></div></div>";
    }
    grid.innerHTML = htmlStr;
    
    document.querySelectorAll(".video-thumbnail video").forEach(function(video, idx) {
        video.addEventListener("loadedmetadata", function() {
            var mins = Math.floor(video.duration / 60);
            var secs = Math.floor(video.duration % 60);
            var durationSpan = document.getElementById("duration-" + idx);
            if(durationSpan) durationSpan.textContent = mins + ":" + (secs < 10 ? "0" : "") + secs;
        });
    });
    
    document.querySelectorAll(".video-thumbnail").forEach(function(thumb) {
        thumb.onclick = function(e) {
            e.stopPropagation();
            var card = this.closest(".card");
            var mediaData = JSON.parse(card.dataset.media);
            if(mediaData && mediaData.length) {
                openLightbox(mediaData, 0, card.dataset.caption);
            }
        };
    });
    
    document.querySelectorAll(".card").forEach(function(card) {
        card.onclick = function(e) {
            if(e.target.closest(".carousel-item") || e.target.closest(".carousel-video-item") || 
               e.target.closest(".comments-btn") || e.target.closest(".select-checkbox") || 
               e.target.closest(".insta-link") || e.target.closest(".video-thumbnail")) {
                return;
            }
            var mediaData = JSON.parse(this.dataset.media);
            if(mediaData && mediaData.length) {
                openLightbox(mediaData, 0, this.dataset.caption);
            }
        };
    });
    
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
        showToast("All images loaded successfully!", false);
    } else {
        showToast(failed.length + " images failed to load", true);
        for(var i=0;i<failed.length;i++) addLog(failed[i], "error");
    }
}

// Storyboard with 300 DPI export
function initCanvas() {
    var canvasEl = document.getElementById("storyboardCanvas");
    if(!canvasEl) { addLog("Canvas element not found!", "error"); return; }
    if(canvas) canvas.dispose();
    canvas = new fabric.Canvas("storyboardCanvas");
    canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
    canvas.backgroundColor = "#ffffff";
    canvas.renderAll();
    addLog("Canvas ready (1080x1440 preview)", "success");
}

function addImageToStoryboard(src) {
    var filename = src.split('/').pop();
    for(var i=0;i<storyboardImages.length;i++){
        if(storyboardImages[i].src === src){ showToast("Already added", true); return; }
    }
    fabric.Image.fromURL(src, function(img) {
        if(!img) { addLog("Failed to load: " + filename, "error"); showToast("Failed: " + filename, true); return; }
        img.set({ hasControls: true, hasBorders: true, lockRotation: true });
        var margin = 20;
        var x = margin + (storyboardImages.length % 3) * 280;
        var y = margin + Math.floor(storyboardImages.length / 3) * 220;
        img.set({ left: x, top: y });
        storyboardImages.push({ src: src, fabricObj: img });
        canvas.add(img);
        canvas.renderAll();
        updateThumbnails();
        updateStoryboardBadge();
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
        };
    });
}

function applyLayout() {
    if(storyboardImages.length === 0) return;
    var tpl = document.getElementById("templateSelect").value;
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
    addLog("Layout applied: " + tpl, "success");
}

function syncSelectedToStoryboard() {
    var srcs = Array.from(selectedSrcs);
    if(srcs.length === 0){ showToast("No images selected", true); return; }
    addLog("Syncing " + srcs.length + " images to storyboard", "info");
    for(var i=0;i<srcs.length;i++) addImageToStoryboard(srcs[i]);
}

function clearAll() {
    if(confirm("Clear all images from storyboard?")){
        for(var i=0;i<storyboardImages.length;i++) canvas.remove(storyboardImages[i].fabricObj);
        storyboardImages = [];
        canvas.renderAll();
        updateThumbnails();
        updateStoryboardBadge();
        showToast("Storyboard cleared", false);
        addLog("Storyboard cleared", "info");
    }
}

function exportHighQuality() {
    if(storyboardImages.length === 0){ showToast("No images to export", true); return; }
    addLog("Starting 300 DPI export (10800 x 14400)...", "info");
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
    
    var a = document.createElement("a");
    a.download = "storyboard_36x48_300dpi.png";
    a.href = offCanvas.toDataURL("image/png");
    a.click();
    addLog("Export complete! File size: " + Math.round(offCanvas.toDataURL("image/png").length / 1024) + "KB", "success");
    showToast("Export complete! 36x48\" at 300 DPI", false);
}

// Wait for DOM to be ready before attaching event listeners
document.addEventListener("DOMContentLoaded", function() {
    addLog("DOM ready, attaching event listeners...", "info");
    
    // Button handlers
    var selectAllBtn = document.getElementById("selectAllBtn");
    if(selectAllBtn) selectAllBtn.onclick = selectAll;
    
    var deselectAllBtn = document.getElementById("deselectAllBtn");
    if(deselectAllBtn) deselectAllBtn.onclick = deselectAll;
    
    var syncBtn = document.getElementById("syncSelectedBtn");
    if(syncBtn) syncBtn.onclick = syncSelectedToStoryboard;
    
    var checkMissingBtn = document.getElementById("checkMissingBtn");
    if(checkMissingBtn) checkMissingBtn.onclick = showMissingImages;
    
    var debugSaveBtn = document.getElementById("debugSaveBtn");
    if(debugSaveBtn) debugSaveBtn.onclick = saveLogs;
    
    var debugCloseBtn = document.getElementById("debugCloseBtn");
    if(debugCloseBtn) debugCloseBtn.onclick = function(){ document.getElementById("debugPanel").style.display = "none"; };
    
    var openStoryboardBtn = document.getElementById("openStoryboardBtn");
    if(openStoryboardBtn) openStoryboardBtn.onclick = function(){ document.getElementById("storyboardModal").classList.add("active"); };
    
    var closeStoryboardBtn = document.getElementById("closeStoryboardBtn");
    if(closeStoryboardBtn) closeStoryboardBtn.onclick = function(){ document.getElementById("storyboardModal").classList.remove("active"); };
    
    var exportBtn = document.getElementById("exportStoryboardBtn");
    if(exportBtn) exportBtn.onclick = exportHighQuality;
    
    var clearBtn = document.getElementById("clearStoryboardBtn");
    if(clearBtn) clearBtn.onclick = clearAll;
    
    var applyTemplateBtn = document.getElementById("applyTemplateBtn");
    if(applyTemplateBtn) applyTemplateBtn.onclick = applyLayout;
    
    var lightboxCloseBtn = document.getElementById("lightboxCloseBtn");
    if(lightboxCloseBtn) lightboxCloseBtn.onclick = closeLightbox;
    
    var lightboxPrev = document.querySelector(".lightbox-prev");
    if(lightboxPrev) lightboxPrev.onclick = prevLightbox;
    
    var lightboxNext = document.querySelector(".lightbox-next");
    if(lightboxNext) lightboxNext.onclick = nextLightbox;
    
    var lightbox = document.getElementById("lightbox");
    if(lightbox) lightbox.onclick = function(e) { if(e.target === this) closeLightbox(); };
    
    var commentsModalClose = document.getElementById("commentsModalClose");
    if(commentsModalClose) commentsModalClose.onclick = function() { document.getElementById("commentsModal").classList.remove("active"); };
    
    var commentsModal = document.getElementById("commentsModal");
    if(commentsModal) commentsModal.onclick = function(e) { if(e.target === this) this.classList.remove("active"); };
    
    var searchInput = document.getElementById("searchInput");
    if(searchInput) {
        searchInput.addEventListener("input", function(e){
            var q = e.target.value.toLowerCase();
            var filtered = allPosts.filter(function(p){ return p.caption.toLowerCase().indexOf(q) !== -1; });
            renderGallery(filtered);
        });
    }
    
    // Keyboard navigation
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
    
    // Initialize
    initCanvas();
    renderGallery(allPosts);
    addLog("=== GALLERY v0033 READY ===", "success");
    addLog("Storyboard button is in the top toolbar", "info");
    addLog("Export creates 10800x14400 PNG (36x48\" at 300 DPI)", "info");
});
</script>
</body>
</html>'''
    
    return html

def main():
    print("=" * 70)
    print("MR. DOUGLAS GALLERY v0033 - 300 DPI Export + Top Bar Button")
    print("=" * 70)
    
    print("\n[1/3] Loading posts...")
    posts = load_posts()
    posts = add_historic_images(posts)
    print(f"Loaded {len(posts)} posts")
    
    print("[2/3] Generating HTML with 300 DPI export...")
    html = build_html(posts)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    print(f"Generated {OUTPUT_HTML}")
    
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
    print("\n✨ v0033 IMPROVEMENTS:")
    print("   🎬 Storyboard button MOVED to top toolbar (no scrolling needed)")
    print("   📸 Export creates FULL 300 DPI image (10800 x 14400 pixels)")
    print("   📏 Perfect for 36x48 inch print at 300 DPI")
    print("   💾 Enhanced logs with categories [INFO]/[OK]/[ERROR]/[WARN]")
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