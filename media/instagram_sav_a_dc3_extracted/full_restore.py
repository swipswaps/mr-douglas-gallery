#!/usr/bin/env python3
"""
Full restoration: keep all gallery data, rebuild timeline and storyboard.
"""

import re
from pathlib import Path

HTML_PATH = Path("index_cloud.html")
BACKUP_PATH = Path("index_cloud_full_restore_backup.html")

# Read original content
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    original = f.read()

# Backup
with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
    f.write(original)

# === 1. Extract the allPosts array (preserve gallery data) ===
match = re.search(r'const allPosts = (\[[\s\S]*?\]);', original)
if not match:
    print("Could not find allPosts array. Aborting.")
    exit(1)
all_posts_js = match.group(1)

# === 2. Find the <body> and the word cloud container ===
body_match = re.search(r'<body[^>]*>([\s\S]*)</body>', original)
if not body_match:
    print("Could not find body.")
    exit(1)
body_content = body_match.group(1)

# Locate where to insert timeline: above the word cloud container or above the gallery grid
wordcloud_marker = re.search(r'(<div class="word-cloud-container"|id="wordcloud"|class="wordcloud-wrap")', body_content)
if not wordcloud_marker:
    print("Could not find word cloud marker.")
    exit(1)
insert_pos = wordcloud_marker.start()  # relative to body_content

# === 3. Build the clean timeline HTML (uses images from /timeline/) ===
timeline_html = """
<!-- ========== CLEAN TIMELINE ========== -->
<style>
.timeline-container {
    background: #f8f9fa;
    border-radius: 1rem;
    padding: 1rem;
    margin-bottom: 2rem;
    clear: both;
    width: 100%;
}
.timeline-header {
    font-size: 1.25rem;
    font-weight: bold;
    margin-bottom: 1rem;
}
.timeline-scroll {
    display: flex;
    overflow-x: auto;
    gap: 1rem;
    padding: 0.5rem;
    scrollbar-width: thin;
}
.timeline-card {
    flex: 0 0 auto;
    width: 150px;
    text-align: center;
    cursor: pointer;
    background: white;
    border-radius: 0.75rem;
    padding: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    position: relative;
}
.timeline-card img {
    width: 100%;
    aspect-ratio: 4/3;
    object-fit: cover;
    border-radius: 0.5rem;
    background: #e2e8f0;
}
.timeline-year {
    font-weight: bold;
    font-size: 0.9rem;
    margin: 0.25rem 0;
}
.timeline-title {
    font-size: 0.7rem;
    color: #334155;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
<div class="timeline-container">
    <div class="timeline-header">✈️ Mr. Douglas Through the Years</div>
    <div class="timeline-scroll" id="timelineScroll"></div>
</div>
<script>
(function() {
    const timelineImages = [
        { year: "1941", title: "United Mr Douglas 1941", src: "timeline/United-mr-douglas-1941.jpg" },
        { year: "1942", title: "United Flying 1942", src: "timeline/united-flying-1942.jpg" },
        { year: "1943", title: "Western 1943", src: "timeline/western-1943.jpg" },
        { year: "1952", title: "Mr Douglas 1952", src: "timeline/mr-douglas-1952.jpg" },
        { year: "1960", title: "Mr Douglas 1960", src: "timeline/mr-douglas-1960.jpg" },
        { year: "1970", title: "Mr Douglas 1970", src: "timeline/mr-douglas-1970.jpg" },
        { year: "1974", title: "Mr Douglas 1974", src: "timeline/mr-douglas-1974.jpg" },
        { year: "1979", title: "Mr Douglas 1979", src: "timeline/mr-douglas-1979.jpg" },
        { year: "1984", title: "Mr Douglas 1984", src: "timeline/mr-douglas-1984-1400x790-slider.jpg" },
        { year: "1988", title: "Mr Douglas 1988", src: "timeline/mr-douglas-1988.jpg" },
        { year: "1990", title: "Mr Douglas 1990", src: "timeline/mr-douglas-1990.jpg" },
        { year: "1992", title: "Mr Douglas 1992", src: "timeline/mr-douglas-1992.jpg" },
        { year: "1996", title: "Mr Douglas 1996", src: "timeline/mr-douglas-1996.jpg" },
        { year: "2018", title: "Drone Front", src: "timeline/Mr-Douglas-2018-drone-front-pix-slider.jpg" }
    ];
    const container = document.getElementById('timelineScroll');
    if (container) {
        container.innerHTML = timelineImages.map(img => `
            <div class="timeline-card" data-src="${img.src}">
                <img src="${img.src}" loading="lazy" onerror="this.src='data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Crect%20width%3D%22100%22%20height%3D%22100%22%20fill%3D%22%23cbd5e1%22%2F%3E%3Ctext%20x%3D%2250%22%20y%3D%2255%22%20text-anchor%3D%22middle%22%20fill%3D%22%23475569%22%3E%F0%9F%93%B8%3C%2Ftext%3E%3C%2Fsvg%3E';">
                <div class="timeline-year">${img.year}</div>
                <div class="timeline-title">${img.title}</div>
            </div>
        `).join('');
    }
})();
</script>
"""

# Insert timeline into body content at the marker position
new_body = body_content[:insert_pos] + timeline_html + "\n" + body_content[insert_pos:]

# === 4. Build complete storyboard + toolbar + checkboxes ===
storyboard_block = """
<!-- ========== COMPLETE STORYBOARD WITH TEMPLATES ========== -->
<style>
.storyboard-btn{position:fixed;bottom:20px;right:20px;background:#3b82f6;color:white;border:none;border-radius:50px;padding:12px 24px;font-size:1rem;font-weight:bold;cursor:pointer;z-index:1000;box-shadow:0 4px 12px rgba(0,0,0,0.3);}
.storyboard-btn:hover{background:#2563eb;}
.gallery-toolbar{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;align-items:center;background:#f1f5f9;padding:8px 12px;border-radius:12px;clear:both;}
.gallery-toolbar button{background:#334155;color:white;border:none;padding:6px 12px;border-radius:8px;cursor:pointer;}
.gallery-toolbar button.primary{background:#3b82f6;}
.gallery-toolbar button.danger{background:#ef4444;}
.select-checkbox{position:absolute;top:8px;left:8px;width:20px;height:20px;cursor:pointer;z-index:5;background:white;border-radius:4px;}
.storyboard-modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:2000;overflow:auto;}
.storyboard-modal.active{display:flex;flex-direction:column;}
.storyboard-container{background:#1e293b;margin:20px auto;padding:20px;border-radius:16px;max-width:95%;width:1200px;}
.storyboard-toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px;}
.storyboard-canvas-wrapper{background:#0f172a;border-radius:12px;padding:12px;text-align:center;overflow-x:auto;}
#storyboardCanvas{border:2px solid #475569;border-radius:8px;background:white;}
.storyboard-controls{display:flex;gap:10px;justify-content:center;margin:15px 0;flex-wrap:wrap;}
.storyboard-controls button{background:#3b82f6;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer;}
.storyboard-controls button.danger{background:#ef4444;}
.storyboard-controls button.success{background:#10b981;}
.storyboard-image-list{background:#0f172a;border-radius:12px;padding:12px;margin-top:20px;}
.storyboard-thumbnails{display:flex;gap:12px;overflow-x:auto;padding:8px;}
.storyboard-thumb{width:80px;height:80px;object-fit:cover;border-radius:8px;cursor:pointer;border:2px solid transparent;}
.storyboard-thumb:hover{border-color:#3b82f6;transform:scale(1.05);}
.close-modal{background:#475569;color:white;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;}
</style>

<div class="gallery-toolbar">
    <span style="font-weight:bold;">📌 Select images:</span>
    <button id="selectAllBtn">Select All</button>
    <button id="deselectAllBtn">Deselect All</button>
    <button id="addSelectedBtn" class="primary">➕ Add Selected to Storyboard</button>
    <span id="selectedCount">0 selected</span>
</div>

<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (36x48")</button>

<div id="storyboardModal" class="storyboard-modal">
    <div class="storyboard-container">
        <div class="storyboard-toolbar">
            <h3 style="color:white;">📸 Storyboard Builder – 36×48" @ 300 DPI</h3>
            <button class="close-modal" id="closeStoryboardBtn">✖ Close</button>
        </div>
        <div class="storyboard-canvas-wrapper">
            <canvas id="storyboardCanvas" width="1080" height="1440" style="width:100%; height:auto; max-width:1080px;"></canvas>
        </div>
        <div class="storyboard-controls">
            <select id="templateSelect" style="padding:6px 12px;border-radius:8px;">
                <option value="grid">📐 Grid (3 cols)</option>
                <option value="twoCol">↔️ Two columns</option>
                <option value="threeCol">↕️ Three columns</option>
                <option value="bigSmall">🖼️ Big + Small</option>
                <option value="center">🎯 Single centered</option>
            </select>
            <button id="applyTemplateBtn" class="success">✨ Apply Template</button>
            <button id="exportStoryboardBtn" class="success">⬇ Export PNG (10800×14400)</button>
            <button id="clearStoryboardBtn" class="danger">🗑 Clear All</button>
        </div>
        <div class="storyboard-image-list">
            <strong style="color:white;">📁 Images (click to remove):</strong>
            <div class="storyboard-thumbnails" id="storyboardThumbnails"></div>
        </div>
    </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
<script>
(function() {
    // ===== STATE =====
    window.storyboardImages = [];
    window.displayCanvas = null;
    const PREVIEW_W = 1080, PREVIEW_H = 1440;
    const TARGET_W = 10800, TARGET_H = 14400;
    const SCALE = TARGET_W / PREVIEW_W;

    const imgCache = new Map();
    function loadImage(src) {
        if (imgCache.has(src)) return Promise.resolve(imgCache.get(src));
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = "Anonymous";
            img.onload = () => { imgCache.set(src, img); resolve(img); };
            img.onerror = reject;
            img.src = src;
        });
    }

    // ===== ADD IMAGES =====
    window.addImageToStoryboard = async function(src, silent=false) {
        if (window.storyboardImages.some(i => i.src === src)) {
            if (!silent) alert("Image already in storyboard");
            return false;
        }
        try {
            const imgEl = await loadImage(src);
            const aspect = imgEl.width / imgEl.height;
            const defaultW = 200;
            const defaultH = defaultW / aspect;
            const newItem = {
                src: src,
                imgElement: imgEl,
                width: imgEl.width,
                height: imgEl.height,
                left: 0, top: 0,
                scaleX: defaultW / imgEl.width,
                scaleY: defaultH / imgEl.height,
                fabricObject: null
            };
            window.storyboardImages.push(newItem);
            if (window.displayCanvas) {
                const fimg = new fabric.Image(imgEl, {
                    left: 0, top: 0,
                    scaleX: defaultW / imgEl.width,
                    scaleY: defaultH / imgEl.height,
                    hasControls: true, hasBorders: true, lockRotation: true
                });
                newItem.fabricObject = fimg;
                window.displayCanvas.add(fimg);
                window.displayCanvas.renderAll();
            }
            updateThumbnails();
            return true;
        } catch(e) {
            if (!silent) alert("Failed: " + e.message);
            return false;
        }
    };

    window.addMultipleImages = async function(srcList) {
        let added = 0;
        for (let src of srcList) {
            if (await window.addImageToStoryboard(src, true)) added++;
        }
        if (added) {
            alert(`Added ${added} image(s)`);
            updateThumbnails();
            applyTemplate('grid');
        } else if (srcList.length) {
            alert("No new images added (maybe duplicates)");
        }
    };

    function updateThumbnails() {
        const container = document.getElementById('storyboardThumbnails');
        if (!container) return;
        container.innerHTML = window.storyboardImages.map((img, idx) =>
            `<img class="storyboard-thumb" src="${img.src}" data-index="${idx}">`
        ).join('');
        document.querySelectorAll('.storyboard-thumb').forEach(thumb => {
            thumb.addEventListener('click', (e) => {
                const idx = parseInt(thumb.dataset.index);
                if (!isNaN(idx)) {
                    if (window.displayCanvas && window.storyboardImages[idx].fabricObject) {
                        window.displayCanvas.remove(window.storyboardImages[idx].fabricObject);
                    }
                    window.storyboardImages.splice(idx, 1);
                    window.displayCanvas?.renderAll();
                    updateThumbnails();
                }
            });
        });
    }

    // ===== TEMPLATES =====
    function applyTemplate(templateName) {
        if (!window.displayCanvas || window.storyboardImages.length === 0) return;
        const cnt = window.storyboardImages.length;
        const margin = 20;
        const w = PREVIEW_W - margin * 2;
        const h = PREVIEW_H - margin * 2;

        if (templateName === 'center') {
            for (let i = 0; i < cnt; i++) {
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                const maxW = w * 0.8, maxH = h * 0.8;
                const sc = Math.min(maxW / img.width, maxH / img.height);
                const drawW = img.width * sc;
                const drawH = img.height * sc;
                const left = margin + (w - drawW) / 2;
                const top = margin + (h - drawH) / 2;
                item.left = left; item.top = top;
                item.scaleX = sc; item.scaleY = sc;
                if (item.fabricObject) item.fabricObject.set({ left, top, scaleX: sc, scaleY: sc });
            }
        } else if (templateName === 'twoCol') {
            const cols = 2;
            const cellW = (w - (cols-1)*margin) / cols;
            for (let i = 0; i < cnt; i++) {
                const row = Math.floor(i / cols);
                const col = i % cols;
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                const aspect = img.width / img.height;
                let drawW = cellW;
                let drawH = drawW / aspect;
                if (drawH > PREVIEW_H / 3) { drawH = PREVIEW_H / 3; drawW = drawH * aspect; }
                const left = margin + col * (cellW + margin);
                const top = margin + row * (drawH + margin);
                item.left = left; item.top = top;
                item.scaleX = drawW / img.width;
                item.scaleY = drawH / img.height;
                if (item.fabricObject) item.fabricObject.set({ left, top, scaleX: item.scaleX, scaleY: item.scaleY });
            }
        } else if (templateName === 'threeCol') {
            const cols = 3;
            const cellW = (w - (cols-1)*margin) / cols;
            for (let i = 0; i < cnt; i++) {
                const row = Math.floor(i / cols);
                const col = i % cols;
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                const aspect = img.width / img.height;
                let drawW = cellW;
                let drawH = drawW / aspect;
                if (drawH > 200) { drawH = 200; drawW = drawH * aspect; }
                const left = margin + col * (cellW + margin);
                const top = margin + row * (drawH + margin);
                item.left = left; item.top = top;
                item.scaleX = drawW / img.width;
                item.scaleY = drawH / img.height;
                if (item.fabricObject) item.fabricObject.set({ left, top, scaleX: item.scaleX, scaleY: item.scaleY });
            }
        } else if (templateName === 'bigSmall' && cnt >= 2) {
            const bigItem = window.storyboardImages[0];
            const bigImg = bigItem.imgElement;
            const bigW = w * 0.6, bigH = h;
            const bigSc = Math.min(bigW / bigImg.width, bigH / bigImg.height);
            const bigDrawW = bigImg.width * bigSc;
            const bigDrawH = bigImg.height * bigSc;
            bigItem.left = margin;
            bigItem.top = margin + (h - bigDrawH) / 2;
            bigItem.scaleX = bigSc; bigItem.scaleY = bigSc;
            if (bigItem.fabricObject) bigItem.fabricObject.set({ left: bigItem.left, top: bigItem.top, scaleX: bigSc, scaleY: bigSc });
            const smallW = w * 0.35;
            let y = margin;
            for (let i = 1; i < cnt; i++) {
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                const aspect = img.width / img.height;
                let drawW = smallW;
                let drawH = drawW / aspect;
                if (drawH > (h / (cnt-1)) - margin) drawH = (h / (cnt-1)) - margin;
                item.left = margin + bigDrawW + margin;
                item.top = y;
                item.scaleX = drawW / img.width;
                item.scaleY = drawH / img.height;
                if (item.fabricObject) item.fabricObject.set({ left: item.left, top: item.top, scaleX: item.scaleX, scaleY: item.scaleY });
                y += drawH + margin;
            }
        } else { // default grid (3 cols)
            const cols = 3;
            const cellW = (w - (cols-1)*margin) / cols;
            for (let i = 0; i < cnt; i++) {
                const row = Math.floor(i / cols);
                const col = i % cols;
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                const aspect = img.width / img.height;
                let drawW = cellW;
                let drawH = drawW / aspect;
                if (drawH > 200) { drawH = 200; drawW = drawH * aspect; }
                const left = margin + col * (cellW + margin);
                const top = margin + row * (drawH + margin);
                item.left = left; item.top = top;
                item.scaleX = drawW / img.width;
                item.scaleY = drawH / img.height;
                if (item.fabricObject) item.fabricObject.set({ left, top, scaleX: item.scaleX, scaleY: item.scaleY });
            }
        }
        window.displayCanvas.renderAll();
    }

    // ===== EXPORT =====
    window.exportStoryboard = async function() {
        if (window.storyboardImages.length === 0) { alert("No images"); return; }
        const off = document.createElement('canvas');
        off.width = TARGET_W; off.height = TARGET_H;
        const ctx = off.getContext('2d');
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, TARGET_W, TARGET_H);
        for (let item of window.storyboardImages) {
            try {
                const img = item.imgElement;
                const left = (item.left || 0) * SCALE;
                const top = (item.top || 0) * SCALE;
                const w = img.width * (item.scaleX || 1) * SCALE;
                const h = img.height * (item.scaleY || 1) * SCALE;
                ctx.drawImage(img, left, top, w, h);
            } catch(e) {}
        }
        const a = document.createElement('a');
        a.download = 'storyboard_36x48_300dpi.png';
        a.href = off.toDataURL('image/png');
        a.click();
    };

    function clearAll() {
        if (confirm("Clear all images?")) {
            window.storyboardImages = [];
            if (window.displayCanvas) { window.displayCanvas.clear(); window.displayCanvas.renderAll(); }
            updateThumbnails();
        }
    }

    // ===== CANVAS INIT =====
    function initCanvas() {
        const canvasEl = document.getElementById('storyboardCanvas');
        if (!canvasEl) return;
        window.displayCanvas = new fabric.Canvas('storyboardCanvas');
        window.displayCanvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
        window.displayCanvas.selection = true;
        window.displayCanvas.on('object:modified', (e) => {
            const obj = e.target;
            const idx = window.storyboardImages.findIndex(i => i.fabricObject === obj);
            if (idx !== -1) {
                window.storyboardImages[idx].left = obj.left;
                window.storyboardImages[idx].top = obj.top;
                window.storyboardImages[idx].scaleX = obj.scaleX;
                window.storyboardImages[idx].scaleY = obj.scaleY;
            }
        });
        window.displayCanvas.renderAll();
        updateThumbnails();
    }

    // ===== MULTI‑SELECT CHECKBOXES (gallery + timeline) =====
    let selectedSrcs = new Set();
    function addCheckboxToImage(img, src) {
        if (!src || img.closest('.card, .timeline-card')?.querySelector('.select-checkbox')) return;
        const chk = document.createElement('input');
        chk.type = 'checkbox';
        chk.className = 'select-checkbox';
        chk.checked = selectedSrcs.has(src);
        chk.addEventListener('change', () => {
            if (chk.checked) selectedSrcs.add(src);
            else selectedSrcs.delete(src);
            const countSpan = document.getElementById('selectedCount');
            if (countSpan) countSpan.innerText = selectedSrcs.size + ' selected';
        });
        const container = img.closest('.card, .timeline-card');
        if (container) {
            container.style.position = 'relative';
            container.appendChild(chk);
        }
    }

    function scanAndAddCheckboxes() {
        // Gallery cards
        document.querySelectorAll('.card img, .timeline-card img, .carousel-item, .card-media').forEach(img => {
            if (img.src && !img.src.startsWith('data:')) addCheckboxToImage(img, img.src);
        });
    }

    function observeGallery() {
        const grid = document.getElementById('galleryGrid');
        if (!grid) return;
        const obs = new MutationObserver(() => scanAndAddCheckboxes());
        obs.observe(grid, { childList: true, subtree: true });
        scanAndAddCheckboxes();
    }

    function selectAll() {
        document.querySelectorAll('.select-checkbox').forEach(chk => { chk.checked = true; });
        document.querySelectorAll('.card img, .timeline-card img').forEach(img => {
            if (img.src && !img.src.startsWith('data:')) selectedSrcs.add(img.src);
        });
        const countSpan = document.getElementById('selectedCount');
        if (countSpan) countSpan.innerText = selectedSrcs.size + ' selected';
    }

    function deselectAll() {
        document.querySelectorAll('.select-checkbox').forEach(chk => { chk.checked = false; });
        selectedSrcs.clear();
        const countSpan = document.getElementById('selectedCount');
        if (countSpan) countSpan.innerText = '0 selected';
    }

    function addSelectedToStoryboard() {
        const srcs = Array.from(selectedSrcs);
        if (srcs.length === 0) { alert("No images selected"); return; }
        window.addMultipleImages(srcs);
    }

    // ===== MAIN =====
    let waitForFabric = setInterval(() => {
        if (typeof fabric !== 'undefined') {
            clearInterval(waitForFabric);
            initCanvas();
            observeGallery();
            // Attach UI event handlers
            const selAll = document.getElementById('selectAllBtn');
            const deselAll = document.getElementById('deselectAllBtn');
            const addSel = document.getElementById('addSelectedBtn');
            const openBtn = document.getElementById('openStoryboardBtn');
            const closeBtn = document.getElementById('closeStoryboardBtn');
            const exportBtn = document.getElementById('exportStoryboardBtn');
            const clearBtn = document.getElementById('clearStoryboardBtn');
            const applyBtn = document.getElementById('applyTemplateBtn');
            const templateSelect = document.getElementById('templateSelect');
            if (selAll) selAll.onclick = selectAll;
            if (deselAll) deselAll.onclick = deselectAll;
            if (addSel) addSel.onclick = addSelectedToStoryboard;
            if (openBtn) openBtn.onclick = () => document.getElementById('storyboardModal')?.classList.add('active');
            if (closeBtn) closeBtn.onclick = () => document.getElementById('storyboardModal')?.classList.remove('active');
            if (exportBtn) exportBtn.onclick = () => window.exportStoryboard();
            if (clearBtn) clearBtn.onclick = clearAll;
            if (applyBtn && templateSelect) {
                applyBtn.onclick = () => applyTemplate(templateSelect.value);
            }
            window.onclick = (e) => { if (e.target === document.getElementById('storyboardModal')) document.getElementById('storyboardModal')?.classList.remove('active'); };
        }
    }, 200);
})();
</script>
<!-- ========== END STORYBOARD ========== -->
"""

# Reassemble full HTML: replace the old body content with the new_body, then insert storyboard before </body>
# But we already have new_body which contains everything except the storyboard. We'll append storyboard at the end of body.
new_body_with_storyboard = new_body + storyboard_block

# Also need to keep the existing script that defines allPosts and renders the gallery.
# The original body already contains that script. We are only adding timeline and storyboard, not removing the gallery script.
# So we must ensure we don't duplicate the </body> tag.
# Simpler: rebuild full HTML with the original <head> and the new body content.
# Extract everything before <body> and after </body> from original.
head_part = original.split('<body')[0] + '<body'
end_part = '</body>' + original.split('</body>')[-1] if '</body>' in original else ''

new_full = head_part + new_body_with_storyboard + end_part

# Write final HTML
with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(new_full)

print("✅ Full restoration completed.")
print("📁 Backup saved as", BACKUP_PATH)
print("💡 Hard refresh (Ctrl+Shift+R). Timeline is above word cloud, all images selectable, storyboard with templates ready.")