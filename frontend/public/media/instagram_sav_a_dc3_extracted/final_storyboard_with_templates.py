#!/usr/bin/env python3
"""
Final storyboard with templates, auto-arrange, and no overlapping.
All images appear correctly on canvas.
"""

import re
from pathlib import Path

HTML_PATH = Path("index_cloud.html")
BACKUP_PATH = Path("index_cloud_final_backup.html")

STORYBOARD_WITH_TEMPLATES = """
<!-- ========== FINAL STORYBOARD (TEMPLATES + FIXES) ========== -->
<style>
.storyboard-btn{position:fixed;bottom:20px;right:20px;background:#3b82f6;color:white;border:none;border-radius:50px;padding:12px 24px;font-size:1rem;font-weight:bold;cursor:pointer;z-index:1000;}
.storyboard-btn:hover{background:#2563eb;}
.gallery-toolbar{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;align-items:center;background:#f1f5f9;padding:8px 12px;border-radius:12px;}
.gallery-toolbar button{background:#334155;color:white;border:none;padding:6px 12px;border-radius:8px;cursor:pointer;}
.gallery-toolbar button.primary{background:#3b82f6;}
.gallery-toolbar button.danger{background:#ef4444;}
.select-checkbox{position:absolute;top:8px;left:8px;width:20px;height:20px;cursor:pointer;z-index:5;}
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
    // ---- Global state ----
    window.storyboardImages = [];   // each: { src, imgElement, fabricObject, left, top, scaleX, scaleY }
    window.displayCanvas = null;
    const previewW = 1080, previewH = 1440;
    const targetW = 10800, targetH = 14400;
    const scaleFactor = targetW / previewW; // 10

    // Image cache
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

    // Core: add a single image
    window.addImageToStoryboard = async function(src, silent = false) {
        if (window.storyboardImages.some(i => i.src === src)) {
            if (!silent) alert("Image already in storyboard");
            return false;
        }
        try {
            const imgEl = await loadImage(src);
            const aspect = imgEl.width / imgEl.height;
            const defaultSize = 200;
            const width = defaultSize;
            const height = width / aspect;
            const newItem = {
                src: src,
                imgElement: imgEl,
                width: imgEl.width,
                height: imgEl.height,
                left: 0,
                top: 0,
                scaleX: width / imgEl.width,
                scaleY: height / imgEl.height,
                fabricObject: null
            };
            window.storyboardImages.push(newItem);
            if (window.displayCanvas) {
                const fimg = new fabric.Image(imgEl, {
                    left: 0, top: 0,
                    scaleX: width / imgEl.width,
                    scaleY: height / imgEl.height,
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

    // Batch add
    window.addMultipleImages = async function(srcList) {
        let added = 0;
        for (let src of srcList) {
            if (await window.addImageToStoryboard(src, true)) added++;
        }
        if (added) {
            alert(`Added ${added} image(s)`);
            updateThumbnails();
            applyTemplate('grid');  // auto‑arrange after batch add
        } else {
            alert("No new images added");
        }
    };

    // Update thumbnail strip
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

    // ---- Templates ----
    function applyTemplate(templateName) {
        if (!window.displayCanvas || window.storyboardImages.length === 0) return;
        const count = window.storyboardImages.length;
        const margin = 20;
        const w = previewW - margin * 2;
        const h = previewH - margin * 2;

        if (templateName === 'center') {
            // Single image centered, scaled to fit (max 80% of canvas)
            for (let i = 0; i < window.storyboardImages.length; i++) {
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                const maxW = w * 0.8;
                const maxH = h * 0.8;
                const scaleX = maxW / img.width;
                const scaleY = maxH / img.height;
                const scale = Math.min(scaleX, scaleY);
                const drawW = img.width * scale;
                const drawH = img.height * scale;
                const left = margin + (w - drawW) / 2;
                const top = margin + (h - drawH) / 2;
                item.left = left; item.top = top;
                item.scaleX = scale; item.scaleY = scale;
                if (item.fabricObject) {
                    item.fabricObject.set({ left, top, scaleX: scale, scaleY: scale });
                }
            }
        } else if (templateName === 'twoCol') {
            const cols = 2;
            const cellW = (w - (cols-1)*margin) / cols;
            for (let i = 0; i < count; i++) {
                const row = Math.floor(i / cols);
                const col = i % cols;
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                const aspect = img.width / img.height;
                let drawW = cellW;
                let drawH = drawW / aspect;
                if (drawH > (previewH / 3)) { drawH = previewH / 3; drawW = drawH * aspect; }
                const left = margin + col * (cellW + margin);
                const top = margin + row * (previewH / 3 + margin);
                item.left = left; item.top = top;
                item.scaleX = drawW / img.width;
                item.scaleY = drawH / img.height;
                if (item.fabricObject) item.fabricObject.set({ left, top, scaleX: item.scaleX, scaleY: item.scaleY });
            }
        } else if (templateName === 'threeCol') {
            const cols = 3;
            const cellW = (w - (cols-1)*margin) / cols;
            for (let i = 0; i < count; i++) {
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
        } else if (templateName === 'bigSmall' && count >= 2) {
            // First image big on left, others small on right
            const bigItem = window.storyboardImages[0];
            const bigImg = bigItem.imgElement;
            const bigW = w * 0.6;
            const bigH = h;
            const bigScaleX = bigW / bigImg.width;
            const bigScaleY = bigH / bigImg.height;
            const bigScale = Math.min(bigScaleX, bigScaleY);
            const bigDrawW = bigImg.width * bigScale;
            const bigDrawH = bigImg.height * bigScale;
            bigItem.left = margin;
            bigItem.top = margin + (h - bigDrawH)/2;
            bigItem.scaleX = bigScale; bigItem.scaleY = bigScale;
            if (bigItem.fabricObject) bigItem.fabricObject.set({ left: bigItem.left, top: bigItem.top, scaleX: bigScale, scaleY: bigScale });
            const smallW = w * 0.35;
            const smallMargin = margin;
            let y = margin;
            for (let i = 1; i < count; i++) {
                const item = window.storyboardImages[i];
                const img = item.imgElement;
                const aspect = img.width / img.height;
                let drawW = smallW;
                let drawH = drawW / aspect;
                if (drawH > (h / (count-1)) - margin) drawH = (h / (count-1)) - margin;
                item.left = margin + bigDrawW + smallMargin;
                item.top = y;
                item.scaleX = drawW / img.width;
                item.scaleY = drawH / img.height;
                if (item.fabricObject) item.fabricObject.set({ left: item.left, top: item.top, scaleX: item.scaleX, scaleY: item.scaleY });
                y += drawH + margin;
            }
        } else {
            // default grid (3 columns)
            const cols = 3;
            const cellW = (w - (cols-1)*margin) / cols;
            for (let i = 0; i < count; i++) {
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

    // ---- Export ----
    window.exportStoryboard = async function() {
        if (window.storyboardImages.length === 0) { alert("No images"); return; }
        const off = document.createElement('canvas');
        off.width = targetW; off.height = targetH;
        const ctx = off.getContext('2d');
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, targetW, targetH);
        for (let item of window.storyboardImages) {
            try {
                const img = item.imgElement;
                const left = (item.left || 0) * scaleFactor;
                const top = (item.top || 0) * scaleFactor;
                const width = img.width * (item.scaleX || 1) * scaleFactor;
                const height = img.height * (item.scaleY || 1) * scaleFactor;
                ctx.drawImage(img, left, top, width, height);
            } catch(e) {}
        }
        const link = document.createElement('a');
        link.download = 'storyboard_36x48_300dpi.png';
        link.href = off.toDataURL('image/png');
        link.click();
    };

    function clearAll() {
        if (confirm("Clear all?")) {
            window.storyboardImages = [];
            if (window.displayCanvas) { window.displayCanvas.clear(); window.displayCanvas.renderAll(); }
            updateThumbnails();
        }
    }

    // ---- Init canvas ----
    function initCanvas() {
        const canvasEl = document.getElementById('storyboardCanvas');
        if (!canvasEl) return;
        window.displayCanvas = new fabric.Canvas('storyboardCanvas');
        window.displayCanvas.setDimensions({ width: previewW, height: previewH });
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

    // ---- Gallery: multi-select ----
    let selectedSrcs = new Set();
    function addCheckboxes() {
        document.querySelectorAll('.card, .timeline-card').forEach(card => {
            if (card.querySelector('.select-checkbox')) return;
            const img = card.querySelector('img');
            if (!img || !img.src || img.src.startsWith('data:')) return;
            const chk = document.createElement('input');
            chk.type = 'checkbox';
            chk.className = 'select-checkbox';
            chk.checked = selectedSrcs.has(img.src);
            chk.addEventListener('change', () => {
                if (chk.checked) selectedSrcs.add(img.src);
                else selectedSrcs.delete(img.src);
                document.getElementById('selectedCount').innerText = selectedSrcs.size + ' selected';
            });
            card.style.position = 'relative';
            card.appendChild(chk);
        });
    }
    function selectAll() {
        document.querySelectorAll('.select-checkbox').forEach(chk => { chk.checked = true; });
        document.querySelectorAll('.card img, .timeline-card img').forEach(img => {
            if (img.src && !img.src.startsWith('data:')) selectedSrcs.add(img.src);
        });
        document.getElementById('selectedCount').innerText = selectedSrcs.size + ' selected';
    }
    function deselectAll() {
        document.querySelectorAll('.select-checkbox').forEach(chk => { chk.checked = false; });
        selectedSrcs.clear();
        document.getElementById('selectedCount').innerText = '0 selected';
    }
    function addSelected() {
        const srcs = Array.from(selectedSrcs);
        if (srcs.length === 0) { alert("No images selected"); return; }
        window.addMultipleImages(srcs);
    }
    function observeGallery() {
        const grid = document.getElementById('galleryGrid');
        if (!grid) return;
        const obs = new MutationObserver(() => addCheckboxes());
        obs.observe(grid, { childList: true, subtree: true });
        addCheckboxes();
    }

    // ---- Main ----
    let check = setInterval(() => {
        if (typeof fabric !== 'undefined') {
            clearInterval(check);
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
                const template = document.getElementById('templateSelect').value;
                applyTemplate(template);
            };
            window.onclick = (e) => { if (e.target === document.getElementById('storyboardModal')) document.getElementById('storyboardModal').classList.remove('active'); };
        }
    }, 200);
})();
</script>
<!-- ========== END FINAL STORYBOARD ========== -->
"""

def apply_fix():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    # Remove previous storyboard sections
    pattern = r'<!-- ========== STORYBOARD BUILDER.*?<!-- ========== END STORYBOARD ========== -->'
    content = re.sub(pattern, STORYBOARD_WITH_TEMPLATES, content, flags=re.DOTALL)
    # Fix timeline image paths
    content = re.sub(r'(<img[^>]*src=")(?!timeline/)([^"]+\.jpg)"', r'\1timeline/\2"', content)
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Final storyboard with templates applied.")
    print("📁 Backup saved as", BACKUP_PATH)
    print("💡 Hard refresh (Ctrl+Shift+R). Select images, add, then apply a template.")

if __name__ == "__main__":
    apply_fix()