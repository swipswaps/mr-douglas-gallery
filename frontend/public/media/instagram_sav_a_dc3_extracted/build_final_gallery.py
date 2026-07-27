#!/usr/bin/env python3
"""
Replace the broken Fabric.js storyboard with a stable HTML/CSS grid + SortableJS + html2canvas.
Reads the existing index_final_with_authors.html (which already has authors and no timeline)
and rewrites the storyboard modal content.
"""

import re
from pathlib import Path

INPUT_HTML = Path("index_final_with_authors.html")
OUTPUT_HTML = Path("index_final_with_fixed_storyboard.html")

if not INPUT_HTML.exists():
    print(f"Error: {INPUT_HTML} not found. Run build_final_gallery.py first.")
    exit(1)

content = INPUT_HTML.read_text(encoding='utf-8')

# Remove old storyboard modal block (non‑greedy)
content = re.sub(
    r'<div id="storyboardModal" class="storyboard-modal">.*?</div>\s*</div>\s*</div>',
    '',
    content,
    flags=re.DOTALL
)

# New storyboard HTML – using double quotes for Python string to avoid escape issues
new_storyboard = """
    <!-- ========== FIXED STORYBOARD (HTML grid + Sortable + html2canvas) ========== -->
    <div id="storyboardModal" class="storyboard-modal">
        <div class="storyboard-container">
            <div style="display:flex; justify-content:space-between;">
                <h3 style="color:white;">📸 Storyboard Builder – 36×48" @ 300 DPI</h3>
                <button class="close-modal" id="closeStoryboardBtn">✖ Close</button>
            </div>
            <div style="background:#0f172a; border-radius:12px; padding:12px; margin-bottom:12px;">
                <div id="storyboardGrid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); gap:12px; background:#1e293b; padding:20px; border-radius:12px; min-height:200px;"></div>
            </div>
            <div class="storyboard-controls">
                <button id="exportStoryboardBtn" class="success">⬇ Export PNG (10800×14400)</button>
                <button id="clearStoryboardBtn" class="danger">🗑 Clear All</button>
            </div>
            <div><strong style="color:white;">📁 Images in storyboard (drag to reorder):</strong>
                <div id="storyboardThumbnails" style="display:flex; gap:12px; overflow-x:auto; padding:8px;"></div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <script>
    (function() {
        let storyboardImages = [];
        const STORAGE_KEY = "storyboard_images_srcs";
        let gridContainer = document.getElementById('storyboardGrid');
        let thumbContainer = document.getElementById('storyboardThumbnails');
        let sortableGrid = null;
        let sortableThumbs = null;

        function updateBadge() {
            const badge = document.getElementById('storyboardCountBadge');
            if (badge) badge.innerText = storyboardImages.length;
        }

        function renderGridAndThumbs() {
            if (!gridContainer || !thumbContainer) return;
            gridContainer.innerHTML = storyboardImages.map((img, idx) => `
                <div data-id="${idx}" style="position:relative; background:#0f172a; border-radius:8px; overflow:hidden; cursor:grab;">
                    <img src="${img.src}" style="width:100%; aspect-ratio:4/3; object-fit:cover; display:block;">
                    <div style="position:absolute; top:4px; right:4px; background:rgba(0,0,0,0.6); border-radius:50%; width:24px; height:24px; display:flex; align-items:center; justify-content:center; cursor:pointer; font-size:16px; color:white;" class="remove-grid-item" data-idx="${idx}">×</div>
                </div>
            `).join('');
            thumbContainer.innerHTML = storyboardImages.map((img, idx) => `
                <div data-id="${idx}" style="position:relative; width:80px; flex-shrink:0; cursor:grab;">
                    <img src="${img.src}" style="width:100%; aspect-ratio:1; object-fit:cover; border-radius:8px;">
                    <div style="position:absolute; top:2px; right:2px; background:rgba(0,0,0,0.6); border-radius:50%; width:20px; height:20px; display:flex; align-items:center; justify-content:center; cursor:pointer; font-size:14px; color:white;" class="remove-thumb" data-idx="${idx}">×</div>
                </div>
            `).join('');

            document.querySelectorAll('.remove-grid-item').forEach(el => {
                el.removeEventListener('click', removeHandlerGrid);
                el.addEventListener('click', removeHandlerGrid);
            });
            document.querySelectorAll('.remove-thumb').forEach(el => {
                el.removeEventListener('click', removeHandlerThumb);
                el.addEventListener('click', removeHandlerThumb);
            });

            if (sortableGrid) sortableGrid.destroy();
            if (sortableThumbs) sortableThumbs.destroy();
            sortableGrid = new Sortable(gridContainer, {
                animation: 150,
                onEnd: function() {
                    const newOrder = [];
                    document.querySelectorAll('#storyboardGrid > div').forEach(div => {
                        const idx = parseInt(div.dataset.id);
                        if (!isNaN(idx)) newOrder.push(storyboardImages[idx]);
                    });
                    storyboardImages = newOrder;
                    saveToLocalStorage();
                    renderGridAndThumbs();
                }
            });
            sortableThumbs = new Sortable(thumbContainer, {
                animation: 150,
                onEnd: function() {
                    const newOrder = [];
                    document.querySelectorAll('#storyboardThumbnails > div').forEach(div => {
                        const idx = parseInt(div.dataset.id);
                        if (!isNaN(idx)) newOrder.push(storyboardImages[idx]);
                    });
                    storyboardImages = newOrder;
                    saveToLocalStorage();
                    renderGridAndThumbs();
                }
            });
        }

        function removeHandlerGrid(e) {
            e.stopPropagation();
            const idx = parseInt(e.currentTarget.dataset.idx);
            if (!isNaN(idx)) {
                storyboardImages.splice(idx, 1);
                saveToLocalStorage();
                renderGridAndThumbs();
                updateBadge();
                showToast("Image removed");
            }
        }
        function removeHandlerThumb(e) {
            e.stopPropagation();
            const idx = parseInt(e.currentTarget.dataset.idx);
            if (!isNaN(idx)) {
                storyboardImages.splice(idx, 1);
                saveToLocalStorage();
                renderGridAndThumbs();
                updateBadge();
                showToast("Image removed");
            }
        }

        async function addImageToStoryboard(src, silent=false) {
            if (storyboardImages.some(i => i.src === src)) {
                if (!silent) showToast("Image already in storyboard");
                return false;
            }
            const img = new Image();
            img.src = src;
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
            });
            storyboardImages.push({ src, imgElement: img, id: Date.now() });
            renderGridAndThumbs();
            saveToLocalStorage();
            updateBadge();
            return true;
        }

        async function addMultipleImages(srcList) {
            let added = 0;
            for (let src of srcList) if (await addImageToStoryboard(src, true)) added++;
            if (added) showToast(`Added ${added} image(s)`);
            else showToast("No new images");
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
                                const img = new Image();
                                img.src = src;
                                await new Promise((resolve, reject) => {
                                    img.onload = resolve;
                                    img.onerror = reject;
                                });
                                storyboardImages.push({ src, imgElement: img, id: Date.now() });
                            }
                        }
                        renderGridAndThumbs();
                        updateBadge();
                    }
                } catch(e) {}
            }
        }

        function clearAll() {
            if (confirm("Clear all images?")) {
                storyboardImages = [];
                renderGridAndThumbs();
                localStorage.removeItem(STORAGE_KEY);
                updateBadge();
                showToast("Storyboard cleared");
            }
        }

        async function exportStoryboard() {
            if (storyboardImages.length === 0) {
                showToast("No images to export");
                return;
            }
            const container = document.getElementById('storyboardGrid');
            const scale = 10;
            const scaledContainer = container.cloneNode(true);
            scaledContainer.style.width = (container.clientWidth * scale) + 'px';
            scaledContainer.style.padding = '20px';
            scaledContainer.style.gap = '12px';
            scaledContainer.style.backgroundColor = '#1e293b';
            scaledContainer.querySelectorAll('img').forEach(img => {
                img.style.width = '100%';
                img.style.aspectRatio = '4/3';
                img.style.objectFit = 'cover';
            });
            document.body.appendChild(scaledContainer);
            try {
                const canvas = await html2canvas(scaledContainer, { scale: 1, backgroundColor: '#1e293b' });
                const finalCanvas = document.createElement('canvas');
                finalCanvas.width = 10800;
                finalCanvas.height = 14400;
                const ctx = finalCanvas.getContext('2d');
                ctx.fillStyle = 'white';
                ctx.fillRect(0, 0, 10800, 14400);
                const scaledWidth = canvas.width;
                const scaledHeight = canvas.height;
                const targetWidth = 10800;
                const targetHeight = 14400;
                const ratio = Math.min(targetWidth / scaledWidth, targetHeight / scaledHeight);
                const drawWidth = scaledWidth * ratio;
                const drawHeight = scaledHeight * ratio;
                const offsetX = (targetWidth - drawWidth) / 2;
                const offsetY = (targetHeight - drawHeight) / 2;
                ctx.drawImage(canvas, offsetX, offsetY, drawWidth, drawHeight);
                const a = document.createElement('a');
                a.download = 'storyboard_36x48_300dpi.png';
                a.href = finalCanvas.toDataURL('image/png');
                a.click();
            } catch(e) {
                showToast("Export failed: " + e.message);
            } finally {
                document.body.removeChild(scaledContainer);
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

        window.addImageToStoryboard = addImageToStoryboard;
        window.addEventListener('DOMContentLoaded', () => {
            renderGridAndThumbs();
            loadFromLocalStorage();
            document.getElementById('exportStoryboardBtn').onclick = exportStoryboard;
            document.getElementById('clearStoryboardBtn').onclick = clearAll;
            document.getElementById('closeStoryboardBtn').onclick = () => document.getElementById('storyboardModal').classList.remove('active');
            const syncBtn = document.getElementById('syncSelectedBtn');
            if (syncBtn) syncBtn.onclick = syncSelectedToStoryboard;
            window.addMultipleImages = addMultipleImages;
            window.syncSelectedToStoryboard = syncSelectedToStoryboard;
        });
    })();
    </script>
    <!-- ========== END FIXED STORYBOARD ========== 
"""

# Insert new storyboard before the lightbox div
lightbox_start = content.find('<div id="lightbox" class="lightbox">')
if lightbox_start == -1:
    content = content.replace('</body>', new_storyboard + '\n</body>')
else:
    content = content[:lightbox_start] + new_storyboard + '\n' + content[lightbox_start:]

# Ensure the storyboard badge exists on the button
if '<span id="storyboardCountBadge"' not in content:
    content = content.replace(
        '<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal)',
        '<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal) <span id="storyboardCountBadge" style="background:#ef4444; border-radius:20px; padding:2px 8px; margin-left:8px; font-size:0.7rem;">0</span>'
    )

OUTPUT_HTML.write_text(content, encoding='utf-8')
print(f"✅ Fixed storyboard written to {OUTPUT_HTML}")
print("   Now open that file, select images, and open the storyboard. Images will appear in a grid, draggable, and export works.")