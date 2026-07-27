#!/usr/bin/env python3
"""
Extract Instagram-style @usernames from the caption and add an 'author' field.
Displays the author above the caption without the '@' symbol.
"""

import re
import json
from pathlib import Path

SOURCE = Path("index_working.html")
TARGET = Path("index_with_at_authors.html")

def extract_at_username(caption):
    """Extract first @username from the caption, return username without @."""
    match = re.search(r'@([\w\.]+)', caption)
    if match:
        return match.group(1)
    return None

print("Reading", SOURCE)
with open(SOURCE, 'r', encoding='utf-8') as f:
    content = f.read()

# Locate allPosts array
match = re.search(r'const allPosts = (\[[\s\S]*?\]);', content)
if not match:
    print("Could not find allPosts array.")
    exit(1)

all_posts = json.loads(match.group(1))
print(f"Loaded {len(all_posts)} posts")

modified = False
for post in all_posts:
    caption = post.get('caption', '')
    username = extract_at_username(caption)
    if username:
        post['author'] = username
        print(f"Extracted @{username} for {post.get('shortcode', 'unknown')}")
        modified = True
    else:
        # fallback to first word (only if no @-mention)
        first_word = caption.split()[0] if caption else "unknown"
        # ignore common stop words
        if first_word.lower() in [
            'the', 'a', 'i', 'we', 'you', 'he', 'she', 'it', 'they', 'we',
            'to', 'for', 'of', 'and', 'in', 'on', 'at', 'by', 'with', 'from',
            'up', 'down', 'out', 'over', 'under', 'again', 'then', 'once',
            'here', 'there', 'all', 'any', 'both', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
            'own', 'same', 'than', 'too', 'very', 'just', 'but', 'do', 'does',
            'did', 'doing', 'have', 'has', 'had', 'having', 'can', 'will'
        ]:
            first_word = "unknown"
        post['author'] = first_word
        print(f"Fallback: '{first_word}' for {post.get('shortcode', 'unknown')}")

if not modified:
    print("No @usernames found. Some posts may have fallback authors.")

# Replace allPosts array with updated JSON
start_marker = "const allPosts = "
start_idx = content.find(start_marker)
if start_idx == -1:
    print("Assignment not found")
    exit(1)

bracket_start = content.find('[', start_idx)
depth = 0
end_idx = bracket_start
for i in range(bracket_start, len(content)):
    ch = content[i]
    if ch == '[':
        depth += 1
    elif ch == ']':
        depth -= 1
        if depth == 0:
            if content[i+1:i+3] == '];':
                end_idx = i + 2
                break
            elif content[i+1] == ';':
                end_idx = i + 1
                break
new_json = json.dumps(all_posts, indent=2)
new_content = content[:bracket_start] + new_json + content[end_idx:]

# Modify the renderGallery function to insert author line above caption.
# We'll replace the `<div class="card-caption">` with author + caption.
author_line = '<div class="card-author" style="font-size:0.8rem; font-weight:bold; color:#60a5fa;">${post.author}</div>\n<div class="card-caption">'
new_content = new_content.replace('<div class="card-caption">', author_line)

with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"\n✅ Usernames (from @mentions) added. Saved to {TARGET}")
print("💡 Start server: python -m http.server 8000")
print(f"   Open http://localhost:8000/{TARGET.name}")