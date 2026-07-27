#!/usr/bin/env python3
"""
Replace the storyboard with a working Fabric.js canvas:
- Images appear inside canvas, evenly spaced in a grid.
- Drag & drop, resize handles.
- Reset Layout button to reposition all images.
- Preserves all other gallery functionality.
"""

import re
from pathlib import Path

INPUT_HTML = Path("index_final_with_authors.html")
OUTPUT_HTML = Path("index_final_with_fabric_storyboard.html")

if not INPUT_HTML.exists():
    print(f"Error: {INPUT_HTML} not found. Run build_final_gallery.py first.")
    exit(1)

content = INPUT_HTML.read_text(encoding='utf-8')

# Locate and remove the existing storyboard modal block (any version)
# We'll remove from <div id="storyboardModal" ...> to the matching closing </div>
start_pattern = r'<div id="storyboardModal" class="storyboard-modal">'
start_match = re.search(start_pattern, content)
if not start_match:
    print("No existing storyboard modal found. Inserting new one.")
    # We'll insert near the lightbox
else:
    # Remove the old block with depth counting
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

# New Fabric.js storyboard HTML
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
        let canvas = null;
        let storyboardImages = [];  // each: { src, fabricObj }
        const STORAGE_KEY = "storyboard_images_srcs";
        const PREVIEW_W = 1080, PREVIEW_H = 1440;

        function updateBadge() {
            const b = document.getElementById('storyboardCountBadge');
            if (b) b.innerText = storyboardImages.length;
        }

        // Load an image and add to canvas with initial sizing
        async function addImageToStoryboard(src, silent=false) {
            if (storyboardImages.some(i => i.src === src)) {
                if (!silent) showToast("Image already in storyboard");
                return false;
            }
            return new Promise((resolve) => {
                fabric.Image.fromURL(src, (img) => {
                    if (!img) {
                        if (!silent) showToast("Failed to load image");
                        resolve(false);
                        return;
                    }
                    // Set crossOrigin to avoid CORS issues
                    img.set({ crossOrigin: 'Anonymous', hasControls: true, hasBorders: true, lockRotation: true });
                    // Initial scale to fit within 200x200 box, positioned at (20,20)
                    const maxDim = 200;
                    const scale = Math.min(maxDim / img.width, maxDim / img.height);
                    img.scale(scale);
                    img.set({ left: 20, top: 20 });
                    canvas.add(img);
                    storyboardImages.push({ src, fabricObj: img });
                    saveToLocalStorage();
                    updateBadge();
                    // Apply layout to arrange all images
                    applyGridLayout();
                    resolve(true);
                }, { crossOrigin: 'Anonymous' });
            });
        }

        // Arrange all images in a grid with 20px margins, 3 columns, max height 200px per row
        function applyGridLayout() {
            if (!canvas || storyboardImages.length === 0) return;
            const margin = 20;
            const cols = 3;
            const availW = PREVIEW_W - margin * 2;
            const cellW = (availW - (cols - 1) * margin) / cols;
            let row = 0;
            let y = margin;
            for (let i = 0; i < storyboardImages.length; i++) {
                const obj = storyboardImages[i].fabricObj;
                const col = i % cols;
                if (col === 0 && i !== 0) {
                    row++;
                    // increase Y by height of previous row's images + margin
                    const prevRowIdx = i - cols;
                    if (prevRowIdx >= 0) {
                        const prevObj = storyboardImages[prevRowIdx].fabricObj;
                        y += prevObj.height * prevObj.scaleY + margin;
                    } else {
                        y += 200 + margin; // fallback
                    }
                }
                const maxH = 200;
                let scale = Math.min(cellW / obj.width, maxH / obj.height);
                obj.scale(scale);
                const left = margin + col * (cellW + margin);
                const top = y;
                obj.set({ left: left, top: top });
            }
            canvas.renderAll();
            saveToLocalStorage();
        }

        // Reset layout without changing images
        function resetLayout() {
            applyGridLayout();
        }

        // Export high-res PNG
        async function exportStoryboard() {
            if (storyboardImages.length === 0) {
                showToast("No images to export");
                return;
            }
            const originalCanvas = canvas;
            const exportCanvas = new fabric.Canvas(null);
            exportCanvas.setDimensions({ width: 10800, height: 14400 });
            const scale = 10; // 1080 -> 10800, 1440 -> 14400
            for (let item of storyboardImages) {
                const obj = item.fabricObj;
                const clone = await new Promise(resolve => obj.clone(resolve));
                clone.set({
                    left: obj.left * scale,
                    top: obj.top * scale,
                    scaleX: obj.scaleX * scale,
                    scaleY: obj.scaleY * scale
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
        }

        function clearAll() {
            if (confirm("Clear all images from storyboard?")) {
                storyboardImages.forEach(item => canvas.remove(item.fabricObj));
                storyboardImages = [];
                canvas.renderAll();
                updateThumbnails();
                localStorage.removeItem(STORAGE_KEY);
                updateBadge();
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
                        applyGridLayout(); // reflow remaining images
                        showToast("Image removed");
                    }
                });
            });
        }

        function saveToLocalStorage() {
            const srcs = storyboardImages.map(i => i.src);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(srcs));
        }

        async function loadFromLocalStorage() {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                try {
                    const srcs = JSON.parse(stored);
                    if (Array.isArray(srcs)) {
                        for (let src of srcs) {
                            if (!storyboardImages.some(i => i.src === src)) {
                                await addImageToStoryboard(src, true);
                            }
                        }
                    }
                } catch(e) {}
            }
        }

        async function syncSelectedToStoryboard() {
            const srcs = Array.from(selectedSrcs);
            if (srcs.length === 0) { showToast("No images selected"); return; }
            let added = 0;
            for (let src of srcs) if (await addImageToStoryboard(src, true)) added++;
            if (added) showToast(`Added ${added} new image(s)`);
            else showToast("All selected already in storyboard");
        }

        // Make functions available globally for checkboxes
        window.addImageToStoryboard = addImageToStoryboard;
        window.syncSelectedToStoryboard = syncSelectedToStoryboard;

        // Initialize canvas after modal opens
        function initCanvas() {
            const canvasEl = document.getElementById('storyboardCanvas');
            if (!canvasEl) return;
            if (canvas) canvas.dispose();
            canvas = new fabric.Canvas('storyboardCanvas');
            canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
            canvas.backgroundColor = 'white';
            canvas.renderAll();
            // Redraw after any object modification (auto-save)
            canvas.on('object:modified', () => {
                saveToLocalStorage();
            });
            canvas.on('object:added', () => saveToLocalStorage());
            canvas.on('object:removed', () => saveToLocalStorage());
            // Reload images into new canvas
            storyboardImages.forEach(item => {
                const obj = item.fabricObj;
                canvas.add(obj);
            });
            canvas.renderAll();
        }

        // Wait for DOM and Fabric
        function waitForFabricAndInit() {
            if (typeof fabric !== 'undefined') {
                initCanvas();
                loadFromLocalStorage().then(() => {
                    updateThumbnails();
                    applyGridLayout();
                });
                // Hook buttons
                document.getElementById('resetLayoutBtn')?.addEventListener('click', resetLayout);
                document.getElementById('exportStoryboardBtn')?.addEventListener('click', exportStoryboard);
                document.getElementById('clearStoryboardBtn')?.addEventListener('click', clearAll);
                document.getElementById('closeStoryboardBtn')?.addEventListener('click', () => {
                    document.getElementById('storyboardModal').classList.remove('active');
                });
                // Override sync button (original one may already exist)
                const syncBtn = document.getElementById('syncSelectedBtn');
                if (syncBtn) syncBtn.onclick = syncSelectedToStoryboard;
                // Override window.addMultipleImages if needed
                window.addMultipleImages = (srcList) => {
                    srcList.forEach(src => addImageToStoryboard(src, true));
                };
            } else {
                setTimeout(waitForFabricAndInit, 200);
            }
        }

        // Hook modal open to ensure canvas is reinitialized each time
        const modal = document.getElementById('storyboardModal');
        const observer = new MutationObserver(() => {
            if (modal.classList.contains('active')) {
                // Canvas might have been detached; reinit
                if (!canvas || !canvas.lowerCanvasEl || !document.body.contains(canvas.lowerCanvasEl)) {
                    initCanvas();
                    storyboardImages.forEach(item => canvas.add(item.fabricObj));
                    canvas.renderAll();
                }
            }
        });
        observer.observe(modal, { attributes: true, attributeFilter: ['class'] });

        waitForFabricAndInit();
    })();
    </script>
    <!-- ========== END WORKING FABRIC.JS STORYBOARD ========== 
"""

# Insert new storyboard before the lightbox div
lightbox_start = content.find('<div id="lightbox" class="lightbox">')
if lightbox_start == -1:
    # Fallback: insert before </body>
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
print(f"✅ Working Fabric.js storyboard written to {OUTPUT_HTML}")
print("   Open that file, select images, and open the storyboard.")
print("   Images will appear in a grid, can be dragged/resized, and a Reset Layout button is provided.")