#!/usr/bin/env python3
"""
Final gallery with thumbnails for videos, proper placeholders, and visible lightbox close button.
"""

import sqlite3
import re
import json
from collections import Counter
from pathlib import Path

def load_posts(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    posts = conn.execute("""
        SELECT shortcode, date, likes, comments_count, caption, folder_name
        FROM posts
        ORDER BY date DESC
    """).fetchall()
    comments_by_post = {}
    for post in posts:
        shortcode = post['shortcode']
        comments = conn.execute(
            "SELECT comment_text FROM comments WHERE shortcode = ?", (shortcode,)
        ).fetchall()
        comments_by_post[shortcode] = [c['comment_text'] for c in comments]
    conn.close()

    post_list = []
    for p in posts:
        folder = Path(p['folder_name'])
        all_media = []
        if folder.exists():
            all_media = sorted([f.name for f in folder.iterdir() if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4'}])
        post_list.append({
            'shortcode': p['shortcode'],
            'date': p['date'],
            'likes': p['likes'],
            'comments_count': p['comments_count'],
            'caption': p['caption'] or '',
            'folder_name': p['folder_name'],
            'comments': comments_by_post[p['shortcode']],
            'all_media': all_media,
            'instagram_url': f"https://www.instagram.com/p/{p['shortcode']}/"
        })
    return post_list

def extract_words(posts):
    stop_words = set(['a','an','and','the','of','to','in','for','on','with','by','at','is','it','that','this','are','was','were','be','been','being','have','has','had','having','do','does','did','doing','but','or','so','for','not','can','will','just','like','get','put','up','down','out','over','under','again','further','then','once','here','there','all','any','both','each','few','more','most','other','some','such','no','nor','only','own','same','than','too','very','s','t','ve','from','into','through','during','before','after','above','below','between','below','off','down','i','you','he','she','it','we','they','me','him','her','us','them','my','your','his','her','its','our','their','what','which','who','whom','whose','this','that','these','those','am','been','were','hasnt','doesnt','isnt','arent','wasnt','werent','dont','didnt','www','com','https','http','instagram','instagramcom','mrdouglas','mrdouglasorg','follow','followus','please','let','see','new','will','now','get','time','like','just','oh','yeah','yes','no','ok','okay'])
    counter = Counter()
    for post in posts:
        for w in re.findall(r'\b[a-zA-Z]+\b', post['caption'].lower()):
            if w not in stop_words and len(w) > 2:
                counter[w] += 1
        for comment in post['comments']:
            for w in re.findall(r'\b[a-zA-Z]+\b', comment.lower()):
                if w not in stop_words and len(w) > 2:
                    counter[w] += 1
    return counter.most_common(300)

def generate_html(posts, word_freq):
    posts_json = json.dumps(posts)
    words_list = [{'word': w, 'count': c} for w, c in word_freq]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>Mr. Douglas - Complete Gallery</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            background-color: #0f172a;
            color: #e2e8f0;
            font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.5;
        }}
        .search-header {{
            position: sticky;
            top: 0;
            z-index: 20;
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid #334155;
            padding: 1rem;
        }}
        .search-container {{ max-width: 1200px; margin: 0 auto; }}
        .search-input {{
            width: 100%;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            background: #1e293b;
            border: 1px solid #475569;
            border-radius: 2rem;
            color: #f1f5f9;
            outline: none;
        }}
        .search-input:focus {{ border-color: #3b82f6; }}
        .wordcloud-container {{
            background: #1e293b;
            border-radius: 1rem;
            padding: 1rem;
            margin-top: 1rem;
        }}
        .wordcloud {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem 1rem;
            justify-content: center;
            max-height: 200px;
            overflow-y: auto;
        }}
        .cloud-word {{
            cursor: pointer;
            transition: all 0.1s ease;
            color: #94a3b8;
        }}
        .cloud-word:hover {{ color: #60a5fa; transform: scale(1.05); }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
            padding: 1.5rem;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .card {{
            background: #1e293b;
            border-radius: 1rem;
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }}
        .card:hover {{ transform: translateY(-4px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.3); }}
        .card-media {{
            width: 100%;
            aspect-ratio: 4/3;
            object-fit: cover;
            background: #0f172a;
        }}
        .video-placeholder {{
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #1e293b;
            color: #94a3b8;
            font-size: 2rem;
        }}
        .card-content {{ padding: 1rem; }}
        .card-meta {{
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: #94a3b8;
            margin-bottom: 0.5rem;
        }}
        .card-caption {{
            font-size: 0.875rem;
            color: #cbd5e1;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
            margin-bottom: 0.75rem;
        }}
        .carousel {{
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
            margin: 0.5rem 0;
            padding-bottom: 0.5rem;
        }}
        .carousel-item {{
            width: 60px;
            height: 60px;
            object-fit: cover;
            border-radius: 8px;
            flex-shrink: 0;
            cursor: pointer;
            background: #0f172a;
        }}
        .carousel-video-placeholder {{
            width: 60px;
            height: 60px;
            background: #1e293b;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            cursor: pointer;
        }}
        .comments-btn {{
            background: none;
            border: none;
            color: #3b82f6;
            cursor: pointer;
            font-size: 0.7rem;
            padding: 0.25rem 0.5rem;
            border-radius: 1rem;
            background: #1e293b;
        }}
        .comments-btn:hover {{ background: #334155; }}
        .card-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.5rem;
        }}
        .insta-link {{
            font-size: 0.75rem;
            color: #3b82f6;
            text-decoration: none;
        }}
        .lightbox {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.9); backdrop-filter: blur(8px);
            display: none; align-items: center; justify-content: center;
            z-index: 1000;
        }}
        .lightbox.active {{ display: flex; }}
        .lightbox-content {{
            position: relative;
            max-width: 90vw;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .lightbox-media {{
            max-width: 100%;
            max-height: 85vh;
            object-fit: contain;
            border-radius: 12px;
        }}
        .lightbox-close {{
            position: absolute;
            top: 10px;
            right: 10px;
            color: white;
            font-size: 2rem;
            cursor: pointer;
            background: rgba(0,0,0,0.5);
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1010;
        }}
        .lightbox-caption {{
            margin-top: 1rem;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            max-width: 90vw;
            font-size: 0.875rem;
        }}
        .modal {{
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: #1e293b;
            border-radius: 1rem;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            z-index: 1100;
            display: none;
            padding: 1rem;
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5);
        }}
        .modal.active {{ display: block; }}
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
        }}
        .modal-close {{
            cursor: pointer;
            font-size: 1.5rem;
            line-height: 1;
        }}
        .comment-item {{
            padding: 0.5rem 0;
            border-bottom: 1px solid #334155;
        }}
        .no-results {{
            text-align: center;
            padding: 3rem;
            color: #94a3b8;
            grid-column: 1 / -1;
        }}
    </style>
</head>
<body>
    <div class="search-header">
        <div class="search-container">
            <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search posts (fuzzy)..." autocomplete="off">
            <div class="wordcloud-container">
                <div id="wordcloud" class="wordcloud">Loading words...</div>
            </div>
        </div>
    </div>
    <div id="galleryGrid" class="grid"></div>

    <!-- Lightbox -->
    <div id="lightbox" class="lightbox">
        <div class="lightbox-content">
            <div class="lightbox-close" id="lightboxClose">×</div>
            <div id="lightboxMediaContainer"></div>
            <div id="lightboxCaption" class="lightbox-caption"></div>
        </div>
    </div>

    <!-- Comments Modal -->
    <div id="commentsModal" class="modal">
        <div class="modal-header">
            <strong>Comments</strong>
            <span id="modalClose" class="modal-close">&times;</span>
        </div>
        <div id="commentsList"></div>
    </div>

    <script>
        const allPosts = {posts_json};

        function isVideo(filename) {{
            return filename && /\.(mp4|mov|avi|mkv)$/i.test(filename);
        }}

        function getMediaPath(folderName, fileName) {{
            return `${{folderName}}/${{fileName}}`;
        }}

        function renderMediaThumb(mediaFile, folderName) {{
            const path = getMediaPath(folderName, mediaFile);
            if (isVideo(mediaFile)) {{
                return `<div class="video-placeholder">🎬</div>`;
            }} else {{
                return `<img class="card-media" src="${{path}}" alt="Post image" loading="lazy" onerror="this.style.display='none'; this.parentElement.querySelector('.fallback')?.style.display='flex';">`;
            }}
        }}

        function renderCarouselItem(mediaFile, folderName) {{
            const path = getMediaPath(folderName, mediaFile);
            if (isVideo(mediaFile)) {{
                return `<div class="carousel-video-placeholder" data-media="${{path}}">🎬</div>`;
            }} else {{
                return `<img class="carousel-item" src="${{path}}" data-media="${{path}}" loading="lazy" onerror="this.style.display='none'; this.outerHTML='<div class=\\'carousel-video-placeholder\\' data-media=\\''+path+'\\'>❌</div>';">`;
            }}
        }}

        function renderGallery(posts) {{
            const grid = document.getElementById('galleryGrid');
            if (!posts.length) {{
                grid.innerHTML = '<div class="no-results">No posts match your search.</div>';
                return;
            }}
            grid.innerHTML = posts.map(post => {{
                const primaryMedia = post.all_media.length ? post.all_media[0] : null;
                const carouselItems = post.all_media.slice(1).map(f => renderCarouselItem(f, post.folder_name)).join('');
                const commentsCount = post.comments.length;
                // Media block with fallback
                let mediaHtml = '';
                if (primaryMedia) {{
                    if (isVideo(primaryMedia)) {{
                        mediaHtml = `<div class="video-placeholder card-media">🎬 Video</div>`;
                    }} else {{
                        mediaHtml = `<img class="card-media" src="${{getMediaPath(post.folder_name, primaryMedia)}}" alt="${{post.caption.substring(0, 60)}}" loading="lazy" onerror="this.style.display='none'; this.parentElement.querySelector('.fallback')?.style.display='flex';">`;
                    }}
                }}
                // Add a fallback div for failed images
                if (!primaryMedia || !isVideo(primaryMedia)) {{
                    mediaHtml += `<div class="fallback" style="display:none; width:100%; height:100%; align-items:center; justify-content:center; background:#1e293b;">📷 No media</div>`;
                }}
                if (!primaryMedia) {{
                    mediaHtml = `<div class="card-media" style="display:flex; align-items:center; justify-content:center;">📷 No media</div>`;
                }}
                return `
                    <div class="card" data-shortcode="${{post.shortcode}}" data-caption="${{post.caption.replace(/"/g, '&quot;')}}">
                        <div style="position:relative; width:100%; aspect-ratio:4/3;">
                            ${{mediaHtml}}
                        </div>
                        <div class="card-content">
                            <div class="card-meta">
                                <span>📅 ${{new Date(post.date).toLocaleDateString()}}</span>
                                <span>❤️ ${{post.likes}}</span>
                                <span>💬 ${{post.comments_count}}</span>
                            </div>
                            <div class="card-caption">${{post.caption.length > 180 ? post.caption.substring(0,180)+'…' : post.caption}}</div>
                            ${{carouselItems ? `<div class="carousel">${{carouselItems}}</div>` : ''}}
                            <div class="card-footer">
                                <a href="${{post.instagram_url}}" target="_blank" class="insta-link" onclick="event.stopPropagation()">🔗 View on Instagram</a>
                                <button class="comments-btn" data-shortcode="${{post.shortcode}}">💬 ${{commentsCount}} comments</button>
                            </div>
                        </div>
                    </div>
                `;
            }}).join('');

            // Carousel thumbnails click
            document.querySelectorAll('.carousel-item, .carousel-video-placeholder').forEach(el => {{
                el.addEventListener('click', (e) => {{
                    e.stopPropagation();
                    let media = el.getAttribute('data-media');
                    if (!media && el.classList.contains('carousel-video-placeholder')) {{
                        // For video placeholder, we need to get media path from folder and filename? The placeholder doesn't have data-media. We'll set it when creating.
                        // In renderCarouselItem we set data-media on the div. Good.
                        media = el.getAttribute('data-media');
                    }}
                    const card = el.closest('.card');
                    const caption = card.getAttribute('data-caption');
                    openLightbox(media, caption);
                }});
            }});

            // Comment buttons
            document.querySelectorAll('.comments-btn').forEach(btn => {{
                btn.addEventListener('click', (e) => {{
                    e.stopPropagation();
                    const shortcode = btn.getAttribute('data-shortcode');
                    const post = allPosts.find(p => p.shortcode === shortcode);
                    if (post && post.comments.length) {{
                        const modal = document.getElementById('commentsModal');
                        const listDiv = document.getElementById('commentsList');
                        listDiv.innerHTML = post.comments.map(c => `<div class="comment-item">💬 ${{c}}</div>`).join('');
                        modal.classList.add('active');
                    }} else {{
                        alert('No comments for this post.');
                    }}
                }});
            }});
        }}

        function openLightbox(src, caption) {{
            const container = document.getElementById('lightboxMediaContainer');
            container.innerHTML = '';
            if (src && src.match(/\.(mp4|mov|avi|mkv)$/i)) {{
                const video = document.createElement('video');
                video.src = src;
                video.controls = true;
                video.className = 'lightbox-media';
                video.style.maxWidth = '90vw';
                video.style.maxHeight = '85vh';
                container.appendChild(video);
            }} else if (src) {{
                const img = document.createElement('img');
                img.src = src;
                img.className = 'lightbox-media';
                img.onerror = () => {{
                    img.style.display = 'none';
                    container.innerHTML = '<div style="color:white; text-align:center;">Image failed to load</div>';
                }};
                container.appendChild(img);
            }} else {{
                container.innerHTML = '<div style="color:white; text-align:center;">No media available</div>';
            }}
            document.getElementById('lightboxCaption').innerText = caption;
            document.getElementById('lightbox').classList.add('active');
        }}

        function fuzzyMatch(text, query) {{
            if (!query) return true;
            return text.toLowerCase().includes(query.toLowerCase());
        }}

        function postMatches(post, query) {{
            if (!query) return true;
            if (fuzzyMatch(post.caption, query)) return true;
            return post.comments.some(c => fuzzyMatch(c, query));
        }}

        function updateWordCloud(posts) {{
            const wordCount = {{}};
            posts.forEach(post => {{
                (post.caption + ' ' + post.comments.join(' ')).toLowerCase().match(/\\b[a-z]+\\b/g)?.forEach(w => {{
                    if (w.length > 2 && !/^(?:a|an|and|the|of|to|in|for|on|with|by|at|is|it|that|this|are|was|were|be|been|being|have|has|had|having|do|does|did|doing|but|or|so|for|not|can|will|just|like|get|put|up|down|out|over|under|again|further|then|once|here|there|all|any|both|each|few|more|most|other|some|such|no|nor|only|own|same|than|too|very|i|you|he|she|it|we|they|me|him|her|us|them|my|your|his|her|its|our|their|what|which|who|whom|whose|these|those|am|been|were|www|com|https|http|instagram|mrdouglas|follow|please|let|see|new|will|now|get|time|like|just)$/.test(w)) wordCount[w] = (wordCount[w] || 0) + 1;
                }});
            }});
            const words = Object.entries(wordCount).map(([w,c]) => ({{word:w, count:c}})).sort((a,b)=>b.count-a.count).slice(0,100);
            const maxF = words.length ? Math.max(...words.map(w=>w.count)) : 1;
            const container = document.getElementById('wordcloud');
            if (!words.length) {{
                container.innerHTML = '<span style="color:#94a3b8;">No words found</span>';
                return;
            }}
            container.innerHTML = words.map(w => `<span class="cloud-word" data-word="${{w.word}}" style="font-size:${{0.8 + (w.count/maxF)*1.5}}rem;">${{w.word}}</span>`).join('');
            document.querySelectorAll('.cloud-word').forEach(el => {{
                el.addEventListener('click', () => {{
                    document.getElementById('searchInput').value = el.getAttribute('data-word');
                    const event = new Event('input', {{ bubbles: true }});
                    document.getElementById('searchInput').dispatchEvent(event);
                }});
            }});
        }}

        let debounceTimer;
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', (e) => {{
            clearTimeout(debounceTimer);
            const query = e.target.value.trim();
            debounceTimer = setTimeout(() => {{
                const filtered = allPosts.filter(p => postMatches(p, query));
                renderGallery(filtered);
                updateWordCloud(filtered);
            }}, 200);
        }});

        // Close lightbox
        document.getElementById('lightboxClose').addEventListener('click', () => {{
            document.getElementById('lightbox').classList.remove('active');
        }});
        document.getElementById('modalClose').addEventListener('click', () => {{
            document.getElementById('commentsModal').classList.remove('active');
        }});
        window.addEventListener('click', (e) => {{
            if (e.target === document.getElementById('lightbox')) document.getElementById('lightbox').classList.remove('active');
            if (e.target === document.getElementById('commentsModal')) document.getElementById('commentsModal').classList.remove('active');
        }});

        // Click on card main media to open lightbox
        document.getElementById('galleryGrid').addEventListener('click', (e) => {{
            const card = e.target.closest('.card');
            if (card && !e.target.closest('.carousel-item') && !e.target.closest('.carousel-video-placeholder') && !e.target.closest('.comments-btn') && !e.target.closest('a')) {{
                let media = null;
                const img = card.querySelector('.card-media');
                if (img && img.tagName === 'IMG') {{
                    media = img.src;
                }} else if (card.querySelector('.video-placeholder')) {{
                    // For video placeholder, we need the actual video file. We can get from post data.
                    const shortcode = card.getAttribute('data-shortcode');
                    const post = allPosts.find(p => p.shortcode === shortcode);
                    if (post && post.all_media.length) {{
                        media = getMediaPath(post.folder_name, post.all_media[0]);
                    }}
                }}
                const caption = card.getAttribute('data-caption');
                openLightbox(media, caption);
            }}
        }});

        // Initial render
        renderGallery(allPosts);
        updateWordCloud(allPosts);
    </script>
</body>
</html>"""
    return html

def main():
    db_path = Path("instagram_posts.db")
    if not db_path.exists():
        print("Error: instagram_posts.db not found. Run build_instagram_db.py first.")
        return
    print("Loading posts...")
    posts = load_posts(db_path)
    print(f"Loaded {len(posts)} posts.")
    print("Extracting word frequencies...")
    word_freq = extract_words(posts)
    print(f"Found {len(word_freq)} unique words.")
    html = generate_html(posts, word_freq)
    output_path = Path("index_cloud.html")
    output_path.write_text(html, encoding='utf-8')
    print(f"✅ Gallery generated: {output_path.resolve()}")
    print("\n📌 To see all features:")
    print("   python -m http.server 8000")
    print("   then open http://localhost:8000/index_cloud.html")
    print("\n   - Video posts show 🎬 icon (click to play in lightbox)")
    print("   - Missing images show a placeholder")
    print("   - Lightbox close button is always visible (top-right)")
    print("   - Word cloud updates as you type, click a word to search")

if __name__ == '__main__':
    main()