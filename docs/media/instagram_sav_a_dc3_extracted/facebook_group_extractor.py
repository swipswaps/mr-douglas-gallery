#!/usr/bin/env python3
"""
Facebook Groups Data Extractor (Official DYA Export)
Extracts images, comments, and descriptions from private groups.
Fully compliant with Facebook's Terms of Service.
"""

import os
import json
import shutil
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote
from tqdm import tqdm
import argparse

def find_groups_folder(archive_path):
    """Locate the 'groups' folder inside the unzipped Facebook archive."""
    archive_path = Path(archive_path)
    if archive_path.is_file():
        archive_path = archive_path.parent
    groups_folder = archive_path / "groups"
    if groups_folder.exists() and groups_folder.is_dir():
        return groups_folder
    # Fallback: search recursively for a folder named 'groups'
    for root, dirs, files in os.walk(archive_path):
        if "groups" in dirs:
            return Path(root) / "groups"
    raise FileNotFoundError("Could not find 'groups' folder in the archive. Make sure you unzipped the file and included Groups in the export.")

def list_available_groups(groups_folder):
    """Return a dict of group_name -> folder_path for each group in the archive."""
    groups = {}
    for item in groups_folder.iterdir():
        if item.is_dir():
            groups[item.name] = item
    return groups

def find_post_files(group_folder):
    """Recursively find all .json or .html files that contain post data."""
    post_files = []
    # JSON files (preferred format)
    for json_file in group_folder.rglob("*.json"):
        # Exclude metadata or index files if needed
        if "comments" not in json_file.name and "likes" not in json_file.name:
            post_files.append(json_file)
    # If no JSON, fall back to .html files (older exports)
    if not post_files:
        for html_file in group_folder.rglob("*.html"):
            if "posts" in html_file.name or "post" in html_file.name:
                post_files.append(html_file)
    return post_files

def parse_json_post(json_path, group_name, output_base):
    """Extract text, comments, images from a JSON post file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Navigate to the actual post content – structure varies slightly
    post = data.get("group_posts", data)
    if isinstance(post, list):
        post = post[0] if post else {}
    
    title = post.get("title", "Untitled Post")
    post_text = post.get("data", [{}])[0].get("post", "") or post.get("post", "")
    timestamp = post.get("timestamp", "")
    attachments = post.get("attachments", []) or post.get("media", [])
    comments_data = post.get("comments", {}).get("data", []) if "comments" in post else []

    # Create a folder for this post
    safe_title = "".join(c for c in title[:50] if c.isalnum() or c in (' ', '_')).strip()
    if not safe_title:
        safe_title = f"post_{json_path.stem}"
    post_folder = output_base / group_name / safe_title
    post_folder.mkdir(parents=True, exist_ok=True)

    # Download images
    image_paths = []
    for idx, att in enumerate(attachments):
        media_url = None
        if isinstance(att, dict):
            media_url = att.get("media", {}).get("uri") or att.get("src") or att.get("url")
        if media_url and ("jpg" in media_url or "png" in media_url or "jpeg" in media_url):
            try:
                img_data = requests.get(media_url, timeout=10).content
                suffix = media_url.split('.')[-1].split('?')[0][:5]
                if suffix.lower() not in ['jpg','jpeg','png','gif']:
                    suffix = 'jpg'
                img_name = f"img_{idx+1}.{suffix}"
                img_path = post_folder / img_name
                with open(img_path, 'wb') as img_f:
                    img_f.write(img_data)
                image_paths.append(str(img_path))
            except Exception as e:
                print(f"  Failed to download {media_url}: {e}")

    # Save post metadata and comments
    result = {
        "post_title": title,
        "post_text": post_text,
        "timestamp": timestamp,
        "images": image_paths,
        "comments": []
    }
    for comment in comments_data:
        comment_text = comment.get("comment", "") or comment.get("text", "")
        author = comment.get("author", "Unknown")
        comment_time = comment.get("timestamp", "")
        result["comments"].append({
            "author": author,
            "text": comment_text,
            "timestamp": comment_time
        })

    # Write metadata JSON
    meta_file = post_folder / "post.json"
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return len(image_paths)

def parse_html_post(html_path, group_name, output_base):
    """Extract posts from HTML files (simpler fallback). Returns number of images downloaded."""
    from bs4 import BeautifulSoup  # Requires additional install: pip install beautifulsoup4
    
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    # This is a simplified fallback; actual HTML structure varies.
    # Better to recommend using JSON export instead.
    print(f"  Warning: HTML parsing is limited. Recommend re-exporting with JSON format.")
    return 0

def main():
    parser = argparse.ArgumentParser(description="Extract posts, comments, and images from Facebook groups (official DYA export).")
    parser.add_argument("archive_path", help="Path to the unzipped Facebook archive folder")
    parser.add_argument("--output", "-o", default="./facebook_groups_export", help="Output directory (default: ./facebook_groups_export)")
    parser.add_argument("--groups", "-g", nargs="+", help="Only process specific group names (default: all)")
    args = parser.parse_args()

    print("🔍 Locating groups folder...")
    groups_folder = find_groups_folder(args.archive_path)
    print(f"✅ Found: {groups_folder}")

    available = list_available_groups(groups_folder)
    if not available:
        print("❌ No group data found in the archive. Did you select 'Groups' in the export?")
        return

    print("\n📁 Available groups in your archive:")
    for idx, name in enumerate(available.keys(), 1):
        print(f"  {idx}. {name}")

    # Select groups
    selected = []
    if args.groups:
        selected = [g for g in args.groups if g in available]
        if not selected:
            print(f"❌ None of the specified groups found. Available: {list(available.keys())}")
            return
    else:
        choice = input("\nEnter numbers to process (e.g. '1,2' or 'all'): ").strip()
        if choice.lower() == 'all':
            selected = list(available.keys())
        else:
            indices = [int(x.strip()) for x in choice.split(',') if x.strip().isdigit()]
            selected = [list(available.keys())[i-1] for i in indices if 1 <= i <= len(available)]

    if not selected:
        print("No groups selected.")
        return

    output_base = Path(args.output)
    output_base.mkdir(parents=True, exist_ok=True)

    total_images = 0
    for group_name in selected:
        print(f"\n📂 Processing group: {group_name}")
        group_folder = available[group_name]
        post_files = find_post_files(group_folder)
        if not post_files:
            print(f"  No post files found in {group_folder}")
            continue
        
        for pfile in tqdm(post_files, desc=f"  Posts in {group_name}"):
            try:
                if pfile.suffix.lower() == '.json':
                    img_count = parse_json_post(pfile, group_name, output_base)
                else:
                    img_count = parse_html_post(pfile, group_name, output_base)
                total_images += img_count
            except Exception as e:
                print(f"  Error processing {pfile.name}: {e}")

    print(f"\n✅ Done! Data exported to: {output_base}")
    print(f"📸 Total images downloaded: {total_images}")
    print("You can browse group folders and open post.json files to see all metadata.")

if __name__ == "__main__":
    main()