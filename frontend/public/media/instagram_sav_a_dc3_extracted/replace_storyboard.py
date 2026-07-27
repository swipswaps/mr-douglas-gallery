#!/usr/bin/env python3
"""
Completely replace the storyboard code in index_cloud.html with a working version.
Exposes addImageToStoryboard globally and adds buttons automatically.
"""

import re
from pathlib import Path

HTML_PATH = Path("index_cloud.html")
BACKUP_PATH = Path("index_cloud_before_replace.html")

# The complete, corrected storyboard HTML/JS block
NEW_STORYBOARD = """
<!-- ========== STORYBOARD BUILDER (FIXED) ========== -->
<style>
.storyboard-btn {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 50px;
    padding: 12px 24px;
    font-size: 1rem;
    font-weight: bold;
    cursor: pointer;
    z-index: 1000;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.storyboard-btn:hover { background: #2563eb; }
.storyboard-modal {
    display: none;
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.85);
    z-index: 2000;
    overflow: auto;
}
.storyboard-modal.active { display: flex; flex-direction: column; }
.storyboard-container {
    background: #1e293b;
    margin: 20px auto;
    padding: 20px;
    border-radius: 16px;
    max-width: 95%;
    width: 1200px;
}
.storyboard-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}
.storyboard-canvas-wrapper {
    background: #0f172a;
    border-radius: 12px;
    padding: 12px;
    text-align: center;
    overflow-x: auto;
}
#storyboardCanvas {
    border: 2px solid #475569;
    border-radius: 8px;
    background: white;
}
.storyboard-controls {
    display: flex;
    gap: 10px;
    justify-content: center;
    margin: 15px 0;
}
.storyboard-controls button {
    background: #3b82f6;
    border: none;
    color: white;
    padding: 8px 16px;
    border-radius: 8px;
    cursor: pointer;
}
.storyboard-controls button.danger { background: #ef4444; }
.storyboard-controls button.success { background: #10b981; }
.storyboard-image-list {
    background: #0f172a;
    border-radius: 12px;
    padding: 12px;
    margin-top: 20px;
}
.storyboard-thumbnails {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding: 8px;
}
.storyboard-thumb {
    width: 80px;
    height: 80px;
    object-fit: cover;
    border-radius: 8px;
    cursor: pointer;
    border: 2px solid transparent;
}
.storyboard-thumb:hover { border-color: #3b82f6; transform: scale(1.05); }
.close-modal {
    background: #475569;
    color: white;
    border: none;
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
}
</style>

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
            <button id="exportStoryboardBtn" class="success">⬇ Export PNG (10800×14400) – 300 DPI</button>
            <button id="clearStoryboardBtn" class="danger">🗑 Clear All</button>
        </div>
        <div class="storyboard-image-list">
            <strong style="color:white;">📁 Images (click to remove):</strong>
            <div class="storyboard-thumbnails" id="storyboardThumbnails"></div>
        </div>
    </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
<script>
(function() {
    // Global state
    window.storyboardImages = [];
    window.displayCanvas = null;

    const targetWidth = 10800;
    const targetHeight = 14400;
    const scaleFactor = 10; // 1080 -> 10800

    // Helper: load image
    function loadImage(src) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = "Anonymous";
            img.onload = () => resolve(img);
            img.onerror = reject;
            img.src = src;
        });
    }

    // Add image to storyboard (global)
    window.addImageToStoryboard = async function(imgSrc) {
        if (window.storyboardImages.some(i => i.src === imgSrc)) {
            alert("Image already in storyboard");
            return;
        }
        try {
            const img = await loadImage(imgSrc);
            const aspect = img.width / img.height;
            const displayWidth = 200;
            const displayHeight = displayWidth / aspect;
            const newImg = {
                src: imgSrc,
                width: img.width,
                height: img.height,
                left: 50,
                top: 50,
                scaleX: displayWidth / img.width,
                scaleY: displayHeight / img.height,
            };
            window.storyboardImages.push(newImg);
            if (window.displayCanvas) {
                const fabricImg = new fabric.Image(img, {
                    left: 50, top: 50,
                    scaleX: displayWidth / img.width,
                    scaleY: displayHeight / img.height,
                    hasControls: true, hasBorders: true, lockRotation: true
                });
                newImg.fabricObject = fabricImg;
                window.displayCanvas.add(fabricImg);
                window.displayCanvas.renderAll();
            }
            updateThumbnails();
        } catch(e) {
            alert("Failed to load image: " + e.message);
        }
    };

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
        offCanvas.width = targetWidth;
        offCanvas.height = targetHeight;
        const ctx = offCanvas.getContext('2d');
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, targetWidth, targetHeight);
        for (let item of window.storyboardImages) {
            try {
                const img = await loadImage(item.src);
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
    function init() {
        const canvasEl = document.getElementById('storyboardCanvas');
        if (!canvasEl) return;
        window.displayCanvas = new fabric.Canvas('storyboardCanvas');
        window.displayCanvas.setDimensions({ width: 1080, height: 1440 });
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
        // Restore any existing images (though initially empty)
        window.storyboardImages.forEach(img => {
            if (img.fabricObject) window.displayCanvas.add(img.fabricObject);
        });
        window.displayCanvas.renderAll();
        updateThumbnails();

        // UI buttons
        document.getElementById('openStoryboardBtn').onclick = () => document.getElementById('storyboardModal').classList.add('active');
        document.getElementById('closeStoryboardBtn').onclick = () => document.getElementById('storyboardModal').classList.remove('active');
        document.getElementById('exportStoryboardBtn').onclick = () => window.exportStoryboard();
        document.getElementById('clearStoryboardBtn').onclick = () => clearStoryboard();
        window.onclick = (e) => { if (e.target === document.getElementById('storyboardModal')) document.getElementById('storyboardModal').classList.remove('active'); };
    }

    // Add buttons to all images (gallery + timeline)
    function addButtonsToImages() {
        function addButtonToImage(img, src) {
            if (!src || img.parentElement.querySelector('.storyboard-add-btn')) return;
            const btn = document.createElement('button');
            btn.className = 'storyboard-add-btn';
            btn.innerHTML = '📌 Add to Storyboard';
            btn.style.cssText = 'position:absolute; bottom:8px; right:8px; background:#3b82f6; color:white; border:none; border-radius:20px; padding:4px 12px; font-size:0.7rem; cursor:pointer; z-index:10;';
            btn.onclick = (e) => {
                e.stopPropagation();
                window.addImageToStoryboard(src);
            };
            let container = img.closest('.card, .timeline-card') || img.parentElement;
            if (getComputedStyle(container).position === 'static') container.style.position = 'relative';
            container.appendChild(btn);
        }
        document.querySelectorAll('.card img, .timeline-card img, .carousel-item, .card-media').forEach(img => {
            if (img.src && !img.src.startsWith('data:')) addButtonToImage(img, img.src);
        });
    }

    // Wait for fabric to load, then init and add buttons
    let checkFabric = setInterval(() => {
        if (typeof fabric !== 'undefined') {
            clearInterval(checkFabric);
            init();
            addButtonsToImages();
            // Observe dynamically added images
            const observer = new MutationObserver(() => addButtonsToImages());
            observer.observe(document.getElementById('galleryGrid') || document.body, { childList: true, subtree: true });
        }
    }, 200);
})();
</script>
<!-- ========== END STORYBOARD ========== -->
"""

def replace_storyboard():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Backup
    with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    # Remove any existing storyboard block (from old versions)
    # Look for the start marker
    pattern = r'<!-- ========== STORYBOARD BUILDER.*?<!-- ========== END STORYBOARD ========== -->'
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, NEW_STORYBOARD, content, flags=re.DOTALL)
    else:
        # If not found, insert before </body>
        new_content = content.replace('</body>', NEW_STORYBOARD + '\n</body>')

    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✅ Storyboard replaced. Backup saved as {BACKUP_PATH}")
    print("💡 Hard refresh your browser (Ctrl+Shift+R). Buttons should appear automatically.")

if __name__ == "__main__":
    replace_storyboard()