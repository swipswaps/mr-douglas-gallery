#!/usr/bin/env python3
"""
Applies all necessary fixes to index_final_with_authors.html to make the Fabric.js storyboard work.
- Adds Fabric.js to <head>
- Replaces the storyboard modal with a working version
- Adds the storyboard controller script
- Exposes selectedSrcs and showToast globally
- Ensures the storyboard badge exists
"""

import re
from pathlib import Path

INPUT = Path("index_final_with_authors.html")
OUTPUT = Path("index_final_fixed_storyboard.html")

if not INPUT.exists():
    print(f"Error: {INPUT} not found.")
    exit(1)

content = INPUT.read_text(encoding='utf-8')

# 1. Add Fabric.js to <head> if not already present
if 'fabric.js' not in content:
    head_close = content.find('</head>')
    if head_close != -1:
        fabric_script = '<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>\n'
        content = content[:head_close] + fabric_script + content[head_close:]
        print("Added Fabric.js to <head>.")
    else:
        print("Warning: </head> not found. Skipping Fabric.js addition.")

# 2. Find and replace the storyboard modal
modal_start = content.find('<div id="storyboardModal"')
if modal_start == -1:
    print("Could not find storyboard modal. Exiting.")
    exit(1)

# Find the matching closing </div> using depth counting
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
    print("Could not find end of storyboard modal.")
    exit(1)

# New modal HTML (from the JSON fix list)
new_modal = '''<div id="storyboardModal" class="storyboard-modal">
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
</div>'''

# New script block
new_script = '''
<script>
(function() {
    let canvas = null;
    let storyboardImages = [];
    const STORAGE_KEY = "storyboard_images_srcs";
    const PREVIEW_W = 1080, PREVIEW_H = 1440;
    const TARGET_W = 10800, TARGET_H = 14400;

    function toast(msg) {
        if (typeof window.showToast === 'function') window.showToast(msg);
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
        if (confirm("Clear all images from storyboard?")) {
            storyboardImages.forEach(i => canvas.remove(i.fabricObj));
            storyboardImages = [];
            canvas.renderAll();
            renderThumbs();
            localStorage.removeItem(STORAGE_KEY);
            updateBadge();
            toast("Storyboard cleared");
        }
    }

    async function syncSelected() {
        if (typeof window.selectedSrcs === 'undefined') { toast("Selection data not available"); return; }
        const srcs = Array.from(window.selectedSrcs);
        if (srcs.length === 0) { toast("No images selected"); return; }
        let added = 0;
        for (let src of srcs) if (await addImage(src, true)) added++;
        toast(added ? `Added ${added} new image(s)` : "All selected already in storyboard");
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
</script>'''

# Replace the old modal with new modal + script
content = content[:modal_start] + new_modal + '\n' + new_script + content[modal_end:]

# 3. Expose selectedSrcs and showToast globally
# Find the line with 'let selectedSrcs = new Set();'
sel_match = re.search(r'let selectedSrcs = new Set\(\);', content)
if sel_match:
    # Insert global exposure right after
    insert_pos = sel_match.end()
    content = content[:insert_pos] + '\n    window.selectedSrcs = selectedSrcs;' + content[insert_pos:]
    print("Exposed selectedSrcs globally.")
else:
    print("Warning: 'let selectedSrcs' not found. Global exposure skipped.")

# Find showToast function definition
toast_match = re.search(r'function showToast\(msg, dur=2000\)\s*\{', content)
if toast_match:
    # Find the closing brace of the function and add window assignment
    # Simple approach: add after the function definition (search for the line after the closing brace)
    # But safer: find the end of the function (count braces)
    start = toast_match.start()
    depth = 0
    i = start
    while i < len(content):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
        i += 1
    else:
        print("Could not find end of showToast function.")
        # fallback: try to add after a known line
        content = content.replace('function showToast(msg, dur=2000) {', 'function showToast(msg, dur=2000) {\n    window.showToast = showToast;')
    if 'end' in locals():
        content = content[:end] + '\n    window.showToast = showToast;' + content[end:]
        print("Exposed showToast globally.")
else:
    print("Warning: showToast function not found. Global exposure skipped.")

# 4. Ensure the storyboard badge exists on the open button
badge_span = '<span id="storyboardCountBadge" style="background:#ef4444; border-radius:20px; padding:2px 8px; margin-left:8px; font-size:0.7rem;">0</span>'
if 'storyboardCountBadge' not in content:
    content = content.replace(
        '<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal)',
        f'<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (modal) {badge_span}'
    )
    print("Added storyboard badge.")

# Write the output
OUTPUT.write_text(content, encoding='utf-8')
print(f"\n✅ Fixed storyboard written to {OUTPUT}")
print("   Open that file with a local server: python -m http.server 8000")
print("   Then select images and open the storyboard.")