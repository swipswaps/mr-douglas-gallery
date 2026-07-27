# fb_group_server.py
import os
import json
import base64
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
# You can change 'my_fb_archive' to any folder name you like.
OUTPUT_DIR = Path("./my_fb_archive")
POSTS_DIR = OUTPUT_DIR / "posts"
IMAGES_DIR = OUTPUT_DIR / "images"

# Create necessary directories
POSTS_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

@app.route('/fetch_post', methods=['POST'])
def handle_post():
    """Endpoint to receive post data from the userscript."""
    data = request.get_json()
    posts = data.get('posts', [])

    for post in posts:
        # Generate a unique filename for each post
        post_id = post.get('post_id', str(uuid.uuid4()))
        timestamp = post.get('timestamp', datetime.now().isoformat())
        content = post.get('post_content', '')

        # Create a dictionary to store as JSON
        post_data = {
            'post_id': post_id,
            'url': post.get('post_url'),
            'timestamp': timestamp,
            'content': content,
            'images': []  # We'll fill this in if we receive images
        }

        # Save the post to a JSON file
        post_filename = POSTS_DIR / f"{post_id}.json"
        with open(post_filename, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, indent=4, ensure_ascii=False)

    return jsonify({"status": "success", "posts_received": len(posts)}), 200


@app.route('/upload', methods=['POST'])
def handle_upload():
    """Endpoint to receive image uploads from the userscript."""
    listing_id = request.form.get('listing_id')
    image_file = request.files.get('file')

    if not listing_id or not image_file:
        return jsonify({"error": "Missing listing_id or file"}), 400

    # Create a safe filename and save the image
    original_filename = image_file.filename
    file_extension = original_filename.split('.')[-1] if '.' in original_filename else 'jpg'
    safe_filename = f"{listing_id}_{uuid.uuid4().hex}.{file_extension}"
    image_path = IMAGES_DIR / safe_filename

    image_file.save(image_path)

    # Update the corresponding post's JSON to include this image path
    post_file = POSTS_DIR / f"{listing_id}.json"
    if post_file.exists():
        with open(post_file, 'r', encoding='utf-8') as f:
            post_data = json.load(f)
        post_data['images'].append(str(image_path))
        with open(post_file, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, indent=4, ensure_ascii=False)

    return jsonify({"status": "uploaded", "path": str(image_path)}), 200


@app.route('/')
def index():
    """Simple status page to show the collector is running."""
    return f"""
    <html>
        <body>
            <h2>Facebook Group Collector is Running</h2>
            <p>Save directory: {OUTPUT_DIR.absolute()}</p>
            <p>Posts saved: {len(list(POSTS_DIR.glob('*.json')))}</p>
            <p>Images saved: {len(list(IMAGES_DIR.glob('*')))}</p>
        </body>
    </html>
    """

if __name__ == '__main__':
    # Run the server on http://localhost:8080
    app.run(host='localhost', port=8080, debug=True)