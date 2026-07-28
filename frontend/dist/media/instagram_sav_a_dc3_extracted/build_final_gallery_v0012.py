#!/usr/bin/env python3
"""
build_final_gallery_v0012.py - FIXED VERSION
"""

import json
import sqlite3
import csv
import re
import sys
import logging
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path("instagram_posts.db")
CSV_PATH = Path("posts.csv")
OUTPUT_HTML = Path("index_v0012.html")
ACCOUNT_OWNER = "sav_a_dc3"

def extract_author_from_comments(comments, caption=""):
    mention_pattern = re.compile(r'@([a-zA-Z0-9_\.]+)')
    all_mentions = []
    for comment in comments:
        if comment.startswith(('Count:', 'Reported by IG:', 'Saved:', 'Comments for')):
            continue
        mentions = mention_pattern.findall(comment)
        all_mentions.extend(mentions)
    filtered = [m for m in all_mentions if m.lower() != ACCOUNT_OWNER.lower()]
    if not filtered:
        return ACCOUNT_OWNER
    counter = Counter(filtered)
    return counter.most_common(1)[0][0]

def load_posts():
    posts = []
    if DB_PATH.exists():
        logger.info(f"Loading from {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT shortcode, date, likes, comments_count, caption, folder_name FROM posts ORDER BY date DESC")
        rows = cur.fetchall()
        for row in rows:
            post = dict(row)
            try:
                comments_rows = conn.execute("SELECT comment_text FROM comments WHERE shortcode = ?", (post['shortcode'],)).fetchall()
                post['comments'] = [c['comment_text'] for c in comments_rows]
            except sqlite3.OperationalError:
                post['comments'] = []
            folder = Path(post['folder_name'])
            all_media = []
            if folder.exists():
                all_media = sorted([f.name for f in folder.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4')])
            post['all_media'] = all_media
            post['instagram_url'] = f"https://www.instagram.com/p/{post['shortcode']}/"
            post['author'] = extract_author_from_comments(post['comments'], post.get('caption', ''))
            posts.append(post)
        conn.close()
        logger.info(f"Loaded {len(posts)} posts")
    return posts

def add_historic_images(posts):
    timeline_folder = Path("timeline")
    if timeline_folder.exists():
        for img_path in sorted(timeline_folder.glob("*.jpg")):
            year_match = re.search(r'\b(19|20)\d{2}\b', img_path.stem)
            year = year_match.group(0) if year_match else "0000"
            title = img_path.stem.replace('-', ' ').replace('_', ' ').title()
            posts.append({
                "shortcode": f"hist_{img_path.stem}",
                "date": f"{year}-07-01 12:00:00",
                "likes": 0,
                "comments_count": 0,
                "caption": f"{title} – Historic photo",
                "folder_name": "timeline",
                "all_media": [img_path.name],
                "comments": [],
                "instagram_url": "#",
                "author": "Historic"
            })
        logger.info(f"Added historic images")
    return posts

def build_html(posts):
    # Proper JSON with no extra quotes
    posts_json = json.dumps(posts, ensure_ascii=False)
    
    html = '<!DOCTYPE html>\n'
    html += '<html>\n<head>\n'
    html += '<meta charset="UTF-8">\n'
    html += '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    html += '<title>Mr. Douglas Gallery</title>\n'
    html += '<style>\n'
    html += '*{box-sizing:border-box}body{margin:0;background:#0f172a;color:#e2e8f0;font-family:system-ui}\n'
    html += '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1rem;padding:1rem}\n'
    html += '.card{background:#1e293b;border-radius:0.5rem;overflow:hidden}\n'
    html += '.card-media{width:100%;aspect-ratio:4/3;object-fit:cover}\n'
    html += '.card-content{padding:0.5rem}\n'
    html += '.author-name{color:#60a5fa}\n'
    html += '.card-meta{font-size:0.75rem;color:#94a3b8;display:flex;justify-content:space-between}\n'
    html += '.card-caption{font-size:0.875rem;margin:0.5rem 0}\n'
    html += '</style>\n'
    html += '</head>\n<body>\n'
    html += '<div id="galleryGrid" class="grid">Loading...</div>\n'
    html += '<script>\n'
    html += 'var allPosts = ' + posts_json + ';\n'
    html += 'var grid = document.getElementById("galleryGrid");\n'
    html += 'console.log("Posts count:", allPosts.length);\n'
    html += 'function renderGallery() {\n'
    html += '  var html = "";\n'
    html += '  for (var i = 0; i < allPosts.length; i++) {\n'
    html += '    var p = allPosts[i];\n'
    html += '    var media = p.all_media && p.all_media.length ? p.all_media[0] : null;\n'
    html += '    var imgSrc = p.folder_name + "/" + media;\n'
    html += '    html += "<div class=\\"card\\">";\n'
    html += '    html += "<img class=\\"card-media\\" src=\\"" + imgSrc + "\\" onerror=\\"console.error(\\\'Failed: \\\' + this.src)\\" loading=\\"lazy\\">";\n'
    html += '    html += "<div class=\\"card-content\\">";\n'
    html += '    html += "<div class=\\"card-meta\\"><span class=\\"author-name\\">@" + (p.author || "unknown") + "</span><span>" + (p.likes || 0) + " likes</span></div>";\n'
    html += '    html += "<div class=\\"card-caption\\">" + (p.caption || "").substring(0,100) + "</div>";\n'
    html += '    html += "</div></div>";\n'
    html += '  }\n'
    html += '  grid.innerHTML = html;\n'
    html += '  console.log("Rendered", allPosts.length, "cards");\n'
    html += '}\n'
    html += 'renderGallery();\n'
    html += '</script>\n'
    html += '</body>\n</html>'
    
    return html

def main():
    print("=" * 60)
    print("MR. DOUGLAS GALLERY BUILDER v0012 - SIMPLE VERSION")
    print("=" * 60)
    
    posts = load_posts()
    posts = add_historic_images(posts)
    logger.info(f"Total posts: {len(posts)}")
    
    html = build_html(posts)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    logger.info(f"Generated {OUTPUT_HTML.resolve()}")
    
    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    print(f"\nStart server: python -m http.server 8000")
    print(f"Open: http://localhost:8000/index_v0012.html")
    print("\nThen press F12 and check the Console tab for errors")

if __name__ == "__main__":
    main()