#!/usr/bin/env python3
"""
Add missing YouTube thumbnails to index_working.html.
Also ensures storyboard handles are preserved.
"""

import re
import json
import requests
from pathlib import Path

SOURCE = Path("index_working.html")
TARGET = Path("index_complete.html")
YOUTUBE_DIR = Path("youtube_thumbs")
YOUTUBE_DIR.mkdir(exist_ok=True)

def extract_youtube_id(text):
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]+)',
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(1)
    return None

def download_thumbnail(yt_id):
    thumb_path = YOUTUBE_DIR / f"{yt_id}.jpg"
    if thumb_path.exists():
        return thumb_path
    for quality in ['maxresdefault', 'hqdefault', 'mqdefault']:
        url = f"https://img.youtube.com/vi/{yt_id}/{quality}.jpg"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                with open(thumb_path, 'wb') as f:
                    f.write(resp.content)
                print(f"✅ Downloaded: {thumb_path}")
                return thumb_path
        except:
            continue
    print(f"⚠️ Failed to download thumbnail for {yt_id}")
    return None

# Read the HTML
with open(SOURCE, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract allPosts array
match = re.search(r'const allPosts = (\[[\s\S]*?\]);', content)
if not match:
    print("Could not find allPosts array.")
    exit(1)

all_posts = json.loads(match.group(1))
print(f"📦 Loaded {len(all_posts)} posts")

modified = False
for post in all_posts:
    caption = post.get('caption', '')
    yt_id = extract_youtube_id(caption)
    if yt_id:
        thumb = download_thumbnail(yt_id)
        if thumb:
            thumb_rel = f"youtube_thumbs/{yt_id}.jpg"
            if thumb_rel not in post.get('all_media', []):
                post['all_media'].append(thumb_rel)
                modified = True
                print(f"➕ Added YouTube thumbnail to post {post.get('shortcode')}")
            else:
                print(f"⏩ YouTube thumbnail already present for {post.get('shortcode')}")

if not modified:
    print("No new YouTube thumbnails added.")
else:
    # Replace the allPosts array safely (count brackets)
    start_marker = "const allPosts = "
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("Could not find assignment")
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
                # Look for '];' or ';'
                if content[i+1:i+3] == '];':
                    end_idx = i + 2
                    break
                elif content[i+1] == ';':
                    end_idx = i + 1
                    break
            elif depth < 0:
                print("Mismatched brackets")
                exit(1)
    new_allposts_json = json.dumps(all_posts, indent=2)
    new_content = content[:bracket_start] + new_allposts_json + content[end_idx:]

    # Write the final HTML
    with open(TARGET, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"\n✅ Saved complete gallery to {TARGET}")
    print("💡 Start the server and open it:")
    print(f"   python -m http.server 8000")
    print(f"   http://localhost:8000/{TARGET.name}")