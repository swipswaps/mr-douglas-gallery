#!/usr/bin/env python3
"""
Enhance storyboard: ensure all images have resize handles, canvas selection enabled,
and add a small helper to show instructions.
"""

from pathlib import Path

SOURCE = Path("index_working.html")
TARGET = Path("index_final.html")

if not SOURCE.exists():
    print("index_working.html not found.")
    exit(1)

with open(SOURCE, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the storyboard script's initCanvas function and enhance it
enhance_script = """
    // Ensure selection and controls are enabled
    function initCanvas() {
        const canvas = document.getElementById('storyboardCanvas');
        if (!canvas) return;
        window.displayCanvas = new fabric.Canvas('storyboardCanvas');
        window.displayCanvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
        window.displayCanvas.selection = true;
        window.displayCanvas.preserveObjectStacking = true;  // better layering
        // Customize control corner style (larger, colored)
        fabric.Object.prototype.set({
            borderColor: '#3b82f6',
            cornerColor: '#3b82f6',
            cornerSize: 8,
            transparentCorners: false,
            borderScaleFactor: 2,
            hasRotatingPoint: false   // disable rotation if not needed
        });
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
"""

# Replace the existing initCanvas function
import re
pattern = r'function initCanvas\(\) \{.*?\n *\}'
new_content = re.sub(pattern, enhance_script, content, flags=re.DOTALL)

# Also ensure that images are added with hasControls explicitly true (they already are, but enforce)
# We'll also add a small instruction box
instruction_html = '''
<div style="position:fixed; bottom:80px; left:20px; background:#1e293b; padding:8px 12px; border-radius:8px; font-size:0.7rem; color:#94a3b8; z-index:999;">
💡 Tip: Click any image in the storyboard to resize or move it. Drag corners to scale.
</div>
'''
new_content = new_content.replace('</body>', instruction_html + '\n</body>')

# Write final file
with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"✅ Enhanced storyboard saved as {TARGET}")
print("💡 Start server: python -m http.server 8000")
print(f"   Open http://localhost:8000/{TARGET.name}")