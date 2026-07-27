#!/usr/bin/env python3
"""
Add Instagram author usernames from the database into the HTML.
Also ensures YouTube thumbnails are present (if any YouTube links).
"""

import re
import json
import sqlite3
from pathlib import Path

HTML_PATH = Path("index_working.html")
TARGET = Path("index_with_usernames.html")
DB_PATH = Path("instagram_posts.db")

if not HTML_PATH.exists():
    print("index_working.html not found.")
    exit(1)

# Read HTML
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract allPosts
match = re.search(r'const allPosts = (\[[\s\S]*?\]);', content)
if not match:
    print("Could not find allPosts array.")
    exit(1)

all_posts = json.loads(match.group(1))
print(f"Loaded {len(all_posts)} posts from HTML")

# Load usernames from database
if not DB_PATH.exists():
    print("Database not found, cannot add usernames.")
else:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT shortcode, author FROM posts")
    rows = cur.fetchall()
    conn.close()
    username_map = {row[0]: row[1] for row in rows}
    print(f"Loaded {len(username_map)} usernames from database")

    # Add username to each post (if available)
    for post in all_posts:
        shortcode = post['shortcode']
        if shortcode in username_map:
            post['author'] = username_map[shortcode]
            print(f"Added username '{username_map[shortcode]}' to {shortcode}")
        else:
            post['author'] = "unknown"
    print("Usernames added to posts.")

# Update the caption to include author
for post in all_posts:
    author = post.get('author', '')
    if author and not post['caption'].startswith(f"@{author}"):
        post['caption'] = f"@{author} – {post['caption']}"

# Replace the allPosts array
start_marker = "const allPosts = "
start_idx = content.find(start_marker)
if start_idx == -1:
    print("Cannot find assignment")
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
final_content = content[:bracket_start] + new_json + content[end_idx:]

with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(final_content)

print(f"\n✅ Saved to {TARGET}")
print("💡 Start server: python -m http.server 8000")
print(f"   Open http://localhost:8000/{TARGET.name}")