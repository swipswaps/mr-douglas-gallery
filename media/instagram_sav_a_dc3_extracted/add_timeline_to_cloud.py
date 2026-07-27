#!/usr/bin/env python3
"""
Add an interactive, horizontal timeline (from historical slideshow images)
above the word cloud in index_cloud.html.
Now copies images into a local 'timeline' folder to avoid 404s.
"""

import re
import shutil
from pathlib import Path

HTML_PATH = Path("index_cloud.html")
BACKUP_PATH = Path("index_cloud_backup.html")
TIMELINE_DIR = Path("timeline")          # local folder for timeline images

# Directories to scan for historical slideshow images
IMAGE_DIRS = [
    Path(".."),                     # ../mr-douglas-1941.jpg etc.
    Path("../notes"),               # ../notes/World Meet Z Hills 1981_...jpg
]

def extract_year(filename):
    """Extract 4-digit year from filename."""
    match = re.search(r'\b(19|20)\d{2}\b', filename)
    return match.group(0) if match else None

def build_timeline_data():
    """Scan directories, collect images with years, sort by year, copy to local folder."""
    TIMELINE_DIR.mkdir(exist_ok=True)
    items = []  # (year, title, relative_path_inside_timeline_dir)
    for img_dir in IMAGE_DIRS:
        if not img_dir.exists():
            continue
        for img_path in img_dir.glob("*.jpg"):
            year = extract_year(img_path.stem)
            if not year:
                continue
            # Create a readable title from filename
            title = img_path.stem.replace("_", " ").replace("-", " ").title()
            # Destination path inside timeline folder
            dest = TIMELINE_DIR / img_path.name
            # Copy if not already there (or overwrite)
            if not dest.exists():
                shutil.copy2(img_path, dest)
            # Relative path for web: "timeline/filename.jpg"
            rel_path = f"timeline/{img_path.name}"
            items.append((year, title, rel_path))
    # Sort by year
    items.sort(key=lambda x: int(x[0]))
    # Remove duplicates (keep first)
    seen = set()
    unique = []
    for y, t, p in items:
        if y not in seen:
            seen.add(y)
            unique.append((y, t, p))
    return unique

def generate_timeline_html(items):
    """Generate the HTML/CSS/JS for the timeline."""
    if not items:
        return "<!-- No timeline images found -->"

    timeline_items_js = ",\n    ".join(
        f'{{ year: "{y}", title: "{t.replace('"', '\\"')}", image: "{p}" }}'
        for y, t, p in items
    )

    return f"""
<!-- Timeline Section (inserted automatically) -->
<style>
.timeline-container {{
    background: #f8f9fa;
    border-radius: 1rem;
    padding: 1rem;
    margin-bottom: 2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}}
.timeline-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 1rem;
    padding: 0 0.5rem;
}}
.timeline-header h3 {{
    margin: 0;
    color: #0f172a;
}}
.timeline-controls {{
    display: flex;
    gap: 0.5rem;
}}
.timeline-btn {{
    background: #334155;
    border: none;
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 0.5rem;
    cursor: pointer;
    font-size: 0.9rem;
}}
.timeline-btn:hover {{
    background: #1e293b;
}}
.timeline-scroll {{
    display: flex;
    overflow-x: auto;
    gap: 1rem;
    padding: 0.5rem 0.5rem 1rem;
    scroll-behavior: smooth;
}}
.timeline-card {{
    flex: 0 0 auto;
    width: 150px;
    text-align: center;
    cursor: pointer;
    transition: transform 0.2s;
    background: white;
    border-radius: 0.75rem;
    padding: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}}
.timeline-card:hover {{
    transform: translateY(-5px);
    background: #f1f5f9;
}}
.timeline-card img {{
    width: 100%;
    aspect-ratio: 4/3;
    object-fit: cover;
    border-radius: 0.5rem;
    background: #e2e8f0;
}}
.timeline-year {{
    font-weight: bold;
    font-size: 1rem;
    margin: 0.25rem 0;
    color: #0f172a;
}}
.timeline-title {{
    font-size: 0.7rem;
    color: #334155;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.timeline-modal {{
    display: none;
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.9);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    flex-direction: column;
}}
.timeline-modal.active {{
    display: flex;
}}
.timeline-modal-content {{
    max-width: 90vw;
    max-height: 85vh;
    background: #0f172a;
    padding: 1rem;
    border-radius: 1rem;
    text-align: center;
}}
.timeline-modal img {{
    max-width: 100%;
    max-height: 70vh;
    border-radius: 0.5rem;
}}
.timeline-modal-caption {{
    color: white;
    margin-top: 1rem;
    font-size: 1rem;
}}
.timeline-modal-close {{
    position: absolute;
    top: 20px;
    right: 30px;
    font-size: 2rem;
    color: white;
    cursor: pointer;
}}
</style>

<div class="timeline-container">
    <div class="timeline-header">
        <h3>✈️ Mr. Douglas Through the Years</h3>
        <div class="timeline-controls">
            <button class="timeline-btn" id="timelinePrevBtn">◀ Prev</button>
            <button class="timeline-btn" id="timelineNextBtn">Next ▶</button>
        </div>
    </div>
    <div class="timeline-scroll" id="timelineScroll"></div>
</div>

<div id="timelineModal" class="timeline-modal">
    <span class="timeline-modal-close" id="timelineModalClose">&times;</span>
    <div class="timeline-modal-content">
        <img id="timelineModalImg" src="" alt="">
        <div class="timeline-modal-caption" id="timelineModalCaption"></div>
    </div>
</div>

<script>
(function() {{
    const timelineData = [
        {timeline_items_js}
    ];

    function renderTimeline() {{
        const container = document.getElementById('timelineScroll');
        if (!container) return;
        container.innerHTML = timelineData.map((item, idx) => `
            <div class="timeline-card" data-index="${{idx}}">
                <img src="${{item.image}}" loading="lazy" onerror="this.src='data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Crect%20width%3D%22100%22%20height%3D%22100%22%20fill%3D%22%23cbd5e1%22%2F%3E%3Ctext%20x%3D%2250%22%20y%3D%2255%22%20text-anchor%3D%22middle%22%20fill%3D%22%23475569%22%3E%F0%9F%93%B8%3C%2Ftext%3E%3C%2Fsvg%3E';">
                <div class="timeline-year">${{item.year}}</div>
                <div class="timeline-title">${{item.title.length > 25 ? item.title.slice(0,22)+'…' : item.title}}</div>
            </div>
        `).join('');

        document.querySelectorAll('.timeline-card').forEach(card => {{
            card.addEventListener('click', (e) => {{
                const idx = parseInt(card.getAttribute('data-index'));
                const item = timelineData[idx];
                const modal = document.getElementById('timelineModal');
                const modalImg = document.getElementById('timelineModalImg');
                const modalCaption = document.getElementById('timelineModalCaption');
                modalImg.src = item.image;
                modalImg.onerror = () => modalImg.src = 'data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20100%20100%22%3E%3Crect%20width%3D%22100%22%20height%3D%22100%22%20fill%3D%22%235c6ac4%22%2F%3E%3Ctext%20x%3D%2250%22%20y%3D%2255%22%20text-anchor%3D%22middle%22%20fill%3D%22white%22%3E%E2%9D%8C%3C%2Ftext%3E%3C%2Fsvg%3E';
                modalCaption.innerText = `${{item.year}} – ${{item.title}}`;
                modal.classList.add('active');
            }});
        }});
    }}

    function scrollToIndex(index) {{
        const cards = document.querySelectorAll('.timeline-card');
        if (cards[index]) cards[index].scrollIntoView({{ behavior: 'smooth', block: 'nearest', inline: 'center' }});
    }}

    let currentFocus = 0;
    function updateFocus(delta) {{
        const cards = document.querySelectorAll('.timeline-card');
        if (!cards.length) return;
        currentFocus = Math.min(Math.max(0, currentFocus + delta), cards.length - 1);
        scrollToIndex(currentFocus);
        cards[currentFocus].style.transform = 'scale(1.05)';
        setTimeout(() => {{ cards[currentFocus].style.transform = ''; }}, 300);
    }}

    document.getElementById('timelinePrevBtn')?.addEventListener('click', () => updateFocus(-1));
    document.getElementById('timelineNextBtn')?.addEventListener('click', () => updateFocus(1));

    // Close modal
    const modal = document.getElementById('timelineModal');
    document.getElementById('timelineModalClose')?.addEventListener('click', () => modal.classList.remove('active'));
    window.addEventListener('click', (e) => {{ if (e.target === modal) modal.classList.remove('active'); }});

    renderTimeline();
}})();
</script>
"""

def inject_timeline_into_html(html_path, timeline_html):
    """Read HTML, find the word cloud container and insert timeline before it."""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Insert above the word cloud area
    match = re.search(r'(<div class="word-cloud-container">|<div id="wordcloud"|class="wordcloud-wrap")', content)
    if not match:
        # Fallback: insert before the gallery grid
        match = re.search(r'(<div class="gallery-grid"|id="galleryGrid")', content)
        if not match:
            print("Could not locate insertion point. Timeline not added.")
            return False

    insert_pos = match.start()
    new_content = content[:insert_pos] + timeline_html + "\n" + content[insert_pos:]
    
    shutil.copy(html_path, BACKUP_PATH)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True

def main():
    print("🔍 Scanning for historical slideshow images...")
    timeline_items = build_timeline_data()
    if not timeline_items:
        print("No images with years found in ../ or ../notes/. Timeline not added.")
        return

    print(f"✅ Found {len(timeline_items)} timeline images (sorted by year).")
    print(f"📁 Copied images to '{TIMELINE_DIR}/' folder for serving.")
    timeline_html = generate_timeline_html(timeline_items)
    
    print("📝 Adding timeline to index_cloud.html...")
    if inject_timeline_into_html(HTML_PATH, timeline_html):
        print(f"✅ Done! Original backed up to {BACKUP_PATH}")
        print("💡 Open http://localhost:8000/index_cloud.html and scroll to see the timeline above the word cloud.")
    else:
        print("❌ Failed to inject timeline.")

if __name__ == "__main__":
    main()