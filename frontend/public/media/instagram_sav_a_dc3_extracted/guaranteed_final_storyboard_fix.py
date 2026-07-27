#!/usr/bin/env python3
"""
Guaranteed storyboard fix – inserts markers then replaces.
"""

import re
from pathlib import Path

INPUT = Path("index_final_with_authors.html")
OUTPUT = Path("index_final_working_storyboard.html")

if not INPUT.exists():
    print(f"Error: {INPUT} not found.")
    exit(1)

content = INPUT.read_text(encoding='utf-8')

# If markers already exist, remove the old storyboard block
if '<!-- STORYBOARD_START -->' in content and '<!-- STORYBOARD_END -->' in content:
    content = re.sub(r'<!-- STORYBOARD_START -->.*?<!-- STORYBOARD_END -->', '', content, flags=re.DOTALL)
    print("Removed previous storyboard markers block.")

# If no markers, find the storyboard modal and wrap it with markers
if '<!-- STORYBOARD_START -->' not in content:
    # Try to find existing modal
    modal_start = content.find('<div id="storyboardModal"')
    if modal_start != -1:
        # Find end of modal (closing </div> after nested)
        depth = 0
        i = modal_start
        while i < len(content):
            if content[i:i+4] == '<div':
                depth += 1
                i += 4
            elif content[i:i+6] == '</div>':
                depth -= 1
                i += 6
                if depth == 0:
                    modal_end = i
                    break
            else:
                i += 1
        else:
            print("Could not find end of existing modal. Exiting.")
            exit(1)
        # Wrap the modal with markers
        content = (content[:modal_start] + 
                   '<!-- STORYBOARD_START -->\n' + 
                   content[modal_start:modal_end] + 
                   '\n<!-- STORYBOARD_END -->' + 
                   content[modal_end:])
        print("Inserted markers around existing storyboard modal.")
    else:
        # No modal found – insert markers before lightbox
        lightbox_pos = content.find('<div id="lightbox"')
        if lightbox_pos == -1:
            print("Cannot find lightbox or storyboard modal. Exiting.")
            exit(1)
        content = (content[:lightbox_pos] + 
                   '<!-- STORYBOARD_START -->\n<!-- STORYBOARD_END -->\n' + 
                   content[lightbox_pos:])
        print("Inserted empty markers before lightbox.")

# Now replace the markers with the working storyboard
working_storyboard = """
<!-- STORYBOARD_START -->
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
    // === WORKING FABRIC.JS STORYBOARD ===
    (function() {
        let canvas = null;
        let storyboardImages = [];
        const STORAGE_KEY = "storyboard_images_srcs";
        const PREVIEW_W = 1080, PREVIEW_H = 1440;
        const TARGET_W = 10800, TARGET_H = 14400;

        function toast(msg) {
            if (typeof showToast === 'function') showToast(msg);
            else alert(msg);
        }

        function updateBadge() {
            const b = document.getElementById('storyboardCountBadge');
            if (b) b.innerText = storyboardImages.length;
        }

        function save() {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(storyboardImages.map(i => i.src)));
        }

        async function load() {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (!stored) return;
            try {
                const srcs = JSON.parse(stored);
                for (let src of srcs) {
                    if (!storyboardImages.some(i => i.src === src))
                        await addImage(src, true);
                }
            } catch(e) { console.error(e); }
        }

        async function addImage(src, silent=false) {
            if (storyboardImages.some(i => i.src === src)) {
                if (!silent) toast("Already in storyboard");
                return false;
            }
            return new Promise((resolve) => {
                fabric.Image.fromURL(src, (img) => {
                    if (!img) { if (!silent) toast("Failed to load"); resolve(false); return; }
                    img.set({ crossOrigin: 'Anonymous', hasControls: true, hasBorders: true, lockRotation: true });
                    const scale = Math.min(200 / img.width, 200 / img.height);
                    img.scale(scale);
                    img.set({ left: 20, top: 20 });
                    canvas.add(img);
                    storyboardImages.push({ src, fabricObj: img });
                    save();
                    updateBadge();
                    applyLayout();
                    renderThumbs();
                    resolve(true);
                }, { crossOrigin: 'Anonymous' });
            });
        }

        function applyLayout() {
            if (!canvas || storyboardImages.length === 0) return;
            const margin = 20, cols = 3;
            const availW = PREVIEW_W - margin * 2;
            const cellW = (availW - (cols - 1) * margin) / cols;
            let y = margin;
            for (let i = 0; i < storyboardImages.length; i++) {
                const obj = storyboardImages[i].fabricObj;
                const col = i % cols;
                if (col === 0 && i !== 0) {
                    const prev = storyboardImages[i-1].fabricObj;
                    y += prev.height * prev.scaleY + margin;
                }
                const maxH = 200;
                let scale = Math.min(cellW / obj.width, maxH / obj.height);
                obj.scale(scale);
                obj.set({ left: margin + col * (cellW + margin), top: y });
            }
            canvas.renderAll();
            save();
        }

        function renderThumbs() {
            const container = document.getElementById('storyboardThumbnails');
            if (!container) return;
            container.innerHTML = storyboardImages.map((img, idx) => `
                <img src="${img.src}" data-idx="${idx}" style="width:80px; height:80px; object-fit:cover; border-radius:8px; cursor:pointer; margin:4px;">
            `).join('');
            container.querySelectorAll('img').forEach(thumb => {
                thumb.onclick = () => {
                    const idx = parseInt(thumb.dataset.idx);
                    canvas.remove(storyboardImages[idx].fabricObj);
                    storyboardImages.splice(idx, 1);
                    canvas.renderAll();
                    renderThumbs();
                    save();
                    updateBadge();
                    applyLayout();
                    toast("Image removed");
                };
            });
        }

        function resetLayout() { applyLayout(); toast("Layout reset"); }

        async function exportHighRes() {
            if (storyboardImages.length === 0) { toast("No images"); return; }
            const exportCanvas = new fabric.Canvas(null);
            exportCanvas.setDimensions({ width: TARGET_W, height: TARGET_H });
            const scale = TARGET_W / PREVIEW_W;
            for (let item of storyboardImages) {
                const obj = item.fabricObj;
                const clone = await new Promise(resolve => obj.clone(resolve));
                clone.set({ left: obj.left * scale, top: obj.top * scale, scaleX: obj.scaleX * scale, scaleY: obj.scaleY * scale });
                exportCanvas.add(clone);
            }
            exportCanvas.renderAll();
            const a = document.createElement('a');
            a.download = 'storyboard_36x48_300dpi.png';
            a.href = exportCanvas.toDataURL({ format: 'png' });
            a.click();
            exportCanvas.dispose();
            toast("Export ready");
        }

        function clearAll() {
            if (confirm("Clear all?")) {
                storyboardImages.forEach(i => canvas.remove(i.fabricObj));
                storyboardImages = [];
                canvas.renderAll();
                renderThumbs();
                localStorage.removeItem(STORAGE_KEY);
                updateBadge();
                toast("Cleared");
            }
        }

        async function syncSelected() {
            if (typeof window.selectedSrcs === 'undefined') { toast("No selection data"); return; }
            const srcs = Array.from(window.selectedSrcs);
            if (srcs.length === 0) { toast("No images selected"); return; }
            let added = 0;
            for (let src of srcs) if (await addImage(src, true)) added++;
            toast(added ? `Added ${added} image(s)` : "All already in storyboard");
        }

        function initCanvas() {
            const el = document.getElementById('storyboardCanvas');
            if (!el) return;
            if (canvas) canvas.dispose();
            canvas = new fabric.Canvas('storyboardCanvas');
            canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
            canvas.setBackgroundColor('white', canvas.renderAll.bind(canvas));
            canvas.on('object:modified', () => save());
            canvas.renderAll();
        }

        window.addImageToStoryboard = addImage;
        window.syncSelectedToStoryboard = syncSelected;

        const modal = document.getElementById('storyboardModal');
        let ready = false;
        const observer = new MutationObserver(() => {
            if (modal.classList.contains('active') && !ready) {
                ready = true;
                initCanvas();
                load().then(() => { applyLayout(); renderThumbs(); updateBadge(); });
            } else if (!modal.classList.contains('active')) {
                ready = false;
            }
        });
        observer.observe(modal, { attributes: true });

        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('resetLayoutBtn')?.addEventListener('click', resetLayout);
            document.getElementById('exportStoryboardBtn')?.addEventListener('click', exportHighRes);
            document.getElementById('clearStoryboardBtn')?.addEventListener('click', clearAll);
            document.getElementById('closeStoryboardBtn')?.addEventListener('click', () => modal.classList.remove('active'));
            const syncBtn = document.getElementById('syncSelectedBtn');
            if (syncBtn) syncBtn.onclick = syncSelected;
            window.addMultipleImages = (list) => list.forEach(src => addImage(src, true));
        });
    })();
    </script>
<!-- STORYBOARD_END -->
"""

# Replace the markers block
content = re.sub(r'<!-- STORYBOARD_START -->.*?<!-- STORYBOARD_END -->', working_storyboard, content, flags=re.DOTALL)

# Ensure badge exists on storyboard button
if '<span id="storyboardCountBadge"' not in content:
    content = content.replace(
        '<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal)',
        '<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal) <span id="storyboardCountBadge" style="background:#ef4444; border-radius:20px; padding:2px 8px; margin-left:8px; font-size:0.7rem;">0</span>'
    )

OUTPUT.write_text(content, encoding='utf-8')
print(f"✅ Working storyboard written to {OUTPUT}")
print("   Open that file, select images, and open the storyboard.")