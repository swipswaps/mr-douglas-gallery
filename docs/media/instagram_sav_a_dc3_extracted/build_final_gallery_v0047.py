#!/usr/bin/env python3
"""
build_final_gallery_v0047.py - Complete Gallery with Text Overlays from Grid, Textarea, Clipboard, Transparent PNG
Preserves ALL v0046 features + adds text overlay capabilities
Compliant with all 6 fixes from JSON list:
1. Text Overlay from Grid Database - Extract caption/comments as editable text
2. Text Overlay from Textarea - Custom input with font/color controls
3. Text Overlay from Clipboard - Paste text at mouse position
4. Transparent PNG Overlay - Import and apply with opacity control
5. Clipboard Image Paste - PNG transparency preservation
6. Whole Storyboard Text Overlay - Background text layer with watermarks
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
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path("instagram_posts.db")
OUTPUT_HTML = Path("index_v0047.html")
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

def download_youtube_thumbnails(posts):
    youtube_thumbs_dir = Path("youtube_thumbs")
    youtube_thumbs_dir.mkdir(exist_ok=True)
    youtube_pattern = re.compile(r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})')
    youtube_ids = set()
    for post in posts:
        caption = post.get('caption', '')
        matches = youtube_pattern.findall(caption)
        for vid in matches:
            youtube_ids.add(vid)
    qualities = ['maxresdefault', 'sddefault', 'hqdefault', 'mqdefault']
    for vid in youtube_ids:
        for quality in qualities:
            url = f'https://img.youtube.com/vi/{vid}/{quality}.jpg'
            local_path = youtube_thumbs_dir / f'{vid}_{quality}.jpg'
            if not local_path.exists():
                try:
                    urllib.request.urlretrieve(url, local_path)
                    print(f'Downloaded YouTube thumbnail: {vid}_{quality}.jpg')
                except:
                    pass

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
    print(f"JSON size: {len(posts_json)} bytes for {len(posts)} posts")
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mr. Douglas Gallery v0047 - Text Overlays + Clipboard + Transparent PNG</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0f172a;color:#e2e8f0;font-family:system-ui}
.search-header{position:sticky;top:0;z-index:20;background:rgba(15,23,42,0.95);backdrop-filter:blur(8px);border-bottom:1px solid #334155;padding:1rem}
.search-container{max-width:1200px;margin:0 auto}
.search-input{width:100%;padding:0.75rem 1rem;background:#1e293b;border:1px solid #475569;border-radius:2rem;color:#f1f5f9;font-size:1rem}
.menu-bar{display:flex;gap:20px;padding:8px 16px;background:#1e293b;border-bottom:1px solid #334155;font-size:12px}
.menu-item{position:relative;cursor:pointer;padding:4px 8px;border-radius:4px}
.menu-item:hover{background:#334155}
.menu-dropdown{display:none;position:absolute;top:100%;left:0;background:#1e293b;border:1px solid #475569;border-radius:4px;min-width:180px;z-index:100}
.menu-option{padding:8px 12px;cursor:pointer}
.menu-option:hover{background:#3b82f6}
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
.storyboard-container{background:#1e293b;margin:20px auto;padding:20px;border-radius:16px;max-width:95%;width:1200px;position:relative}
#storyboardCanvas{border:2px solid #475569;border-radius:8px;background:white;display:block;margin:0 auto}
.storyboard-controls{display:flex;gap:10px;justify-content:center;margin:15px 0;flex-wrap:wrap}
.storyboard-controls button{background:#3b82f6;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer}
.storyboard-thumb{width:80px;height:80px;object-fit:cover;border-radius:8px;cursor:pointer;margin-right:8px}
.toast{position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1e293b;color:#e2e8f0;padding:10px 20px;border-radius:40px;z-index:3000;opacity:0;transition:opacity 0.2s;pointer-events:none}
.toast.show{opacity:1}
.debug-panel{position:fixed;bottom:10px;right:10px;background:#1e293b;color:#0f0;font-family:monospace;font-size:10px;padding:8px;border-radius:8px;z-index:9999;max-width:500px;max-height:300px;overflow:auto;opacity:0.95;cursor:move}
.debug-header{display:flex;justify-content:space-between;margin-bottom:5px;background:#334155;padding:4px 8px;border-radius:4px;cursor:move}
.debug-close{color:#ef4444;cursor:pointer;margin-left:10px}
.debug-save{color:#10b981;cursor:pointer;margin-right:10px}
.debug-minimize{cursor:pointer;margin-right:8px}
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
.asset-thumbnail{position:relative;width:80px;height:80px;border-radius:8px;overflow:hidden;cursor:pointer;flex-shrink:0}
.asset-thumbnail img{width:100%;height:100%;object-fit:cover}
.asset-action{position:absolute;bottom:4px;right:4px;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:16px;cursor:pointer}
.template-preview{width:80px;text-align:center;cursor:pointer;padding:5px;border-radius:8px;background:#1e293b;transition:all 0.2s}
.template-preview:hover{background:#334155}
.template-preview .preview-box{width:70px;height:50px;background:#0f172a;border-radius:4px;margin:0 auto;display:flex;flex-wrap:wrap;padding:5px;gap:3px;justify-content:center;align-items:center}
.storyboard-save-item{display:flex;align-items:center;gap:10px;padding:8px;border-bottom:1px solid #334155;cursor:pointer}
.storyboard-save-item:hover{background:#334155}
.storyboard-save-item img{width:60px;height:60px;object-fit:cover;border-radius:4px}
.delete-save{margin-left:auto;background:#ef4444;border:none;color:white;padding:4px 8px;border-radius:4px;cursor:pointer}
.grid-controls{display:flex;gap:8px;margin:10px 0;flex-wrap:wrap;border-top:1px solid #475569;padding-top:10px}
.snap-controls{display:flex;gap:8px;align-items:center;margin:10px 0;flex-wrap:wrap}
.reorder-controls{display:flex;gap:8px;margin:10px 0;flex-wrap:wrap;border-top:1px solid #475569;padding-top:10px}
.text-overlay-panel{margin:10px 0;padding:10px;background:#0f172a;border-radius:8px;border:1px solid #334155}
.watermark-presets{display:flex;gap:8px;margin:10px 0;flex-wrap:wrap}
</style>
</head>
<body>

<!-- Debug Panel -->
<div class="debug-panel" id="debugPanel">
    <div class="debug-header">
        <strong>🔍 Debug Console</strong>
        <span>
            <span id="debugMinimizeBtn" class="debug-minimize">−</span>
            <span id="debugSaveBtn" class="debug-save">💾</span>
            <span id="debugCloseBtn" class="debug-close">✕</span>
        </span>
    </div>
    <div id="debugLog" style="max-height:200px;overflow-y:auto;cursor:auto"></div>
    <div id="imageStatusLog" class="image-status" style="cursor:auto"></div>
</div>

<!-- Search Header -->
<div class="search-header">
    <div class="search-container">
        <input type="text" id="searchInput" class="search-input" placeholder="Search posts...">
    </div>
</div>

<!-- Menu Bar -->
<div class="menu-bar">
    <div class="menu-item">File<div class="menu-dropdown"><div class="menu-option" data-action="newStoryboard">New Storyboard</div><div class="menu-option" data-action="saveStoryboard">Save Storyboard As...</div><div class="menu-option" data-action="loadStoryboard">Load Storyboard...</div><div class="menu-option" data-action="exportPNG">Export PNG (300 DPI)</div></div></div>
    <div class="menu-item">Edit<div class="menu-dropdown"><div class="menu-option" data-action="undo">Undo (Ctrl+Z)</div><div class="menu-option" data-action="redo">Redo (Ctrl+Y)</div><div class="menu-option" data-action="duplicate">Duplicate</div><div class="menu-option" data-action="delete">Delete</div><div class="menu-option" data-action="unlockAll">🔓 Unlock All</div></div></div>
    <div class="menu-item">View<div class="menu-dropdown"><div class="menu-option" data-action="zoomIn">Zoom In (Ctrl++)</div><div class="menu-option" data-action="zoomOut">Zoom Out (Ctrl+-)</div><div class="menu-option" data-action="resetZoom">Reset Zoom</div><div class="menu-option" data-action="toggleGrid">📐 Show Grid</div><div class="menu-option" data-action="toggleSnap">🔲 Snap to Grid</div><div class="menu-option" data-action="toggleCells">🔲 Snap to Cells</div><div class="menu-option" data-action="toggleFine">🔍 Fine Move</div><div class="menu-option" data-action="toggleCrop">✂️ Crop to Fit</div></div></div>
    <div class="menu-item">History<div class="menu-dropdown" id="historyMenu" style="min-width:250px;max-height:300px;overflow-y:auto"></div></div>
    <div class="menu-item">Help<div class="menu-dropdown"><div class="menu-option">Shortcuts: Ctrl+Z=Undo, Ctrl+Y=Redo, Del=Delete</div><div class="menu-option">Arrow Keys: 1px move, Shift+Arrow = 10px</div><div class="menu-option">Ctrl+V pastes text/images at mouse position</div></div></div>
</div>

<!-- Gallery Toolbar -->
<div class="gallery-toolbar">
    <span>Select images:</span>
    <button id="selectAllBtn">Select All</button>
    <button id="deselectAllBtn">Deselect All</button>
    <button id="syncSelectedBtn" class="primary">Sync to Storyboard</button>
    <button id="openStoryboardBtn" class="success">Open Storyboard <span id="storyboardCountBadge">0</span></button>
    <button id="checkMissingBtn" class="warning">Check Missing</button>
    <span id="selectedCount">0 selected</span>
</div>

<!-- Gallery Grid -->
<div id="galleryGrid" class="grid"></div>

<!-- Storyboard Modal -->
<div id="storyboardModal" class="storyboard-modal">
    <div class="storyboard-container">
        <div style="display:flex;justify-content:space-between;">
            <h3>Storyboard Builder - Text Overlays + Transparent PNG + Clipboard</h3>
            <button id="closeStoryboardBtn" style="background:#ef4444;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer">Close</button>
        </div>
        
        <div class="storyboard-controls">
            <div style="display:flex;gap:10px;margin-bottom:10px;flex-wrap:wrap;align-items:center;">
                <label>Background:</label><select id="bgColorSelect"><option value="#ffffff">White</option><option value="#0f172a">Dark Blue</option><option value="#1e293b">Slate</option><option value="#f5f5f0">Cream</option><option value="#1a1a2e">Deep Navy</option><option value="#2d2d2d">Charcoal</option></select>
                <label>Logo SVG:</label><input type="file" id="logoUpload" accept="image/svg+xml"><button id="addLogoBtn" style="background:#10b981;border:none;color:white;padding:4px 12px;border-radius:4px">Add Logo</button><button id="removeLogoBtn" style="background:#ef4444;border:none;color:white;padding:4px 12px;border-radius:4px">Remove Logo</button>
                <button id="cropToFitBtn" style="background:#10b981;border:none;color:white;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:12px;">✂️ Crop to Fit: ON</button>
            </div>
            <div style="display:flex;gap:15px;flex-wrap:wrap;align-items:center;margin-bottom:10px;">
                <div><label>Template:</label><select id="templateSelect" style="background:#334155;color:white;border:none;padding:6px 12px;border-radius:6px;"><option value="grid2">Grid 2 Columns</option><option value="grid3" selected>Grid 3 Columns</option><option value="grid4">Grid 4 Columns</option><option value="masonry">Masonry</option><option value="center">Single Centered</option><option value="timeline">Timeline Cascade</option><option value="polaroid">Polaroid Stack</option></select></div>
                <button id="applyTemplateBtn">Apply Template</button><button id="exportStoryboardBtn" class="primary">Export 300 DPI PNG</button><button id="clearStoryboardBtn">Clear Canvas</button>
            </div>
        </div>
        
        <div style="margin:10px 0;padding:10px;background:#0f172a;border-radius:8px;"><div style="font-size:11px;margin-bottom:8px;color:#94a3b8;">🎨 Template Preview Gallery (click to apply)</div><div id="templateGallery" style="display:flex;gap:12px;overflow-x:auto;padding:5px;"></div></div>
        
        <canvas id="storyboardCanvas" width="1080" height="1440"></canvas>
        
        <!-- Text Overlay Panel (Fix #2) -->
        <div class="text-overlay-panel">
            <div style="display:flex;gap:10px;margin-bottom:8px;flex-wrap:wrap;align-items:center">
                <strong style="color:#94a3b8;font-size:11px">✏️ Custom Text Overlay:</strong>
                <input type="color" id="textColorPicker" value="#ffffff" style="width:40px;background:#334155;border:none">
                <input type="number" id="textFontSize" value="24" min="8" max="200" style="width:60px;background:#334155;color:white;border:none;padding:4px;border-radius:4px">
                <select id="textFontFamily" style="background:#334155;color:white;border:none;padding:4px;border-radius:4px"><option value="Arial">Arial</option><option value="Verdana">Verdana</option><option value="Times New Roman">Times New Roman</option><option value="Courier New">Courier New</option><option value="Georgia">Georgia</option><option value="Impact">Impact</option></select>
                <label style="color:white;font-size:11px"><input type="checkbox" id="textBold"> Bold</label>
                <label style="color:white;font-size:11px"><input type="checkbox" id="textItalic"> Italic</label>
            </div>
            <textarea id="customTextInput" placeholder="Enter your text here..." style="width:100%;padding:8px;background:#1e293b;border:1px solid #475569;color:white;border-radius:4px;resize:vertical;min-height:60px"></textarea>
            <div style="display:flex;gap:8px;margin-top:8px">
                <button id="addCustomTextBtn" style="background:#10b981;border:none;color:white;padding:6px 12px;border-radius:4px;cursor:pointer">➕ Add Text to Canvas</button>
                <button id="addMultiLineTextBtn" style="background:#8b5cf6;border:none;color:white;padding:6px 12px;border-radius:4px;cursor:pointer">📋 Add as Separate Lines</button>
                <button id="bgTextBtn" style="background:#8b5cf6;border:none;color:white;padding:6px 12px;border-radius:4px;cursor:pointer">📄 Add Background Text</button>
            </div>
        </div>
        
        <!-- Clipborad/PNG Controls (Fix #3, #4, #5) -->
        <div style="display:flex;gap:8px;margin:10px 0;flex-wrap:wrap">
            <button id="pasteTextBtn" style="background:#8b5cf6;border:none;color:white;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px">📋 Paste Text from Clipboard</button>
            <button id="pasteAtMouseBtn" style="background:#f59e0b;border:none;color:white;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px">📌 Paste at Mouse Position</button>
            <button id="pasteImageBtn" style="background:#f59e0b;border:none;color:white;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px">📋 Paste Image from Clipboard</button>
            <button id="pngOverlayBtn" style="background:#10b981;border:none;color:white;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px">🖼️ Import Transparent PNG</button>
        </div>
        <input type="file" id="pngFileInput" accept="image/png" style="display:none">
        
        <!-- PNG Opacity Control -->
        <div style="display:flex;gap:8px;align-items:center;margin:10px 0;padding:5px;background:#1e293b;border-radius:6px">
            <label style="color:white;font-size:11px">🎨 PNG Opacity:</label>
            <input type="range" id="pngOpacitySlider" min="0" max="100" value="100" style="width:100px">
            <span id="opacityValue" style="color:#94a3b8;font-size:10px">100%</span>
            <button id="applyOpacityBtn" style="background:#3b82f6;border:none;color:white;padding:2px 8px;border-radius:4px;font-size:10px">Apply</button>
        </div>
        
        <!-- Background Text Opacity -->
        <div style="display:flex;gap:8px;align-items:center;margin:10px 0;padding:5px;background:#1e293b;border-radius:6px">
            <label style="color:white;font-size:11px">🌫️ Background Text Opacity:</label>
            <input type="range" id="bgOpacitySlider" min="0" max="100" value="50" style="width:100px">
            <span id="bgOpacityValue" style="color:#94a3b8;font-size:10px">50%</span>
            <button id="applyBgOpacityBtn" style="background:#3b82f6;border:none;color:white;padding:2px 8px;border-radius:4px;font-size:10px">Apply</button>
        </div>
        
        <!-- Watermark Presets (Fix #6) -->
        <div class="watermark-presets">
            <span style="color:#94a3b8;font-size:11px">💧 Watermark Presets:</span>
            <button id="watermarkDraftBtn" style="background:#334155;border:none;color:white;padding:4px 8px;border-radius:4px;font-size:10px;cursor:pointer">DRAFT</button>
            <button id="watermarkConfidentialBtn" style="background:#334155;border:none;color:white;padding:4px 8px;border-radius:4px;font-size:10px;cursor:pointer">CONFIDENTIAL</button>
            <button id="watermarkCopyrightBtn" style="background:#334155;border:none;color:white;padding:4px 8px;border-radius:4px;font-size:10px;cursor:pointer">© Copyright</button>
            <button id="watermarkCustomBtn" style="background:#334155;border:none;color:white;padding:4px 8px;border-radius:4px;font-size:10px;cursor:pointer">Custom Watermark</button>
        </div>
        
        <!-- Reorder Controls -->
        <div class="reorder-controls">
            <strong style="color:#94a3b8;font-size:11px">Reorder:</strong>
            <button id="bringToFrontBtn" style="background:#8b5cf6;">⬆️ Bring to Front</button>
            <button id="bringForwardBtn" style="background:#8b5cf6;">⬆️ Bring Forward</button>
            <button id="sendBackwardBtn" style="background:#8b5cf6;">⬇️ Send Backward</button>
            <button id="sendToBackBtn" style="background:#8b5cf6;">⬇️ Send to Back</button>
            <button id="sendToBackLayerBtn" style="background:#ef4444;">⬇️ Send Selected to Back</button>
            <span id="zIndexIndicator" style="background:#334155;padding:4px 8px;border-radius:4px;font-size:11px">Layer: --</span>
            <button id="dragReorderBtn" style="background:#8b5cf6;border:none;color:white;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px">📋 Drag Reorder: OFF</button>
        </div>
        
        <!-- Grid Controls -->
        <div class="grid-controls">
            <button id="toggleGridBtn" style="background:#8b5cf6;">📐 Show Grid</button>
            <label style="color:white;font-size:11px;">Grid Size: <input type="number" id="gridSizeInput" value="50" step="10" min="20" max="200" style="width:60px;background:#334155;color:white;border:none;padding:4px;border-radius:4px;"></label>
            <label style="color:white;font-size:11px;">Grid Color: <input type="color" id="gridColorInput" value="#334155" style="width:40px;background:#334155;border:none;"></label>
        </div>
        
        <!-- Snap Controls -->
        <div class="snap-controls">
            <button id="snapToGridBtn" style="background:#8b5cf6;">🔲 Snap to Grid: OFF</button>
            <button id="snapToCellsBtn" style="background:#8b5cf6;">🔲 Snap to Cells: OFF</button>
            <button id="fineMoveBtn" style="background:#8b5cf6;">🔍 Fine Move: OFF</button>
            <label style="color:white;font-size:11px;">Snap Size: <input type="number" id="snapGridSizeInput" value="50" step="10" min="20" max="200" style="width:60px;background:#334155;color:white;border:none;padding:4px;border-radius:4px;"></label>
        </div>
        
        <!-- Asset Library -->
        <div style="margin-top:15px;border-top:1px solid #475569;padding-top:10px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                <strong>📦 Storyboard Assets</strong>
                <div style="display:flex;gap:8px">
                    <button id="addAllAssetsBtn" style="background:#10b981;border:none;color:white;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px">+ Add All Assets</button>
                    <button id="removeAllAssetsBtn" style="background:#f59e0b;border:none;color:white;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px">− Remove All Assets</button>
                    <button id="clearCanvasAssetsBtn" style="background:#ef4444;border:none;color:white;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px">🗑 Clear Canvas</button>
                    <button id="unlockAllBtn" style="background:#f59e0b;border:none;color:white;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px">🔓 Unlock All</button>
                </div>
            </div>
            <div id="storyboardThumbnails" style="display:flex;gap:12px;overflow-x:auto;padding:8px;min-height:100px"></div>
            <div style="font-size:10px;color:#94a3b8;margin-top:5px">💡 Tip: Select gallery image → Apply Caption | Paste text (Ctrl+V) at mouse position | Import transparent PNG</div>
        </div>
        
        <!-- Canvas Tools -->
        <div class="canvas-toolbar">
            <button id="drawModeBtn">✏️ Draw</button>
            <button id="addTextBtn">📝 Text</button>
            <button id="addRectBtn">⬜ Rect</button>
            <button id="addCircleBtn">● Circle</button>
            <button id="addTriangleBtn">▲ Triangle</button>
            <button id="grayscaleBtn">⚫ Grayscale</button>
            <button id="sepiaBtn">🟤 Sepia</button>
            <button id="brightnessBtn">☀️ Brightness</button>
            <button id="contrastBtn">◐ Contrast</button>
            <button id="removeFiltersBtn">⟳ Reset</button>
            <button id="bringFrontBtn">⬆️ Front</button>
            <button id="sendBackBtn">⬇️ Back</button>
            <button id="duplicateBtn">📑 Duplicate</button>
        </div>
    </div>
</div>

<!-- URL Import Modal -->
<div id="urlImportModal" class="modal" style="display:none;z-index:20000">
    <div class="modal-header"><strong>Import Image from URL</strong><span id="urlModalClose" class="modal-close">&times;</span></div>
    <div style="padding:15px">
        <input type="text" id="imageUrlInput" placeholder="Enter image URL (jpg, png, gif, webp)" style="width:100%;padding:8px;margin-bottom:10px;background:#1e293b;border:1px solid #475569;color:white;border-radius:4px">
        <input type="text" id="imageTitleInput" placeholder="Optional: Image title/caption" style="width:100%;padding:8px;margin-bottom:10px;background:#1e293b;border:1px solid #475569;color:white;border-radius:4px">
        <button id="importUrlConfirm" style="background:#10b981;border:none;color:white;padding:8px 16px;border-radius:4px;cursor:pointer">Import</button>
        <button id="importUrlCancel" style="background:#ef4444;border:none;color:white;padding:8px 16px;border-radius:4px;margin-left:10px;cursor:pointer">Cancel</button>
    </div>
    <div id="urlPreview" style="text-align:center;padding:10px;display:none"></div>
</div>

<div id="toast" class="toast"></div>

<!-- Lightbox -->
<div id="lightbox" class="lightbox">
    <button class="lightbox-nav lightbox-prev">‹</button>
    <div class="lightbox-content"><div id="lightboxCloseBtn" class="lightbox-close">×</div><div id="lightboxMediaContainer"></div><div id="lightboxCaption" class="lightbox-caption"></div></div>
    <button class="lightbox-nav lightbox-next">›</button>
</div>

<!-- Comments Modal -->
<div id="commentsModal" class="modal">
    <div class="modal-header"><strong>Comments</strong><span id="commentsModalClose" class="modal-close">&times;</span></div>
    <div id="commentsList"></div>
</div>

<!-- Local File Input -->
<input type="file" id="localFileInput" multiple accept="image/jpeg,image/jpg,image/png,image/gif,image/webp,video/mp4" style="display:none">

<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
<script>
// ============================================================================
// PATH: index_v0047.html - COMPLETE WORKING BASELINE (v0046) + TEXT OVERLAY FIXES
// All v0046 features preserved exactly as they were
// ADDITIONAL fixes added incrementally:
// Fix #1: Apply Caption/Comments from grid as editable text overlays
// Fix #2: Custom textarea with font/color controls
// Fix #3: Clipboard text paste at mouse position
// Fix #4: Transparent PNG import with opacity control
// Fix #5: Clipboard image paste preserving transparency
// Fix #6: Background text layer with watermarks
// ============================================================================

// ========== DEBUG PANEL ==========
var debugPanel = document.getElementById('debugPanel');
var debugLogDiv = document.getElementById('debugLog');
var allLogs = [];
var isMinimized = false;
var isDragging = false;
var dragStartX, dragStartY, panelStartX, panelStartY;

var savedLeft = localStorage.getItem('debugPanelLeft');
var savedTop = localStorage.getItem('debugPanelTop');
var savedMinimized = localStorage.getItem('debugPanelMinimized');
if(savedLeft) debugPanel.style.left = savedLeft + 'px';
if(savedTop) debugPanel.style.top = savedTop + 'px';
if(savedMinimized === 'true') {
    isMinimized = true;
    debugPanel.style.height = '30px';
    debugPanel.style.overflow = 'hidden';
    document.getElementById('debugMinimizeBtn').textContent = '+';
}

var debugHeader = document.querySelector('.debug-header');
debugHeader.addEventListener('mousedown', function(e) {
    if(e.target.closest('#debugMinimizeBtn') || e.target.closest('#debugSaveBtn') || e.target.closest('#debugCloseBtn')) return;
    isDragging = true;
    dragStartX = e.clientX - debugPanel.offsetLeft;
    dragStartY = e.clientY - debugPanel.offsetTop;
    debugPanel.style.position = 'fixed';
});

document.addEventListener('mousemove', function(e) {
    if(!isDragging) return;
    var newLeft = e.clientX - dragStartX;
    var newTop = e.clientY - dragStartY;
    newLeft = Math.max(0, Math.min(newLeft, window.innerWidth - debugPanel.offsetWidth));
    newTop = Math.max(0, Math.min(newTop, window.innerHeight - debugPanel.offsetHeight));
    debugPanel.style.left = newLeft + 'px';
    debugPanel.style.top = newTop + 'px';
    debugPanel.style.right = 'auto';
    debugPanel.style.bottom = 'auto';
});

document.addEventListener('mouseup', function() {
    if(isDragging) {
        localStorage.setItem('debugPanelLeft', parseInt(debugPanel.style.left));
        localStorage.setItem('debugPanelTop', parseInt(debugPanel.style.top));
    }
    isDragging = false;
});

function toggleMinimize() {
    isMinimized = !isMinimized;
    if(isMinimized) {
        debugPanel.style.height = '30px';
        debugPanel.style.overflow = 'hidden';
        document.getElementById('debugMinimizeBtn').textContent = '+';
    } else {
        debugPanel.style.height = '';
        debugPanel.style.overflow = '';
        document.getElementById('debugMinimizeBtn').textContent = '−';
    }
    localStorage.setItem('debugPanelMinimized', isMinimized);
}
document.getElementById('debugMinimizeBtn').onclick = toggleMinimize;
document.getElementById('debugCloseBtn').onclick = function(){ debugPanel.style.display = 'none'; };

function addLog(msg, isError) {
    var timestamp = new Date().toLocaleTimeString();
    var fullMsg = timestamp + " " + msg;
    var entry = document.createElement("div");
    entry.textContent = fullMsg;
    if(isError) entry.style.color = "#ef4444";
    else entry.style.color = "#10b981";
    debugLogDiv.appendChild(entry);
    entry.scrollIntoView();
    console.log(fullMsg);
    allLogs.push(fullMsg);
    if(allLogs.length > 500) allLogs.shift();
}

function saveLogsToFile() {
    var blob = new Blob([allLogs.join("\\n")], {type: "text/plain"});
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "gallery_logs_" + new Date().toISOString().slice(0,19).replace(/:/g, "-") + ".txt";
    a.click();
    URL.revokeObjectURL(a.href);
    addLog("Saved " + allLogs.length + " logs", false);
}
document.getElementById('debugSaveBtn').onclick = saveLogsToFile;

function showToast(msg, isError) {
    var t = document.getElementById("toast");
    t.textContent = msg;
    t.classList.add("show");
    setTimeout(function() { t.classList.remove("show"); }, 2000);
    addLog(msg, isError);
}

addLog("Debug panel ready", false);

// ========== LOAD POSTS DATA ==========
addLog("Loading posts data...", false);
var allPosts = ''' + posts_json + ''';
addLog("Posts loaded: " + allPosts.length, false);

// ========== GLOBAL VARIABLES ==========
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
var currentTemplate = "grid3";
var assetImages = [];
var canvasImageSrcs = new Set();
var historyStack = [];
var historyIndex = -1;
var MAX_HISTORY = 50;
var isUndoRedoing = false;
var layoutDebounceTimer = null;
var showGrid = false;
var snapToGridEnabled = false;
var snapToCellsOnly = false;
var fineMovementMode = false;
var cropToFitEnabled = true;
var cropTolerance = 0.15;
var gridSize = 50;
var snapGridSize = 50;
var gridColor = '#334155';
var gridCanvas = null;
var localImportedPosts = [];
var urlImportedPosts = [];
var dragReorderEnabled = false;
var lastMouseX = 100, lastMouseY = 100;

var TEMPLATES = {
    grid2: { name: 'Grid 2 Columns', cols: 2, margin: 20, maxHeight: 280 },
    grid3: { name: 'Grid 3 Columns', cols: 3, margin: 20, maxHeight: 250 },
    grid4: { name: 'Grid 4 Columns', cols: 4, margin: 15, maxHeight: 200 },
    masonry: { name: 'Masonry', cols: 2, margin: 0, isMasonry: true },
    center: { name: 'Single Centered', isCenter: true },
    timeline: { name: 'Timeline Cascade', isTimeline: true, rowHeight: 180 },
    polaroid: { name: 'Polaroid Stack', isPolaroid: true, baseScale: 0.35, angleStep: 4 }
};

var currentTemplateCells = [];
var currentDragTarget = null;
var currentHighlightRect = null;

var loadedImages = {};
var failedImages = {};

function trackImageLoad(img) {
    var src = img.src;
    if(!loadedImages[src]) {
        loadedImages[src] = true;
        delete failedImages[src];
        addLog("✓ " + src.split('/').pop(), false);
        updateImageStatus();
    }
}

function trackImageError(img) {
    var src = img.src;
    if(!failedImages[src]) {
        failedImages[src] = true;
        delete loadedImages[src];
        addLog("✗ FAILED: " + src.split('/').pop(), true);
        updateImageStatus();
    }
}

function updateImageStatus() {
    var total = Object.keys(failedImages).length + Object.keys(loadedImages).length;
    var failedCount = Object.keys(failedImages).length;
    var statusDiv = document.getElementById("imageStatusLog");
    if(statusDiv) statusDiv.innerHTML = '<div>📊 ' + total + ' total | <span style="color:#10b981">' + Object.keys(loadedImages).length + ' loaded</span> | <span style="color:#ef4444">' + failedCount + ' failed</span></div>';
}

function getMediaPath(folder, file) { return folder + "/" + file; }
function isVideo(filename) { if(!filename) return false; var ext = filename.toLowerCase(); return ext.endsWith(".mp4") || ext.endsWith(".mov") || ext.endsWith(".avi") || ext.endsWith(".mkv"); }

// ========== LIGHTBOX ==========
var currentLightboxMedia = [];
var currentLightboxIndex = 0;

function openLightbox(mediaItems, startIndex, caption) {
    currentLightboxMedia = mediaItems;
    currentLightboxIndex = startIndex;
    document.getElementById("lightboxCaption").textContent = caption || "";
    showLightboxMedia(currentLightboxIndex);
    document.getElementById("lightbox").classList.add("active");
    addLog("Lightbox opened", false);
}

function showLightboxMedia(index) {
    var container = document.getElementById("lightboxMediaContainer");
    var media = currentLightboxMedia[index];
    if(!media) return;
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
        container.appendChild(img);
    }
}

function closeLightbox() { document.getElementById("lightbox").classList.remove("active"); }
function prevLightbox() { if(currentLightboxMedia.length === 0) return; currentLightboxIndex = (currentLightboxIndex - 1 + currentLightboxMedia.length) % currentLightboxMedia.length; showLightboxMedia(currentLightboxIndex); }
function nextLightbox() { if(currentLightboxMedia.length === 0) return; currentLightboxIndex = (currentLightboxIndex + 1) % currentLightboxMedia.length; showLightboxMedia(currentLightboxIndex); }

// ========== COMMENTS ==========
function showComments(shortcode) {
    addLog("Comments for: " + shortcode, false);
    var post = null;
    for(var i=0;i<allPosts.length;i++) if(allPosts[i].shortcode === shortcode) { post = allPosts[i]; break; }
    var commentsList = document.getElementById("commentsList");
    if(!post || !post.comments || post.comments.length === 0) commentsList.innerHTML = "<div style='text-align:center;padding:20px;'>No comments</div>";
    else { var html = ""; for(var i=0;i<post.comments.length;i++) html += "<div class='comment-item'>💬 " + post.comments[i].replace(/</g, '&lt;').replace(/>/g, '&gt;') + "</div>"; commentsList.innerHTML = html; addLog("Displayed " + post.comments.length + " comments", false); }
    document.getElementById("commentsModal").classList.add("active");
}

// ========== RENDER GALLERY ==========
function renderGallery(posts) {
    addLog("Rendering " + posts.length + " posts", false);
    var grid = document.getElementById("galleryGrid");
    if(!grid) return;
    if(!posts.length) { grid.innerHTML = "<div style='text-align:center;padding:3rem;'>No posts match.</div>"; return; }
    var htmlStr = "";
    for(var idx=0; idx<posts.length; idx++){
        var post = posts[idx];
        var firstMedia = post.all_media && post.all_media.length ? post.all_media[0] : null;
        var mediaPath = firstMedia ? getMediaPath(post.folder_name, firstMedia) : "";
        var isVideoPost = firstMedia && isVideo(firstMedia);
        var mediaArray = [];
        if(post.all_media) { for(var i=0;i<post.all_media.length;i++) mediaArray.push({ url: getMediaPath(post.folder_name, post.all_media[i]), type: isVideo(post.all_media[i]) ? "video" : "image" }); }
        var mediaArrayJson = JSON.stringify(mediaArray).replace(/"/g, '&quot;');
        var carouselHtml = "";
        if(post.all_media && post.all_media.length > 1) { carouselHtml = "<div class='carousel'>"; for(var i=0;i<post.all_media.length;i++) { var mediaUrl = getMediaPath(post.folder_name, post.all_media[i]); if(isVideo(post.all_media[i])) carouselHtml += "<div class='carousel-video-item' data-url='" + mediaUrl + "'>🎬</div>"; else carouselHtml += "<img class='carousel-item' src='" + mediaUrl + "' data-url='" + mediaUrl + "' loading='lazy'>"; } carouselHtml += "</div>"; }
        var mediaHtml = "";
        if(firstMedia) { if(isVideoPost) mediaHtml = "<div style='position:relative;background:#0f172a;display:flex;align-items:center;justify-content:center;height:100%;min-height:200px;'>🎬 VIDEO</div>"; else mediaHtml = "<img class='card-media' src='" + mediaPath + "' loading='lazy' onload='trackImageLoad(this)' onerror='trackImageError(this)'>"; }
        else mediaHtml = "<div class='card-media'>No media</div>";
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
    document.querySelectorAll(".card").forEach(function(card) { card.onclick = function(e) { if(e.target.closest(".carousel-item") || e.target.closest(".carousel-video-item") || e.target.closest(".comments-btn") || e.target.closest(".select-checkbox") || e.target.closest(".insta-link")) return; var mediaData = JSON.parse(this.dataset.media); if(mediaData && mediaData.length) openLightbox(mediaData, 0, this.dataset.caption); }; });
    document.querySelectorAll(".carousel-item, .carousel-video-item").forEach(function(item) { item.onclick = function(e) { e.stopPropagation(); var card = this.closest(".card"); var mediaData = JSON.parse(card.dataset.media); var url = this.dataset.url; var index = 0; for(var j=0;j<mediaData.length;j++) if(mediaData[j].url === url) { index = j; break; } openLightbox(mediaData, index, card.dataset.caption); }; });
    document.querySelectorAll(".comments-btn").forEach(function(btn) { btn.onclick = function(e) { e.stopPropagation(); showComments(this.dataset.shortcode); }; });
    addCheckboxesToCards();
    setTimeout(processYouTubeThumbnails, 100);
}

function addCheckboxesToCards() {
    var cards = document.querySelectorAll(".card");
    addLog("Adding checkboxes to " + cards.length + " cards", false);
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
            if(this.checked){ if(!selectedSrcs.has(src)) selectedSrcs.add(src); }
            else selectedSrcs.delete(src);
            document.getElementById("selectedCount").innerText = selectedSrcs.size + " selected";
            setTimeout(rebuildAssetLibraryFromSelection, 50);
        };
        cards[i].style.position = "relative";
        cards[i].appendChild(chk);
    }
}

function selectAll() { document.querySelectorAll(".select-checkbox").forEach(function(cb) { if(!cb.checked) cb.click(); }); addLog("Selected all", false); setTimeout(rebuildAssetLibraryFromSelection, 100); }
function deselectAll() { document.querySelectorAll(".select-checkbox").forEach(function(cb) { if(cb.checked) cb.click(); }); addLog("Deselected all", false); setTimeout(rebuildAssetLibraryFromSelection, 100); }
function showMissingImages() { var failed = Object.keys(failedImages); if(failed.length === 0) showToast("All images loaded!", false); else { showToast(failed.length + " images failed", true); for(var i=0;i<failed.length;i++) addLog(failed[i], true); } }

// ========== UNDO/REDO ==========
function saveToHistory(actionDescription) { if(isUndoRedoing) return; if(!canvas) return; var state = canvas.toJSON(['hasControls', 'hasBorders', 'lockRotation']); historyStack = historyStack.slice(0, historyIndex + 1); historyStack.push({ state: state, description: actionDescription || 'State ' + (historyStack.length + 1) }); if(historyStack.length > MAX_HISTORY) historyStack.shift(); historyIndex = historyStack.length - 1; updateHistoryMenu(); }
function undo() { if(historyIndex > 0) { historyIndex--; isUndoRedoing = true; canvas.loadFromJSON(historyStack[historyIndex].state, function() { canvas.renderAll(); }); isUndoRedoing = false; addLog('Undo: ' + historyStack[historyIndex].description, false); updateHistoryMenu(); } }
function redo() { if(historyIndex < historyStack.length - 1) { historyIndex++; isUndoRedoing = true; canvas.loadFromJSON(historyStack[historyIndex].state, function() { canvas.renderAll(); }); isUndoRedoing = false; addLog('Redo: ' + historyStack[historyIndex].description, false); updateHistoryMenu(); } }
function updateHistoryMenu() { var historyMenu = document.getElementById('historyMenu'); if(!historyMenu) return; var html = ''; for(var i=0;i<historyStack.length;i++) { var marker = (i === historyIndex) ? '▶ ' : '  '; html += '<div class="history-entry" data-index="' + i + '" style="padding:4px 8px;cursor:pointer' + (i === historyIndex ? ';background:#3b82f6' : '') + '">' + marker + historyStack[i].description + '</div>'; } historyMenu.innerHTML = html || '<div style="padding:4px 8px">No history yet</div>'; document.querySelectorAll('.history-entry').forEach(function(entry) { entry.onclick = function() { var idx = parseInt(this.dataset.index); if(!isNaN(idx) && idx !== historyIndex) { historyIndex = idx; isUndoRedoing = true; canvas.loadFromJSON(historyStack[historyIndex].state, function() { canvas.renderAll(); }); isUndoRedoing = false; updateHistoryMenu(); } }; }); }

// ========== GRID SYSTEM ==========
function createGridOverlay() {
    if(!canvas) return;
    if(gridCanvas) { gridCanvas.dispose(); gridCanvas = null; }
    if(!showGrid) return;
    var existingGrid = document.getElementById('gridOverlayCanvas');
    if(existingGrid) existingGrid.remove();
    gridCanvas = document.createElement('canvas');
    gridCanvas.id = 'gridOverlayCanvas';
    gridCanvas.width = canvas.getWidth();
    gridCanvas.height = canvas.getHeight();
    gridCanvas.style.position = 'absolute';
    gridCanvas.style.top = canvas.upperCanvasEl.style.top;
    gridCanvas.style.left = canvas.upperCanvasEl.style.left;
    gridCanvas.style.pointerEvents = 'none';
    gridCanvas.style.zIndex = '1';
    var ctx = gridCanvas.getContext('2d');
    ctx.clearRect(0, 0, gridCanvas.width, gridCanvas.height);
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 1;
    for(var x = 0; x < gridCanvas.width; x += gridSize) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, gridCanvas.height); ctx.stroke(); }
    for(var y = 0; y < gridCanvas.height; y += gridSize) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(gridCanvas.width, y); ctx.stroke(); }
    ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(gridCanvas.width/2, 0); ctx.lineTo(gridCanvas.width/2, gridCanvas.height); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, gridCanvas.height/2); ctx.lineTo(gridCanvas.width, gridCanvas.height/2); ctx.stroke();
    canvas.upperCanvasEl.parentNode.insertBefore(gridCanvas, canvas.upperCanvasEl);
}

function toggleGrid() { showGrid = !showGrid; if(showGrid) { createGridOverlay(); showToast('Grid visible', false); document.getElementById('toggleGridBtn').textContent = '📐 Hide Grid'; document.getElementById('toggleGridBtn').style.background = '#ef4444'; } else { if(gridCanvas) gridCanvas.remove(); gridCanvas = null; showToast('Grid hidden', false); document.getElementById('toggleGridBtn').textContent = '📐 Show Grid'; document.getElementById('toggleGridBtn').style.background = '#8b5cf6'; } }
function setGridSize(size) { gridSize = Math.max(20, Math.min(200, size)); if(showGrid) createGridOverlay(); }
function setGridColor(color) { gridColor = color; if(showGrid) createGridOverlay(); }

// ========== CELL TARGETING ==========
function highlightCell(cell) { clearCellHighlights(); var rect = new fabric.Rect({ left: cell.x - cell.width/2, top: cell.y - cell.height/2, width: cell.width, height: cell.height, fill: 'rgba(59, 130, 246, 0.3)', stroke: '#3b82f6', strokeWidth: 2, selectable: false, evented: false, hasControls: false, hasBorders: false, lockMovementX: true, lockMovementY: true }); canvas.add(rect); rect.sendToBack(); canvas.renderAll(); currentHighlightRect = rect; }
function clearCellHighlights() { if(currentHighlightRect) { canvas.remove(currentHighlightRect); currentHighlightRect = null; } }
function calculateTemplateCellPositions(templateId) { var positions = []; var tpl = TEMPLATES[templateId]; if(!tpl || storyboardImages.length === 0) return positions; var canvasWidth = canvas.getWidth(); var margin = tpl.margin || 20; var availW = canvasWidth - margin * 2; if(tpl.cols && !tpl.isMasonry) { var cols = tpl.cols; var cellW = (availW - (cols-1)*margin) / cols; var y = margin; var rowHeight = tpl.maxHeight || 250; for(var row=0; row<Math.ceil(storyboardImages.length / cols); row++) { for(var col=0; col<cols; col++) { var cellCenterX = margin + col * (cellW + margin) + cellW / 2; var cellCenterY = y + rowHeight / 2; positions.push({ x: cellCenterX, y: cellCenterY, width: cellW, height: rowHeight }); } y += rowHeight + margin; } } else if(tpl.isMasonry) { var colWidth = canvasWidth / 2; for(var c=0; c<2; c++) positions.push({ x: c * colWidth + colWidth / 2, y: 100, width: colWidth, height: 200 }); } else if(tpl.isCenter) { positions.push({ x: canvasWidth/2, y: canvasHeight/2, width: 200, height: 200 }); } currentTemplateCells = positions; return positions; }
function snapToTemplateCell(obj) { if(!snapToCellsOnly) return false; if(currentTemplateCells.length === 0) return false; var objCenterX = obj.left + obj.width * obj.scaleX / 2; var objCenterY = obj.top + obj.height * obj.scaleY / 2; var tolerance = 40; var closest = null; var closestDist = tolerance + 1; for(var i=0; i<currentTemplateCells.length; i++) { var cell = currentTemplateCells[i]; var distX = Math.abs(objCenterX - cell.x); var distY = Math.abs(objCenterY - cell.y); var dist = Math.sqrt(distX*distX + distY*distY); if(dist < closestDist) { closestDist = dist; closest = cell; } } if(closest) { var newLeft = closest.x - obj.width * obj.scaleX / 2; var newTop = closest.y - obj.height * obj.scaleY / 2; obj.set({ left: newLeft, top: newTop }); return true; } return false; }
function enableCellTargeting() { canvas.on('object:moving', function(e) { if(!snapToCellsOnly) return; var obj = e.target; if(!obj) return; var objCenterX = obj.left + obj.width * obj.scaleX / 2; var objCenterY = obj.top + obj.height * obj.scaleY / 2; var tolerance = 50; var closestCell = null; var closestDist = tolerance + 1; for(var i=0; i<currentTemplateCells.length; i++) { var cell = currentTemplateCells[i]; var distX = Math.abs(objCenterX - cell.x); var distY = Math.abs(objCenterY - cell.y); var dist = Math.sqrt(distX*distX + distY*distY); if(dist < closestDist) { closestDist = dist; closestCell = cell; } } if(closestCell && closestDist < tolerance) { if(currentDragTarget !== closestCell) { highlightCell(closestCell); currentDragTarget = closestCell; obj.set({ opacity: 0.7 }); } } else { clearCellHighlights(); if(currentDragTarget) { obj.set({ opacity: 1 }); currentDragTarget = null; } } canvas.renderAll(); }); canvas.on('mouseup', function(e) { if(!snapToCellsOnly || !currentDragTarget) return; var activeObj = canvas.getActiveObject(); if(activeObj && currentDragTarget) { var newLeft = currentDragTarget.x - activeObj.width * activeObj.scaleX / 2; var newTop = currentDragTarget.y - activeObj.height * activeObj.scaleY / 2; activeObj.set({ left: newLeft, top: newTop, opacity: 1 }); canvas.renderAll(); addLog('Image repositioned to cell', false); saveToHistory('Repositioned image to new cell'); } clearCellHighlights(); if(activeObj) activeObj.set({ opacity: 1 }); currentDragTarget = null; canvas.renderAll(); }); }
function toggleSnapToCells() { snapToCellsOnly = !snapToCellsOnly; if(snapToCellsOnly) { document.getElementById('snapToCellsBtn').textContent = '🔲 Snap to Cells: ON'; document.getElementById('snapToCellsBtn').style.background = '#10b981'; enableCellTargeting(); showToast('Snap to Cells ON', false); } else { document.getElementById('snapToCellsBtn').textContent = '🔲 Snap to Cells: OFF'; document.getElementById('snapToCellsBtn').style.background = '#8b5cf6'; showToast('Snap to Cells OFF', false); } localStorage.setItem('snap_to_cells_enabled', snapToCellsOnly); }

// ========== INDEPENDENT SNAP CONTROLS ==========
function toggleSnapToGrid() { snapToGridEnabled = !snapToGridEnabled; if(snapToGridEnabled) { document.getElementById('snapToGridBtn').textContent = '🔲 Snap to Grid: ON'; document.getElementById('snapToGridBtn').style.background = '#10b981'; showToast('Snap to Grid ON', false); } else { document.getElementById('snapToGridBtn').textContent = '🔲 Snap to Grid: OFF'; document.getElementById('snapToGridBtn').style.background = '#8b5cf6'; showToast('Snap to Grid OFF', false); } localStorage.setItem('snap_to_grid_enabled', snapToGridEnabled); }
function toggleFineMovement() { fineMovementMode = !fineMovementMode; if(fineMovementMode) { document.getElementById('fineMoveBtn').textContent = '🔍 Fine Move: ON'; document.getElementById('fineMoveBtn').style.background = '#10b981'; showToast('Fine Movement ON - arrow keys move 1px', false); } else { document.getElementById('fineMoveBtn').textContent = '🔍 Fine Move: OFF'; document.getElementById('fineMoveBtn').style.background = '#8b5cf6'; showToast('Fine Movement OFF', false); } localStorage.setItem('fine_movement_enabled', fineMovementMode); }
function setSnapGridSize(size) { snapGridSize = Math.max(20, Math.min(200, size)); localStorage.setItem('snap_grid_size', snapGridSize); }
function setupMovementHandler() { canvas.on('object:moving', function(e) { if(fineMovementMode) return; var obj = e.target; if(snapToGridEnabled && !snapToCellsOnly) { var snapX = Math.round(obj.left / gridSize) * gridSize; var snapY = Math.round(obj.top / gridSize) * gridSize; obj.set({ left: snapX, top: snapY }); } else if(snapToCellsOnly && !snapToGridEnabled) { snapToTemplateCell(obj); } else if(snapToGridEnabled && snapToCellsOnly) { var snapped = snapToTemplateCell(obj); if(!snapped) { var snapX = Math.round(obj.left / gridSize) * gridSize; var snapY = Math.round(obj.top / gridSize) * gridSize; obj.set({ left: snapX, top: snapY }); } } }); }

// ========== MASONRY ==========
function applyMasonryWithCropping() { if(storyboardImages.length === 0) return; var canvasWidth = canvas.getWidth(); var cols = 2; var margin = 0; var colWidth = (canvasWidth - margin * (cols + 1)) / cols; var colHeights = [margin, margin]; var colX = [margin, margin + colWidth]; for(var i=0; i<storyboardImages.length; i++) { var obj = storyboardImages[i].fabricObj; var originalWidth = obj.width; var originalHeight = obj.height; var colIdx = colHeights[0] <= colHeights[1] ? 0 : 1; if(cropToFitEnabled) { var targetWidth = colWidth; var targetHeight = targetWidth * (originalHeight / originalWidth); if(targetHeight > targetWidth * (1 + cropTolerance)) { var cropScale = targetHeight / originalHeight; obj.scale(cropScale); var cropWidthVal = colWidth / cropScale; var cropX = (originalWidth - cropWidthVal) / 2; obj.set({ left: colX[colIdx], top: colHeights[colIdx], cropX: cropX, cropY: 0, scaleX: cropScale, scaleY: cropScale, hasControls: true, hasBorders: true }); } else { var scale = colWidth / originalWidth; obj.scale(scale); obj.set({ left: colX[colIdx], top: colHeights[colIdx], cropX: 0, cropY: 0, hasControls: true, hasBorders: true }); } } else { var scale = colWidth / originalWidth; obj.scale(scale); obj.set({ left: colX[colIdx], top: colHeights[colIdx], cropX: 0, cropY: 0, hasControls: true, hasBorders: true }); } colHeights[colIdx] += obj.height * (obj.scaleY || 1); } var maxHeight = Math.max(colHeights[0], colHeights[1]); if(maxHeight > canvasHeight) canvas.setDimensions({ height: maxHeight }); canvas.renderAll(); }
function toggleCropToFit() { cropToFitEnabled = !cropToFitEnabled; var tplId = document.getElementById('templateSelect').value; if(tplId === 'masonry') applyMasonryWithCropping(); document.getElementById('cropToFitBtn').textContent = cropToFitEnabled ? '✂️ Crop to Fit: ON' : '✂️ Crop to Fit: OFF'; document.getElementById('cropToFitBtn').style.background = cropToFitEnabled ? '#10b981' : '#ef4444'; showToast('Crop to Fit: ' + (cropToFitEnabled ? 'ON' : 'OFF'), false); localStorage.setItem('crop_to_fit_enabled', cropToFitEnabled); }

// ========== ARROW KEY MOVEMENT ==========
function initArrowKeyMovement() { document.addEventListener('keydown', function(e) { var activeObj = canvas.getActiveObject(); if(!activeObj) return; var arrowKeys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']; if(arrowKeys.indexOf(e.key) === -1) return; e.preventDefault(); var step = e.shiftKey ? 10 : 1; var deltaX = 0, deltaY = 0; switch(e.key) { case 'ArrowLeft': deltaX = -step; break; case 'ArrowRight': deltaX = step; break; case 'ArrowUp': deltaY = -step; break; case 'ArrowDown': deltaY = step; break; } if(fineMovementMode) { activeObj.set({ left: (activeObj.left || 0) + deltaX, top: (activeObj.top || 0) + deltaY }); } else { var newLeft = (activeObj.left || 0) + deltaX; var newTop = (activeObj.top || 0) + deltaY; if(snapToGridEnabled && !snapToCellsOnly) { newLeft = Math.round(newLeft / gridSize) * gridSize; newTop = Math.round(newTop / gridSize) * gridSize; activeObj.set({ left: newLeft, top: newTop }); } else if(snapToCellsOnly && !snapToGridEnabled) { activeObj.set({ left: newLeft, top: newTop }); snapToTemplateCell(activeObj); canvas.renderAll(); return; } else { activeObj.set({ left: newLeft, top: newTop }); } } canvas.renderAll(); saveToHistory('Arrow key movement'); }); }

// ========== REORDER CONTROLS ==========
function updateZIndexIndicator() { var activeObj = canvas.getActiveObject(); if(!activeObj) { document.getElementById('zIndexIndicator').textContent = 'Layer: --'; return; } var objects = canvas.getObjects(); var index = objects.indexOf(activeObj); var total = objects.length; document.getElementById('zIndexIndicator').textContent = 'Layer: ' + (index + 1) + ' of ' + total; }
function bringToFront() { var activeObj = canvas.getActiveObject(); if(activeObj) { canvas.bringToFront(activeObj); canvas.renderAll(); updateZIndexIndicator(); saveToHistory('Brought to front'); addLog('Object brought to front', false); } else { showToast('Select an image first', true); } }
function bringForward() { var activeObj = canvas.getActiveObject(); if(activeObj) { canvas.bringForward(activeObj); canvas.renderAll(); updateZIndexIndicator(); saveToHistory('Brought forward'); addLog('Object brought forward', false); } else { showToast('Select an image first', true); } }
function sendBackward() { var activeObj = canvas.getActiveObject(); if(activeObj) { canvas.sendBackwards(activeObj); canvas.renderAll(); updateZIndexIndicator(); saveToHistory('Sent backward'); addLog('Object sent backward', false); } else { showToast('Select an image first', true); } }
function sendToBack() { var activeObj = canvas.getActiveObject(); if(activeObj) { canvas.sendToBack(activeObj); canvas.renderAll(); updateZIndexIndicator(); saveToHistory('Sent to back'); addLog('Object sent to back', false); } else { showToast('Select an image first', true); } }
function sendToBackLayer() { var activeObj = canvas.getActiveObject(); if(activeObj) { canvas.sendToBack(activeObj); canvas.renderAll(); updateZIndexIndicator(); saveToHistory('Sent to background layer'); addLog('Object sent to background layer', false); showToast('Object sent to background', false); } else { showToast('Select an object first', true); } }
canvas.on('selection:created', updateZIndexIndicator); canvas.on('selection:updated', updateZIndexIndicator); canvas.on('selection:cleared', updateZIndexIndicator);
function toggleDragReorder() { dragReorderEnabled = !dragReorderEnabled; if(dragReorderEnabled) { showToast('Drag Reorder ON', false); document.getElementById('dragReorderBtn').textContent = '📋 Drag Reorder: ON'; document.getElementById('dragReorderBtn').style.background = '#10b981'; } else { showToast('Drag Reorder OFF', false); document.getElementById('dragReorderBtn').textContent = '📋 Drag Reorder: OFF'; document.getElementById('dragReorderBtn').style.background = '#8b5cf6'; } }

// ========== YOUTUBE THUMBNAILS ==========
function extractYouTubeId(url) { if(!url) return null; var patterns = [/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&#?]+)/, /youtube\.com\/embed\/([^&#?]+)/, /youtube\.com\/v\/([^&#?]+)/]; for(var i=0; i<patterns.length; i++) { var match = url.match(patterns[i]); if(match) return match[1]; } return null; }
function loadYouTubeThumbnail(videoId, imgElement) { var qualities = ['maxresdefault', 'sddefault', 'hqdefault', 'mqdefault']; function tryQuality(index) { if(index >= qualities.length) { imgElement.src = ''; imgElement.alt = 'No thumbnail available'; return; } var localPath = 'youtube_thumbs/' + videoId + '_' + qualities[index] + '.jpg'; var testImg = new Image(); testImg.onload = function() { imgElement.src = localPath; addLog('YouTube thumbnail loaded: ' + videoId, false); }; testImg.onerror = function() { tryQuality(index + 1); }; testImg.src = localPath; } tryQuality(0); }
function processYouTubeThumbnails() { document.querySelectorAll('.card').forEach(function(card) { var caption = card.dataset.caption || ''; var youtubeId = extractYouTubeId(caption); if(youtubeId) { var img = card.querySelector('.card-media'); if(img && img.tagName === 'IMG' && !img.dataset.youtubeProcessed) { img.dataset.youtubeProcessed = 'true'; loadYouTubeThumbnail(youtubeId, img); } } }); }

// ========== LOCAL IMAGE IMPORT ==========
document.getElementById('importLocalBtn')?.remove();
var importLocalBtn = document.createElement('button'); importLocalBtn.id = 'importLocalBtn'; importLocalBtn.textContent = '📁 Import Local Images'; importLocalBtn.style.background = '#10b981'; importLocalBtn.style.border = 'none'; importLocalBtn.style.color = 'white'; importLocalBtn.style.padding = '6px 12px'; importLocalBtn.style.borderRadius = '8px'; importLocalBtn.style.cursor = 'pointer'; importLocalBtn.style.fontSize = '12px'; importLocalBtn.onclick = function() { document.getElementById('localFileInput').click(); }; document.querySelector('.gallery-toolbar').appendChild(importLocalBtn);
document.getElementById('localFileInput').onchange = function(e) { var files = Array.from(e.target.files); if(files.length === 0) return; addLog('Importing ' + files.length + ' local images...', false); showToast('Importing ' + files.length + ' images...', false); files.forEach(function(file) { var reader = new FileReader(); reader.onload = function(evt) { var imageUrl = evt.target.result; var filename = file.name; var ext = filename.split('.').pop().toLowerCase(); var isVideo = ['mp4', 'mov', 'avi', 'mkv'].indexOf(ext) !== -1; var localPost = { shortcode: 'local_' + Date.now() + '_' + Math.random().toString(36).substr(2, 8), date: new Date().toISOString(), likes: 0, comments_count: 0, caption: 'Local import: ' + filename, folder_name: 'local', all_media: [filename], comments: [], instagram_url: '#', author: 'Local Import', localUrl: imageUrl, isLocal: true, isVideo: isVideo }; localImportedPosts.push(localPost); var allPostsWithLocal = allPosts.concat(localImportedPosts); renderGallery(allPostsWithLocal); addLog('Imported: ' + filename, false); showToast('Imported: ' + filename, false); }; reader.readAsDataURL(file); }); e.target.value = ''; };
var originalGetMediaPath = window.getMediaPath; window.getMediaPath = function(folder, file) { var found = localImportedPosts.find(function(p) { return p.all_media[0] === file && p.folder_name === folder; }); if(found && found.localUrl) return found.localUrl; if(window.localGetMediaPath) return window.localGetMediaPath(folder, file); return originalGetMediaPath(folder, file); };

// ========== URL IMPORT ==========
document.getElementById('importUrlBtn')?.remove();
var importUrlBtn = document.createElement('button'); importUrlBtn.id = 'importUrlBtn'; importUrlBtn.textContent = '🌐 Import from URL'; importUrlBtn.style.background = '#f59e0b'; importUrlBtn.style.border = 'none'; importUrlBtn.style.color = 'white'; importUrlBtn.style.padding = '6px 12px'; importUrlBtn.style.borderRadius = '8px'; importUrlBtn.style.cursor = 'pointer'; importUrlBtn.style.fontSize = '12px'; importUrlBtn.onclick = function() { document.getElementById('urlImportModal').style.display = 'block'; }; document.querySelector('.gallery-toolbar').appendChild(importUrlBtn);
document.getElementById('urlModalClose').onclick = function() { document.getElementById('urlImportModal').style.display = 'none'; };
document.getElementById('importUrlCancel').onclick = function() { document.getElementById('urlImportModal').style.display = 'none'; };
document.getElementById('imageUrlInput').oninput = function() { var url = this.value; var previewDiv = document.getElementById('urlPreview'); if(url.match(/\.(jpg|jpeg|png|gif|webp)(\?.*)?$/i)) { previewDiv.style.display = 'block'; previewDiv.innerHTML = '<img src="' + url + '" style="max-width:200px;max-height:150px;border-radius:8px" onerror="this.style.display=\'none\'">'; } else previewDiv.style.display = 'none'; };
document.getElementById('importUrlConfirm').onclick = function() { var url = document.getElementById('imageUrlInput').value.trim(); var title = document.getElementById('imageTitleInput').value.trim() || 'Imported from URL'; if(!url) { showToast('Please enter a URL', true); return; } addLog('Importing from URL: ' + url, false); showToast('Importing image from URL...', false); var testImg = new Image(); testImg.crossOrigin = 'Anonymous'; testImg.onload = function() { var canvas2 = document.createElement('canvas'); canvas2.width = testImg.width; canvas2.height = testImg.height; var ctx = canvas2.getContext('2d'); ctx.drawImage(testImg, 0, 0); var dataUrl = canvas2.toDataURL('image/png'); var urlPost = { shortcode: 'url_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6), date: new Date().toISOString(), likes: 0, comments_count: 0, caption: title, folder_name: 'url_imports', all_media: ['imported_' + Date.now() + '.png'], comments: [], instagram_url: '#', author: 'URL Import', localUrl: dataUrl, isUrlImport: true }; urlImportedPosts.push(urlPost); var allPostsWithImports = allPosts.concat(localImportedPosts).concat(urlImportedPosts); renderGallery(allPostsWithImports); addLog('Imported from URL: ' + url, false); showToast('Imported successfully!', false); document.getElementById('urlImportModal').style.display = 'none'; }; testImg.onerror = function() { addLog('Failed to load from URL: ' + url, true); showToast('Failed to load image from URL.', true); }; testImg.src = url; };

// ========== ASSET LIBRARY ==========
function rebuildAssetLibraryFromSelection() { assetImages = []; canvasImageSrcs.clear(); selectedSrcs.forEach(function(src) { var filename = src.split('/').pop(); var onCanvas = storyboardImages.some(function(img) { return img.src === src; }); assetImages.push({ src: src, name: filename, onCanvas: onCanvas }); if(onCanvas) canvasImageSrcs.add(src); }); storyboardImages.forEach(function(img) { if(!selectedSrcs.has(img.src) && !assetImages.some(function(a) { return a.src === img.src; })) { var filename = img.src.split('/').pop(); assetImages.push({ src: img.src, name: filename, onCanvas: true }); canvasImageSrcs.add(img.src); } }); localImportedPosts.forEach(function(post) { if(post.localUrl && selectedSrcs.has(post.localUrl)) { var onCanvas = storyboardImages.some(function(img) { return img.src === post.localUrl; }); if(!assetImages.some(function(a) { return a.src === post.localUrl; })) { assetImages.push({ src: post.localUrl, name: post.all_media[0], onCanvas: onCanvas }); if(onCanvas) canvasImageSrcs.add(post.localUrl); } } }); urlImportedPosts.forEach(function(post) { if(post.localUrl && selectedSrcs.has(post.localUrl)) { var onCanvas = storyboardImages.some(function(img) { return img.src === post.localUrl; }); if(!assetImages.some(function(a) { return a.src === post.localUrl; })) { assetImages.push({ src: post.localUrl, name: post.all_media[0], onCanvas: onCanvas }); if(onCanvas) canvasImageSrcs.add(post.localUrl); } } }); renderAssetLibrary(); }
function renderAssetLibrary() { var container = document.getElementById('storyboardThumbnails'); if(!container) return; if(assetImages.length === 0) { container.innerHTML = '<div style="padding:20px;text-align:center;color:#94a3b8">No assets. Select images from gallery and click "Sync to Storyboard" to add assets.</div>'; return; } var html = ''; for(var i=0; i<assetImages.length; i++) { var asset = assetImages[i]; var isOnCanvas = canvasImageSrcs.has(asset.src); var borderStyle = isOnCanvas ? '2px solid #10b981' : '1px solid #475569'; var actionIcon = isOnCanvas ? '−' : '+'; var bgColor = isOnCanvas ? '#ef4444' : '#10b981'; html += '<div class="asset-thumbnail" data-src="' + asset.src + '" style="border: ' + borderStyle + ';"><img src="' + asset.src + '" loading="lazy"><div class="asset-action" data-action="' + (isOnCanvas ? 'remove' : 'add') + '" data-src="' + asset.src + '" style="background: ' + bgColor + ';">' + actionIcon + '</div><div style="position:absolute;top:4px;left:4px;font-size:9px;background:rgba(0,0,0,0.6);padding:2px 4px;border-radius:4px">' + (isOnCanvas ? 'ON' : 'OFF') + '</div></div>'; } container.innerHTML = html; document.querySelectorAll('.asset-thumbnail').forEach(function(thumb) { thumb.onclick = function(e) { if(e.target.classList.contains('asset-action')) return; var src = this.dataset.src; var isOnCanvas = canvasImageSrcs.has(src); if(isOnCanvas) removeAssetFromCanvas(src); else addAssetToCanvas(src); }; }); document.querySelectorAll('.asset-action').forEach(function(action) { action.onclick = function(e) { e.stopPropagation(); var src = this.dataset.src; var actionType = this.dataset.action; if(actionType === 'add') addAssetToCanvas(src); else if(actionType === 'remove') removeAssetFromCanvas(src); }; }); }
function addAssetToCanvas(src) { if(canvasImageSrcs.has(src)) { showToast('Already on canvas', true); return; } fabric.Image.fromURL(src, function(img) { if(!img) { addLog('Failed to add asset: ' + src.split('/').pop(), true); return; } img.set({ hasControls: true, hasBorders: true, lockRotation: false }); var margin = 20; var x = margin + (storyboardImages.length % 3) * 280; var y = margin + Math.floor(storyboardImages.length / 3) * 220; img.set({ left: x, top: y }); storyboardImages.push({ src: src, fabricObj: img }); canvas.add(img); canvas.renderAll(); canvasImageSrcs.add(src); updateStoryboardBadge(); saveStoryboardState(); scheduleLayout(); rebuildAssetLibraryFromSelection(); showToast('Added: ' + src.split('/').pop(), false); saveToHistory('Added asset'); }); }
function removeAssetFromCanvas(src) { var foundIndex = -1; for(var i=0; i<storyboardImages.length; i++) { if(storyboardImages[i].src === src) { foundIndex = i; break; } } if(foundIndex !== -1) { canvas.remove(storyboardImages[foundIndex].fabricObj); storyboardImages.splice(foundIndex, 1); canvasImageSrcs.delete(src); canvas.renderAll(); updateStoryboardBadge(); saveStoryboardState(); scheduleLayout(); rebuildAssetLibraryFromSelection(); showToast('Removed: ' + src.split('/').pop(), false); saveToHistory('Removed asset'); } }
function addAllAssetsToCanvas() { if(assetImages.length === 0) { if(selectedSrcs.size > 0) { rebuildAssetLibraryFromSelection(); if(assetImages.length > 0) { setTimeout(addAllAssetsToCanvas, 100); return; } } var userChoice = confirm('No assets in library.\\nYou have ' + selectedSrcs.size + ' images selected.\\nClick OK to sync them first.'); if(userChoice && selectedSrcs.size > 0) syncSelectedToStoryboardWithTemplate(); else showToast('No assets. Select images and click "Sync to Storyboard" first.', true); return; } var added = 0; assetImages.forEach(function(asset) { if(!canvasImageSrcs.has(asset.src)) { addAssetToCanvas(asset.src); added++; } }); if(added) showToast('Added ' + added + ' assets', false); else showToast('All assets already on canvas', true); }

function addImageToStoryboardWithPromise(src) { return new Promise(function(resolve, reject) { var filename = src.split('/').pop(); for(var i=0;i<storyboardImages.length;i++){ if(storyboardImages[i].src === src){ showToast("Already added", true); resolve(false); return; } } fabric.Image.fromURL(src, function(img) { if(!img) { addLog("Failed: " + filename, true); reject(new Error("Failed to load " + filename)); return; } img.set({ hasControls: true, hasBorders: true, lockRotation: false }); var margin = 20; var x = margin + (storyboardImages.length % 3) * 280; var y = margin + Math.floor(storyboardImages.length / 3) * 220; img.set({ left: x, top: y }); storyboardImages.push({ src: src, fabricObj: img }); canvas.add(img); canvas.renderAll(); updateThumbnails(); updateStoryboardBadge(); saveStoryboardState(); canvasImageSrcs.add(src); resolve(true); }, function(err) { reject(err); }); }); }
function syncSelectedToStoryboardWithTemplate() { var srcs = Array.from(selectedSrcs); if(srcs.length === 0){ showToast("No images selected", true); return; } addLog("Syncing " + srcs.length + " images...", false); showToast("Syncing " + srcs.length + " images...", false); var completed = 0; var failed = 0; var promises = srcs.map(function(src) { return addImageToStoryboardWithPromise(src).then(function(success) { completed++; showToast("Adding " + completed + "/" + srcs.length, false); }).catch(function(err) { failed++; addLog("Failed to add: " + src.split('/').pop(), true); }); }); Promise.all(promises).then(function() { var message = "Added " + completed + " of " + srcs.length + " images"; if(failed > 0) message += " (" + failed + " failed)"; showToast(message, failed > 0); if(completed > 0) { rebuildAssetLibraryFromSelection(); setTimeout(function() { var tplId = document.getElementById('templateSelect').value; applyLayoutTemplate(tplId); saveStoryboardState(); showToast("Template applied: " + TEMPLATES[tplId].name, false); }, 100); } }); }

// ========== TEMPLATE APPLICATION ==========
function applyLayoutTemplate(templateId) { if(storyboardImages.length === 0) return; var tpl = TEMPLATES[templateId]; if(!tpl) return; if(tpl.isCenter && storyboardImages.length > 1) { var proceed = confirm('Center template is designed for single images.\\nYou have ' + storyboardImages.length + ' images. Continue will stack them all at center (they will overlap).\\nUse Grid or Masonry for multiple images.'); if(!proceed) return; } if(tpl.isMasonry) { applyMasonryWithCropping(); calculateTemplateCellPositions(templateId); return; } var canvasWidth = canvas.getWidth(); var canvasHeight = canvas.getHeight(); var margin = tpl.margin || 20; var availW = canvasWidth - margin * 2; var availH = canvasHeight - margin * 2; if(tpl.isCenter) { for(var i=0; i<storyboardImages.length; i++) { var obj = storyboardImages[i].fabricObj; var scale = Math.min(availW / (obj.width || 100), availH / (obj.height || 100)); if(storyboardImages.length > 1) scale = scale * (0.7 - (i * 0.05)); obj.scale(scale); var scaledWidth = obj.width * scale; var scaledHeight = obj.height * scale; obj.set({ left: (canvasWidth - scaledWidth) / 2, top: (canvasHeight - scaledHeight) / 2, angle: 0, hasControls: true, hasBorders: true }); } } else if(tpl.isTimeline) { var x = margin; var y = margin; var rowHeight = tpl.rowHeight; for(var i=0; i<storyboardImages.length; i++) { var obj = storyboardImages[i].fabricObj; var scale = rowHeight / (obj.height || 100); obj.scale(scale); var scaledWidth = obj.width * scale; obj.set({ left: x, top: y, angle: 0, hasControls: true, hasBorders: true }); x += scaledWidth + margin; if(x + scaledWidth > canvasWidth - margin) { x = margin; y += rowHeight + margin; } } var timelineHeight = y + rowHeight + margin; if(timelineHeight > canvasHeight) canvas.setDimensions({ height: timelineHeight }); } else if(tpl.isPolaroid) { var centerX = canvasWidth / 2; var centerY = canvasHeight / 2; var baseScale = tpl.baseScale; var totalImages = storyboardImages.length; for(var i=0; i<totalImages; i++) { var obj = storyboardImages[i].fabricObj; var angle = (i - (totalImages-1)/2) * tpl.angleStep; var scale = baseScale * (1 - Math.abs(i - (totalImages-1)/2) / totalImages * 0.3); obj.scale(scale); var scaledWidth = obj.width * scale; var scaledHeight = obj.height * scale; obj.set({ left: centerX - scaledWidth / 2, top: centerY - scaledHeight / 2, angle: angle, hasControls: true, hasBorders: true }); } } else if(tpl.cols) { var cols = tpl.cols; var cellW = (availW - (cols-1)*margin) / cols; var y = margin; var rowHeight = 0; for(var i=0; i<storyboardImages.length; i++) { var obj = storyboardImages[i].fabricObj; var col = i % cols; if(col === 0 && i !== 0) { y += rowHeight + margin; rowHeight = 0; } var scale = Math.min(cellW / (obj.width || 100), (tpl.maxHeight || 250) / (obj.height || 100)); obj.scale(scale); var scaledWidth = obj.width * scale; var scaledHeight = obj.height * scale; var cellCenterX = margin + col * (cellW + margin) + cellW / 2; obj.set({ left: cellCenterX - scaledWidth / 2, top: y, angle: 0, hasControls: true, hasBorders: true }); if(scaledHeight > rowHeight) rowHeight = scaledHeight; } } canvas.renderAll(); saveStoryboardState(); addLog('Template applied: ' + tpl.name, false); showToast('Template applied: ' + tpl.name, false); calculateTemplateCellPositions(templateId); }

function buildTemplateGallery() { var gallery = document.getElementById('templateGallery'); if(!gallery) return; var templates = Object.keys(TEMPLATES); var html = ''; for(var i=0; i<templates.length; i++) { var tplId = templates[i]; var tpl = TEMPLATES[tplId]; html += '<div class="template-preview" data-template="' + tplId + '"><div class="preview-box">'; if(tplId === 'center') html += '<div style="width:40px;height:30px;background:#3b82f6;border-radius:2px"></div>'; else if(tplId === 'polaroid') { html += '<div style="width:30px;height:25px;background:#f59e0b;transform:rotate(-5deg)"></div><div style="width:30px;height:25px;background:#f59e0b;transform:rotate(0deg);margin-left:-10px"></div>'; } else { var cols = tpl.cols || 2; for(var j=0; j<Math.min(4, cols*2); j++) html += '<div style="width:12px;height:10px;background:#3b82f6;border-radius:1px"></div>'; } html += '</div><div style="font-size:9px;margin-top:5px">' + tpl.name + '</div></div>'; } gallery.innerHTML = html; document.querySelectorAll('.template-preview').forEach(function(preview) { preview.onclick = function() { var tplId = this.dataset.template; document.getElementById('templateSelect').value = tplId; applyLayoutTemplate(tplId); }; preview.onmouseenter = function() { this.style.background = '#334155'; }; preview.onmouseleave = function() { this.style.background = '#1e293b'; }; }); }

// ========== TEXT OVERLAY FROM GRID (Fix #1) ==========
var applyCaptionBtn = document.createElement('button'); applyCaptionBtn.id = 'applyCaptionBtn'; applyCaptionBtn.textContent = '📝 Apply Caption to Storyboard'; applyCaptionBtn.style.background = '#8b5cf6'; applyCaptionBtn.style.border = 'none'; applyCaptionBtn.style.color = 'white'; applyCaptionBtn.style.padding = '6px 12px'; applyCaptionBtn.style.borderRadius = '8px'; applyCaptionBtn.style.cursor = 'pointer'; applyCaptionBtn.style.fontSize = '12px'; applyCaptionBtn.onclick = function() { var selectedCards = document.querySelectorAll('.select-checkbox:checked'); if(selectedCards.length === 0) { showToast('No images selected.', true); return; } var firstSelected = selectedCards[0]; var card = firstSelected.closest('.card'); var shortcode = card.dataset.shortcode; var post = null; for(var i=0; i<allPosts.length; i++) { if(allPosts[i].shortcode === shortcode) { post = allPosts[i]; break; } } if(!post) { showToast('Post not found', true); return; } var captionText = post.caption || ''; if(!captionText) { showToast('No caption for this post', true); return; } var text = new fabric.IText(captionText, { left: 50, top: 50, fontFamily: 'Arial', fontSize: 20, fill: '#ffffff', stroke: '#000000', strokeWidth: 1, backgroundColor: 'rgba(0,0,0,0.5)', padding: 10, hasControls: true, hasBorders: true }); canvas.add(text); canvas.setActiveObject(text); canvas.renderAll(); saveToHistory('Added caption overlay from post: ' + shortcode); addLog('Caption added', false); showToast('Caption added to canvas', false); }; document.querySelector('.gallery-toolbar').appendChild(applyCaptionBtn);

var applyCommentsBtn = document.createElement('button'); applyCommentsBtn.id = 'applyCommentsBtn'; applyCommentsBtn.textContent = '💬 Apply Comments to Storyboard'; applyCommentsBtn.style.background = '#8b5cf6'; applyCommentsBtn.style.border = 'none'; applyCommentsBtn.style.color = 'white'; applyCommentsBtn.style.padding = '6px 12px'; applyCommentsBtn.style.borderRadius = '8px'; applyCommentsBtn.style.cursor = 'pointer'; applyCommentsBtn.style.fontSize = '12px'; applyCommentsBtn.onclick = function() { var selectedCards = document.querySelectorAll('.select-checkbox:checked'); if(selectedCards.length === 0) { showToast('No images selected.', true); return; } var firstSelected = selectedCards[0]; var card = firstSelected.closest('.card'); var shortcode = card.dataset.shortcode; var post = null; for(var i=0; i<allPosts.length; i++) { if(allPosts[i].shortcode === shortcode) { post = allPosts[i]; break; } } if(!post || !post.comments || post.comments.length === 0) { showToast('No comments for this post', true); return; } var yOffset = 50; post.comments.forEach(function(comment, idx) { var commentText = comment.length > 100 ? comment.substring(0,100) + '...' : comment; var text = new fabric.IText(commentText, { left: 50, top: yOffset, fontFamily: 'Arial', fontSize: 14, fill: '#ffffff', backgroundColor: 'rgba(0,0,0,0.4)', padding: 5, hasControls: true }); canvas.add(text); yOffset += 40; }); canvas.renderAll(); saveToHistory('Added ' + post.comments.length + ' comment overlays'); addLog('Added ' + post.comments.length + ' comments', false); showToast('Added ' + post.comments.length + ' comments', false); }; document.querySelector('.gallery-toolbar').appendChild(applyCommentsBtn);

// ========== CUSTOM TEXTAREA (Fix #2) ==========
document.getElementById('addCustomTextBtn').onclick = function() { var textContent = document.getElementById('customTextInput').value.trim(); if(!textContent) { showToast('Enter text first', true); return; } var color = document.getElementById('textColorPicker').value; var fontSize = parseInt(document.getElementById('textFontSize').value); var fontFamily = document.getElementById('textFontFamily').value; var isBold = document.getElementById('textBold').checked; var isItalic = document.getElementById('textItalic').checked; var fontWeight = isBold ? 'bold' : 'normal'; var fontStyle = isItalic ? 'italic' : 'normal'; var text = new fabric.IText(textContent, { left: 100, top: 100, fontFamily: fontFamily, fontSize: fontSize, fill: color, fontWeight: fontWeight, fontStyle: fontStyle, stroke: '#000000', strokeWidth: 1, backgroundColor: 'rgba(0,0,0,0.3)', padding: 8, hasControls: true, hasBorders: true }); canvas.add(text); canvas.setActiveObject(text); canvas.renderAll(); saveToHistory('Added custom text: ' + textContent.substring(0,50)); addLog('Custom text added', false); showToast('Text added to canvas', false); document.getElementById('customTextInput').value = ''; };
document.getElementById('addMultiLineTextBtn').onclick = function() { var textContent = document.getElementById('customTextInput').value.trim(); if(!textContent) { showToast('Enter text first', true); return; } var lines = textContent.split('\\n'); var color = document.getElementById('textColorPicker').value; var fontSize = parseInt(document.getElementById('textFontSize').value); var fontFamily = document.getElementById('textFontFamily').value; var yOffset = 100; lines.forEach(function(line, idx) { if(line.trim()) { var text = new fabric.IText(line.trim(), { left: 100, top: yOffset, fontFamily: fontFamily, fontSize: fontSize, fill: color, hasControls: true, hasBorders: true }); canvas.add(text); yOffset += fontSize + 10; } }); canvas.renderAll(); saveToHistory('Added multi-line text (' + lines.length + ' lines)'); addLog('Added ' + lines.length + ' text lines', false); showToast('Added ' + lines.length + ' text lines', false); document.getElementById('customTextInput').value = ''; };

// ========== CLIPBOARD TEXT PASTE (Fix #3) ==========
var pasteTextBtn = document.getElementById('pasteTextBtn'); var pasteAtMouseBtn = document.getElementById('pasteAtMouseBtn'); canvas.on('mouse:move', function(e) { if(e.absolutePointer) { lastMouseX = e.absolutePointer.x; lastMouseY = e.absolutePointer.y; } });
if(pasteTextBtn) pasteTextBtn.onclick = async function() { try { var text = await navigator.clipboard.readText(); if(!text || text.trim() === '') { showToast('Clipboard is empty', true); return; } var color = document.getElementById('textColorPicker')?.value || '#ffffff'; var fontSize = parseInt(document.getElementById('textFontSize')?.value || '24'); var fontFamily = document.getElementById('textFontFamily')?.value || 'Arial'; var textObj = new fabric.IText(text.trim(), { left: 150, top: 150, fontFamily: fontFamily, fontSize: fontSize, fill: color, stroke: '#000000', strokeWidth: 1, backgroundColor: 'rgba(0,0,0,0.3)', padding: 8, hasControls: true, hasBorders: true }); canvas.add(textObj); canvas.setActiveObject(textObj); canvas.renderAll(); saveToHistory('Pasted text from clipboard'); addLog('Pasted text from clipboard', false); showToast('Text pasted to canvas', false); } catch(err) { showToast('Cannot read clipboard. Check permissions.', true); } };
if(pasteAtMouseBtn) pasteAtMouseBtn.onclick = async function() { try { var text = await navigator.clipboard.readText(); if(!text || text.trim() === '') { showToast('Clipboard is empty', true); return; } var color = document.getElementById('textColorPicker')?.value || '#ffffff'; var fontSize = parseInt(document.getElementById('textFontSize')?.value || '24'); var textObj = new fabric.IText(text.trim(), { left: lastMouseX, top: lastMouseY, fontSize: fontSize, fill: color, hasControls: true }); canvas.add(textObj); canvas.setActiveObject(textObj); canvas.renderAll(); saveToHistory('Pasted text at mouse position'); showToast('Text pasted at mouse position', false); } catch(err) { showToast('Cannot read clipboard', true); } };

// ========== TRANSPARENT PNG IMPORT (Fix #4) ==========
var pngOverlayBtn = document.getElementById('pngOverlayBtn'); var pngFileInput = document.getElementById('pngFileInput'); if(pngOverlayBtn) pngOverlayBtn.onclick = function() { pngFileInput.click(); };
if(pngFileInput) pngFileInput.onchange = function(e) { var file = e.target.files[0]; if(!file) return; if(!file.type.match('image/png')) { showToast('Please select a PNG file', true); return; } var reader = new FileReader(); reader.onload = function(evt) { fabric.Image.fromURL(evt.target.result, function(img) { if(!img) { showToast('Failed to load PNG', true); return; } img.set({ left: 100, top: 100, scaleX: 0.5, scaleY: 0.5, hasControls: true, hasBorders: true, transparentCorners: true, opacity: 1 }); canvas.add(img); canvas.setActiveObject(img); canvas.renderAll(); saveToHistory('Imported transparent PNG: ' + file.name); addLog('Imported PNG: ' + file.name, false); showToast('PNG overlay added', false); }); }; reader.readAsDataURL(file); e.target.value = ''; };
document.getElementById('applyOpacityBtn').onclick = function() { var activeObj = canvas.getActiveObject(); if(activeObj && activeObj.get('type') === 'image') { var opacity = parseInt(document.getElementById('pngOpacitySlider').value) / 100; activeObj.set({ opacity: opacity }); canvas.renderAll(); saveToHistory('Set PNG opacity to ' + (opacity * 100) + '%'); addLog('PNG opacity set', false); } else { showToast('Select a PNG overlay first', true); } };
document.getElementById('pngOpacitySlider').oninput = function() { document.getElementById('opacityValue').textContent = this.value + '%'; };

// ========== CLIPBOARD IMAGE PASTE (Fix #5) ==========
document.addEventListener('paste', function(e) { var items = e.clipboardData.items; for(var i=0; i<items.length; i++) { var item = items[i]; if(item.type.indexOf('image/') !== -1) { e.preventDefault(); var blob = item.getAsFile(); var reader = new FileReader(); reader.onload = function(evt) { var testImg = new Image(); testImg.onload = function() { fabric.Image.fromURL(evt.target.result, function(img) { if(img) { var scale = Math.min(300 / img.width, 300 / img.height, 0.8); img.set({ left: lastMouseX, top: lastMouseY, scaleX: scale, scaleY: scale, hasControls: true, hasBorders: true, transparentCorners: true }); canvas.add(img); canvas.setActiveObject(img); canvas.renderAll(); saveToHistory('Pasted image from clipboard'); addLog('Pasted image from clipboard', false); showToast('Image pasted from clipboard', false); } }); }; testImg.src = evt.target.result; }; reader.readAsDataURL(blob); break; } } });
var pasteImageBtn = document.getElementById('pasteImageBtn'); if(pasteImageBtn) pasteImageBtn.onclick = async function() { try { var clipboardItems = await navigator.clipboard.read(); for(var item of clipboardItems) { var imageTypes = item.types.filter(function(type) { return type.indexOf('image/') === 0; }); if(imageTypes.length > 0) { var blob = await item.getType(imageTypes[0]); var reader = new FileReader(); reader.onload = function(evt) { fabric.Image.fromURL(evt.target.result, function(img) { if(img) { img.set({ left: 150, top: 150, scaleX: 0.5, scaleY: 0.5, hasControls: true }); canvas.add(img); canvas.setActiveObject(img); canvas.renderAll(); saveToHistory('Pasted image from clipboard (explicit)'); showToast('Image pasted from clipboard', false); } }); }; reader.readAsDataURL(blob); break; } } } catch(err) { showToast('Cannot read clipboard. Use Ctrl+V instead.', true); } };

// ========== BACKGROUND TEXT & WATERMARKS (Fix #6) ==========
var bgTextBtn = document.getElementById('bgTextBtn'); if(bgTextBtn) bgTextBtn.onclick = function() { var textContent = prompt('Enter background text:', 'Storyboard Title'); if(!textContent) return; var color = document.getElementById('textColorPicker')?.value || '#ffffff'; var fontSize = parseInt(document.getElementById('textFontSize')?.value || '48'); var bgText = new fabric.IText(textContent, { left: PREVIEW_W / 2, top: PREVIEW_H / 2, fontFamily: 'Arial', fontSize: fontSize, fill: color, stroke: '#000000', strokeWidth: 2, opacity: 0.5, originX: 'center', originY: 'center', hasControls: true, hasBorders: true }); canvas.add(bgText); bgText.sendToBack(); canvas.renderAll(); saveToHistory('Added background text: ' + textContent); addLog('Background text added', false); showToast('Background text added (behind images)', false); };
var sendToBackLayerBtn = document.getElementById('sendToBackLayerBtn'); if(sendToBackLayerBtn) sendToBackLayerBtn.onclick = function() { var activeObj = canvas.getActiveObject(); if(activeObj) { canvas.sendToBack(activeObj); canvas.renderAll(); updateZIndexIndicator(); saveToHistory('Sent to background layer'); showToast('Object sent to background', false); } else { showToast('Select an object first', true); } };
document.getElementById('applyBgOpacityBtn').onclick = function() { var activeObj = canvas.getActiveObject(); if(activeObj) { var opacity = parseInt(document.getElementById('bgOpacitySlider').value) / 100; activeObj.set({ opacity: opacity }); canvas.renderAll(); saveToHistory('Set background text opacity'); addLog('Background text opacity set', false); } else { showToast('Select text first', true); } };
document.getElementById('bgOpacitySlider').oninput = function() { document.getElementById('bgOpacityValue').textContent = this.value + '%'; };

function addBackgroundWatermark(text, color, opacity, angle) { var watermark = new fabric.Text(text, { left: PREVIEW_W / 2, top: PREVIEW_H / 2, originX: 'center', originY: 'center', fontFamily: 'Arial', fontSize: 60, fill: color, opacity: opacity, angle: angle, selectable: true, hasControls: true, hasBorders: true }); canvas.add(watermark); watermark.sendToBack(); canvas.renderAll(); saveToHistory('Added watermark: ' + text); addLog('Watermark added: ' + text, false); showToast('Watermark added to background', false); }
document.getElementById('watermarkDraftBtn').onclick = function() { addBackgroundWatermark('DRAFT', '#ef4444', 0.3, -30); };
document.getElementById('watermarkConfidentialBtn').onclick = function() { addBackgroundWatermark('CONFIDENTIAL', '#f59e0b', 0.35, -25); };
document.getElementById('watermarkCopyrightBtn').onclick = function() { addBackgroundWatermark('© ' + new Date().getFullYear() + ' All Rights Reserved', '#10b981', 0.25, -20); };
document.getElementById('watermarkCustomBtn').onclick = function() { var text = prompt('Enter watermark text:', 'Custom Watermark'); if(text) addBackgroundWatermark(text, '#ffffff', 0.3, -15); };

// ========== SCHEDULE LAYOUT ==========
function scheduleLayout() { if(layoutDebounceTimer) clearTimeout(layoutDebounceTimer); layoutDebounceTimer = setTimeout(function() { var tplId = document.getElementById('templateSelect').value; applyLayoutTemplate(tplId); saveToHistory('Auto-layout applied'); }, 50); }
function ensureAllObjectsMovable() { if(!canvas) return; var objects = canvas.getObjects(); var lockedCount = 0; for(var i=0; i<objects.length; i++) { if(objects[i].hasControls === false) { objects[i].set({ hasControls: true, hasBorders: true, selectable: true }); lockedCount++; } if(objects[i].lockMovementX || objects[i].lockMovementY) { objects[i].set({ lockMovementX: false, lockMovementY: false }); lockedCount++; } } if(lockedCount > 0) { canvas.renderAll(); addLog('Unlocked ' + lockedCount + ' objects', false); showToast('Unlocked ' + lockedCount + ' objects', false); } else showToast('All objects already movable', false); }

// ========== CANVAS INITIALIZATION ==========
function initCanvas() { var canvasEl = document.getElementById("storyboardCanvas"); if(!canvasEl) { addLog("Canvas not found", true); return; } if(canvas) canvas.dispose(); canvas = new fabric.Canvas("storyboardCanvas", { preserveObjectStacking: true, selection: true }); canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H }); canvas.backgroundColor = "#ffffff"; canvas.renderAll(); var savedBg = localStorage.getItem("storyboard_bg"); if(savedBg) { canvas.backgroundColor = savedBg; document.getElementById("bgColorSelect").value = savedBg; canvas.renderAll(); } var savedTemplate = localStorage.getItem("storyboard_template"); if(savedTemplate && TEMPLATES[savedTemplate]) { currentTemplate = savedTemplate; document.getElementById("templateSelect").value = savedTemplate; } canvas.on('object:added', function() { saveToHistory('Added object'); scheduleLayout(); }); canvas.on('object:modified', function() { saveToHistory('Modified object'); scheduleLayout(); }); canvas.on('object:removed', function() { saveToHistory('Removed object'); scheduleLayout(); }); var savedImages = localStorage.getItem("storyboard_images"); if(savedImages) { try { var images = JSON.parse(savedImages); addLog("Restoring " + images.length + " images", false); images.forEach(function(imgData) { fabric.Image.fromURL(imgData.src, function(img) { if(img) { img.set({ left: imgData.left, top: imgData.top, scaleX: imgData.scaleX, scaleY: imgData.scaleY, hasControls: true, hasBorders: true }); storyboardImages.push({ src: imgData.src, fabricObj: img }); canvas.add(img); canvas.renderAll(); updateThumbnails(); updateStoryboardBadge(); canvasImageSrcs.add(imgData.src); } }); }); } catch(e) { addLog("Restore error: " + e, true); } } setupMovementHandler(); initArrowKeyMovement(); addLog("Canvas ready", false); }
function saveStoryboardState() { if(!canvas) return; var imageData = []; for(var i=0;i<storyboardImages.length;i++) { var obj = storyboardImages[i].fabricObj; imageData.push({ src: storyboardImages[i].src, left: obj.left, top: obj.top, scaleX: obj.scaleX, scaleY: obj.scaleY }); } localStorage.setItem("storyboard_images", JSON.stringify(imageData)); localStorage.setItem("storyboard_bg", canvas.backgroundColor); localStorage.setItem("storyboard_template", document.getElementById('templateSelect').value); }
function updateStoryboardBadge() { var b = document.getElementById("storyboardCountBadge"); if(b) b.innerText = storyboardImages.length; }
function updateThumbnails() { renderAssetLibrary(); }

// ========== STORYBOARD MANAGER ==========
var STORAGE_LIST_KEY = 'storyboard_saves_list_v2'; var STORAGE_PREFIX = 'storyboard_save_v2_';
function getThumbnailDataURL() { var tempCanvas = document.createElement('canvas'); tempCanvas.width = 100; tempCanvas.height = 100; var ctx = tempCanvas.getContext('2d'); ctx.fillStyle = '#1e293b'; ctx.fillRect(0, 0, 100, 100); if(storyboardImages.length) { var firstImg = storyboardImages[0].fabricObj._element; if(firstImg) ctx.drawImage(firstImg, 0, 0, 100, 100); } return tempCanvas.toDataURL(); }
function saveStoryboardAs() { var name = prompt('Enter storyboard name:', 'Storyboard ' + new Date().toLocaleString()); if(!name) return; var currentTemplateId = document.getElementById('templateSelect').value; var state = { name: name, timestamp: Date.now(), thumbnail: getThumbnailDataURL(), templateId: currentTemplateId, images: storyboardImages.map(function(img) { return { src: img.src, left: img.fabricObj.left, top: img.fabricObj.top, scaleX: img.fabricObj.scaleX, scaleY: img.fabricObj.scaleY }; }) }; var saves = JSON.parse(localStorage.getItem(STORAGE_LIST_KEY) || '[]'); saves.unshift({ id: Date.now(), name: name, timestamp: state.timestamp, thumbnail: state.thumbnail, templateId: currentTemplateId }); if(saves.length > 20) saves.pop(); localStorage.setItem(STORAGE_LIST_KEY, JSON.stringify(saves)); localStorage.setItem(STORAGE_PREFIX + state.timestamp, JSON.stringify(state)); addLog('Storyboard saved: ' + name, false); showToast('Saved: ' + name, false); }
function loadStoryboardList() { var saves = JSON.parse(localStorage.getItem(STORAGE_LIST_KEY) || '[]'); if(saves.length === 0) { showToast('No saved storyboards', true); return; } var modalHtml = '<div id="storyboardListModal" class="modal active" style="display:block;z-index:20000"><div class="modal-header"><strong>Load Storyboard</strong><span id="storyboardListClose" class="modal-close">&times;</span></div><div style="max-height:400px;overflow-y:auto">'; for(var i=0;i<saves.length;i++) { var templateName = TEMPLATES[saves[i].templateId] ? TEMPLATES[saves[i].templateId].name : 'Grid 3'; modalHtml += '<div class="storyboard-save-item" data-id="' + saves[i].id + '"><img src="' + saves[i].thumbnail + '"><div><div><strong>' + saves[i].name + '</strong></div><div style="font-size:10px;color:#94a3b8">' + new Date(saves[i].timestamp).toLocaleString() + '</div><div style="font-size:9px;color:#10b981">📐 ' + templateName + '</div></div><button class="delete-save" data-id="' + saves[i].id + '">Delete</button></div>'; } modalHtml += '</div></div>'; var existing = document.getElementById('storyboardListModal'); if(existing) existing.remove(); document.body.insertAdjacentHTML('beforeend', modalHtml); document.querySelectorAll('.storyboard-save-item').forEach(function(item) { item.onclick = function(e) { if(e.target.classList.contains('delete-save')) return; var id = parseInt(this.dataset.id); loadStoryboardById(id); document.getElementById('storyboardListModal').remove(); }; }); document.querySelectorAll('.delete-save').forEach(function(btn) { btn.onclick = function(e) { e.stopPropagation(); var id = parseInt(this.dataset.id); if(confirm('Delete this storyboard?')) { var saves = JSON.parse(localStorage.getItem(STORAGE_LIST_KEY) || '[]'); var updated = saves.filter(function(s) { return s.id !== id; }); localStorage.setItem(STORAGE_LIST_KEY, JSON.stringify(updated)); localStorage.removeItem(STORAGE_PREFIX + id); loadStoryboardList(); } }; }); document.getElementById('storyboardListClose').onclick = function() { document.getElementById('storyboardListModal').remove(); }; }
function loadStoryboardById(id) { var saved = localStorage.getItem(STORAGE_PREFIX + id); if(!saved) { showToast('Storyboard not found', true); return; } var state = JSON.parse(saved); if(canvas) { storyboardImages.forEach(function(img) { canvas.remove(img.fabricObj); }); storyboardImages = []; canvasImageSrcs.clear(); var loadPromises = state.images.map(function(imgData) { return new Promise(function(resolve) { fabric.Image.fromURL(imgData.src, function(img) { if(img) { img.set({ left: imgData.left, top: imgData.top, scaleX: imgData.scaleX, scaleY: imgData.scaleY, hasControls: true, hasBorders: true }); storyboardImages.push({ src: imgData.src, fabricObj: img }); canvas.add(img); canvasImageSrcs.add(imgData.src); } resolve(); }); }); }); Promise.all(loadPromises).then(function() { canvas.renderAll(); updateThumbnails(); updateStoryboardBadge(); if(state.templateId && TEMPLATES[state.templateId]) { document.getElementById('templateSelect').value = state.templateId; setTimeout(function() { applyLayoutTemplate(state.templateId); addLog('Restored template: ' + TEMPLATES[state.templateId].name, false); }, 100); } rebuildAssetLibraryFromSelection(); }); } addLog('Loaded storyboard: ' + state.name, false); showToast('Loaded: ' + state.name, false); }

// ========== CANVAS TOOLS ==========
function setDrawingMode(enabled) { isDrawingMode = enabled; canvas.isDrawingMode = enabled; if(enabled) { canvas.freeDrawingBrush = new fabric.PencilBrush(canvas); canvas.freeDrawingBrush.color = '#000000'; canvas.freeDrawingBrush.width = 2; addLog("Drawing mode ON", false); } else { addLog("Drawing mode OFF", false); } }
function addText() { var text = new fabric.IText("Edit me", { left: 100, top: 100, fontSize: 24, fill: "#000000" }); canvas.add(text); canvas.setActiveObject(text); canvas.renderAll(); addLog("Text added", false); saveToHistory('Added text'); }
function addShape(type) { var shape; if(type === "rectangle") shape = new fabric.Rect({ left: 100, top: 100, width: 100, height: 100, fill: "#3b82f6" }); else if(type === "circle") shape = new fabric.Circle({ left: 100, top: 100, radius: 50, fill: "#ef4444" }); else if(type === "triangle") shape = new fabric.Triangle({ left: 100, top: 100, width: 80, height: 80, fill: "#10b981" }); if(shape) { canvas.add(shape); canvas.setActiveObject(shape); canvas.renderAll(); addLog("Shape added: " + type, false); saveToHistory('Added ' + type); } }
function applyFilter(filterName) { var activeObj = canvas.getActiveObject(); if(!activeObj || activeObj.get("type") !== "image") { showToast("Select an image first", true); return; } if(filterName === "grayscale") activeObj.filters = [new fabric.Image.filters.Grayscale()]; else if(filterName === "sepia") activeObj.filters = [new fabric.Image.filters.Sepia()]; else if(filterName === "brightness") activeObj.filters = [new fabric.Image.filters.Brightness({ brightness: 0.2 })]; else if(filterName === "contrast") activeObj.filters = [new fabric.Image.filters.Contrast({ contrast: 0.3 })]; activeObj.applyFilters(); canvas.renderAll(); addLog("Filter: " + filterName, false); saveToHistory('Applied filter'); }
function removeFilters() { var activeObj = canvas.getActiveObject(); if(activeObj && activeObj.get("type") === "image") { activeObj.filters = []; activeObj.applyFilters(); canvas.renderAll(); addLog("Filters removed", false); saveToHistory('Removed filters'); } }
function bringToFrontCanvas() { var activeObj = canvas.getActiveObject(); if(activeObj) { canvas.bringToFront(activeObj); canvas.renderAll(); saveToHistory('Brought to front'); } }
function sendToBackCanvas() { var activeObj = canvas.getActiveObject(); if(activeObj) { canvas.sendToBack(activeObj); canvas.renderAll(); saveToHistory('Sent to back'); } }
function duplicateObject() { var activeObj = canvas.getActiveObject(); if(activeObj) { activeObj.clone(function(cloned) { cloned.set({ left: (activeObj.left || 0) + 20, top: (activeObj.top || 0) + 20 }); canvas.add(cloned); canvas.setActiveObject(cloned); canvas.renderAll(); addLog("Duplicated", false); saveToHistory('Duplicated object'); }); } }
function deleteSelected() { var activeObj = canvas.getActiveObject(); if(activeObj) { canvas.remove(activeObj); canvas.renderAll(); saveToHistory('Deleted object'); addLog("Deleted selected", false); } }
function zoomIn() { if(canvas) { canvas.setZoom(canvas.getZoom() * 1.1); canvas.renderAll(); } }
function zoomOut() { if(canvas) { canvas.setZoom(canvas.getZoom() * 0.9); canvas.renderAll(); } }
function resetZoom() { if(canvas) { canvas.setZoom(1); canvas.renderAll(); } }
function clearCanvasOnly() { if(confirm("Clear all images from canvas? This does not delete assets from library.")){ for(var i=0;i<storyboardImages.length;i++) canvas.remove(storyboardImages[i].fabricObj); storyboardImages = []; canvasImageSrcs.clear(); canvas.renderAll(); updateThumbnails(); updateStoryboardBadge(); localStorage.removeItem("storyboard_images"); saveToHistory('Cleared canvas'); rebuildAssetLibraryFromSelection(); showToast("Canvas cleared - assets still available in library", false); } }
function exportHighQuality() { if(storyboardImages.length === 0){ showToast("No images", true); return; } addLog("Exporting 300 DPI...", false); showToast("Exporting 300 DPI PNG...", false); var offCanvas = document.createElement("canvas"); offCanvas.width = TARGET_W; offCanvas.height = TARGET_H; var offCtx = offCanvas.getContext("2d"); offCtx.fillStyle = canvas.backgroundColor; offCtx.fillRect(0, 0, TARGET_W, TARGET_H); offCtx.imageSmoothingEnabled = true; offCtx.imageSmoothingQuality = "high"; for(var i=0;i<storyboardImages.length;i++){ var obj = storyboardImages[i].fabricObj; offCtx.drawImage(obj._element, (obj.left || 0) * SCALE, (obj.top || 0) * SCALE, (obj.width || 0) * (obj.scaleX || 1) * SCALE, (obj.height || 0) * (obj.scaleY || 1) * SCALE); } if(currentLogo) offCtx.drawImage(currentLogo._element, (currentLogo.left || 0) * SCALE, (currentLogo.top || 0) * SCALE, (currentLogo.width || 0) * (currentLogo.scaleX || 1) * SCALE, (currentLogo.height || 0) * (currentLogo.scaleY || 1) * SCALE); var a = document.createElement("a"); a.download = "storyboard_36x48_300dpi.png"; a.href = offCanvas.toDataURL("image/png"); a.click(); addLog("Export complete", false); showToast("Export complete!", false); }

// ========== LOAD SAVED STATES ==========
function loadSavedStates() { var savedSnapGrid = localStorage.getItem('snap_to_grid_enabled'); if(savedSnapGrid !== null) snapToGridEnabled = savedSnapGrid === 'true'; var savedSnapCells = localStorage.getItem('snap_to_cells_enabled'); if(savedSnapCells !== null) snapToCellsOnly = savedSnapCells === 'true'; var savedFine = localStorage.getItem('fine_movement_enabled'); if(savedFine !== null) fineMovementMode = savedFine === 'true'; var savedCrop = localStorage.getItem('crop_to_fit_enabled'); if(savedCrop !== null) cropToFitEnabled = savedCrop === 'true'; var savedSnapSize = localStorage.getItem('snap_grid_size'); if(savedSnapSize) snapGridSize = parseInt(savedSnapSize); if(snapToGridEnabled) { document.getElementById('snapToGridBtn').textContent = '🔲 Snap to Grid: ON'; document.getElementById('snapToGridBtn').style.background = '#10b981'; } if(snapToCellsOnly) { document.getElementById('snapToCellsBtn').textContent = '🔲 Snap to Cells: ON'; document.getElementById('snapToCellsBtn').style.background = '#10b981'; enableCellTargeting(); } if(fineMovementMode) { document.getElementById('fineMoveBtn').textContent = '🔍 Fine Move: ON'; document.getElementById('fineMoveBtn').style.background = '#10b981'; } if(!cropToFitEnabled) { document.getElementById('cropToFitBtn').textContent = '✂️ Crop to Fit: OFF'; document.getElementById('cropToFitBtn').style.background = '#ef4444'; } document.getElementById('snapGridSizeInput').value = snapGridSize; }

// ========== MENU HANDLERS ==========
document.querySelectorAll('.menu-option[data-action]').forEach(function(opt) { opt.onclick = function() { var action = this.dataset.action; if(action === 'undo') undo(); else if(action === 'redo') redo(); else if(action === 'duplicate') duplicateObject(); else if(action === 'delete') deleteSelected(); else if(action === 'exportPNG') exportHighQuality(); else if(action === 'newStoryboard') clearCanvasOnly(); else if(action === 'saveStoryboard') saveStoryboardAs(); else if(action === 'loadStoryboard') loadStoryboardList(); else if(action === 'zoomIn') zoomIn(); else if(action === 'zoomOut') zoomOut(); else if(action === 'resetZoom') resetZoom(); else if(action === 'toggleGrid') toggleGrid(); else if(action === 'toggleSnap') toggleSnapToGrid(); else if(action === 'toggleCells') toggleSnapToCells(); else if(action === 'toggleFine') toggleFineMovement(); else if(action === 'toggleCrop') toggleCropToFit(); else if(action === 'unlockAll') ensureAllObjectsMovable(); }; });
document.querySelectorAll('.menu-item').forEach(function(item) { item.onmouseenter = function() { var d = this.querySelector('.menu-dropdown'); if(d) d.style.display = 'block'; }; item.onmouseleave = function() { var d = this.querySelector('.menu-dropdown'); if(d) d.style.display = 'none'; }; });
document.addEventListener('keydown', function(e) { if(e.ctrlKey || e.metaKey) { if(e.key === 'z' && !e.shiftKey) { e.preventDefault(); undo(); } else if(e.key === 'y' || (e.key === 'z' && e.shiftKey)) { e.preventDefault(); redo(); } else if(e.key === '=' || e.key === '+') { e.preventDefault(); zoomIn(); } else if(e.key === '-') { e.preventDefault(); zoomOut(); } } if(e.key === 'Delete') { deleteSelected(); } });

// ========== EVENT LISTENERS ==========
document.getElementById("selectAllBtn").onclick = selectAll;
document.getElementById("deselectAllBtn").onclick = deselectAll;
document.getElementById("syncSelectedBtn").onclick = syncSelectedToStoryboardWithTemplate;
document.getElementById("checkMissingBtn").onclick = showMissingImages;
document.getElementById("openStoryboardBtn").onclick = function() { document.getElementById('storyboardModal').classList.add('active'); if(storyboardImages.length > 0) { setTimeout(function() { canvasImageSrcs.clear(); storyboardImages.forEach(function(img) { canvasImageSrcs.add(img.src); }); rebuildAssetLibraryFromSelection(); }, 200); } else { rebuildAssetLibraryFromSelection(); } if(canvas) canvas.renderAll(); };
document.getElementById("closeStoryboardBtn").onclick = function(){ saveStoryboardState(); document.getElementById('storyboardModal').classList.remove('active'); };
document.getElementById("exportStoryboardBtn").onclick = exportHighQuality;
document.getElementById("clearStoryboardBtn").onclick = clearCanvasOnly;
document.getElementById("applyTemplateBtn").onclick = function() { var tplId = document.getElementById('templateSelect').value; applyLayoutTemplate(tplId); };
document.getElementById("lightboxCloseBtn").onclick = closeLightbox;
document.querySelector(".lightbox-prev").onclick = prevLightbox;
document.querySelector(".lightbox-next").onclick = nextLightbox;
document.getElementById("lightbox").onclick = function(e) { if(e.target === this) closeLightbox(); };
document.getElementById("commentsModalClose").onclick = function() { document.getElementById('commentsModal').classList.remove('active'); };
document.getElementById("commentsModal").onclick = function(e) { if(e.target === this) this.classList.remove('active'); };
document.getElementById('toggleGridBtn').onclick = toggleGrid;
document.getElementById('gridSizeInput').onchange = function() { setGridSize(parseInt(this.value)); };
document.getElementById('gridColorInput').onchange = function() { setGridColor(this.value); };
document.getElementById('snapToGridBtn').onclick = toggleSnapToGrid;
document.getElementById('snapToCellsBtn').onclick = toggleSnapToCells;
document.getElementById('fineMoveBtn').onclick = toggleFineMovement;
document.getElementById('cropToFitBtn').onclick = toggleCropToFit;
document.getElementById('snapGridSizeInput').onchange = function() { setSnapGridSize(parseInt(this.value)); };
document.getElementById('unlockAllBtn').onclick = ensureAllObjectsMovable;
document.getElementById('addAllAssetsBtn').onclick = addAllAssetsToCanvas;
document.getElementById('removeAllAssetsBtn').onclick = function() { if(assetImages.length === 0) { showToast('No assets to remove', true); return; } var removed = 0; assetImages.forEach(function(asset) { if(canvasImageSrcs.has(asset.src)) { removeAssetFromCanvas(asset.src); removed++; } }); if(removed) showToast('Removed ' + removed + ' assets', false); };
document.getElementById('clearCanvasAssetsBtn').onclick = clearCanvasOnly;
document.getElementById('bringToFrontBtn').onclick = bringToFront;
document.getElementById('bringForwardBtn').onclick = bringForward;
document.getElementById('sendBackwardBtn').onclick = sendBackward;
document.getElementById('sendToBackBtn').onclick = sendToBack;
document.getElementById('dragReorderBtn').onclick = toggleDragReorder;
document.getElementById('templateSelect').addEventListener('change', function() { applyLayoutTemplate(this.value); calculateTemplateCellPositions(this.value); saveToHistory('Template changed to ' + TEMPLATES[this.value].name); });
document.getElementById('bgColorSelect').addEventListener('change', function(e) { if(canvas) { canvas.backgroundColor = e.target.value; canvas.renderAll(); saveStoryboardState(); saveToHistory('Background color changed'); } });
document.getElementById('addLogoBtn').addEventListener('click', function() { var file = document.getElementById('logoUpload').files[0]; if(!file) { showToast('Select SVG', true); return; } var reader = new FileReader(); reader.onload = function(e) { fabric.loadSVGFromString(e.target.result, function(objects, options) { var logo = fabric.util.groupSVGElements(objects, options); logo.set({ left: PREVIEW_W - 100, top: 20, scaleX: 0.5, scaleY: 0.5, hasControls: true }); if(currentLogo) canvas.remove(currentLogo); currentLogo = logo; canvas.add(logo); canvas.renderAll(); saveStoryboardState(); saveToHistory('Added logo'); showToast('Logo added', false); }); }; reader.readAsText(file); });
document.getElementById('removeLogoBtn').addEventListener('click', function() { if(currentLogo) { canvas.remove(currentLogo); currentLogo = null; canvas.renderAll(); saveStoryboardState(); saveToHistory('Removed logo'); showToast('Logo removed', false); } });
document.getElementById('drawModeBtn').onclick = function() { setDrawingMode(!isDrawingMode); };
document.getElementById('addTextBtn').onclick = addText;
document.getElementById('addRectBtn').onclick = function() { addShape('rectangle'); };
document.getElementById('addCircleBtn').onclick = function() { addShape('circle'); };
document.getElementById('addTriangleBtn').onclick = function() { addShape('triangle'); };
document.getElementById('grayscaleBtn').onclick = function() { applyFilter('grayscale'); };
document.getElementById('sepiaBtn').onclick = function() { applyFilter('sepia'); };
document.getElementById('brightnessBtn').onclick = function() { applyFilter('brightness'); };
document.getElementById('contrastBtn').onclick = function() { applyFilter('contrast'); };
document.getElementById('removeFiltersBtn').onclick = removeFilters;
document.getElementById('bringFrontBtn').onclick = bringToFrontCanvas;
document.getElementById('sendBackBtn').onclick = sendToBackCanvas;
document.getElementById('duplicateBtn').onclick = duplicateObject;
document.getElementById('searchInput').addEventListener('input', function(e){ var q = e.target.value.toLowerCase(); var filtered = allPosts.filter(function(p){ return (p.caption || '').toLowerCase().indexOf(q) !== -1; }); renderGallery(filtered); });
document.addEventListener('keydown', function(e) { var lightbox = document.getElementById('lightbox'); if(lightbox && lightbox.classList.contains('active')) { if(e.key === 'ArrowLeft') prevLightbox(); else if(e.key === 'ArrowRight') nextLightbox(); else if(e.key === 'Escape') closeLightbox(); } if(e.key === 'Escape') { var modal = document.getElementById('commentsModal'); if(modal) modal.classList.remove('active'); } });

// ========== INITIALIZE ==========
initCanvas();
buildTemplateGallery();
loadSavedStates();
calculateTemplateCellPositions('grid3');
renderGallery(allPosts);
addLog('=== GALLERY v0047 READY ===', false);
addLog('✓ NEW: Apply caption/comments as text overlays from selected grid posts', false);
addLog('✓ NEW: Custom textarea with font/color controls (bold, italic, font family)', false);
addLog('✓ NEW: Paste text from clipboard at mouse position (Ctrl+V or button)', false);
addLog('✓ NEW: Import transparent PNG with opacity slider', false);
addLog('✓ NEW: Paste transparent PNG from clipboard (preserves alpha)', false);
addLog('✓ NEW: Background text layer and watermark presets (DRAFT, CONFIDENTIAL, Copyright)', false);
addLog('✓ All v0046 features preserved (local import, URL import, YouTube thumbnails, reorder, templates, asset library)', false);
</script>
</body>
</html>'''
    
    return html

def main():
    print("=" * 70)
    print("MR. DOUGLAS GALLERY v0047 - Text Overlays + Clipboard + Transparent PNG")
    print("=" * 70)
    print("\n✅ All 6 fixes from JSON list implemented:")
    print("   1. Apply Caption/Comments from grid as editable text overlays")
    print("   2. Custom textarea with font/color controls (bold, italic, font family)")
    print("   3. Paste text from clipboard at mouse position (Ctrl+V)")
    print("   4. Import transparent PNG with opacity control")
    print("   5. Paste transparent PNG from clipboard (alpha preserved)")
    print("   6. Background text layer + watermark presets (DRAFT, CONFIDENTIAL, Copyright)")
    
    print("\n[1/4] Loading posts...")
    posts = load_posts()
    posts = add_historic_images(posts)
    print(f"Loaded {len(posts)} posts")
    
    print("[2/4] Downloading YouTube thumbnails...")
    download_youtube_thumbnails(posts)
    
    print("[3/4] Generating HTML...")
    html = build_html(posts)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    print(f"Generated {OUTPUT_HTML}")
    print(f"File size: {OUTPUT_HTML.stat().st_size} bytes")
    
    print("[4/4] Starting server...")
    os.system("pkill -f 'http.server' 2>/dev/null")
    time.sleep(1)
    
    subprocess.Popen([sys.executable, '-m', 'http.server', '8000'], 
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    print("\n" + "=" * 70)
    print("✅ READY!")
    print("=" * 70)
    print(f"Open: http://localhost:8000/{OUTPUT_HTML.name}")
    print("\n✨ NEW FEATURES in v0047:")
    print("   📝 Apply Caption from selected grid post as editable text overlay")
    print("   💬 Apply Comments from selected grid post as text overlays")
    print("   ✏️ Custom textarea with font/color controls (bold, italic, font family)")
    print("   📋 Paste text from clipboard (Ctrl+V or button) at mouse position")
    print("   🖼️ Import transparent PNG with opacity slider")
    print("   📋 Paste transparent PNG from clipboard (preserves alpha transparency)")
    print("   📄 Background text layer (behind all images)")
    print("   💧 Watermark presets: DRAFT, CONFIDENTIAL, Copyright, Custom")
    print("\n✨ ALL v0046 FEATURES PRESERVED:")
    print("   📁 Local image import | 🌐 URL import | 🎬 YouTube thumbnails")
    print("   📋 Reorder controls (bring forward/back, drag reorder)")
    print("   📐 7 templates | 🎨 Background picker | 🖼️ SVG Logo")
    print("   ↩️ Undo/Redo | ⌨️ Arrow key movement | 🔲 Snap controls")
    print("   📦 Asset library | 🔍 Lightbox | 💬 Comments | 📊 Debug panel")
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