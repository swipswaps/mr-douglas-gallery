#!/usr/bin/env python3
"""
Patch storyboard to add buttons to ALL images (gallery cards + timeline thumbs)
"""

from pathlib import Path

HTML_PATH = Path("index_cloud.html")
BACKUP_PATH = Path("index_cloud_buttons_backup.html")

# The JavaScript patch that replaces enableImageSelection()
PATCH_SCRIPT = """
    // ===== PATCHED: Add storyboard buttons to all images =====
    function enableImageSelection() {
        // Helper to add button to a single image element
        function addButtonToImage(img, src) {
            if (!src) return;
            // Avoid duplicate buttons
            if (img.parentElement.querySelector('.storyboard-add-btn')) return;
            const btn = document.createElement('button');
            btn.className = 'storyboard-add-btn';
            btn.innerHTML = '📌 Add to Storyboard';
            btn.style.position = 'absolute';
            btn.style.bottom = '8px';
            btn.style.right = '8px';
            btn.style.background = '#3b82f6';
            btn.style.color = 'white';
            btn.style.border = 'none';
            btn.style.borderRadius = '20px';
            btn.style.padding = '4px 12px';
            btn.style.fontSize = '0.7rem';
            btn.style.cursor = 'pointer';
            btn.style.zIndex = '10';
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                addImageToStoryboard(src);
            });
            // Make the container relatively positioned
            let container = img.closest('.card, .timeline-card, .card-content, .timeline-card');
            if (!container) container = img.parentElement;
            if (getComputedStyle(container).position === 'static') container.style.position = 'relative';
            container.appendChild(btn);
        }

        // Scan for all images in .card and .timeline-card
        function scanAndAddButtons() {
            // Gallery images inside .card
            document.querySelectorAll('.card img, .card .carousel-item, .card-media').forEach(img => {
                let src = img.src;
                if (src && !src.startsWith('data:')) addButtonToImage(img, src);
            });
            // Timeline images inside .timeline-card
            document.querySelectorAll('.timeline-card img').forEach(img => {
                let src = img.src;
                if (src && !src.startsWith('data:')) addButtonToImage(img, src);
            });
        }

        // Initial scan
        scanAndAddButtons();

        // Watch for dynamically loaded content (e.g., lazy-loaded gallery)
        const observer = new MutationObserver(() => scanAndAddButtons());
        const targetNode = document.getElementById('galleryGrid') || document.body;
        observer.observe(targetNode, { childList: true, subtree: true });
    }
"""

def patch_file():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if "PATCHED: Add storyboard buttons" in content:
        print("Already patched. Exiting.")
        return

    # Find the old enableImageSelection function and replace it
    import re
    # Match from "function enableImageSelection() {" to its closing "}"
    pattern = r'(function enableImageSelection\(\) \{[^}]+\})'
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, PATCH_SCRIPT.strip(), content, flags=re.DOTALL)
    else:
        # If not found, just append the patch at the end of the script section
        new_content = content.replace('// Wait for DOM', PATCH_SCRIPT + '\n\n    // Wait for DOM')

    # Backup
    with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"✅ Patched {HTML_PATH}")
    print(f"📁 Backup saved as {BACKUP_PATH}")

if __name__ == "__main__":
    patch_file()