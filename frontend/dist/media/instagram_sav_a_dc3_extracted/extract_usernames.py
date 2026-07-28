#!/usr/bin/env python3
"""
Extract usernames from the caption text and add a separate 'author' field.
Display author above caption.
"""

import re
import json
from pathlib import Path

SOURCE = Path("index_working.html")
TARGET = Path("index_with_authors.html")

def extract_username(caption):
    if not caption:
        return None
    # Take first line before newline or period
    first_line = caption.split('\n')[0].strip()
    # If it looks like a name or handle (letters, spaces, @, .)
    if re.match(r'^@?[\w\s\.]+$', first_line) and len(first_line) < 40:
        return first_line
    # Otherwise take first word
    words = caption.split()
    if words:
        first_word = words[0]
        # Exclude common stop words
        if first_word.lower() not in ['the', 'a', 'i', 'we', 'you', 'he', 'she', 'it', 'they', 'we', 'to', 'for', 'of', 'and', 'in', 'on', 'at', 'by', 'with', 'from', 'up', 'down', 'out', 'over', 'under', 'again', 'then', 'once', 'here', 'there', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'than', 'too', 'very', 'just', 'but', 'do', 'does', 'did', 'doing', 'have', 'has', 'had', 'having', 'can', 'will']:
            return first_word
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
    if 'author' in post:
        continue
    caption = post.get('caption', '')
    username = extract_username(caption)
    if username:
        post['author'] = username
        print(f"Extracted '{username}' for {post.get('shortcode', 'unknown')}")
        modified = True
    else:
        post['author'] = "unknown"

if not modified:
    print("No new usernames extracted.")
    # Still update the HTML to display author (even if 'unknown')
    # But we need to update anyway to add the author field if missing.

# Replace allPosts array with new JSON
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

# Modify renderGallery to display author
# We need to find the part where card HTML is generated and insert a div for author.
# Look for the template literal that builds the card. We'll replace a specific line.
# Original has something like: return `<div class="card" ...> ... <div class="card-content"> ...`
# We'll insert author line after the card-meta div or before card-caption.
# Simpler: replace the existing card-caption line with author + caption.
author_line = '<div class="card-author" style="font-size:0.8rem; font-weight:bold; color:#60a5fa;">${post.author}</div>'
# Find the line that contains '<div class="card-caption">' and insert author above it.
# We'll do a regex replacement with a callback to avoid breaking other code.

# The pattern: `<div class="card-caption">${post.caption...}</div>`
# We'll replace with `author_line + '\n' + original`
import re
def add_author(match):
    return author_line + '\n' + match.group(0)

new_content = re.sub(r'(<div class="card-caption">[\s\S]*?</div>)', add_author, new_content)

with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"\n✅ Usernames added. Saved to {TARGET}")
print("💡 Start server: python -m http.server 8000")
print(f"   Open http://localhost:8000/{TARGET.name}")