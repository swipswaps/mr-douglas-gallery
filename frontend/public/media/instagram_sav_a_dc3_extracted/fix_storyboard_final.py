#!/usr/bin/env python3
"""
Properly expose storyboard functions and add buttons to all images.
"""

import re
from pathlib import Path

HTML_PATH = Path("index_cloud.html")
BACKUP_PATH = Path("index_cloud_before_final_fix.html")

# This will be inserted right after the storyboard script definition
PATCH_SCRIPT = """
<script>
(function() {
    // Wait for the storyboard's internal function to become available
    let checkInterval = setInterval(function() {
        // The storyboard script defines addImageToStoryboard inside its closure.
        // We need to capture it by re‑evaluating? Actually, the original storyboard
        // script defines addImageToStoryboard as an async function inside its own scope.
        // We can't access it directly. Instead, we'll inject a modified version of
        // the storyboard that exposes the function.
        // But that's messy. Instead, we'll override the storyboard's global button
        // creation with our own that directly manipulates the storyboard's data array.
        
        // Alternative: since the storyboard uses a global variable `storyboardImages`
        // which is also inside the same closure, we can't access it either.
        // So let's re‑declare the storyboard with exposed functions.
        
        // Check if the storyboard modal exists and if fabric is loaded
        if (typeof fabric !== 'undefined' && document.getElementById('storyboardCanvas')) {
            clearInterval(checkInterval);
            
            // Expose necessary functions globally
            window.storyboardImages = window.storyboardImages || [];
            window.displayCanvas = null;
            
            window.addImageToStoryboard = async function(imgSrc) {
                if (window.storyboardImages.some(i => i.src === imgSrc)) {
                    alert("Image already in storyboard");
                    return;
                }
                try {
                    const img = await new Promise((resolve, reject) => {
                        const i = new Image();
                        i.crossOrigin = "Anonymous";
                        i.onload = () => resolve(i);
                        i.onerror = reject;
                        i.src = imgSrc;
                    });
                    const aspect = img.width / img.height;
                    const displayWidth = 200;
                    const displayHeight = displayWidth / aspect;
                    window.storyboardImages.push({
                        src: imgSrc,
                        width: img.width,
                        height: img.height,
                        left: 50,
                        top: 50,
                        scaleX: displayWidth / img.width,
                        scaleY: displayHeight / img.height,
                        fabricObject: null
                    });
                    if (window.displayCanvas) {
                        const fabricImg = new fabric.Image(img, {
                            left: 50, top: 50,
                            scaleX: displayWidth / img.width,
                            scaleY: displayHeight / img.height,
                            hasControls: true, hasBorders: true, lockRotation: true
                        });
                        window.storyboardImages[window.storyboardImages.length-1].fabricObject = fabricImg;
                        window.displayCanvas.add(fabricImg);
                        window.displayCanvas.renderAll();
                    }
                    updateThumbnailsWrapper();
                } catch(e) {
                    alert("Failed to load image: "+e.message);
                }
            };
            
            function updateThumbnailsWrapper() {
                const container = document.getElementById('storyboardThumbnails');
                if (!container) return;
                container.innerHTML = window.storyboardImages.map((img, idx) =>
                    `<img class="storyboard-thumb" src="${img.src}" data-index="${idx}" style="cursor:pointer;">`
                ).join('');
                document.querySelectorAll('.storyboard-thumb').forEach(thumb => {
                    thumb.addEventListener('click', (e) => {
                        const idx = parseInt(thumb.dataset.index);
                        if (!isNaN(idx)) {
                            window.storyboardImages.splice(idx,1);
                            if (window.displayCanvas) {
                                window.displayCanvas.clear();
                                window.storyboardImages.forEach(item => {
                                    if (item.fabricObject) window.displayCanvas.add(item.fabricObject);
                                });
                                window.displayCanvas.renderAll();
                            }
                            updateThumbnailsWrapper();
                        }
                    });
                });
            }
            
            // Hook into existing canvas if already created
            const canvasEl = document.getElementById('storyboardCanvas');
            if (canvasEl && !window.displayCanvas) {
                window.displayCanvas = new fabric.Canvas('storyboardCanvas');
                window.displayCanvas.setDimensions({ width: 1080, height: 1440 });
                window.displayCanvas.on('object:modified', (e) => {
                    const obj = e.target;
                    const idx = window.storyboardImages.findIndex(item => item.fabricObject === obj);
                    if (idx !== -1) {
                        window.storyboardImages[idx].left = obj.left;
                        window.storyboardImages[idx].top = obj.top;
                        window.storyboardImages[idx].scaleX = obj.scaleX;
                        window.storyboardImages[idx].scaleY = obj.scaleY;
                    }
                });
                window.storyboardImages.forEach(item => {
                    if (item.fabricObject) window.displayCanvas.add(item.fabricObject);
                });
                window.displayCanvas.renderAll();
            }
            
            // Add buttons to all images
            function addButtonToImage(img, src) {
                if (!src || img.parentElement.querySelector('.storyboard-add-btn')) return;
                const btn = document.createElement('button');
                btn.className = 'storyboard-add-btn';
                btn.innerHTML = '📌 Add to Storyboard';
                btn.style.cssText = 'position:absolute; bottom:8px; right:8px; background:#3b82f6; color:white; border:none; border-radius:20px; padding:4px 12px; font-size:0.7rem; cursor:pointer; z-index:10;';
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (typeof window.addImageToStoryboard === 'function') {
                        window.addImageToStoryboard(src);
                    } else {
                        alert('Storyboard not ready');
                    }
                });
                let container = img.closest('.card, .timeline-card') || img.parentElement;
                if (getComputedStyle(container).position === 'static') container.style.position = 'relative';
                container.appendChild(btn);
            }
            
            function scanImages() {
                document.querySelectorAll('.card img, .timeline-card img, .carousel-item, .card-media').forEach(img => {
                    if (img.src && !img.src.startsWith('data:')) addButtonToImage(img, img.src);
                });
            }
            
            scanImages();
            const observer = new MutationObserver(() => scanImages());
            observer.observe(document.getElementById('galleryGrid') || document.body, { childList: true, subtree: true });
        }
    }, 200);
})();
</script>
"""

def apply_patch():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup
    with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Remove any previous broken patch attempts (look for our markers)
    # We'll insert the patch right before </body>
    if "final_storyboard_fix" in content:
        # Remove previous fixes to avoid conflicts
        content = re.sub(r'<script>\s*// Wait for the storyboard.*?</script>\s*', '', content, flags=re.DOTALL)
    
    # Insert the new patch before </body>
    new_content = content.replace('</body>', PATCH_SCRIPT + '\n</body>')
    
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Patched {HTML_PATH}")
    print(f"📁 Backup saved as {BACKUP_PATH}")

if __name__ == "__main__":
    apply_patch()