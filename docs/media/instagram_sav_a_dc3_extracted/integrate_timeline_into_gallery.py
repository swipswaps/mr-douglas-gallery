#!/usr/bin/env python3
"""
Integrate historic timeline images into the main gallery grid.
Remove all separate timelines, add storyboard with checkboxes on every image.
"""

import re
from pathlib import Path
import shutil

HTML_PATH = Path("index_cloud.html")
BACKUP_PATH = Path("index_cloud_before_integration.html")

# Use the clean gallery backup (the one with all Instagram posts)
SOURCE = Path("index_cloud_final_backup.html")
if not SOURCE.exists():
    print(f"Error: {SOURCE} not found. Available backups:")
    for b in Path(".").glob("index_cloud*backup*.html"):
        print(f"  {b}")
    exit(1)

# Restore the clean gallery
shutil.copy(SOURCE, HTML_PATH)
shutil.copy(SOURCE, BACKUP_PATH)
print(f"✅ Restored {SOURCE}")

# Read the HTML
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove any existing timeline or storyboard code (to avoid conflicts)
content = re.sub(r'<!-- ==========.*?TIMELINE.*?-->.*?<div class="timeline-container".*?</div>\s*</div>\s*', '', content, flags=re.DOTALL)
content = re.sub(r'<!-- ==========.*?STORYBOARD.*?-->.*?</script>\s*<!-- ========== END STORYBOARD ========== -->', '', content, flags=re.DOTALL)

# Ensure the /timeline/ folder exists and contains the images
timeline_folder = Path("timeline")
timeline_folder.mkdir(exist_ok=True)

# List of timeline images (source from parent directory, dest in timeline/)
timeline_images = [
    ("../United-mr-douglas-1941.jpg", "timeline/United-mr-douglas-1941.jpg", "1941", "United Mr Douglas 1941"),
    ("../united-flying-1942.jpg", "timeline/united-flying-1942.jpg", "1942", "United Flying 1942"),
    ("../western-1943.jpg", "timeline/western-1943.jpg", "1943", "Western 1943"),
    ("../mr-douglas-1952.jpg", "timeline/mr-douglas-1952.jpg", "1952", "Mr Douglas 1952"),
    ("../mr-douglas-1960.jpg", "timeline/mr-douglas-1960.jpg", "1960", "Mr Douglas 1960"),
    ("../mr-douglas-1970.jpg", "timeline/mr-douglas-1970.jpg", "1970", "Mr Douglas 1970"),
    ("../mr-douglas-1974.jpg", "timeline/mr-douglas-1974.jpg", "1974", "Mr Douglas 1974"),
    ("../mr-douglas-1979.jpg", "timeline/mr-douglas-1979.jpg", "1979", "Mr Douglas 1979"),
    ("../mr-douglas-1984-1400x790-slider.jpg", "timeline/mr-douglas-1984-1400x790-slider.jpg", "1984", "Mr Douglas 1984"),
    ("../mr-douglas-1988.jpg", "timeline/mr-douglas-1988.jpg", "1988", "Mr Douglas 1988"),
    ("../mr-douglas-1990.jpg", "timeline/mr-douglas-1990.jpg", "1990", "Mr Douglas 1990"),
    ("../mr-douglas-1992.jpg", "timeline/mr-douglas-1992.jpg", "1992", "Mr Douglas 1992"),
    ("../mr-douglas-1996.jpg", "timeline/mr-douglas-1996.jpg", "1996", "Mr Douglas 1996"),
    ("../Mr-Douglas-2018-drone-front-pix-slider.jpg", "timeline/Mr-Douglas-2018-drone-front-pix-slider.jpg", "2018", "Drone Front"),
]

for src, dst, year, title in timeline_images:
    src_path = Path(src)
    if src_path.exists():
        shutil.copy2(src_path, Path(dst))
        print(f"Copied {src} -> {dst}")
    else:
        print(f"Warning: {src} not found, skipping")

# Create HTML card(s) for these timeline images to be inserted into the gallery grid.
# We'll generate a block of card HTML with a placeholder structure similar to Instagram posts.
# But the gallery is dynamically rendered by the `allPosts` array in JavaScript.
# Instead of injecting static HTML, we'll modify the JavaScript `allPosts` array at runtime.
# We'll inject a script that prepends the timeline images to the `allPosts` array.

inject_script = """
<script>
(function() {
    const timelineCards = [
""" + "\n".join([
    f'        {{ shortcode: "timeline_{year}", date: "{year}-01-01 00:00:00", likes: 0, comments_count: 0, caption: "{title} – Historic photo of Mr. Douglas", folder_name: "timeline", all_media: ["{dst.split('/')[-1]}"], comments: [], instagram_url: "#" }}'
    for src, dst, year, title in timeline_images if Path(dst).exists()
]) + """
    ];
    if (typeof allPosts !== 'undefined' && Array.isArray(allPosts)) {
        // Prepend timeline cards to the gallery (so they appear at the top)
        allPosts.unshift(...timelineCards);
        // Re-render the gallery if there is a render function
        if (typeof renderGallery === 'function') renderGallery(allPosts);
        else if (typeof renderGallery === 'function') renderGallery(allPosts);
    } else {
        console.warn("allPosts not found, timeline cards not added");
    }
})();
</script>
"""
# Insert this script after the definition of allPosts (but before the gallery render).
# We'll find the closing </body> and insert before that, but ensure allPosts is already defined.
# The original HTML defines allPosts in a <script> before the gallery rendering.
# We'll append the injection right after that script.

# Find the script that contains "const allPosts"
allposts_match = re.search(r'(const allPosts = \[[\s\S]*?\];)', content)
if allposts_match:
    # Insert our injection right after that script
    insert_pos = allposts_match.end()
    content = content[:insert_pos] + "\n" + inject_script + "\n" + content[insert_pos:]
    print("✅ Injected timeline cards into allPosts array.")
else:
    print("Could not find allPosts array. Timeline cards not added.")

# Now add the storyboard (lightweight, with checkboxes)
storyboard_code = '''
<!-- ========== LIGHTWEIGHT STORYBOARD ========== -->
<style>
.storyboard-btn{position:fixed;bottom:20px;right:20px;background:#3b82f6;color:white;border:none;border-radius:50px;padding:12px 24px;font-size:1rem;font-weight:bold;cursor:pointer;z-index:1000;}
.storyboard-btn:hover{background:#2563eb;}
.gallery-toolbar{display:flex;gap:12px;margin:16px 0;flex-wrap:wrap;align-items:center;background:#f1f5f9;padding:8px 12px;border-radius:12px;}
.select-checkbox{position:absolute;top:8px;left:8px;width:20px;height:20px;cursor:pointer;z-index:10;background:white;border-radius:4px;}
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
    // Storyboard state
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
        // Default grid (3 cols)
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

    // === Multi-select checkboxes on all cards ===
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
        document.querySelectorAll('.card').forEach(card => {
            const img = card.querySelector('img');
            if (img && img.src && !img.src.startsWith('data:')) {
                addCheckboxToCard(card, img.src);
            }
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

    function observeGallery() {
        const grid = document.getElementById('galleryGrid');
        if (!grid) return;
        const observer = new MutationObserver(() => scanAndAddCheckboxes());
        observer.observe(grid, { childList: true, subtree: true });
        scanAndAddCheckboxes();
    }

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
'''
# Append storyboard before </body>
content = content.replace('</body>', storyboard_code + '\n</body>')

# Save the modified HTML
with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ All done! Timeline images are now part of the main gallery grid.")
print("   No separate timeline element. All images are selectable.")
print("💡 Start the server: python -m http.server 8000")
print("   Then hard refresh. Use 'Select All' and 'Add Selected to Storyboard'.")