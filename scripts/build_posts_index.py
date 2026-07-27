import os
import json
from pathlib import Path

def parse_info(info_path):
    data = {}
    with open(info_path, 'r', encoding='utf-8') as f:
        for line in f:
            if ':' in line:
                key, val = line.split(':', 1)
                data[key.strip()] = val.strip()
    return data

def parse_comments(comments_path):
    if not os.path.exists(comments_path):
        return []
    with open(comments_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def build_posts_index(root_dir, output_json):
    posts = []
    root = Path(root_dir)
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        info_path = folder / 'info.txt'
        if not info_path.exists():
            continue
        info = parse_info(info_path)
        media_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.mp4', '*.webm']:
            media_files.extend(folder.glob(ext))
        media_files = sorted(media_files, key=lambda p: p.name)
        comments = parse_comments(folder / 'comments.txt')
        posts.append({
            'id': folder.name,
            'date': info.get('Date', ''),
            'caption': info.get('Caption', ''),
            'media': [str(p.relative_to(root)) for p in media_files],
            'comments': comments,
        })
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
    print(f"Written {len(posts)} posts to {output_json}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python build_posts_index.py <extracted_dir> <output_json>")
        sys.exit(1)
    build_posts_index(sys.argv[1], sys.argv[2])
