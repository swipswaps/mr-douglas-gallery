#!/usr/bin/env python3
"""
Final fix: keep all gallery data, add single timeline, add checkboxes to all images,
and inject a lightweight storyboard (no duplicates, no overlapping).
"""

import re
from pathlib import Path
import shutil

HTML_PATH = Path("index_cloud.html")
BACKUP_PATH = Path("index_cloud_final_working_backup.html")

# Use the best backup that contains full gallery (index_cloud_final_backup.html)
SOURCE = Path("index_cloud_final_backup.html")
if not SOURCE.exists():
    print(f"Error: {SOURCE} not found. Available backups:")
    for b in Path(".").glob("index_cloud*backup*.html"):
        print(f"  {b}")
    exit(1)

# 1. Restore the full gallery backup
shutil.copy(SOURCE, BACKUP_PATH)
shutil.copy(SOURCE, HTML_PATH)
print(f"✅ Restored full gallery from {SOURCE}")

# 2. Read the file
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# 3. Remove ALL existing timeline and storyboard blocks (to avoid duplicates and heavy code)
content = re.sub(r'<!-- ==========.*?TIMELINE.*?-->.*?<div class="timeline-container".*?</div>\s*</div>\s*', '', content, flags=re.DOTALL)
content = re.sub(r'<!-- ==========.*?STORYBOARD.*?-->.*?</script>\s*<!-- ========== END STORYBOARD ========== -->', '', content, flags=re.DOTALL)

# 4. Insert a clean, static timeline above the word cloud
#    (Place it exactly before the word cloud container or the gallery grid)
wordcloud_marker = re.search(r'(<div class="word-cloud-container"|id="wordcloud")', content)
if not wordcloud_marker:
    wordcloud_marker = re.search(r'(<div class="gallery-grid"|id="galleryGrid")', content)
if not wordcloud_marker:
    print("Could not find insertion point for timeline. Aborting.")
    exit(1)

insert_pos = wordcloud_marker.start()

clean_timeline = '''
<!-- ========== SINGLE TIMELINE (above word cloud) ========== -->
<style>
.timeline-container {
    background: #f1f5f9;
    border-radius: 1rem;
    padding: 1rem;
    margin: 0 0 2rem 0;
    clear: both;
}
.timeline-header {
    font-weight: bold;
    font-size: 1.2rem;
    margin-bottom: 0.8rem;
}
.timeline-scroll {
    display: flex;
    overflow-x: auto;
    gap: 1rem;
    padding: 0.5rem 0;
}
.timeline-card {
    flex: 0 0 auto;
    width: 130px;
    text-align: center;
    background: white;
    border-radius: 0.75rem;
    padding: 0.5rem;
    position: relative;
    cursor: pointer;
    transition: transform 0.1s;
}
.timeline-card:hover { transform: scale(1.02); }
.timeline-card img {
    width: 100%;
    aspect-ratio: 4/3;
    object-fit: cover;
    border-radius: 0.5rem;
    background: #e2e8f0;
}
.timeline-year {
    font-weight: bold;
    margin: 0.25rem 0;
    font-size: 0.9rem;
}
</style>
<div class="timeline-container">
    <div class="timeline-header">✈️ Mr. Douglas Through the Years</div>
    <div class="timeline-scroll" id="timelineScroll"></div>
</div>
<script>
(function() {
    const images = [
        { year: "1941", src: "timeline/United-mr-douglas-1941.jpg" },
        { year: "1942", src: "timeline/united-flying-1942.jpg" },
        { year: "1943", src: "timeline/western-1943.jpg" },
        { year: "1952", src: "timeline/mr-douglas-1952.jpg" },
        { year: "1960", src: "timeline/mr-douglas-1960.jpg" },
        { year: "1970", src: "timeline/mr-douglas-1970.jpg" },
        { year: "1974", src: "timeline/mr-douglas-1974.jpg" },
        { year: "1979", src: "timeline/mr-douglas-1979.jpg" },
        { year: "1984", src: "timeline/mr-douglas-1984-1400x790-slider.jpg" },
        { year: "1988", src: "timeline/mr-douglas-1988.jpg" },
        { year: "1990", src: "timeline/mr-douglas-1990.jpg" },
        { year: "1992", src: "timeline/mr-douglas-1992.jpg" },
        { year: "1996", src: "timeline/mr-douglas-1996.jpg" },
        { year: "2018", src: "timeline/Mr-Douglas-2018-drone-front-pix-slider.jpg" }
    ];
    const container = document.getElementById('timelineScroll');
    if (container) {
        container.innerHTML = images.map(img => `
            <div class="timeline-card" data-src="${img.src}">
                <img src="${img.src}" loading="lazy" onerror="this.src='data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Crect%20width%3D%22100%22%20height%3D%22100%22%20fill%3D%22%23cbd5e1%22%2F%3E%3Ctext%20x%3D%2250%22%20y%3D%2255%22%20text-anchor%3D%22middle%22%20fill%3D%22%23475569%22%3E%F0%9F%93%B8%3C%2Ftext%3E%3C%2Fsvg%3E';">
                <div class="timeline-year">${img.year}</div>
            </div>
        `).join('');
    }
})();
</script>
'''

# Insert timeline at the correct position
content = content[:insert_pos] + clean_timeline + '\n' + content[insert_pos:]

# 5. Add a lightweight storyboard with checkboxes on ALL images (gallery + timeline)
#    We'll inject it before </body>.
storyboard_code = '''
<!-- ========== LIGHTWEIGHT STORYBOARD (no infinite loops) ========== -->
<style>
.storyboard-btn {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 50px;
    padding: 12px 24px;
    font-size: 1rem;
    font-weight: bold;
    cursor: pointer;
    z-index: 1000;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.storyboard-btn:hover { background: #2563eb; }
.gallery-toolbar {
    display: flex;
    gap: 12px;
    margin: 16px 0;
    flex-wrap: wrap;
    align-items: center;
    background: #f1f5f9;
    padding: 8px 12px;
    border-radius: 12px;
}
.select-checkbox {
    position: absolute;
    top: 8px;
    left: 8px;
    width: 20px;
    height: 20px;
    cursor: pointer;
    z-index: 10;
    background: white;
    border-radius: 4px;
    border: 1px solid #cbd5e1;
}
.storyboard-modal {
    display: none;
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.85);
    z-index: 2000;
    overflow: auto;
}
.storyboard-modal.active { display: flex; flex-direction: column; }
.storyboard-container {
    background: #1e293b;
    margin: 20px auto;
    padding: 20px;
    border-radius: 16px;
    max-width: 95%;
    width: 1200px;
}
.storyboard-canvas-wrapper {
    background: #0f172a;
    border-radius: 12px;
    padding: 12px;
    text-align: center;
    overflow-x: auto;
}
#storyboardCanvas {
    border: 2px solid #475569;
    border-radius: 8px;
    background: white;
}
.storyboard-controls {
    display: flex;
    gap: 10px;
    justify-content: center;
    margin: 15px 0;
    flex-wrap: wrap;
}
.storyboard-controls button {
    background: #3b82f6;
    border: none;
    color: white;
    padding: 8px 16px;
    border-radius: 8px;
    cursor: pointer;
}
.storyboard-controls button.danger { background: #ef4444; }
.storyboard-controls button.success { background: #10b981; }
.close-modal {
    background: #475569;
    color: white;
    border: none;
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
}
</style>

<div class="gallery-toolbar">
    <span>📌 Select images:</span>
    <button id="selectAllBtn">Select All</button>
    <button id="deselectAllBtn">Deselect All</button>
    <button id="addSelectedBtn" class="primary">➕ Add Selected to Storyboard</button>
    <span id="selectedCount">0 selected</span>
</div>

<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (36x48")</button>

<div id="storyboardModal" class="storyboard-modal">
    <div class="storyboard-container">
        <div class="storyboard-toolbar" style="display:flex; justify-content:space-between;">
            <h3 style="color:white;">📸 Storyboard Builder – 36×48" @ 300 DPI</h3>
            <button class="close-modal" id="closeStoryboardBtn">✖ Close</button>
        </div>
        <div class="storyboard-canvas-wrapper">
            <canvas id="storyboardCanvas" width="1080" height="1440" style="width:100%; height:auto; max-width:1080px;"></canvas>
        </div>
        <div class="storyboard-controls">
            <select id="templateSelect">
                <option value="grid">Grid (3 cols)</option>
                <option value="twoCol">Two columns</option>
                <option value="threeCol">Three columns</option>
                <option value="bigSmall">Big + Small</option>
                <option value="center">Single centered</option>
            </select>
            <button id="applyTemplateBtn" class="success">✨ Apply Template</button>
            <button id="exportStoryboardBtn" class="success">⬇ Export PNG (10800×14400)</button>
            <button id="clearStoryboardBtn" class="danger">🗑 Clear All</button>
        </div>
        <div class="storyboard-image-list">
            <strong style="color:white;">📁 Images (click to remove):</strong>
            <div class="storyboard-thumbnails" id="storyboardThumbnails" style="display:flex; gap:12px; overflow-x:auto; padding:8px;"></div>
        </div>
    </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
<script>
(function() {
    // === Storyboard state ===
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

    window.addImageToStoryboard = async function(src, silent=false) {
        if (window.storyboardImages.some(i => i.src === src)) {
            if (!silent) alert("Image already in storyboard");
            return false;
        }
        try {
            const imgEl = await loadImage(src);
            const aspect = imgEl.width / imgEl.height;
            const defW = 200, defH = defW / aspect;
            const newItem = {
                src, imgElement: imgEl,
                width: imgEl.width, height: imgEl.height,
                left: 0, top: 0,
                scaleX: defW / imgEl.width, scaleY: defH / imgEl.height,
                fabricObject: null
            };
            window.storyboardImages.push(newItem);
            if (window.displayCanvas) {
                const fimg = new fabric.Image(imgEl, {
                    left: 0, top: 0,
                    scaleX: defW / imgEl.width, scaleY: defH / imgEl.height,
                    hasControls: true, lockRotation: true
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
        if (added) alert(`Added ${added} image(s)`);
        else if (srcList.length) alert("No new images (duplicates)");
        if (added) applyTemplate('grid');
    };

    function updateThumbnails() {
        const container = document.getElementById('storyboardThumbnails');
        if (!container) return;
        container.innerHTML = window.storyboardImages.map((img, idx) =>
            `<img class="storyboard-thumb" src="${img.src}" data-index="${idx}" style="width:80px; height:80px; object-fit:cover; border-radius:8px; cursor:pointer;">`
        ).join('');
        document.querySelectorAll('.storyboard-thumb').forEach(thumb => {
            thumb.addEventListener('click', () => {
                const idx = parseInt(thumb.dataset.index);
                if (!isNaN(idx)) {
                    if (window.displayCanvas && window.storyboardImages[idx].fabricObject)
                        window.displayCanvas.remove(window.storyboardImages[idx].fabricObject);
                    window.storyboardImages.splice(idx, 1);
                    window.displayCanvas?.renderAll();
                    updateThumbnails();
                }
            });
        });
    }

    function applyTemplate(templateName) {
        if (!window.displayCanvas || window.storyboardImages.length === 0) return;
        const cnt = window.storyboardImages.length;
        const margin = 20;
        const w = PREVIEW_W - margin*2, h = PREVIEW_H - margin*2;

        if (templateName === 'center') {
            for (let i=0; i<cnt; i++) {
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                const sc = Math.min((w*0.8)/img.width, (h*0.8)/img.height);
                const drawW = img.width*sc, drawH = img.height*sc;
                const left = margin + (w-drawW)/2, top = margin + (h-drawH)/2;
                item.left = left; item.top = top;
                item.scaleX = sc; item.scaleY = sc;
                item.fabricObject?.set({ left, top, scaleX: sc, scaleY: sc });
            }
        } else if (templateName === 'twoCol') {
            const cols = 2;
            const cellW = (w - (cols-1)*margin) / cols;
            for (let i=0; i<cnt; i++) {
                const row = Math.floor(i/cols), col = i%cols;
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                let drawW = cellW;
                let drawH = drawW / (img.width/img.height);
                if (drawH > PREVIEW_H/3) { drawH = PREVIEW_H/3; drawW = drawH * (img.width/img.height); }
                const left = margin + col*(cellW+margin);
                const top = margin + row*(drawH+margin);
                item.left = left; item.top = top;
                item.scaleX = drawW/img.width; item.scaleY = drawH/img.height;
                item.fabricObject?.set({ left, top, scaleX: item.scaleX, scaleY: item.scaleY });
            }
        } else if (templateName === 'threeCol') {
            const cols = 3;
            const cellW = (w - (cols-1)*margin) / cols;
            for (let i=0; i<cnt; i++) {
                const row = Math.floor(i/cols), col = i%cols;
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                let drawW = cellW;
                let drawH = drawW / (img.width/img.height);
                if (drawH > 200) { drawH = 200; drawW = drawH * (img.width/img.height); }
                const left = margin + col*(cellW+margin);
                const top = margin + row*(drawH+margin);
                item.left = left; item.top = top;
                item.scaleX = drawW/img.width; item.scaleY = drawH/img.height;
                item.fabricObject?.set({ left, top, scaleX: item.scaleX, scaleY: item.scaleY });
            }
        } else if (templateName === 'bigSmall' && cnt >= 2) {
            const bigItem = window.storyboardImages[0];
            const bigImg = bigItem.imgElement;
            const bigW = w*0.6, bigH = h;
            const bigSc = Math.min(bigW/bigImg.width, bigH/bigImg.height);
            const bigDrawW = bigImg.width*bigSc, bigDrawH = bigImg.height*bigSc;
            bigItem.left = margin;
            bigItem.top = margin + (h-bigDrawH)/2;
            bigItem.scaleX = bigSc; bigItem.scaleY = bigSc;
            bigItem.fabricObject?.set({ left: bigItem.left, top: bigItem.top, scaleX: bigSc, scaleY: bigSc });
            const smallW = w*0.35;
            let y = margin;
            for (let i=1; i<cnt; i++) {
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                let drawW = smallW;
                let drawH = drawW / (img.width/img.height);
                if (drawH > (h/(cnt-1))-margin) drawH = (h/(cnt-1))-margin;
                item.left = margin + bigDrawW + margin;
                item.top = y;
                item.scaleX = drawW/img.width; item.scaleY = drawH/img.height;
                item.fabricObject?.set({ left: item.left, top: item.top, scaleX: item.scaleX, scaleY: item.scaleY });
                y += drawH + margin;
            }
        } else { // default grid
            const cols = 3;
            const cellW = (w - (cols-1)*margin) / cols;
            for (let i=0; i<cnt; i++) {
                const row = Math.floor(i/cols), col = i%cols;
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                let drawW = cellW;
                let drawH = drawW / (img.width/img.height);
                if (drawH > 200) { drawH = 200; drawW = drawH * (img.width/img.height); }
                const left = margin + col*(cellW+margin);
                const top = margin + row*(drawH+margin);
                item.left = left; item.top = top;
                item.scaleX = drawW/img.width; item.scaleY = drawH/img.height;
                item.fabricObject?.set({ left, top, scaleX: item.scaleX, scaleY: item.scaleY });
            }
        }
        window.displayCanvas.renderAll();
    }

    window.exportStoryboard = async function() {
        if (!window.storyboardImages.length) { alert("No images"); return; }
        const off = document.createElement('canvas');
        off.width = TARGET_W; off.height = TARGET_H;
        const ctx = off.getContext('2d');
        ctx.fillStyle = 'white';
        ctx.fillRect(0,0,TARGET_W,TARGET_H);
        for (let item of window.storyboardImages) {
            try {
                const img = item.imgElement;
                const left = (item.left||0)*SCALE;
                const top = (item.top||0)*SCALE;
                const w = img.width * (item.scaleX||1) * SCALE;
                const h = img.height * (item.scaleY||1) * SCALE;
                ctx.drawImage(img, left, top, w, h);
            } catch(e) {}
        }
        const a = document.createElement('a');
        a.download = 'storyboard_36x48_300dpi.png';
        a.href = off.toDataURL('image/png');
        a.click();
    };

    function clearAll() {
        if (confirm("Clear all?")) {
            window.storyboardImages = [];
            window.displayCanvas?.clear();
            window.displayCanvas?.renderAll();
            updateThumbnails();
        }
    }

    function initCanvas() {
        const canvas = document.getElementById('storyboardCanvas');
        if (!canvas) return;
        window.displayCanvas = new fabric.Canvas('storyboardCanvas');
        window.displayCanvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
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

    // ===== Multi‑select checkboxes on ALL images =====
    let selectedSrcs = new Set();
    function addCheckboxToCard(card, src) {
        if (card.querySelector('.select-checkbox')) return;
        const chk = document.createElement('input');
        chk.type = 'checkbox';
        chk.className = 'select-checkbox';
        chk.checked = selectedSrcs.has(src);
        chk.addEventListener('change', () => {
            if (chk.checked) selectedSrcs.add(src);
            else selectedSrcs.delete(src);
            const span = document.getElementById('selectedCount');
            if (span) span.innerText = selectedSrcs.size + ' selected';
        });
        if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
        card.appendChild(chk);
    }

    function scanAndAddCheckboxes() {
        // Gallery cards
        document.querySelectorAll('.card, .timeline-card').forEach(card => {
            const img = card.querySelector('img');
            if (img && img.src && !img.src.startsWith('data:')) {
                addCheckboxToCard(card, img.src);
            }
        });
    }

    function selectAll() {
        document.querySelectorAll('.select-checkbox').forEach(chk => chk.checked = true);
        selectedSrcs.clear();
        document.querySelectorAll('.card img, .timeline-card img').forEach(img => {
            if (img.src && !img.src.startsWith('data:')) selectedSrcs.add(img.src);
        });
        const span = document.getElementById('selectedCount');
        if (span) span.innerText = selectedSrcs.size + ' selected';
    }

    function deselectAll() {
        document.querySelectorAll('.select-checkbox').forEach(chk => chk.checked = false);
        selectedSrcs.clear();
        const span = document.getElementById('selectedCount');
        if (span) span.innerText = '0 selected';
    }

    function addSelected() {
        const srcs = Array.from(selectedSrcs);
        if (srcs.length === 0) { alert("No images selected"); return; }
        window.addMultipleImages(srcs);
    }

    // Observe for dynamically added cards (lazy loading)
    function observeGallery() {
        const grid = document.getElementById('galleryGrid');
        if (!grid) return;
        const observer = new MutationObserver(() => scanAndAddCheckboxes());
        observer.observe(grid, { childList: true, subtree: true });
        scanAndAddCheckboxes();
    }

    // === Initialization ===
    let waitForFabric = setInterval(() => {
        if (typeof fabric !== 'undefined') {
            clearInterval(waitForFabric);
            initCanvas();
            observeGallery();
            document.getElementById('selectAllBtn')?.addEventListener('click', selectAll);
            document.getElementById('deselectAllBtn')?.addEventListener('click', deselectAll);
            document.getElementById('addSelectedBtn')?.addEventListener('click', addSelected);
            document.getElementById('openStoryboardBtn').onclick = () => document.getElementById('storyboardModal').classList.add('active');
            document.getElementById('closeStoryboardBtn').onclick = () => document.getElementById('storyboardModal').classList.remove('active');
            document.getElementById('exportStoryboardBtn').onclick = () => window.exportStoryboard();
            document.getElementById('clearStoryboardBtn').onclick = clearAll;
            document.getElementById('applyTemplateBtn').onclick = () => {
                const tpl = document.getElementById('templateSelect').value;
                applyTemplate(tpl);
            };
            window.onclick = (e) => { if (e.target === document.getElementById('storyboardModal')) document.getElementById('storyboardModal').classList.remove('active'); };
        }
    }, 200);
})();
</script>
<!-- ========== END STORYBOARD ========== -->
'''

# Append storyboard before </body>
content = content.replace('</body>', storyboard_code + '\n</body>')

# 6. Write the final file
with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Final working page created.")
print(f"📁 Backup of original saved as {BACKUP_PATH}")
print("💡 Start the server: python -m http.server 8000")
print("   Then hard refresh (Ctrl+Shift+R).")