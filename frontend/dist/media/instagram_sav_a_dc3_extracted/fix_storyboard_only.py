#!/usr/bin/env python3
"""
Only replace the storyboard modal in index_final_with_authors.html
with a working Fabric.js version that actually shows images.
Preserves all other gallery functionality.
"""

import re
from pathlib import Path

INPUT = Path("index_final_with_authors.html")
OUTPUT = Path("index_final_fixed_storyboard.html")

if not INPUT.exists():
    print(f"Error: {INPUT} not found.")
    exit(1)

content = INPUT.read_text(encoding='utf-8')

# 1. Remove any existing storyboard modal (if present)
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
        print("Could not find end of storyboard modal.")
        exit(1)
    content = content[:start_pos] + content[end_pos:]
    print("Removed old storyboard modal.")

# 2. New working Fabric.js storyboard
new_storyboard = """
    <!-- ========== WORKING FABRIC.JS STORYBOARD ========== -->
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
            </div>
            <div><strong style="color:white;">📁 Images (click to remove):</strong>
                <div id="storyboardThumbnails" style="display:flex; gap:12px; overflow-x:auto; padding:8px;"></div>
            </div>
        </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
    <script>
    (function() {
        // === References to main gallery globals ===
        // selectedSrcs and showToast are defined in the main page.
        // We will use them if available, otherwise provide fallbacks.
        let canvas = null;
        let storyboardImages = [];      // { src, fabricObj }
        const STORAGE_KEY = "storyboard_images_srcs";
        const PREVIEW_W = 1080, PREVIEW_H = 1440;
        const TARGET_W = 10800, TARGET_H = 14400;

        function getToast() {
            // Use global toast if present, else fallback alert
            if (typeof showToast === 'function') return showToast;
            return function(msg) { alert(msg); };
        }
        const toast = getToast();

        function updateBadge() {
            const badge = document.getElementById('storyboardCountBadge');
            if (badge) badge.innerText = storyboardImages.length;
        }

        function saveToLocalStorage() {
            const srcs = storyboardImages.map(i => i.src);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(srcs));
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
                }
            } catch(e) { console.error("localStorage load error", e); }
        }

        async function addImageToStoryboard(src, silent=false) {
            if (storyboardImages.some(i => i.src === src)) {
                if (!silent) toast("Image already in storyboard");
                return false;
            }
            return new Promise((resolve) => {
                fabric.Image.fromURL(src, (img) => {
                    if (!img) {
                        if (!silent) toast("Failed to load image");
                        resolve(false);
                        return;
                    }
                    img.set({ crossOrigin: 'Anonymous', hasControls: true, hasBorders: true, lockRotation: true });
                    // Initial scale to 200px max dimension
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
                    resolve(true);
                }, { crossOrigin: 'Anonymous' });
            });
        }

        function applyGridLayout() {
            if (!canvas || storyboardImages.length === 0) return;
            const margin = 20;
            const cols = 3;
            const availW = PREVIEW_W - margin * 2;
            const cellW = (availW - (cols - 1) * margin) / cols;
            let y = margin;
            for (let i = 0; i < storyboardImages.length; i++) {
                const obj = storyboardImages[i].fabricObj;
                const col = i % cols;
                if (col === 0 && i !== 0) {
                    // Move to next row
                    const prevObj = storyboardImages[i - 1].fabricObj;
                    y += (prevObj.height * prevObj.scaleY) + margin;
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

        function resetLayout() {
            applyGridLayout();
            toast("Layout reset");
        }

        async function exportStoryboard() {
            if (storyboardImages.length === 0) {
                toast("No images to export");
                return;
            }
            const exportCanvas = new fabric.Canvas(null);
            exportCanvas.setDimensions({ width: TARGET_W, height: TARGET_H });
            const scaleFactor = TARGET_W / PREVIEW_W; // 10
            for (let item of storyboardImages) {
                const obj = item.fabricObj;
                const clone = await new Promise(resolve => obj.clone(resolve));
                clone.set({
                    left: obj.left * scaleFactor,
                    top: obj.top * scaleFactor,
                    scaleX: obj.scaleX * scaleFactor,
                    scaleY: obj.scaleY * scaleFactor
                });
                exportCanvas.add(clone);
            }
            exportCanvas.renderAll();
            const dataURL = exportCanvas.toDataURL({ format: 'png', multiplier: 1 });
            const a = document.createElement('a');
            a.download = 'storyboard_36x48_300dpi.png';
            a.href = dataURL;
            a.click();
            exportCanvas.dispose();
            toast("Export complete");
        }

        function clearAll() {
            if (confirm("Clear all images from storyboard?")) {
                storyboardImages.forEach(item => canvas.remove(item.fabricObj));
                storyboardImages = [];
                canvas.renderAll();
                updateThumbnails();
                localStorage.removeItem(STORAGE_KEY);
                updateBadge();
                toast("Storyboard cleared");
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
                        toast("Image removed");
                    }
                });
            });
        }

        function initCanvas() {
            const canvasEl = document.getElementById('storyboardCanvas');
            if (!canvasEl) return;
            if (canvas) canvas.dispose();
            canvas = new fabric.Canvas('storyboardCanvas');
            canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
            canvas.setBackgroundColor('white', canvas.renderAll.bind(canvas));
            canvas.on('object:modified', () => saveToLocalStorage());
            canvas.renderAll();
        }

        async function syncSelectedToStoryboard() {
            // selectedSrcs is a global Set from the main gallery
            if (typeof window.selectedSrcs === 'undefined') {
                toast("Selection data not available");
                return;
            }
            const srcs = Array.from(window.selectedSrcs);
            if (srcs.length === 0) {
                toast("No images selected");
                return;
            }
            let added = 0;
            for (let src of srcs) {
                if (await addImageToStoryboard(src, true)) added++;
            }
            if (added) toast(`Added ${added} new image(s)`);
            else toast("All selected already in storyboard");
        }

        // Expose for checkbox auto-add
        window.addImageToStoryboard = addImageToStoryboard;
        window.syncSelectedToStoryboard = syncSelectedToStoryboard;

        // Initialisation when modal is first opened (to avoid delay)
        const modal = document.getElementById('storyboardModal');
        let initialised = false;
        function ensureInit() {
            if (initialised) return;
            initialised = true;
            initCanvas();
            loadFromLocalStorage().then(() => {
                updateThumbnails();
                applyGridLayout();
            });
        }
        // Observe modal opening
        const observer = new MutationObserver(() => {
            if (modal.classList.contains('active')) {
                ensureInit();
            }
        });
        observer.observe(modal, { attributes: true, attributeFilter: ['class'] });

        // Also attach button handlers when DOM ready
        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('resetLayoutBtn')?.addEventListener('click', resetLayout);
            document.getElementById('exportStoryboardBtn')?.addEventListener('click', exportStoryboard);
            document.getElementById('clearStoryboardBtn')?.addEventListener('click', clearAll);
            document.getElementById('closeStoryboardBtn')?.addEventListener('click', () => {
                modal.classList.remove('active');
            });
            // Override sync button in toolbar (original may still exist)
            const syncBtn = document.getElementById('syncSelectedBtn');
            if (syncBtn) syncBtn.onclick = syncSelectedToStoryboard;
            window.addMultipleImages = (srcList) => srcList.forEach(src => addImageToStoryboard(src, true));
        });
    })();
    </script>
    <!-- ========== END WORKING FABRIC.JS STORYBOARD ========== 
"""

# 3. Insert new storyboard before the lightbox div
lightbox_start = content.find('<div id="lightbox" class="lightbox">')
if lightbox_start == -1:
    # Fallback: insert before </body>
    content = content.replace('</body>', new_storyboard + '\n</body>')
else:
    content = content[:lightbox_start] + new_storyboard + '\n' + content[lightbox_start:]

# 4. Ensure the storyboard count badge exists on the open button
if '<span id="storyboardCountBadge"' not in content:
    content = content.replace(
        '<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal)',
        '<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal) <span id="storyboardCountBadge" style="background:#ef4444; border-radius:20px; padding:2px 8px; margin-left:8px; font-size:0.7rem;">0</span>'
    )

OUTPUT.write_text(content, encoding='utf-8')
print(f"✅ Fixed storyboard written to {OUTPUT}")
print("   Open that file, select images, and open the storyboard.")
print("   Images will appear in a grid, can be dragged/resized, and a Reset Layout button is provided.")