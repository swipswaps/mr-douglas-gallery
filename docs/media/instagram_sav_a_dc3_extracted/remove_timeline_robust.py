#!/usr/bin/env python3
from pathlib import Path
import re

html = Path("index_cloud.html").read_text(encoding='utf-8')

# Method 1: Find the timeline container and use a stack to remove it
lines = html.splitlines()
new_lines = []
in_timeline = False
depth = 0
timeline_start_pattern = re.compile(r'<div\s+class="timeline-container"')

for line in lines:
    if not in_timeline:
        if timeline_start_pattern.search(line):
            in_timeline = True
            depth = 1
            # Also find all opening divs in this line
            depth += line.count('<div') - line.count('</div')
            # Skip adding this line
            continue
        else:
            new_lines.append(line)
    else:
        # Count divs inside this line
        depth += line.count('<div')
        depth -= line.count('</div')
        if depth <= 0:
            in_timeline = False
        # else: skip line

# Write back
Path("index_cloud.html").write_text('\n'.join(new_lines), encoding='utf-8')
print("Robust removal done.")