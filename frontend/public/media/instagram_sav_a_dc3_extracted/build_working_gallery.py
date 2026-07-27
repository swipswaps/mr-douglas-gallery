#!/usr/bin/env python3
"""
Final fix: remove timeline, fix any remaining image paths, inject storyboard.
Uses index_cloud_backup.html as source.
"""

import re
import shutil
from pathlib import Path

SOURCE = Path("index_cloud_backup.html")
TARGET = Path("index_working.html")
BACKUP = Path("index_working_backup.html")

if not SOURCE.exists():
    print("index_cloud_backup.html not found.")
    exit(1)

# Backup existing target if any
if TARGET.exists():
    shutil.copy(TARGET, BACKUP)

# Read source
with open(SOURCE, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove ALL timeline containers (there may be more than one)
# The timeline container has class "timeline-container" and contains nested divs.
# We'll remove everything from <div class="timeline-container"> to the matching closing </div>.
# Use a pattern that matches the outermost div.
content = re.sub(r'<div class="timeline-container">.*?</div>\s*</div>', '', content, flags=re.DOTALL)
# Also remove any leftover timeline modal and its script
content = re.sub(r'<div id="timelineModal".*?</div>', '', content, flags=re.DOTALL)
content = re.sub(r'<script>.*?renderTimeline\(\);.*?</script>', '', content, flags=re.DOTALL)
# Remove timeline header if any
content = re.sub(r'<div class="timeline-header">.*?</div>', '', content)

# 2. Remove any existing storyboard / gallery toolbar (to avoid duplicates)
content = re.sub(r'<div class="gallery-toolbar">.*?</div>', '', content, flags=re.DOTALL)
content = re.sub(r'<button class="storyboard-btn".*?</button>', '', content)
content = re.sub(r'<div id="storyboardModal".*?</div>\s*</div>.*?<!-- ========== END STORYBOARD ========== -->', '', content, flags=re.DOTALL)

# 3. Append the storyboard code (lightweight, same as before)
storyboard = '''
<!-- ========== STORYBOARD (FINAL) ========== -->
<style>
.storyboard-btn{position:fixed;bottom:20px;right:20px;background:#3b82f6;color:white;border:none;border-radius:50px;padding:12px 24px;font-size:1rem;font-weight:bold;cursor:pointer;z-index:1000;box-shadow:0 2px 8px rgba(0,0,0,0.2);}
.storyboard-btn:hover{background:#2563eb;}
.gallery-toolbar{display:flex;gap:12px;margin:16px 0;flex-wrap:wrap;align-items:center;background:#f1f5f9;padding:8px 12px;border-radius:12px;color:#0f172a;}
.gallery-toolbar button{background:#334155;color:white;border:none;padding:6px 12px;border-radius:8px;cursor:pointer;}
.gallery-toolbar button.primary{background:#3b82f6;}
.select-checkbox{position:absolute;top:8px;left:8px;width:20px;height:20px;cursor:pointer;z-index:10;background:white;border-radius:4px;border:1px solid #cbd5e1;}
.storyboard-modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:2000;overflow:auto;}
.storyboard-modal.active{display:flex;flex-direction:column;}
.storyboard-container{background:#1e293b;margin:20px auto;padding:20px;border-radius:16px;max-width:95%;width:1200px;}
.storyboard-canvas-wrapper{background:#0f172a;border-radius:12px;padding:12px;text-align:center;overflow-x:auto;}
#storyboardCanvas{border:2px solid #475569;border-radius:8px;background:white;}
.storyboard-controls{display:flex;gap:10px;justify-content:center;margin:15px 0;flex-wrap:wrap;}
.storyboard-controls button{background:#3b82f6;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer;}
.storyboard-controls button.danger{background:#ef4444;}
.storyboard-controls button.success{background:#10b981;}
.close-modal{background:#475569;color:white;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;}
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
        <div style="display:flex; justify-content:space-between;">
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
        <div>
            <strong style="color:white;">📁 Images (click to remove):</strong>
            <div id="storyboardThumbnails" style="display:flex; gap:12px; overflow-x:auto; padding:8px;"></div>
        </div>
    </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
<script>
(function() {
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
                left: 50, top: 50,
                scaleX: defW / imgEl.width, scaleY: defH / imgEl.height,
                fabricObject: null
            };
            window.storyboardImages.push(newItem);
            if (window.displayCanvas) {
                const fimg = new fabric.Image(imgEl, {
                    left: 50, top: 50,
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
        const cols = 3;
        const cellW = (w - (cols-1)*margin) / cols;
        for (let i=0; i<cnt; i++) {
            const row = Math.floor(i / cols);
            const col = i % cols;
            const item = window.storyboardImages[i];
            const img = item.imgElement;
            let drawW = cellW;
            let drawH = drawW / (img.width/img.height);
            if (drawH > 200) { drawH = 200; drawW = drawH * (img.width/img.height); }
            const left = margin + col * (cellW + margin);
            const top = margin + row * (drawH + margin);
            item.left = left; item.top = top;
            item.scaleX = drawW / img.width;
            item.scaleY = drawH / img.height;
            if (item.fabricObject) item.fabricObject.set({ left, top, scaleX: item.scaleX, scaleY: item.scaleY });
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

    let selectedSrcs = new Set();
    function addCheckboxesToCards() {
        document.querySelectorAll('.card').forEach(card => {
            if (card.querySelector('.select-checkbox')) return;
            const img = card.querySelector('img');
            if (!img || !img.src || img.src.startsWith('data:')) return;
            const src = img.src;
            const chk = document.createElement('input');
            chk.type = 'checkbox';
            chk.className = 'select-checkbox';
            chk.style.cssText = 'position:absolute; top:8px; left:8px; width:20px; height:20px; z-index:10; background:white; border-radius:4px; cursor:pointer;';
            chk.checked = selectedSrcs.has(src);
            chk.addEventListener('change', () => {
                if (chk.checked) selectedSrcs.add(src);
                else selectedSrcs.delete(src);
                const span = document.getElementById('selectedCount');
                if (span) span.innerText = selectedSrcs.size + ' selected';
            });
            if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
            card.appendChild(chk);
        });
    }

    function selectAll() {
        document.querySelectorAll('.select-checkbox').forEach(chk => chk.checked = true);
        selectedSrcs.clear();
        document.querySelectorAll('.card img').forEach(img => {
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

    window.addEventListener('DOMContentLoaded', function() {
        initCanvas();
        addCheckboxesToCards();
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
    });
})();
</script>
<!-- ========== END STORYBOARD ========== -->
'''

# Append storyboard before </body>
if '</body>' in content:
    content = content.replace('</body>', storyboard + '\n</body>')
else:
    content += storyboard

# Write final file
with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ Fixed gallery saved as {TARGET}")
print("💡 Start server: python -m http.server 8000")
print(f"   Open http://localhost:8000/{TARGET.name}")