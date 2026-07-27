#!/usr/bin/env python3
"""
Ultimate storyboard fix:
- Multi-select in gallery
- Batch add to canvas
- Auto-grid arrangement
- Each image retains original resolution for 300 DPI export
"""

import re
from pathlib import Path

HTML_PATH = Path("index_cloud.html")
BACKUP_PATH = Path("index_cloud_ultimate_backup.html")

# The complete, corrected storyboard with multi-select and auto-grid
ULTIMATE_STORYBOARD = """
<!-- ========== ULTIMATE STORYBOARD ========== -->
<style>
.storyboard-btn{position:fixed;bottom:20px;right:20px;background:#3b82f6;color:white;border:none;border-radius:50px;padding:12px 24px;font-size:1rem;font-weight:bold;cursor:pointer;z-index:1000;box-shadow:0 4px 12px rgba(0,0,0,0.3);}
.storyboard-btn:hover{background:#2563eb;}

/* Multi-select toolbar */
.gallery-toolbar{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;align-items:center;background:#f1f5f9;padding:8px 12px;border-radius:12px;}
.gallery-toolbar button{background:#334155;color:white;border:none;padding:6px 12px;border-radius:8px;cursor:pointer;font-size:0.8rem;}
.gallery-toolbar button.primary{background:#3b82f6;}
.gallery-toolbar button.danger{background:#ef4444;}
.select-checkbox{position:absolute;top:8px;left:8px;width:20px;height:20px;cursor:pointer;z-index:5;background:white;border-radius:4px;border:1px solid #cbd5e1;}

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

<!-- Gallery toolbar for multi-select -->
<div class="gallery-toolbar">
    <span style="font-weight:bold;">📌 Select images:</span>
    <button id="selectAllBtn">Select All</button>
    <button id="deselectAllBtn">Deselect All</button>
    <button id="addSelectedBtn" class="primary">➕ Add Selected to Storyboard</button>
    <span style="font-size:0.8rem;color:#475569;" id="selectedCount">0 selected</span>
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
            <button id="autoGridBtn" class="success">📐 Auto-arrange Grid</button>
            <button id="exportStoryboardBtn" class="success">⬇ Export PNG (10800×14400) – 300 DPI</button>
            <button id="clearStoryboardBtn" class="danger">🗑 Clear All</button>
        </div>
        <div class="storyboard-image-list">
            <strong style="color:white;">📁 Images in storyboard (click to remove):</strong>
            <div class="storyboard-thumbnails" id="storyboardThumbnails"></div>
        </div>
    </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
<script>
(function() {
    // === Global storyboard state ===
    window.storyboardImages = [];    // each: { src, imgElement, fabricObject, left, top, scaleX, scaleY, width, height }
    window.displayCanvas = null;
    const targetW = 10800, targetH = 14400;
    const previewW = 1080, previewH = 1440;
    const scaleFactor = targetW / previewW;  // 10

    // Helper: load image once (cached)
    const imageCache = new Map();
    function loadImage(src) {
        if (imageCache.has(src)) return Promise.resolve(imageCache.get(src));
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = "Anonymous";
            img.onload = () => {
                imageCache.set(src, img);
                resolve(img);
            };
            img.onerror = reject;
            img.src = src;
        });
    }

    // Add a single image to storyboard (core function)
    window.addImageToStoryboard = async function(src, silent = false) {
        if (window.storyboardImages.some(i => i.src === src)) {
            if (!silent) alert("Image already in storyboard");
            return false;
        }
        try {
            const imgEl = await loadImage(src);
            // Default size: 200px width on preview canvas
            const aspect = imgEl.width / imgEl.height;
            const previewWidth = 200;
            const previewHeight = previewWidth / aspect;
            const scaleX = previewWidth / imgEl.width;
            const scaleY = previewHeight / imgEl.height;

            const newItem = {
                src: src,
                imgElement: imgEl,
                width: imgEl.width,
                height: imgEl.height,
                left: 50,
                top: 50,
                scaleX: scaleX,
                scaleY: scaleY,
                fabricObject: null
            };
            window.storyboardImages.push(newItem);
            if (window.displayCanvas) {
                const fabricImg = new fabric.Image(imgEl, {
                    left: 50, top: 50,
                    scaleX: scaleX, scaleY: scaleY,
                    hasControls: true, hasBorders: true, lockRotation: true
                });
                newItem.fabricObject = fabricImg;
                window.displayCanvas.add(fabricImg);
                window.displayCanvas.renderAll();
            }
            updateThumbnails();
            return true;
        } catch(e) {
            if (!silent) alert("Failed to load image: " + e.message);
            return false;
        }
    };

    // Add multiple images (batch)
    window.addMultipleImagesToStoryboard = async function(srcList) {
        let added = 0;
        for (let src of srcList) {
            const success = await window.addImageToStoryboard(src, true);
            if (success) added++;
        }
        if (added > 0) {
            alert(`Added ${added} image(s) to storyboard`);
            updateThumbnails();
            // Auto-arrange after batch add (optional)
            if (window.storyboardImages.length > 0) autoArrange();
        } else {
            alert("No new images added (duplicates or errors)");
        }
    };

    // Auto-arrange images in a grid (columns = 3)
    function autoArrange() {
        if (!window.displayCanvas || window.storyboardImages.length === 0) return;
        const cols = 3;
        const margin = 20;
        const availableWidth = previewW - margin * 2;
        const cellWidth = (availableWidth - (cols-1)*margin) / cols;
        let row = 0, col = 0;
        for (let i = 0; i < window.storyboardImages.length; i++) {
            const item = window.storyboardImages[i];
            const img = item.imgElement;
            const aspect = img.width / img.height;
            let drawWidth = cellWidth;
            let drawHeight = drawWidth / aspect;
            if (drawHeight > cellWidth * 0.8) { // constrain height
                drawHeight = cellWidth * 0.8;
                drawWidth = drawHeight * aspect;
            }
            const left = margin + col * (cellWidth + margin);
            const top = margin + row * (cellWidth + margin);
            const scaleX = drawWidth / img.width;
            const scaleY = drawHeight / img.height;
            if (item.fabricObject) {
                item.fabricObject.set({ left: left, top: top, scaleX: scaleX, scaleY: scaleY });
            } else {
                // recreate if missing (should not happen)
                const fabricImg = new fabric.Image(img, { left: left, top: top, scaleX: scaleX, scaleY: scaleY, hasControls: true, lockRotation: true });
                item.fabricObject = fabricImg;
                window.displayCanvas.add(fabricImg);
            }
            item.left = left;
            item.top = top;
            item.scaleX = scaleX;
            item.scaleY = scaleY;
            col++;
            if (col >= cols) { col = 0; row++; }
        }
        window.displayCanvas.renderAll();
    }

    // Update thumbnail strip at bottom
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

    // Export high-res PNG
    window.exportStoryboard = async function() {
        if (window.storyboardImages.length === 0) {
            alert("No images in storyboard");
            return;
        }
        const offCanvas = document.createElement('canvas');
        offCanvas.width = targetW;
        offCanvas.height = targetH;
        const ctx = offCanvas.getContext('2d');
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
            } catch(e) { console.warn(e); }
        }
        const link = document.createElement('a');
        link.download = 'storyboard_36x48_300dpi.png';
        link.href = offCanvas.toDataURL('image/png');
        link.click();
    };

    function clearStoryboard() {
        if (confirm("Remove all images?")) {
            window.storyboardImages = [];
            if (window.displayCanvas) {
                window.displayCanvas.clear();
                window.displayCanvas.renderAll();
            }
            updateThumbnails();
        }
    }

    // Initialize canvas and UI
    function initStoryboard() {
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

        document.getElementById('openStoryboardBtn').onclick = () => document.getElementById('storyboardModal').classList.add('active');
        document.getElementById('closeStoryboardBtn').onclick = () => document.getElementById('storyboardModal').classList.remove('active');
        document.getElementById('exportStoryboardBtn').onclick = () => window.exportStoryboard();
        document.getElementById('clearStoryboardBtn').onclick = clearStoryboard;
        document.getElementById('autoGridBtn').onclick = () => autoArrange();
        window.onclick = (e) => { if (e.target === document.getElementById('storyboardModal')) document.getElementById('storyboardModal').classList.remove('active'); };
    }

    // === Multi-select gallery integration ===
    let selectedImages = new Set(); // store image src

    function addCheckboxesToCards() {
        document.querySelectorAll('.card, .timeline-card').forEach(card => {
            if (card.querySelector('.select-checkbox')) return;
            const img = card.querySelector('img');
            if (!img || !img.src || img.src.startsWith('data:')) return;
            const chk = document.createElement('input');
            chk.type = 'checkbox';
            chk.className = 'select-checkbox';
            chk.checked = selectedImages.has(img.src);
            chk.addEventListener('change', (e) => {
                e.stopPropagation();
                if (chk.checked) selectedImages.add(img.src);
                else selectedImages.delete(img.src);
                updateSelectedCount();
            });
            card.style.position = 'relative';
            card.appendChild(chk);
        });
    }

    function updateSelectedCount() {
        const span = document.getElementById('selectedCount');
        if (span) span.innerText = `${selectedImages.size} selected`;
    }

    function selectAll() {
        document.querySelectorAll('.select-checkbox').forEach(chk => {
            chk.checked = true;
            const card = chk.closest('.card, .timeline-card');
            const img = card?.querySelector('img');
            if (img && img.src) selectedImages.add(img.src);
        });
        updateSelectedCount();
    }

    function deselectAll() {
        document.querySelectorAll('.select-checkbox').forEach(chk => {
            chk.checked = false;
        });
        selectedImages.clear();
        updateSelectedCount();
    }

    function addSelectedToStoryboard() {
        const srcs = Array.from(selectedImages);
        if (srcs.length === 0) {
            alert("No images selected");
            return;
        }
        window.addMultipleImagesToStoryboard(srcs);
    }

    // Watch for dynamically added cards
    function observeGallery() {
        const gallery = document.getElementById('galleryGrid');
        if (!gallery) return;
        const observer = new MutationObserver(() => addCheckboxesToCards());
        observer.observe(gallery, { childList: true, subtree: true });
        addCheckboxesToCards();
    }

    // ========== MAIN ==========
    let ready = setInterval(() => {
        if (typeof fabric !== 'undefined') {
            clearInterval(ready);
            initStoryboard();
            observeGallery();

            // Attach toolbar buttons
            const selAll = document.getElementById('selectAllBtn');
            const deselAll = document.getElementById('deselectAllBtn');
            const addSel = document.getElementById('addSelectedBtn');
            if (selAll) selAll.onclick = selectAll;
            if (deselAll) deselAll.onclick = deselectAll;
            if (addSel) addSel.onclick = addSelectedToStoryboard;
        }
    }, 200);
})();
</script>
<!-- ========== END ULTIMATE STORYBOARD ========== -->
"""

def apply_ultimate():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Backup
    with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    # Remove any existing storyboard block (matches any from previous versions)
    pattern = r'<!-- ========== STORYBOARD BUILDER.*?<!-- ========== END STORYBOARD ========== -->'
    content = re.sub(pattern, ULTIMATE_STORYBOARD, content, flags=re.DOTALL)

    # Ensure timeline images are prefixed correctly (already fixed in earlier script, but do it again)
    content = re.sub(r'(<img[^>]*src=")(?!timeline/)([^"]+\.jpg)"', r'\1timeline/\2"', content)

    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ Ultimate storyboard applied.")
    print("📁 Backup saved as", BACKUP_PATH)
    print("💡 Hard refresh (Ctrl+Shift+R) then look for checkboxes on each gallery image.")

if __name__ == "__main__":
    apply_ultimate()