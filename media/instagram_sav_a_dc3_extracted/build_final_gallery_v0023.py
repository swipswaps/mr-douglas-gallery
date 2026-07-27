#!/usr/bin/env python3
"""
build_final_gallery_v0023.py - Persistent Storyboard with Logging
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
OUTPUT_HTML = Path("index_v0023.html")
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
<title>Mr. Douglas Gallery v0023 - Persistent Storyboard</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0f172a;color:#e2e8f0;font-family:system-ui}
.search-header{position:sticky;top:0;z-index:20;background:rgba(15,23,42,0.95);backdrop-filter:blur(8px);border-bottom:1px solid #334155;padding:1rem}
.search-container{max-width:1200px;margin:0 auto}
.search-input{width:100%;padding:0.75rem 1rem;background:#1e293b;border:1px solid #475569;border-radius:2rem;color:#f1f5f9}
.gallery-toolbar{position:sticky;top:90px;z-index:15;display:flex;gap:12px;margin:0 1.5rem 1rem;flex-wrap:wrap;align-items:center;background:#1e293b;padding:8px 12px;border-radius:12px}
.gallery-toolbar button{background:#334155;color:white;border:none;padding:6px 12px;border-radius:8px;cursor:pointer}
.gallery-toolbar button.primary{background:#3b82f6}
.gallery-toolbar button.warning{background:#f59e0b}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1.5rem;padding:1.5rem;max-width:1400px;margin:0 auto}
.card{background:#1e293b;border-radius:1rem;overflow:hidden;cursor:pointer;position:relative}
.card:hover{transform:translateY(-4px)}
.card-media{width:100%;aspect-ratio:4/3;object-fit:cover;background:#0f172a}
.card-media.load-error{opacity:0.5;filter:grayscale(1)}
.card-content{padding:1rem}
.card-meta{display:flex;justify-content:space-between;font-size:0.75rem;color:#94a3b8;margin-bottom:0.5rem;flex-wrap:wrap}
.author-name{color:#60a5fa}
.select-checkbox{position:absolute;top:8px;left:8px;width:20px;height:20px;cursor:pointer;z-index:10}
.storyboard-btn{position:fixed;bottom:20px;right:20px;background:#3b82f6;color:white;border:none;border-radius:50px;padding:12px 24px;cursor:pointer;z-index:1000}
.storyboard-modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:2000;overflow:auto}
.storyboard-modal.active{display:flex;flex-direction:column}
.storyboard-container{background:#1e293b;margin:20px auto;padding:20px;border-radius:16px;max-width:95%;width:1200px}
#storyboardCanvas{border:2px solid #475569;border-radius:8px;background:white;display:block;margin:0 auto;cursor:crosshair}
.storyboard-controls{display:flex;gap:10px;justify-content:center;margin:15px 0;flex-wrap:wrap}
.storyboard-controls button{background:#3b82f6;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer}
.storyboard-thumb{width:80px;height:80px;object-fit:cover;border-radius:8px;cursor:pointer;margin-right:8px}
.toast{position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1e293b;color:#e2e8f0;padding:10px 20px;border-radius:40px;z-index:3000;opacity:0;transition:opacity 0.2s}
.toast.show{opacity:1}
.debug-panel{position:fixed;bottom:10px;right:10px;background:#1e293b;color:#0f0;font-family:monospace;font-size:10px;padding:8px;border-radius:8px;z-index:9999;max-width:500px;max-height:300px;overflow:auto;opacity:0.95;cursor:move}
.debug-panel.minimized{height:35px;overflow:hidden}
.debug-header{display:flex;justify-content:space-between;margin-bottom:5px;cursor:move;background:#334155;padding:4px 8px;border-radius:4px}
.debug-close{color:#ef4444;cursor:pointer;margin-left:10px}
.debug-save{color:#10b981;cursor:pointer;margin-right:10px}
.image-status{font-size:9px;color:#94a3b8;border-top:1px solid #334155;margin-top:5px;padding-top:5px}
.image-status.failed{color:#ef4444}
.image-status.loaded{color:#10b981}
.lightbox{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);display:none;align-items:center;justify-content:center;z-index:1000}
.lightbox.active{display:flex}
.modal{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1e293b;border-radius:1rem;max-width:600px;width:90%;max-height:80vh;overflow-y:auto;z-index:1100;display:none;padding:1rem}
.modal.active{display:block}
</style>
</head>
<body>

<div class="debug-panel" id="debugPanel">
    <div class="debug-header">
        <strong>🔍 Debug Console</strong>
        <span>
            <span id="debugSave" class="debug-save" title="Save logs">💾</span>
            <span id="debugMinimize" style="cursor:pointer;margin-right:8px;">−</span>
            <span id="debugClose" class="debug-close">✕</span>
        </span>
    </div>
    <div id="debugLog" style="max-height:200px;overflow-y:auto"></div>
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
    <button id="syncSelectedBtn" class="primary">Sync Selected to Storyboard</button>
    <button id="checkMissingBtn" class="warning">Check Missing Images</button>
    <button id="saveLogsBtn" class="warning">💾 Save Logs</button>
    <span id="selectedCount">0 selected</span>
</div>

<div id="galleryGrid" class="grid"></div>

<button class="storyboard-btn" id="openStoryboardBtn">Open Storyboard <span id="storyboardCountBadge">0</span></button>

<div id="storyboardModal" class="storyboard-modal">
    <div class="storyboard-container">
        <div style="display:flex;justify-content:space-between;">
            <h3>Storyboard Builder - Persistent Layout</h3>
            <button id="closeStoryboardBtn" style="background:#ef4444;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer">Close</button>
        </div>
        <div class="storyboard-controls">
            <select id="templateSelect">
                <option value="grid">Grid (3 cols)</option>
                <option value="center">Single centered</option>
                <option value="masonry">Masonry</option>
            </select>
            <select id="upscaleMode">
                <option value="lanczos">Lanczos (Sharp edges)</option>
                <option value="edge">Edge-Aware (Better for curves/text)</option>
            </select>
            <button id="applyTemplateBtn">Apply Template</button>
            <button id="exportStoryboardBtn" class="primary">Export Super Resolution PNG</button>
            <button id="clearStoryboardBtn">Clear All</button>
        </div>
        <canvas id="storyboardCanvas" width="1080" height="1440"></canvas>
        <div><strong>Images (click to remove):</strong>
            <div id="storyboardThumbnails" style="display:flex;gap:12px;overflow-x:auto;padding:8px;"></div>
        </div>
    </div>
</div>

<div id="toast" class="toast"></div>
<div id="lightbox" class="lightbox"><div class="lightbox-content"><div id="lightboxClose" style="position:absolute;top:10px;right:10px;color:white;font-size:2rem;cursor:pointer;">×</div><div id="lightboxMediaContainer"></div></div></div>
<div id="commentsModal" class="modal"><div><strong>Comments</strong><span id="modalClose" style="float:right;cursor:pointer;">&times;</span></div><div id="commentsList"></div></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
<script>
var allPosts = ''' + posts_json + ''';
var allLogs = [];
var imageLoadErrors = {};
var imageLoadSuccess = {};

// ========== PERSISTENT STORAGE ==========
var STORAGE_IMAGES_KEY = "storyboard_images_data";
var STORAGE_BG_KEY = "storyboard_bg_color";
var STORAGE_TEMPLATE_KEY = "storyboard_template";
var STORAGE_UPSCALE_KEY = "storyboard_upscale_mode";
var STORAGE_LOGS_KEY = "storyboard_logs";

// Debug panel controls
var debugPanel = document.getElementById("debugPanel");
var debugLog = document.getElementById("debugLog");
var imageStatusLog = document.getElementById("imageStatusLog");
var minimized = false;

document.getElementById("debugMinimize").onclick = function() {
    minimized = !minimized;
    if(minimized) {
        debugPanel.classList.add("minimized");
        this.textContent = "+";
    } else {
        debugPanel.classList.remove("minimized");
        this.textContent = "−";
    }
};
document.getElementById("debugClose").onclick = function() {
    debugPanel.style.display = "none";
};

function saveLogsToFile() {
    var logsText = allLogs.join("\\n");
    var blob = new Blob([logsText], {type: "text/plain"});
    var a = document.createElement("a");
    var url = URL.createObjectURL(blob);
    a.href = url;
    a.download = "gallery_logs_" + new Date().toISOString().slice(0,19).replace(/:/g, "-") + ".txt";
    a.click();
    URL.revokeObjectURL(url);
    showToast("Logs saved to file");
}

function saveLogsToLocalStorage() {
    try {
        localStorage.setItem(STORAGE_LOGS_KEY, JSON.stringify(allLogs.slice(-500)));
        addLog("Logs saved to localStorage");
    } catch(e) { console.warn(e); }
}

function loadLogsFromLocalStorage() {
    try {
        var saved = localStorage.getItem(STORAGE_LOGS_KEY);
        if(saved) {
            var logs = JSON.parse(saved);
            for(var i=0;i<logs.length;i++) {
                addLog(logs[i].replace(/^\\d+:\\d+:\\d+\\s+/, ''), false, true);
            }
            addLog("Loaded " + logs.length + " previous logs");
        }
    } catch(e) { console.warn(e); }
}

function addLog(msg, isError, skipSave) {
    var timestamp = new Date().toLocaleTimeString();
    var fullMsg = timestamp + " " + msg;
    var d = document.createElement("div");
    d.textContent = fullMsg;
    if(isError) d.style.color = "#ef4444";
    debugLog.appendChild(d);
    if(debugLog.children.length > 100) debugLog.removeChild(debugLog.children[0]);
    console.log(msg);
    if(!skipSave) {
        allLogs.push(fullMsg);
        if(allLogs.length > 1000) allLogs.shift();
        saveLogsToLocalStorage();
    }
}

// Make debug panel draggable
var isDragging = false, dragStartX, dragStartY, panelStartX, panelStartY;
debugPanel.addEventListener("mousedown", function(e) {
    if(e.target.closest("#debugMinimize") || e.target.closest("#debugClose") || e.target.closest("#debugSave")) return;
    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    panelStartX = debugPanel.offsetLeft;
    panelStartY = debugPanel.offsetTop;
    debugPanel.style.position = "fixed";
});
document.addEventListener("mousemove", function(e) {
    if(!isDragging) return;
    var dx = e.clientX - dragStartX;
    var dy = e.clientY - dragStartY;
    debugPanel.style.left = (panelStartX + dx) + "px";
    debugPanel.style.top = (panelStartY + dy) + "px";
    debugPanel.style.right = "auto";
    debugPanel.style.bottom = "auto";
});
document.addEventListener("mouseup", function() { isDragging = false; });

function showToast(msg) {
    var t = document.getElementById("toast");
    t.textContent = msg;
    t.classList.add("show");
    setTimeout(function() { t.classList.remove("show"); }, 2000);
    addLog("Toast: " + msg);
}

function getMediaPath(folder, file) {
    return folder + "/" + file;
}

// Gallery render with error tracking
function renderGallery(posts) {
    addLog("Rendering " + posts.length + " posts");
    var grid = document.getElementById("galleryGrid");
    if(!posts.length){ grid.innerHTML = "<div style='text-align:center;padding:3rem;'>No posts match.</div>"; return; }
    var htmlStr = "";
    for(var idx=0; idx<posts.length; idx++){
        var post = posts[idx];
        var pm = post.all_media.length ? post.all_media[0] : null;
        var mediaHtml = "";
        if(pm){ 
            var mp = getMediaPath(post.folder_name, pm); 
            mediaHtml = "<img class='card-media' src='" + mp + "' loading='lazy' data-path='" + mp + "' onerror='trackImageError(this)' onload='trackImageLoad(this)'>"; 
        }
        else { mediaHtml = "<div class='card-media'>No media</div>"; }
        htmlStr += "<div class='card' data-shortcode='" + post.shortcode + "' data-folder='" + post.folder_name + "'>";
        htmlStr += "<div style='position:relative;width:100%;aspect-ratio:4/3;'>" + mediaHtml + "</div>";
        htmlStr += "<div class='card-content'>";
        htmlStr += "<div class='card-meta'><span class='author-name'>@" + post.author + "</span><span>📅 " + new Date(post.date).toLocaleDateString() + "</span></div>";
        htmlStr += "</div></div>";
    }
    grid.innerHTML = htmlStr;
    addCheckboxesToCards();
    updateImageStatus();
}

function trackImageError(img) {
    var src = img.src;
    if(!imageLoadErrors[src]) {
        imageLoadErrors[src] = true;
        delete imageLoadSuccess[src];
        img.classList.add("load-error");
        addLog("❌ IMAGE FAILED: " + src, true);
        updateImageStatus();
    }
}

function trackImageLoad(img) {
    var src = img.src;
    if(!imageLoadSuccess[src]) {
        imageLoadSuccess[src] = true;
        delete imageLoadErrors[src];
        addLog("✅ Image loaded: " + src);
        updateImageStatus();
    }
}

function updateImageStatus() {
    var total = Object.keys(imageLoadErrors).length + Object.keys(imageLoadSuccess).length;
    var failed = Object.keys(imageLoadErrors).length;
    var html = '<div><strong>📊 Image Load Status:</strong> ' + total + ' total, ' + 
               '<span style="color:#10b981">' + Object.keys(imageLoadSuccess).length + ' loaded</span>, ' +
               '<span style="color:#ef4444">' + failed + ' failed</span></div>';
    if(failed > 0) {
        var failedList = Object.keys(imageLoadErrors).slice(0,5);
        html += '<div style="font-size:9px;color:#ef4444">Failed: ' + failedList.join(', ') + 
                (failed > 5 ? '...' : '') + '</div>';
    }
    imageStatusLog.innerHTML = html;
}

// Selection
var selectedSrcs = new Set();

function addCheckboxesToCards(){
    var cards = document.querySelectorAll(".card");
    for(var i=0;i<cards.length;i++){
        if(cards[i].querySelector(".select-checkbox")) continue;
        var img = cards[i].querySelector("img");
        if(!img || !img.src) continue;
        var chk = document.createElement("input");
        chk.type = "checkbox"; chk.className = "select-checkbox";
        chk.onchange = function(e){
            e.stopPropagation();
            var card = this.closest(".card");
            var imgEl = card.querySelector("img");
            if(this.checked){ 
                selectedSrcs.add(imgEl.src);
                addImageToStoryboard(imgEl.src);
            } else { 
                selectedSrcs.delete(imgEl.src); 
            }
            document.getElementById("selectedCount").innerText = selectedSrcs.size + " selected";
        };
        cards[i].style.position = "relative";
        cards[i].appendChild(chk);
    }
}

function selectAll(){
    var checkboxes = document.querySelectorAll(".select-checkbox");
    for(var i=0;i<checkboxes.length;i++) {
        if(!checkboxes[i].checked) checkboxes[i].click();
    }
}

function deselectAll(){
    var checkboxes = document.querySelectorAll(".select-checkbox");
    for(var i=0;i<checkboxes.length;i++) {
        if(checkboxes[i].checked) checkboxes[i].click();
    }
}

function checkMissingImages() {
    var failed = Object.keys(imageLoadErrors);
    if(failed.length === 0) {
        showToast("All images loaded successfully!");
    } else {
        showToast(failed.length + " images failed to load. Check debug panel.");
        addLog("=== MISSING IMAGES (" + failed.length + ") ===");
        for(var i=0;i<failed.length;i++) addLog("  " + failed[i], true);
    }
}

// ========== PERSISTENT STORYBOARD ==========
var canvas = null;
var storyboardImages = [];
var PREVIEW_W = 1080, PREVIEW_H = 1440;
var TARGET_W = 10800, TARGET_H = 14400;
var SCALE = TARGET_W / PREVIEW_W;
var currentTemplate = "grid";
var currentUpscaleMode = "lanczos";

function initCanvas() {
    var canvasEl = document.getElementById("storyboardCanvas");
    if(!canvasEl) return;
    if(canvas) canvas.dispose();
    canvas = new fabric.Canvas("storyboardCanvas", { 
        enableRetinaScaling: true, 
        imageSmoothingEnabled: true,
        imageSmoothingQuality: "high",
        selection: true
    });
    canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
    canvas.backgroundColor = "#ffffff";
    var ctx = canvas.getContext("2d");
    if(ctx) ctx.imageSmoothingQuality = "high";
    canvas.renderAll();
    addLog("Canvas initialized");
    
    // Restore saved state
    loadStoryboardState();
}

function saveStoryboardState() {
    var imageData = [];
    for(var i=0;i<storyboardImages.length;i++) {
        imageData.push({
            src: storyboardImages[i].src,
            left: storyboardImages[i].fabricObj.left,
            top: storyboardImages[i].fabricObj.top,
            scaleX: storyboardImages[i].fabricObj.scaleX,
            scaleY: storyboardImages[i].fabricObj.scaleY,
            width: storyboardImages[i].originalWidth,
            height: storyboardImages[i].originalHeight
        });
    }
    localStorage.setItem(STORAGE_IMAGES_KEY, JSON.stringify(imageData));
    localStorage.setItem(STORAGE_BG_KEY, canvas.backgroundColor);
    localStorage.setItem(STORAGE_TEMPLATE_KEY, document.getElementById("templateSelect").value);
    localStorage.setItem(STORAGE_UPSCALE_KEY, document.getElementById("upscaleMode").value);
    addLog("Storyboard state saved (" + imageData.length + " images)");
}

function loadStoryboardState() {
    var savedImages = localStorage.getItem(STORAGE_IMAGES_KEY);
    var savedBg = localStorage.getItem(STORAGE_BG_KEY);
    var savedTemplate = localStorage.getItem(STORAGE_TEMPLATE_KEY);
    var savedUpscale = localStorage.getItem(STORAGE_UPSCALE_KEY);
    
    if(savedTemplate) {
        document.getElementById("templateSelect").value = savedTemplate;
        currentTemplate = savedTemplate;
    }
    if(savedUpscale) {
        document.getElementById("upscaleMode").value = savedUpscale;
        currentUpscaleMode = savedUpscale;
    }
    if(savedBg && canvas) {
        canvas.backgroundColor = savedBg;
    }
    
    if(savedImages) {
        try {
            var images = JSON.parse(savedImages);
            addLog("Loading " + images.length + " saved images...");
            var loadPromises = [];
            for(var i=0;i<images.length;i++) {
                loadPromises.push(restoreSavedImage(images[i]));
            }
            Promise.all(loadPromises).then(function() {
                if(canvas) canvas.renderAll();
                updateStoryboardBadge();
                updateThumbnails();
                addLog("Storyboard restored");
            });
        } catch(e) { addLog("Error loading saved state: " + e, true); }
    }
}

function restoreSavedImage(imgData) {
    return new Promise(function(resolve) {
        fabric.Image.fromURL(imgData.src, function(fabricImg) {
            if(!fabricImg) { resolve(); return; }
            fabricImg.set({
                left: imgData.left,
                top: imgData.top,
                scaleX: imgData.scaleX,
                scaleY: imgData.scaleY,
                hasControls: true,
                hasBorders: true,
                lockRotation: true
            });
            storyboardImages.push({
                src: imgData.src,
                fabricObj: fabricImg,
                originalWidth: imgData.width,
                originalHeight: imgData.height
            });
            canvas.add(fabricImg);
            resolve();
        });
    });
}

// Lanczos kernel and resampling functions
function lanczosKernel(x, a) {
    a = a || 3;
    if (x === 0) return 1;
    if (Math.abs(x) >= a) return 0;
    var pi = Math.PI;
    var pix = pi * x;
    var pixA = pi * x / a;
    return (Math.sin(pix) * Math.sin(pixA)) / (pix * pixA);
}

function lanczosResample(sourceCanvas, targetWidth, targetHeight) {
    var source = sourceCanvas.getContext("2d").getImageData(0, 0, sourceCanvas.width, sourceCanvas.height);
    var sourceWidth = sourceCanvas.width;
    var sourceHeight = sourceCanvas.height;
    var targetCanvas = document.createElement("canvas");
    targetCanvas.width = targetWidth;
    targetCanvas.height = targetHeight;
    var targetCtx = targetCanvas.getContext("2d");
    var targetData = targetCtx.createImageData(targetWidth, targetHeight);
    var scaleX = sourceWidth / targetWidth;
    var scaleY = sourceHeight / targetHeight;
    
    for (var y = 0; y < targetHeight; y++) {
        var sy = y * scaleY;
        var syInt = Math.floor(sy);
        var syFrac = sy - syInt;
        for (var x = 0; x < targetWidth; x++) {
            var sx = x * scaleX;
            var sxInt = Math.floor(sx);
            var sxFrac = sx - sxInt;
            var r = 0, g = 0, b = 0, a_total = 0;
            var weightTotal = 0;
            for (var dy = -3; dy <= 3; dy++) {
                var sampleY = syInt + dy;
                if (sampleY < 0 || sampleY >= sourceHeight) continue;
                var lanczosY = lanczosKernel((syFrac - dy) / scaleY, 3);
                for (var dx = -3; dx <= 3; dx++) {
                    var sampleX = sxInt + dx;
                    if (sampleX < 0 || sampleX >= sourceWidth) continue;
                    var lanczosX = lanczosKernel((sxFrac - dx) / scaleX, 3);
                    var weight = lanczosX * lanczosY;
                    var idx = (sampleY * sourceWidth + sampleX) * 4;
                    r += source.data[idx] * weight;
                    g += source.data[idx+1] * weight;
                    b += source.data[idx+2] * weight;
                    a_total += source.data[idx+3] * weight;
                    weightTotal += weight;
                }
            }
            var targetIdx = (y * targetWidth + x) * 4;
            targetData.data[targetIdx] = r / weightTotal;
            targetData.data[targetIdx+1] = g / weightTotal;
            targetData.data[targetIdx+2] = b / weightTotal;
            targetData.data[targetIdx+3] = a_total / weightTotal;
        }
    }
    targetCtx.putImageData(targetData, 0, 0);
    return targetCanvas;
}

function edgeAwareResample(sourceCanvas, targetWidth, targetHeight) {
    var source = sourceCanvas.getContext("2d").getImageData(0, 0, sourceCanvas.width, sourceCanvas.height);
    var sourceWidth = sourceCanvas.width;
    var sourceHeight = sourceCanvas.height;
    var targetCanvas = document.createElement("canvas");
    targetCanvas.width = targetWidth;
    targetCanvas.height = targetHeight;
    var targetCtx = targetCanvas.getContext("2d");
    var targetData = targetCtx.createImageData(targetWidth, targetHeight);
    var scaleX = sourceWidth / targetWidth;
    var scaleY = sourceHeight / targetHeight;
    
    function detectEdge(x, y, data, w, h) {
        if(x < 1 || y < 1 || x >= w-1 || y >= h-1) return 0;
        var idx = (y * w + x) * 4;
        var gx = 0, gy = 0;
        gx += -1 * data[idx-4-w*4];
        gx += -2 * data[idx-4];
        gx += -1 * data[idx-4+w*4];
        gx += 1 * data[idx+4-w*4];
        gx += 2 * data[idx+4];
        gx += 1 * data[idx+4+w*4];
        gy += -1 * data[idx-4-w*4];
        gy += -2 * data[idx-w*4];
        gy += -1 * data[idx+4-w*4];
        gy += 1 * data[idx-4+w*4];
        gy += 2 * data[idx+w*4];
        gy += 1 * data[idx+4+w*4];
        return Math.sqrt(gx*gx + gy*gy) / 255;
    }
    
    for (var y = 0; y < targetHeight; y++) {
        var sy = y * scaleY;
        var syInt = Math.floor(sy);
        var syFrac = sy - syInt;
        for (var x = 0; x < targetWidth; x++) {
            var sx = x * scaleX;
            var sxInt = Math.floor(sx);
            var sxFrac = sx - sxInt;
            var edgeStrength = detectEdge(sxInt, syInt, source.data, sourceWidth, sourceHeight);
            var r = 0, g = 0, b = 0, a_total = 0;
            var weightTotal = 0;
            var kernelRadius = edgeStrength > 0.3 ? 2 : 3;
            
            for (var dy = -kernelRadius; dy <= kernelRadius; dy++) {
                var sampleY = syInt + dy;
                if (sampleY < 0 || sampleY >= sourceHeight) continue;
                var lanczosY = lanczosKernel((syFrac - dy) / scaleY, kernelRadius);
                for (var dx = -kernelRadius; dx <= kernelRadius; dx++) {
                    var sampleX = sxInt + dx;
                    if (sampleX < 0 || sampleX >= sourceWidth) continue;
                    var lanczosX = lanczosKernel((sxFrac - dx) / scaleX, kernelRadius);
                    var weight = lanczosX * lanczosY;
                    if(edgeStrength > 0.2) weight *= (1 + edgeStrength * 0.5);
                    var idx = (sampleY * sourceWidth + sampleX) * 4;
                    r += source.data[idx] * weight;
                    g += source.data[idx+1] * weight;
                    b += source.data[idx+2] * weight;
                    a_total += source.data[idx+3] * weight;
                    weightTotal += weight;
                }
            }
            var targetIdx = (y * targetWidth + x) * 4;
            targetData.data[targetIdx] = Math.min(255, r / weightTotal);
            targetData.data[targetIdx+1] = Math.min(255, g / weightTotal);
            targetData.data[targetIdx+2] = Math.min(255, b / weightTotal);
            targetData.data[targetIdx+3] = a_total / weightTotal;
        }
    }
    targetCtx.putImageData(targetData, 0, 0);
    return targetCanvas;
}

function addImageToStoryboard(src) {
    var filename = src.split('/').pop();
    addLog("Adding: " + filename);
    
    for(var i=0;i<storyboardImages.length;i++){
        if(storyboardImages[i].src === src){ 
            showToast("Already in storyboard"); 
            return;
        }
    }
    
    var img = new Image();
    img.crossOrigin = null;
    img.onload = function() {
        addLog("Loaded: " + img.width + "x" + img.height);
        var targetDisplayWidth = PREVIEW_W * 0.33;
        var needsUpscale = (img.width < targetDisplayWidth);
        var upscaleMode = document.getElementById("upscaleMode").value;
        currentUpscaleMode = upscaleMode;
        
        function addToCanvas(imageUrl) {
            fabric.Image.fromURL(imageUrl, function(fabricImg) {
                if(!fabricImg) { showToast("Failed to load image"); return; }
                fabricImg.set({ hasControls: true, hasBorders: true, lockRotation: true });
                var margin = 20;
                var x = margin + (storyboardImages.length % 3) * 300;
                var y = margin + Math.floor(storyboardImages.length / 3) * 200;
                fabricImg.set({ left: x, top: y });
                storyboardImages.push({ 
                    src: src, 
                    fabricObj: fabricImg, 
                    originalWidth: img.width, 
                    originalHeight: img.height 
                });
                canvas.add(fabricImg);
                canvas.renderAll();
                updateThumbnails();
                updateStoryboardBadge();
                saveStoryboardState();
                showToast("Image added");
            });
        }
        
        if(needsUpscale) {
            addLog("Upscaling with " + upscaleMode + " from " + img.width + "x" + img.height);
            var sourceCanvas = document.createElement("canvas");
            sourceCanvas.width = img.width;
            sourceCanvas.height = img.height;
            var ctx = sourceCanvas.getContext("2d");
            ctx.drawImage(img, 0, 0);
            var upscaleTarget = Math.max(targetDisplayWidth * 2, img.width * 2);
            var upscaleHeight = (img.height / img.width) * upscaleTarget;
            var upscaledCanvas = (upscaleMode === "edge") ? 
                edgeAwareResample(sourceCanvas, upscaleTarget, upscaleHeight) :
                lanczosResample(sourceCanvas, upscaleTarget, upscaleHeight);
            addToCanvas(upscaledCanvas.toDataURL("image/png"));
        } else {
            addToCanvas(src);
        }
    };
    img.onerror = function() {
        addLog("ERROR loading: " + src, true);
        showToast("Failed to load: " + filename);
    };
    img.src = src;
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
    var thumbs = document.querySelectorAll(".storyboard-thumb");
    for(var i=0;i<thumbs.length;i++){
        thumbs[i].onclick = function(e){
            e.stopPropagation();
            var idx = parseInt(this.dataset.index);
            canvas.remove(storyboardImages[idx].fabricObj);
            storyboardImages.splice(idx,1);
            canvas.renderAll();
            updateThumbnails();
            updateStoryboardBadge();
            saveStoryboardState();
            showToast("Image removed");
        };
    }
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
            var scale = Math.min(cellW / obj.width, 300 / obj.height);
            obj.scale(scale);
            obj.set({ left: margin + col * (cellW + margin), top: y });
            if(col === cols-1 || i === storyboardImages.length-1) {
                y += obj.height * scale + margin;
            }
        }
    } else if(tpl === "center") {
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
    addLog("Layout applied: " + tpl);
}

function syncSelectedToStoryboard() {
    var srcs = Array.from(selectedSrcs);
    if(srcs.length === 0){ showToast("No images selected"); return; }
    for(var i=0;i<srcs.length;i++) addImageToStoryboard(srcs[i]);
}

function clearAll() {
    if(confirm("Clear all images from storyboard?")){
        for(var i=0;i<storyboardImages.length;i++) canvas.remove(storyboardImages[i].fabricObj);
        storyboardImages = [];
        canvas.renderAll();
        updateThumbnails();
        updateStoryboardBadge();
        localStorage.removeItem(STORAGE_IMAGES_KEY);
        showToast("Storyboard cleared");
        saveStoryboardState();
    }
}

function exportHighQuality() {
    if(storyboardImages.length === 0){ showToast("No images to export"); return; }
    addLog("Starting super-resolution export...");
    showToast("Exporting super resolution PNG...");
    
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
    a.download = "storyboard_" + currentUpscaleMode + "_" + new Date().toISOString().slice(0,19).replace(/:/g, "-") + ".png";
    a.href = offCanvas.toDataURL("image/png");
    a.click();
    addLog("Export complete");
    showToast("Export complete!");
}

// Event listeners
document.getElementById("selectAllBtn").onclick = selectAll;
document.getElementById("deselectAllBtn").onclick = deselectAll;
document.getElementById("syncSelectedBtn").onclick = syncSelectedToStoryboard;
document.getElementById("checkMissingBtn").onclick = checkMissingImages;
document.getElementById("saveLogsBtn").onclick = saveLogsToFile;
document.getElementById("debugSave").onclick = saveLogsToFile;
document.getElementById("openStoryboardBtn").onclick = function(){ document.getElementById("storyboardModal").classList.add("active"); };
document.getElementById("closeStoryboardBtn").onclick = function(){ 
    document.getElementById("storyboardModal").classList.remove("active");
    saveStoryboardState();
};
document.getElementById("exportStoryboardBtn").onclick = exportHighQuality;
document.getElementById("clearStoryboardBtn").onclick = clearAll;
document.getElementById("applyTemplateBtn").onclick = applyLayout;

document.getElementById("searchInput").addEventListener("input", function(e){
    var q = e.target.value.toLowerCase();
    var filtered = allPosts.filter(function(p){ return p.caption.toLowerCase().indexOf(q) !== -1; });
    renderGallery(filtered);
});
document.getElementById("lightboxClose").onclick = function(){ document.getElementById("lightbox").classList.remove("active"); };
document.getElementById("modalClose").onclick = function(){ document.getElementById("commentsModal").classList.remove("active"); };

// Fix click handling on canvas
document.getElementById("storyboardCanvas").style.cursor = "crosshair";

// Initialize
initCanvas();
renderGallery(allPosts);
loadLogsFromLocalStorage();
addLog("=== READY - Persistent Storyboard v0023 ===");
addLog("Images will persist after closing/reopening storyboard");
</script>
</body>
</html>'''
    
    return html

def main():
    print("=" * 70)
    print("MR. DOUGLAS GALLERY BUILDER v0023 - Persistent Storyboard")
    print("=" * 70)
    
    print("\n[1/3] Loading posts...")
    posts = load_posts()
    posts = add_historic_images(posts)
    print(f"Loaded {len(posts)} posts")
    
    print("[2/3] Generating HTML with persistence...")
    html = build_html(posts)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    print(f"Generated {OUTPUT_HTML}")
    
    print("[3/3] Starting server...")
    os.system("pkill -f 'http.server' 2>/dev/null")
    os.system("pkill -f 'run_error_server' 2>/dev/null")
    time.sleep(1)
    
    subprocess.Popen([sys.executable, '-m', 'http.server', '8000'], 
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    print("\n" + "=" * 70)
    print("✅ READY!")
    print("=" * 70)
    print(f"Open: http://localhost:8000/{OUTPUT_HTML.name}")
    print("\n✨ NEW FEATURES v0023:")
    print("   💾 Persistent storyboard - Images keep position after reopen")
    print("   📝 Logs saved to localStorage and exportable to file")
    print("   🔍 Image failure tracking - See exactly which images fail")
    print("   🖱️ Fixed click handling on canvas objects")
    print("   💾 Save Logs button - Export all logs to text file")
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