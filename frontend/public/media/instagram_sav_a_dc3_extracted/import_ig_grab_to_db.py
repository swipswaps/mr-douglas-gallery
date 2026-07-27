#!/usr/bin/env python3
import os
import re
import sqlite3
from pathlib import Path

def parse_info_txt(filepath):
    """Extract fields from info.txt."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    data = {}
    # Use regex to capture fields
    data['url'] = re.search(r'URL: (.+)', content).group(1) if re.search(r'URL: (.+)', content) else ''
    data['date'] = re.search(r'Date: (.+)', content).group(1) if re.search(r'Date: (.+)', content) else ''
    data['type'] = re.search(r'Type: (.+)', content).group(1) if re.search(r'Type: (.+)', content) else ''
    data['likes'] = int(re.search(r'Likes: (\d+)', content).group(1)) if re.search(r'Likes: (\d+)', content) else 0
    data['comments'] = int(re.search(r'Comments: (\d+)', content).group(1)) if re.search(r'Comments: (\d+)', content) else 0
    data['location'] = re.search(r'Location: (.+)', content).group(1) if re.search(r'Location: (.+)', content) else ''
    data['items'] = int(re.search(r'Items: (\d+)', content).group(1)) if re.search(r'Items: (\d+)', content) else 0
    # Caption is everything after "Caption:" line
    caption_match = re.search(r'Caption:\n(.*?)(?=\n\n|$)', content, re.DOTALL)
    data['caption'] = caption_match.group(1).strip() if caption_match else ''
    # Shortcode from URL (e.g., /p/BqVG175ndpx/)
    shortcode_match = re.search(r'/p/([^/]+)/', data['url'])
    data['shortcode'] = shortcode_match.group(1) if shortcode_match else ''
    return data

def parse_comments_txt(filepath):
    """Return list of comment texts from comments.txt."""
    comments = []
    if not os.path.exists(filepath):
        return comments
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('--'):  # skip separators
                comments.append(line)
    return comments

def main():
    base_dir = Path('/home/owner/Documents/instagram_sav_a_dc3_extracted')
    db_path = base_dir / 'instagram_posts.db'

    # Connect to SQLite (will create file)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            shortcode TEXT PRIMARY KEY,
            url TEXT,
            date TEXT,
            type TEXT,
            likes INTEGER,
            comments_count INTEGER,
            location TEXT,
            items INTEGER,
            caption TEXT,
            folder_name TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shortcode TEXT,
            comment_text TEXT,
            FOREIGN KEY(shortcode) REFERENCES posts(shortcode)
        )
    ''')

    # Loop over all subdirectories (each is a post)
    for subdir in sorted(base_dir.iterdir()):
        if not subdir.is_dir():
            continue
        info_file = subdir / 'info.txt'
        if not info_file.exists():
            continue
        data = parse_info_txt(info_file)
        shortcode = data.get('shortcode')
        if not shortcode:
            continue

        # Insert post (ignore duplicates – same shortcode)
        c.execute('''
            INSERT OR IGNORE INTO posts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            shortcode,
            data['url'],
            data['date'],
            data['type'],
            data['likes'],
            data['comments'],
            data['location'],
            data['items'],
            data['caption'],
            subdir.name
        ))

        # Insert comments
        comments_file = subdir / 'comments.txt'
        for comment in parse_comments_txt(comments_file):
            if comment:  # avoid empty lines
                c.execute('INSERT INTO comments (shortcode, comment_text) VALUES (?, ?)',
                          (shortcode, comment))

    # Commit and fetch counts before closing
    conn.commit()
    post_count = c.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    comment_count = c.execute('SELECT COUNT(*) FROM comments').fetchone()[0]
    conn.close()

    print(f"Database created at {db_path}")
    print(f"Posts inserted: {post_count}")
    print(f"Comments inserted: {comment_count}")

if __name__ == '__main__':
    main()