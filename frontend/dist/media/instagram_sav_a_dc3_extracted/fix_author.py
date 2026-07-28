import re
import json
import sys

def add_author_to_html(input_file, output_file, author="sav_a_dc3"):
    with open(input_file, 'r', encoding='utf-8') as f:
        html = f.read()

    # Find the allPosts = [...] block
    # Match from "const allPosts = [" to the closing "];"
    pattern = r'(const allPosts = )(\[[\s\S]*?\]);'
    match = re.search(pattern, html)
    if not match:
        print("Could not find allPosts array in HTML")
        sys.exit(1)

    prefix = match.group(1)   # "const allPosts = "
    array_text = match.group(2)  # the JSON array as a string

    # Parse the JSON array (it's valid JavaScript, which is also valid JSON)
    try:
        posts = json.loads(array_text)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print("Attempting to fix common issues...")
        # Sometimes the array contains JavaScript comments or trailing commas – we can clean
        # But the original likely is pure JSON. We'll assume it's correct.
        sys.exit(1)

    # Add author to each post
    for post in posts:
        post['author'] = author

    # Re-serialize with proper indentation (same as original)
    new_array_text = json.dumps(posts, indent=2, ensure_ascii=False)

    # Replace the old array with the new one
    new_html = html.replace(array_text, new_array_text)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(new_html)

    print(f"✅ Written {output_file} with author '{author}' added to all posts.")

if __name__ == "__main__":
    add_author_to_html("index_cloud_backup.html", "index_with_author.html")