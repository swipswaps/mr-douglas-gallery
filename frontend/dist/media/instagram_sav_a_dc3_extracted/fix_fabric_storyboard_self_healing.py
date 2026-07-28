#!/usr/bin/env python3
"""
Replace the storyboard with a self‑healing Fabric.js canvas that:
- Shows images correctly in a grid
- Logs errors to a visible panel
- Provides a "Heal" button to reinit canvas and reload images
- Works independently of main gallery scope
"""

import re
from pathlib import Path

INPUT_HTML = Path("index_final_with_authors.html")
OUTPUT_HTML = Path("index_final_self_healing.html")

if not INPUT_HTML.exists():
    print(f"Error: {INPUT_HTML} not found.")
    exit(1)

content = INPUT_HTML.read_text(encoding='utf-8')

# Remove any existing storyboard modal (same as before)
start_pattern = r'<div id="storyboardModal" class="storyboard-modal">'
start_match = re.search(start_pattern, content)
if start_match:
    start_pos = start_match.start()
    depth = 0
    i = start_pos
    while i < len(content):
        if content[i:i+4] == '<div':
            depth += 1
            i += 4
        elif content[i:i+6] == '</div>':
            depth -= 1
            i += 6
            if depth == 0:
                end_pos = i
                break
        else:
            i += 1
    else:
        print("Could not find end of storyboard modal, aborting.")
        exit(1)
    content = content[:start_pos] + content[end_pos:]

# New self‑healing storyboard HTML
new_storyboard = """
    <!-- ========== SELF‑HEALING STORYBOARD ========== -->
    <div id="storyboardModal" class="storyboard-modal">
        <div class="storyboard-container">
            <div style="display:flex; justify-content:space-between;">
                <h3 style="color:white;">📸 Storyboard Builder – 36×48" @ 300 DPI</h3>
                <button class="close-modal" id="closeStoryboardBtn">✖ Close</button>
            </div>
            <div class="storyboard-canvas-wrapper">
                <canvas id="storyboardCanvas" width="1080" height="1440"></canvas>
            </div>
            <div class="storyboard-controls">
                <button id="resetLayoutBtn" class="success">🔄 Reset Layout</button>
                <button id="exportStoryboardBtn" class="success">⬇ Export PNG (10800×14400)</button>
                <button id="clearStoryboardBtn" class="danger">🗑 Clear All</button>
                <button id="healStoryboardBtn" style="background:#f59e0b;">🔧 Heal</button>
            </div>
            <div><strong style="color:white;">📁 Images (click to remove):</strong>
                <div id="storyboardThumbnails" style="display:flex; gap:12px; overflow-x:auto; padding:8px;"></div>
            </div>
            <div id="storyboardErrorLog" style="background:#1e293b; border-radius:8px; padding:8px; margin-top:12px; max-height:100px; overflow-y:auto; font-family:monospace; font-size:12px; color:#f87171;"></div>
        </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
    <script>
    // ========== SELF‑HEALING FABRIC.JS STORYBOARD ==========
    (function() {
        // Internal state
        let canvas = null;
        let storyboardImages = [];      // each: { src, fabricObj }
        const STORAGE_KEY = "storyboard_images_srcs";
        const PREVIEW_W = 1080, PREVIEW_H = 1440;
        let errorLog = [];
        let logDiv = null;

        function addError(msg) {
            errorLog.unshift(`[${new Date().toLocaleTimeString()}] ${msg}`);
            if (logDiv) logDiv.innerHTML = errorLog.slice(0, 20).map(e => `<div>⚠️ ${e}</div>`).join('');
            console.error(msg);
        }

        function showToast(msg, dur=2000) {
            // Use global toast if available, else create fallback
            const toast = document.getElementById('toast');
            if (toast) {
                toast.textContent = msg;
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), dur);
            } else {
                alert(msg);
            }
        }

        function updateBadge() {
            const badge = document.getElementById('storyboardCountBadge');
            if (badge) badge.innerText = storyboardImages.length;
        }

        function saveToLocalStorage() {
            try {
                const srcs = storyboardImages.map(i => i.src);
                localStorage.setItem(STORAGE_KEY, JSON.stringify(srcs));
                addError("Saved to localStorage");
            } catch(e) { addError("localStorage save failed: " + e.message); }
        }

        async function loadFromLocalStorage() {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (!stored) return;
            try {
                const srcs = JSON.parse(stored);
                if (Array.isArray(srcs) && srcs.length) {
                    for (let src of srcs) {
                        if (!storyboardImages.some(i => i.src === src)) {
                            await addImageToStoryboard(src, true);
                        }
                    }
                    applyGridLayout();
                    addError(`Loaded ${storyboardImages.length} images from localStorage`);
                }
            } catch(e) { addError("localStorage load error: " + e.message); }
        }

        async function addImageToStoryboard(src, silent=false) {
            if (storyboardImages.some(i => i.src === src)) {
                if (!silent) showToast("Image already in storyboard");
                return false;
            }
            addError(`Attempting to add: ${src}`);
            return new Promise((resolve) => {
                fabric.Image.fromURL(src, (img) => {
                    if (!img) {
                        addError(`Failed to load image: ${src}`);
                        if (!silent) showToast("Failed to load image");
                        resolve(false);
                        return;
                    }
                    img.set({ crossOrigin: 'Anonymous', hasControls: true, hasBorders: true, lockRotation: true });
                    const maxDim = 200;
                    const scale = Math.min(maxDim / img.width, maxDim / img.height);
                    img.scale(scale);
                    img.set({ left: 20, top: 20 });
                    if (canvas) canvas.add(img);
                    storyboardImages.push({ src, fabricObj: img });
                    saveToLocalStorage();
                    updateBadge();
                    applyGridLayout();
                    updateThumbnails();
                    addError(`Added image: ${src}`);
                    resolve(true);
                }, { crossOrigin: 'Anonymous' });
            });
        }

        function applyGridLayout() {
            if (!canvas || storyboardImages.length === 0) return;
            addError("Applying grid layout");
            const margin = 20;
            const cols = 3;
            const availW = PREVIEW_W - margin * 2;
            const cellW = (availW - (cols - 1) * margin) / cols;
            let y = margin;
            for (let i = 0; i < storyboardImages.length; i++) {
                const obj = storyboardImages[i].fabricObj;
                const col = i % cols;
                if (col === 0 && i !== 0) {
                    const prevRowIdx = i - cols;
                    if (prevRowIdx >= 0) {
                        const prevObj = storyboardImages[prevRowIdx].fabricObj;
                        y += prevObj.height * prevObj.scaleY + margin;
                    } else {
                        y += 200 + margin;
                    }
                }
                const maxH = 200;
                let scale = Math.min(cellW / obj.width, maxH / obj.height);
                obj.scale(scale);
                const left = margin + col * (cellW + margin);
                obj.set({ left: left, top: y });
            }
            canvas.renderAll();
            saveToLocalStorage();
        }

        function resetLayout() { applyGridLayout(); }

        async function exportStoryboard() {
            if (storyboardImages.length === 0) { showToast("No images to export"); return; }
            addError("Exporting high-res PNG");
            const exportCanvas = new fabric.Canvas(null);
            exportCanvas.setDimensions({ width: 10800, height: 14400 });
            const scale = 10;
            for (let item of storyboardImages) {
                const obj = item.fabricObj;
                const clone = await new Promise(resolve => obj.clone(resolve));
                clone.set({ left: obj.left * scale, top: obj.top * scale, scaleX: obj.scaleX * scale, scaleY: obj.scaleY * scale });
                exportCanvas.add(clone);
            }
            exportCanvas.renderAll();
            const dataURL = exportCanvas.toDataURL({ format: 'png', multiplier: 1 });
            const a = document.createElement('a');
            a.download = 'storyboard_36x48_300dpi.png';
            a.href = dataURL;
            a.click();
            exportCanvas.dispose();
            addError("Export completed");
        }

        function clearAll() {
            if (confirm("Clear all images from storyboard?")) {
                storyboardImages.forEach(item => canvas.remove(item.fabricObj));
                storyboardImages = [];
                canvas.renderAll();
                updateThumbnails();
                localStorage.removeItem(STORAGE_KEY);
                updateBadge();
                addError("Storyboard cleared");
                showToast("Storyboard cleared");
            }
        }

        function updateThumbnails() {
            const container = document.getElementById('storyboardThumbnails');
            if (!container) return;
            container.innerHTML = storyboardImages.map((img, idx) => `
                <img class="storyboard-thumb" src="${img.src}" data-index="${idx}" style="width:80px; height:80px; object-fit:cover; border-radius:8px; cursor:pointer;">
            `).join('');
            document.querySelectorAll('.storyboard-thumb').forEach(thumb => {
                thumb.addEventListener('click', () => {
                    const idx = parseInt(thumb.dataset.index);
                    if (!isNaN(idx)) {
                        canvas.remove(storyboardImages[idx].fabricObj);
                        storyboardImages.splice(idx, 1);
                        canvas.renderAll();
                        updateThumbnails();
                        saveToLocalStorage();
                        updateBadge();
                        applyGridLayout();
                        showToast("Image removed");
                        addError(`Removed image index ${idx}`);
                    }
                });
            });
        }

        // Heal: reinitialize canvas and reload all images from storage
        async function healStoryboard() {
            addError("Healing storyboard...");
            if (canvas) canvas.dispose();
            canvas = new fabric.Canvas('storyboardCanvas');
            canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
            canvas.backgroundColor = 'white';
            canvas.renderAll();
            canvas.on('object:modified', () => saveToLocalStorage());
            // Reload all images from storyboardImages (preserve fabric objects)
            for (let item of storyboardImages) {
                const img = item.fabricObj;
                canvas.add(img);
            }
            canvas.renderAll();
            applyGridLayout();
            addError("Healing complete");
        }

        function initCanvas() {
            const canvasEl = document.getElementById('storyboardCanvas');
            if (!canvasEl) { addError("Canvas element not found"); return false; }
            if (canvas) canvas.dispose();
            canvas = new fabric.Canvas('storyboardCanvas');
            canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
            canvas.backgroundColor = 'white';
            canvas.renderAll();
            canvas.on('object:modified', () => saveToLocalStorage());
            addError("Canvas initialised");
            return true;
        }

        async function syncSelectedToStoryboard() {
            // We need to get selectedSrcs from the main gallery – it's a global variable
            if (typeof window.selectedSrcs === 'undefined') {
                addError("selectedSrcs not defined – cannot sync");
                showToast("Cannot sync: selection data not available");
                return;
            }
            const srcs = Array.from(window.selectedSrcs);
            if (srcs.length === 0) { showToast("No images selected"); return; }
            let added = 0;
            for (let src of srcs) {
                if (await addImageToStoryboard(src, true)) added++;
            }
            if (added) showToast(`Added ${added} new image(s)`);
            else showToast("All selected already in storyboard");
            addError(`Sync added ${added} images`);
        }

        // Expose globally for checkbox auto-add
        window.addImageToStoryboard = addImageToStoryboard;
        window.syncSelectedToStoryboard = syncSelectedToStoryboard;

        // Setup event listeners and initialisation when DOM ready
        document.addEventListener('DOMContentLoaded', async () => {
            logDiv = document.getElementById('storyboardErrorLog');
            addError("Storyboard initialising");
            initCanvas();
            await loadFromLocalStorage();
            updateThumbnails();
            applyGridLayout();
            document.getElementById('resetLayoutBtn')?.addEventListener('click', resetLayout);
            document.getElementById('exportStoryboardBtn')?.addEventListener('click', exportStoryboard);
            document.getElementById('clearStoryboardBtn')?.addEventListener('click', clearAll);
            document.getElementById('healStoryboardBtn')?.addEventListener('click', healStoryboard);
            document.getElementById('closeStoryboardBtn')?.addEventListener('click', () => {
                document.getElementById('storyboardModal').classList.remove('active');
            });
            // Override global sync button (original one may exist)
            const syncBtn = document.getElementById('syncSelectedBtn');
            if (syncBtn) syncBtn.onclick = syncSelectedToStoryboard;
            window.addMultipleImages = (srcList) => { srcList.forEach(src => addImageToStoryboard(src, true)); };
            addError("Storyboard ready");
        });
    })();
    </script>
    <!-- ========== END SELF‑HEALING STORYBOARD ========== 
"""

# Insert new storyboard before the lightbox div
lightbox_start = content.find('<div id="lightbox" class="lightbox">')
if lightbox_start == -1:
    content = content.replace('</body>', new_storyboard + '\n</body>')
else:
    content = content[:lightbox_start] + new_storyboard + '\n' + content[lightbox_start:]

# Ensure the storyboard badge exists on the open button
if '<span id="storyboardCountBadge"' not in content:
    content = content.replace(
        '<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal)',
        '<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal) <span id="storyboardCountBadge" style="background:#ef4444; border-radius:20px; padding:2px 8px; margin-left:8px; font-size:0.7rem;">0</span>'
    )

OUTPUT_HTML.write_text(content, encoding='utf-8')
print(f"✅ Self‑healing storyboard written to {OUTPUT_HTML}")
print("   Open that file, select images, and open the storyboard.")
print("   Any errors will appear in the red log panel. Use the 'Heal' button if needed.")