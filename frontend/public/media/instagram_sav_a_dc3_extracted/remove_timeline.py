#!/usr/bin/env python3
import re
from pathlib import Path

html = Path("index_cloud.html").read_text(encoding='utf-8')

# Remove the timeline container (including any nested divs)
# This pattern matches from <div class="timeline-container"> to the next </div> that closes it.
# It assumes the timeline container has a unique class and is not nested inside another timeline.
html = re.sub(r'<div class="timeline-container">.*?</div>\s*</div>', '', html, flags=re.DOTALL)

# Also remove any leftover timeline header or script that creates timeline
html = re.sub(r'<!-- ==========.*?TIMELINE.*?-->.*?<div class="timeline-scroll".*?</div>\s*</div>\s*', '', html, flags=re.DOTALL)
html = re.sub(r'<div class="timeline-header">.*?</div>', '', html)

Path("index_cloud.html").write_text(html, encoding='utf-8')
print("Timeline removed.")