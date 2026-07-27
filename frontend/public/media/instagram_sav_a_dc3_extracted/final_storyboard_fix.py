#!/usr/bin/env python3
"""
Replace the broken Fabric.js storyboard with a robust HTML grid + SortableJS.
- Images appear immediately in a grid.
- Drag to reorder.
- Export to 10800x14400 PNG using html2canvas.
- Works with existing checkboxes and sync button.
"""

import re
from pathlib import Path

INPUT = Path("index_final_with_authors.html")
OUTPUT = Path("index_final_robust_storyboard.html")

if not INPUT.exists():
    print(f"Error: {INPUT} not found.")
    exit(1)

content = INPUT.read_text(encoding='utf-8')

# Remove any existing storyboard modal
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

# New robust storyboard HTML (no Fabric.js)
new_storyboard = """
    <!-- ========== ROBUST STORYBOARD (Grid + SortableJS + html2canvas) ========== -->
    <div id="storyboardModal" class="storyboard-modal">
        <div class="storyboard-container">
            <div style="display:flex; justify-content:space-between;">
                <h3 style="color:white;">📸 Storyboard Builder – 36×48" @ 300 DPI</h3>
                <button class="close-modal" id="closeStoryboardBtn">✖ Close</button>
            </div>
            <div style="background:#0f172a; border-radius:12px; padding:12px; margin-bottom:12px; overflow:auto;">
                <div id="storyboardGrid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); gap:12px; background:#1e293b; padding:20px; border-radius:12px; min-height:200px;"></div>
            </div>
            <div class="storyboard-controls">
                <button id="exportStoryboardBtn" class="success">⬇ Export PNG (10800×14400)</button>
                <button id="clearStoryboardBtn" class="danger">🗑 Clear All</button>
            </div>
            <div><strong style="color:white;">📁 Images (drag to reorder, click to remove):</strong>
                <div id="storyboardThumbnails" style="display:flex; gap:12px; overflow-x:auto; padding:8px;"></div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <script>
    (function() {
        let storyboardImages = [];      // list of { src, imgElement }
        const STORAGE_KEY = "storyboard_images_srcs";
        let gridContainer = null;
        let thumbContainer = null;
        let sortableGrid = null;
        let sortableThumbs = null;

        function getToast() {
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
                }
            } catch(e) { console.error("localStorage load error", e); }
        }

        async function addImageToStoryboard(src, silent=false) {
            if (storyboardImages.some(i => i.src === src)) {
                if (!silent) toast("Image already in storyboard");
                return false;
            }
            // Load image to ensure it works
            const img = new Image();
            img.src = src;
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
            });
            storyboardImages.push({ src, imgElement: img });
            renderGridAndThumbs();
            saveToLocalStorage();
            updateBadge();
            return true;
        }

        function renderGridAndThumbs() {
            if (!gridContainer || !thumbContainer) return;
            // Render main grid
            gridContainer.innerHTML = storyboardImages.map((img, idx) => `
                <div data-id="${idx}" style="position:relative; background:#0f172a; border-radius:8px; overflow:hidden; cursor:grab;">
                    <img src="${img.src}" style="width:100%; aspect-ratio:4/3; object-fit:cover; display:block;">
                    <div style="position:absolute; top:4px; right:4px; background:rgba(0,0,0,0.6); border-radius:50%; width:24px; height:24px; display:flex; align-items:center; justify-content:center; cursor:pointer; font-size:16px; color:white;" class="remove-grid-item" data-idx="${idx}">×</div>
                </div>
            `).join('');
            // Render thumbnails
            thumbContainer.innerHTML = storyboardImages.map((img, idx) => `
                <div data-id="${idx}" style="position:relative; width:80px; flex-shrink:0; cursor:grab;">
                    <img src="${img.src}" style="width:100%; aspect-ratio:1; object-fit:cover; border-radius:8px;">
                    <div style="position:absolute; top:2px; right:2px; background:rgba(0,0,0,0.6); border-radius:50%; width:20px; height:20px; display:flex; align-items:center; justify-content:center; cursor:pointer; font-size:14px; color:white;" class="remove-thumb" data-idx="${idx}">×</div>
                </div>
            `).join('');

            // Attach remove handlers
            document.querySelectorAll('.remove-grid-item').forEach(el => {
                el.removeEventListener('click', removeHandler);
                el.addEventListener('click', removeHandler);
            });
            document.querySelectorAll('.remove-thumb').forEach(el => {
                el.removeEventListener('click', removeHandler);
                el.addEventListener('click', removeHandler);
            });

            // Reinitialise Sortable
            if (sortableGrid) sortableGrid.destroy();
            if (sortableThumbs) sortableThumbs.destroy();
            sortableGrid = new Sortable(gridContainer, {
                animation: 150,
                onEnd: function() {
                    reorderFromGrid();
                }
            });
            sortableThumbs = new Sortable(thumbContainer, {
                animation: 150,
                onEnd: function() {
                    reorderFromThumbs();
                }
            });
        }

        function removeHandler(e) {
            e.stopPropagation();
            const idx = parseInt(e.currentTarget.dataset.idx);
            if (!isNaN(idx)) {
                storyboardImages.splice(idx, 1);
                renderGridAndThumbs();
                saveToLocalStorage();
                updateBadge();
                toast("Image removed");
            }
        }

        function reorderFromGrid() {
            const newOrder = [];
            document.querySelectorAll('#storyboardGrid > div').forEach(div => {
                const idx = parseInt(div.dataset.id);
                if (!isNaN(idx)) newOrder.push(storyboardImages[idx]);
            });
            storyboardImages = newOrder;
            saveToLocalStorage();
            renderGridAndThumbs(); // refresh indices
        }

        function reorderFromThumbs() {
            const newOrder = [];
            document.querySelectorAll('#storyboardThumbnails > div').forEach(div => {
                const idx = parseInt(div.dataset.id);
                if (!isNaN(idx)) newOrder.push(storyboardImages[idx]);
            });
            storyboardImages = newOrder;
            saveToLocalStorage();
            renderGridAndThumbs();
        }

        async function exportStoryboard() {
            if (storyboardImages.length === 0) {
                toast("No images to export");
                return;
            }
            const container = document.getElementById('storyboardGrid');
            // Clone the grid for scaling
            const scale = 10; // 1080px -> 10800px
            const clone = container.cloneNode(true);
            clone.style.width = (container.clientWidth * scale) + 'px';
            clone.style.padding = '20px';
            clone.style.gap = '12px';
            clone.style.backgroundColor = '#1e293b';
            clone.querySelectorAll('img').forEach(img => {
                img.style.width = '100%';
                img.style.aspectRatio = '4/3';
                img.style.objectFit = 'cover';
            });
            document.body.appendChild(clone);
            try {
                const canvas = await html2canvas(clone, { scale: 1, backgroundColor: '#1e293b' });
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
                toast("Export complete");
            } catch(e) {
                toast("Export failed: " + e.message);
                console.error(e);
            } finally {
                document.body.removeChild(clone);
            }
        }

        function clearAll() {
            if (confirm("Clear all images from storyboard?")) {
                storyboardImages = [];
                renderGridAndThumbs();
                localStorage.removeItem(STORAGE_KEY);
                updateBadge();
                toast("Storyboard cleared");
            }
        }

        async function syncSelectedToStoryboard() {
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

        // Initialisation when modal opens
        const modal = document.getElementById('storyboardModal');
        let initialised = false;
        function ensureInit() {
            if (initialised) return;
            initialised = true;
            gridContainer = document.getElementById('storyboardGrid');
            thumbContainer = document.getElementById('storyboardThumbnails');
            loadFromLocalStorage().then(() => {
                renderGridAndThumbs();
                updateBadge();
            });
        }

        const observer = new MutationObserver(() => {
            if (modal.classList.contains('active')) {
                ensureInit();
            }
        });
        observer.observe(modal, { attributes: true, attributeFilter: ['class'] });

        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('exportStoryboardBtn')?.addEventListener('click', exportStoryboard);
            document.getElementById('clearStoryboardBtn')?.addEventListener('click', clearAll);
            document.getElementById('closeStoryboardBtn')?.addEventListener('click', () => {
                modal.classList.remove('active');
            });
            const syncBtn = document.getElementById('syncSelectedBtn');
            if (syncBtn) syncBtn.onclick = syncSelectedToStoryboard;
            window.addMultipleImages = (srcList) => srcList.forEach(src => addImageToStoryboard(src, true));
        });
    })();
    </script>
    <!-- ========== END ROBUST STORYBOARD ========== 
"""

# Insert before the lightbox div
lightbox_start = content.find('<div id="lightbox" class="lightbox">')
if lightbox_start == -1:
    content = content.replace('</body>', new_storyboard + '\n</body>')
else:
    content = content[:lightbox_start] + new_storyboard + '\n' + content[lightbox_start:]

# Ensure the storyboard badge exists
if '<span id="storyboardCountBadge"' not in content:
    content = content.replace(
        '<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal)',
        '<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal) <span id="storyboardCountBadge" style="background:#ef4444; border-radius:20px; padding:2px 8px; margin-left:8px; font-size:0.7rem;">0</span>'
    )

OUTPUT.write_text(content, encoding='utf-8')
print(f"✅ Robust storyboard written to {OUTPUT}")
print("   Open that file, select images, and open the storyboard.")
print("   Images will appear in a grid. Drag to reorder, click × to remove.")
print("   Export to 10800×14400 PNG works without canvas issues.")