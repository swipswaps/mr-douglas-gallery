#!/usr/bin/env python3
"""
Final: restore full gallery (from backup), fix timeline paths, remove duplicates,
place timeline above word cloud, and ensure storyboard checkboxes work everywhere.
"""

import re
from pathlib import Path
import shutil

# Use the best backup that has full gallery (784KB)
SOURCE = Path("index_cloud_final_backup.html")
TARGET = Path("index_cloud.html")
BACKUP = Path("index_cloud_before_final_fix.html")

if not SOURCE.exists():
    print("Error: index_cloud_final_backup.html not found.")
    print("Available backups:", list(Path(".").glob("index_cloud*backup*.html")))
    exit(1)

# 1. Copy the full gallery backup to target
shutil.copy(SOURCE, BACKUP)
shutil.copy(SOURCE, TARGET)

print(f"✅ Restored full gallery from {SOURCE}")

# 2. Read the file
with open(TARGET, 'r', encoding='utf-8') as f:
    content = f.read()

# 3. Remove ALL existing timeline containers (to avoid duplicates)
content = re.sub(r'<div class="timeline-container">.*?</div>\s*</div>\s*', '', content, flags=re.DOTALL)
content = re.sub(r'<!-- ========== CLEAN TIMELINE ========== -->.*?<div class="timeline-scroll".*?</div>\s*</div>\s*', '', content, flags=re.DOTALL)

# 4. Create a clean, single timeline block that uses /timeline/ paths
clean_timeline = '''
<!-- ========== SINGLE TIMELINE (above word cloud) ========== -->
<style>
.timeline-container {
    background: #f8f9fa;
    border-radius: 1rem;
    padding: 1rem;
    margin: 1rem 0 2rem 0;
    clear: both;
}
.timeline-header {
    font-size: 1.2rem;
    font-weight: bold;
    margin-bottom: 1rem;
}
.timeline-scroll {
    display: flex;
    overflow-x: auto;
    gap: 1rem;
    padding: 0.5rem 0;
    scrollbar-width: thin;
}
.timeline-card {
    flex: 0 0 auto;
    width: 150px;
    text-align: center;
    cursor: pointer;
    background: white;
    border-radius: 0.75rem;
    padding: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    position: relative;
}
.timeline-card img {
    width: 100%;
    aspect-ratio: 4/3;
    object-fit: cover;
    border-radius: 0.5rem;
    background: #e2e8f0;
}
.timeline-year {
    font-weight: bold;
    margin: 0.25rem 0;
}
.timeline-title {
    font-size: 0.7rem;
    color: #334155;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>
<div class="timeline-container">
    <div class="timeline-header">✈️ Mr. Douglas Through the Years</div>
    <div class="timeline-scroll" id="timelineScroll"></div>
</div>
<script>
(function() {
    const images = [
        { year: "1941", title: "United Mr Douglas 1941", src: "timeline/United-mr-douglas-1941.jpg" },
        { year: "1942", title: "United Flying 1942", src: "timeline/united-flying-1942.jpg" },
        { year: "1943", title: "Western 1943", src: "timeline/western-1943.jpg" },
        { year: "1952", title: "Mr Douglas 1952", src: "timeline/mr-douglas-1952.jpg" },
        { year: "1960", title: "Mr Douglas 1960", src: "timeline/mr-douglas-1960.jpg" },
        { year: "1970", title: "Mr Douglas 1970", src: "timeline/mr-douglas-1970.jpg" },
        { year: "1974", title: "Mr Douglas 1974", src: "timeline/mr-douglas-1974.jpg" },
        { year: "1979", title: "Mr Douglas 1979", src: "timeline/mr-douglas-1979.jpg" },
        { year: "1984", title: "Mr Douglas 1984", src: "timeline/mr-douglas-1984-1400x790-slider.jpg" },
        { year: "1988", title: "Mr Douglas 1988", src: "timeline/mr-douglas-1988.jpg" },
        { year: "1990", title: "Mr Douglas 1990", src: "timeline/mr-douglas-1990.jpg" },
        { year: "1992", title: "Mr Douglas 1992", src: "timeline/mr-douglas-1992.jpg" },
        { year: "1996", title: "Mr Douglas 1996", src: "timeline/mr-douglas-1996.jpg" },
        { year: "2018", title: "Drone Front", src: "timeline/Mr-Douglas-2018-drone-front-pix-slider.jpg" }
    ];
    const container = document.getElementById('timelineScroll');
    if (container) {
        container.innerHTML = images.map(img => `
            <div class="timeline-card" data-src="${img.src}">
                <img src="${img.src}" loading="lazy" onerror="this.src='data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Crect%20width%3D%22100%22%20height%3D%22100%22%20fill%3D%22%23cbd5e1%22%2F%3E%3Ctext%20x%3D%2250%22%20y%3D%2255%22%20text-anchor%3D%22middle%22%20fill%3D%22%23475569%22%3E%F0%9F%93%B8%3C%2Ftext%3E%3C%2Fsvg%3E';">
                <div class="timeline-year">${img.year}</div>
                <div class="timeline-title">${img.title}</div>
            </div>
        `).join('');
    }
})();
</script>
'''

# 5. Insert the timeline just above the word cloud container
wordcloud_pattern = r'(<div class="word-cloud-container"|id="wordcloud"|class="wordcloud-wrap")'
match = re.search(wordcloud_pattern, content)
if match:
    insert_pos = match.start()
    new_content = content[:insert_pos] + clean_timeline + '\n' + content[insert_pos:]
else:
    # Fallback: insert before the gallery grid
    gallery_marker = r'(<div class="gallery-grid"|id="galleryGrid")'
    match2 = re.search(gallery_marker, content)
    if match2:
        insert_pos = match2.start()
        new_content = content[:insert_pos] + clean_timeline + '\n' + content[insert_pos:]
    else:
        print("Could not find insertion point. Timeline not moved.")
        new_content = content

# 6. Ensure storyboard checkbox observer covers both gallery and timeline images.
# The existing storyboard script (still present) already tries to add checkboxes.
# We'll add a small patch to make it more reliable.
patch_script = '''
<script>
(function() {
    // Ensure checkboxes are added to ALL images (gallery + timeline) after page fully loads
    function addCheckboxesToAllCards() {
        document.querySelectorAll('.card, .timeline-card, .carousel-item').forEach(card => {
            // If card already has a checkbox, skip
            if (card.querySelector('.select-checkbox')) return;
            const img = card.querySelector('img, .carousel-item');
            if (!img || !img.src || img.src.startsWith('data:')) return;
            const chk = document.createElement('input');
            chk.type = 'checkbox';
            chk.className = 'select-checkbox';
            chk.style.cssText = 'position:absolute; top:8px; left:8px; width:20px; height:20px; z-index:5; cursor:pointer; background:white; border-radius:4px;';
            chk.addEventListener('change', (e) => {
                e.stopPropagation();
                // Update the global selected count if the storyboard script already defines it
                if (window.selectedSrcs) {
                    if (chk.checked) window.selectedSrcs.add(img.src);
                    else window.selectedSrcs.delete(img.src);
                    const countSpan = document.getElementById('selectedCount');
                    if (countSpan) countSpan.innerText = (window.selectedSrcs ? window.selectedSrcs.size : 0) + ' selected';
                }
            });
            if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
            card.appendChild(chk);
        });
    }
    // Run initially and observe changes
    addCheckboxesToAllCards();
    const observer = new MutationObserver(addCheckboxesToAllCards);
    observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
'''
new_content = new_content.replace('</body>', patch_script + '\n</body>')

# 7. Write the final file
with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Final fix complete.")
print("📁 Backup of previous state saved as", BACKUP)
print("💡 Now start the server: python -m http.server 8000")
print("   Then hard refresh (Ctrl+Shift+R).")