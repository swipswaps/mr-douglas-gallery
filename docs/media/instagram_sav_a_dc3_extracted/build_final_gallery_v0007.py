#!/usr/bin/env python3
"""
build_final_gallery_v0007.py

Generates index_v0007.html with working gallery display.
"""

import json
import sqlite3
import csv
import re
import sys
import logging
from collections import Counter
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

DB_PATH = Path("instagram_posts.db")
CSV_PATH = Path("posts.csv")
OUTPUT_HTML = Path("index_v0007.html")
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
    posts_json = json.dumps(posts, ensure_ascii=False)
    
    html_template = """<!DOCTYPE html>
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
        .video-placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #1e293b; font-size: 2rem; }
        .card-content { padding: 1rem; }
        .card-meta { display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; flex-wrap: wrap; }
        .author-name { color: #60a5fa; }
        .card-caption { font-size: 0.875rem; color: #cbd5e1; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 0.75rem; }
        .carousel { display: flex; gap: 0.5rem; overflow-x: auto; margin: 0.5rem 0; }
        .carousel-item { width: 60px; height: 60px; object-fit: cover; border-radius: 8px; cursor: pointer; background: #0f172a; }
        .carousel-video-placeholder { width: 60px; height: 60px; background: #1e293b; border-radius: 8px; display: flex; align-items: center; justify-content: center; cursor: pointer; }
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
        .storyboard-thumb { width: 80px; height: 80px; object-fit: cover; border-radius: 8px; cursor: pointer; margin-right: 8px; }
        .toast { position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); background: #1e293b; color: #e2e8f0; padding: 10px 20px; border-radius: 40px; z-index: 3000; opacity: 0; transition: opacity 0.2s; }
        .toast.show { opacity: 1; }
        .no-results { text-align: center; padding: 3rem; color: #94a3b8; grid-column: 1 / -1; }
    </style>
</head>
<body>
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
    <button class="storyboard-btn" id="openStoryboardBtn">Open Storyboard <span id="storyboardCountBadge" style="background:#ef4444; border-radius:20px; padding:2px 8px; margin-left:8px;">0</span></button>
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
            <div><strong>Images (click to remove):</strong><div id="storyboardThumbnails" style="display:flex; gap:12px; overflow-x:auto; padding:8px;"></div></div>
        </div>
    </div>
    <div id="toast" class="toast"></div>
    <div id="lightbox" class="lightbox"><div class="lightbox-content"><div class="lightbox-close" id="lightboxClose">×</div><div id="lightboxMediaContainer"></div><div id="lightboxCaption"></div></div></div>
    <div id="commentsModal" class="modal"><div class="modal-header"><strong>Comments</strong><span id="modalClose" class="modal-close">&times;</span></div><div id="commentsList"></div></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
    <script>
        const allPosts = """ + posts_json + """;
        const DISPLAY_MODE = \"""" + DISPLAY_MODE + """\";

        function showToast(msg, dur) {
            dur = dur || 2000;
            var t = document.getElementById('toast');
            t.textContent = msg;
            t.classList.add('show');
            setTimeout(function() { t.classList.remove('show'); }, dur);
        }

        function getMediaPath(folder, file) { return folder + '/' + file; }

        function renderGallery(posts) {
            var grid = document.getElementById('galleryGrid');
            if (!posts.length) { grid.innerHTML = '<div class="no-results">No posts match your search.</div>'; return; }
            var html = '';
            for (var idx = 0; idx < posts.length; idx++) {
                var post = posts[idx];
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
                    mediaHtml = '<img class="card-media" src="' + mp + '" loading="lazy">';
                } else {
                    mediaHtml = '<div class="card-media" style="display:flex; align-items:center; justify-content:center;">No media</div>';
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
            attachCommentListeners();
            attachCarouselListeners();
            addCheckboxesToCards();
        }

        function attachCommentListeners() {
            var btns = document.querySelectorAll('.comments-btn');
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
            for (var i = 0; i < items.length; i++) {
                items[i].onclick = carouselHandler;
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
            var c = document.getElementById('lightboxMediaContainer');
            c.innerHTML = '';
            var img = document.createElement('img');
            img.src = src;
            img.style.maxWidth = '90vw';
            img.style.maxHeight = '85vh';
            c.appendChild(img);
            document.getElementById('lightboxCaption').innerText = caption;
            document.getElementById('lightbox').classList.add('active');
        }

        function updateWordCloud(posts) {
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

        // Storyboard
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
            return new Promise(function(resolve) {
                fabric.Image.fromURL(src, function(img) {
                    if (!img) {
                        if (!silent) showToast("Failed to load image");
                        resolve(false);
                        return;
                    }
                    img.set({ crossOrigin: 'Anonymous', hasControls: true, hasBorders: true, lockRotation: true });
                    storyboardImages.push({ src: src, fabricObj: img, originalWidth: img.width, originalHeight: img.height });
                    canvas.add(img);
                    applyLayout(currentTemplate);
                    updateThumbnails();
                    saveToLocalStorage();
                    updateStoryboardBadge();
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
                html += '<img class="storyboard-thumb" src="' + storyboardImages[i].src + '" data-index="' + i + '">';
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
                                            canvas.add(img);
                                        }
                                        resolve();
                                    }, { crossOrigin: 'Anonymous' });
                                }));
                            })(srcs[i]);
                        }
                        Promise.all(promises).then(function() {
                            applyLayout(currentTemplate);
                            updateThumbnails();
                            updateStoryboardBadge();
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
        }

        function addCheckboxesToCards() {
            var cards = document.querySelectorAll('.card');
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
            var htmlContent = '<!DOCTYPE html><html><head><title>Storyboard</title><style>body{margin:0;background:#0f172a;color:white;}canvas{display:block;margin:20px auto;border:2px solid #475569;background:white;}.controls{text-align:center;padding:10px;}button{margin:5px;padding:8px 16px;background:#3b82f6;border:none;color:white;border-radius:8px;cursor:pointer;}</style><script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"><\\/script></head><body><div class="controls"><button id="exportBtn">Export PNG</button><button id="closeBtn" onclick="window.close()">Close</button></div><canvas id="storyboardCanvasNew" width="1080" height="1440"></canvas><script>var srcs = ' + JSON.stringify(srcs) + ';
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
                loadAll();<\\/script></body></html>';
            w.document.write(htmlContent);
            w.document.close();
        }

        (function init() {
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
        })();
    </script>
</body>
</html>"""
    
    return html_template

def main():
    logger.info("Starting gallery build v0007")
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

if __name__ == "__main__":
    main()