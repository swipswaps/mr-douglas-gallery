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
            mention_pattern = re.compile(r'@([a-zA-Z0-9_\.]+)')
            all_mentions = []
            for comment in post['comments']:
                if not comment.startswith(('Count:', 'Reported by IG:', 'Saved:', 'Comments for')):
                    mentions = mention_pattern.findall(comment)
                    all_mentions.extend(mentions)
            filtered = [m for m in all_mentions if m.lower() != ACCOUNT_OWNER.lower()]
            post['author'] = filtered[0] if filtered else ACCOUNT_OWNER
            posts.append(post)
        conn.close()
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
    return posts

def build_html(posts):
    posts_json = json.dumps(posts, ensure_ascii=False)
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mr. Douglas Gallery v0024 - Fast & Reliable</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0f172a;color:#e2e8f0;font-family:system-ui}
.search-header{position:sticky;top:0;z-index:20;background:rgba(15,23,42,0.95);backdrop-filter:blur(8px);border-bottom:1px solid #334155;padding:1rem}
.search-container{max-width:1200px;margin:0 auto}
.search-input{width:100%;padding:0.75rem 1rem;background:#1e293b;border:1px solid #475569;border-radius:2rem;color:#f1f5f9}
.gallery-toolbar{position:sticky;top:90px;z-index:15;display:flex;gap:12px;margin:0 1.5rem 1rem;flex-wrap:wrap;align-items:center;background:#1e293b;padding:8px 12px;border-radius:12px}
.gallery-toolbar button{background:#334155;color:white;border:none;padding:6px 12px;border-radius:8px;cursor:pointer}
.gallery-toolbar button.primary{background:#3b82f6}
.gallery-toolbar button.warning{background:#f59e0b}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1.5rem;padding:1.5rem;max-width:1400px;margin:0 auto}
.card{background:#1e293b;border-radius:1rem;overflow:hidden;cursor:pointer;position:relative}
.card:hover{transform:translateY(-4px)}
.card-media{width:100%;aspect-ratio:4/3;object-fit:cover;background:#0f172a}
.card-media.load-error{opacity:0.3;filter:grayscale(1)}
.card-content{padding:1rem}
.card-meta{display:flex;justify-content:space-between;font-size:0.75rem;color:#94a3b8;margin-bottom:0.5rem;flex-wrap:wrap}
.author-name{color:#60a5fa}
.select-checkbox{position:absolute;top:8px;left:8px;width:20px;height:20px;cursor:pointer;z-index:10}
.storyboard-btn{position:fixed;bottom:20px;right:20px;background:#3b82f6;color:white;border:none;border-radius:50px;padding:12px 24px;cursor:pointer;z-index:1000}
.storyboard-modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:2000;overflow:auto}
.storyboard-modal.active{display:flex;flex-direction:column}
.storyboard-container{background:#1e293b;margin:20px auto;padding:20px;border-radius:16px;max-width:95%;width:1200px}
#storyboardCanvas{border:2px solid #475569;border-radius:8px;background:white;display:block;margin:0 auto}
.storyboard-controls{display:flex;gap:10px;justify-content:center;margin:15px 0;flex-wrap:wrap}
.storyboard-controls button{background:#3b82f6;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer}
.storyboard-thumb{width:80px;height:80px;object-fit:cover;border-radius:8px;cursor:pointer;margin-right:8px}
.toast{position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1e293b;color:#e2e8f0;padding:10px 20px;border-radius:40px;z-index:3000;opacity:0;transition:opacity 0.2s}
.toast.show{opacity:1}
.debug-panel{position:fixed;bottom:10px;right:10px;background:#1e293b;color:#0f0;font-family:monospace;font-size:10px;padding:8px;border-radius:8px;z-index:9999;max-width:500px;max-height:300px;overflow:auto;opacity:0.95}
.debug-header{display:flex;justify-content:space-between;margin-bottom:5px;background:#334155;padding:4px 8px;border-radius:4px}
.debug-close{color:#ef4444;cursor:pointer;margin-left:10px}
.debug-save{color:#10b981;cursor:pointer;margin-right:10px}
.image-status{font-size:9px;border-top:1px solid #334155;margin-top:5px;padding-top:5px}
.lightbox{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);display:none;align-items:center;justify-content:center;z-index:1000}
.lightbox.active{display:flex}
.modal{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1e293b;border-radius:1rem;max-width:600px;width:90%;max-height:80vh;overflow-y:auto;z-index:1100;display:none;padding:1rem}
.modal.active{display:block}
</style>
</head>
<body>

<div class="debug-panel" id="debugPanel">
    <div class="debug-header">
        <strong>🔍 Debug Console</strong>
        <span>
            <span id="debugSave" class="debug-save" title="Save logs">💾</span>
            <span id="debugClose" class="debug-close">✕</span>
        </span>
    </div>
    <div id="debugLog" style="max-height:200px;overflow-y:auto"></div>
    <div id="imageStatusLog" class="image-status"></div>
</div>

<div class="search-header">
    <div class="search-container">
        <input type="text" id="searchInput" class="search-input" placeholder="Search posts...">
    </div>
</div>

<div class="gallery-toolbar">
    <span>Select images:</span>
    <button id="selectAllBtn">Select All</button>
    <button id="deselectAllBtn">Deselect All</button>
    <button id="syncSelectedBtn" class="primary">Sync Selected to Storyboard</button>
    <button id="checkMissingBtn" class="warning">Show Missing Images</button>
    <span id="selectedCount">0 selected</span>
</div>

<div id="galleryGrid" class="grid"></div>

<button class="storyboard-btn" id="openStoryboardBtn">Open Storyboard <span id="storyboardCountBadge">0</span></button>

<div id="storyboardModal" class="storyboard-modal">
    <div class="storyboard-container">
        <div style="display:flex;justify-content:space-between;">
            <h3>Storyboard Builder</h3>
            <button id="closeStoryboardBtn" style="background:#ef4444;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer">Close</button>
        </div>
        <div class="storyboard-controls">
            <select id="templateSelect">
                <option value="grid">Grid (3 cols)</option>
                <option value="center">Single centered</option>
                <option value="masonry">Masonry</option>
            </select>
            <button id="applyTemplateBtn">Apply Template</button>
            <button id="exportStoryboardBtn" class="primary">Export PNG</button>
            <button id="clearStoryboardBtn">Clear All</button>
        </div>
        <canvas id="storyboardCanvas" width="1080" height="1440"></canvas>
        <div><strong>Images (click to remove):</strong>
            <div id="storyboardThumbnails" style="display:flex;gap:12px;overflow-x:auto;padding:8px;"></div>
        </div>
    </div>
</div>

<div id="toast" class="toast"></div>
<div id="lightbox" class="lightbox"><div class="lightbox-content"><div id="lightboxClose" style="position:absolute;top:10px;right:10px;color:white;font-size:2rem;cursor:pointer;">×</div><div id="lightboxMediaContainer"></div></div></div>
<div id="commentsModal" class="modal"><div><strong>Comments</strong><span id="modalClose" style="float:right;cursor:pointer;">&times;</span></div><div id="commentsList"></div></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
<script>
var allPosts = ''' + posts_json + ''';
var allLogs = [];
var failedImages = {};
var loadedImages = {};

// Simple logging that actually works
function addLog(msg, isError) {
    var timestamp = new Date().toLocaleTimeString();
    var fullMsg = timestamp + " " + msg;
    var logDiv = document.getElementById("debugLog");
    var entry = document.createElement("div");
    entry.textContent = fullMsg;
    if(isError) entry.style.color = "#ef4444";
    logDiv.appendChild(entry);
    entry.scrollIntoView();
    console.log(fullMsg);
    
    // Store for export
    allLogs.push(fullMsg);
    if(allLogs.length > 500) allLogs.shift();
}

function saveLogs() {
    var logsText = allLogs.join("\\n");
    var blob = new Blob([logsText], {type: "text/plain"});
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "gallery_logs_" + new Date().toISOString().slice(0,19).replace(/:/g, "-") + ".txt";
    a.click();
    URL.revokeObjectURL(a.href);
    addLog("Logs saved to file");
}

function showToast(msg) {
    var t = document.getElementById("toast");
    t.textContent = msg;
    t.classList.add("show");
    setTimeout(function() { t.classList.remove("show"); }, 2000);
    addLog("Toast: " + msg);
}

function getMediaPath(folder, file) {
    return folder + "/" + file;
}

// Track image loading
function trackImageLoad(img) {
    var src = img.src;
    if(!loadedImages[src]) {
        loadedImages[src] = true;
        delete failedImages[src];
        addLog("✓ Loaded: " + src.split('/').pop());
        updateImageStatus();
    }
}

function trackImageError(img) {
    var src = img.src;
    if(!failedImages[src]) {
        failedImages[src] = true;
        delete loadedImages[src];
        img.classList.add("load-error");
        addLog("✗ FAILED: " + src, true);
        updateImageStatus();
    }
}

function updateImageStatus() {
    var total = Object.keys(failedImages).length + Object.keys(loadedImages).length;
    var failedCount = Object.keys(failedImages).length;
    var html = '<div><strong>📊 Images:</strong> ' + total + ' total | ' +
               '<span style="color:#10b981">' + Object.keys(loadedImages).length + ' loaded</span> | ' +
               '<span style="color:#ef4444">' + failedCount + ' failed</span></div>';
    if(failedCount > 0) {
        var failList = Object.keys(failedImages).slice(0,3);
        html += '<div style="color:#ef4444">Failed: ' + failList.map(function(s){return s.split('/').pop();}).join(', ') + 
                (failedCount > 3 ? '...' : '') + '</div>';
    }
    document.getElementById("imageStatusLog").innerHTML = html;
}

// Render gallery with proper error tracking
function renderGallery(posts) {
    addLog("Rendering " + posts.length + " posts");
    var grid = document.getElementById("galleryGrid");
    if(!posts.length) {
        grid.innerHTML = "<div style='text-align:center;padding:3rem;'>No posts match.</div>";
        return;
    }
    
    var htmlStr = "";
    for(var idx=0; idx<posts.length; idx++){
        var post = posts[idx];
        var pm = post.all_media.length ? post.all_media[0] : null;
        var mediaHtml = "";
        if(pm){ 
            var mp = getMediaPath(post.folder_name, pm);
            // Use onerror directly on img element
            mediaHtml = "<img class='card-media' src='" + mp + "' loading='lazy' onload='trackImageLoad(this)' onerror='trackImageError(this)'>";
        } else {
            mediaHtml = "<div class='card-media'>No media</div>";
        }
        htmlStr += "<div class='card' data-shortcode='" + post.shortcode + "' data-src='" + mp + "'>";
        htmlStr += "<div style='position:relative;width:100%;aspect-ratio:4/3;'>" + mediaHtml + "</div>";
        htmlStr += "<div class='card-content'>";
        htmlStr += "<div class='card-meta'><span class='author-name'>@" + post.author + "</span><span>📅 " + new Date(post.date).toLocaleDateString() + "</span></div>";
        htmlStr += "</div></div>";
    }
    grid.innerHTML = htmlStr;
    
    // Add checkboxes after images are in DOM
    setTimeout(addCheckboxesToCards, 100);
}

// Add checkboxes to cards - fixed to ensure they work
function addCheckboxesToCards() {
    var cards = document.querySelectorAll(".card");
    addLog("Adding checkboxes to " + cards.length + " cards");
    
    for(var i=0;i<cards.length;i++){
        if(cards[i].querySelector(".select-checkbox")) continue;
        
        var img = cards[i].querySelector("img");
        if(!img || !img.src) continue;
        
        var chk = document.createElement("input");
        chk.type = "checkbox";
        chk.className = "select-checkbox";
        chk.dataset.src = img.src;
        
        chk.onclick = function(e) {
            e.stopPropagation();
        };
        
        chk.onchange = function(e) {
            e.stopPropagation();
            var src = this.dataset.src;
            if(this.checked){
                if(!selectedSrcs.has(src)) {
                    selectedSrcs.add(src);
                    addImageToStoryboard(src);
                }
            } else {
                selectedSrcs.delete(src);
            }
            document.getElementById("selectedCount").innerText = selectedSrcs.size + " selected";
            addLog("Checkbox " + (this.checked ? "checked" : "unchecked") + ": " + src.split('/').pop());
        };
        
        cards[i].style.position = "relative";
        cards[i].appendChild(chk);
    }
}

var selectedSrcs = new Set();

function selectAll() {
    var checkboxes = document.querySelectorAll(".select-checkbox");
    addLog("Select All: " + checkboxes.length + " checkboxes");
    for(var i=0;i<checkboxes.length;i++){
        if(!checkboxes[i].checked) checkboxes[i].click();
    }
}

function deselectAll() {
    var checkboxes = document.querySelectorAll(".select-checkbox");
    addLog("Deselect All: " + checkboxes.length + " checkboxes");
    for(var i=0;i<checkboxes.length;i++){
        if(checkboxes[i].checked) checkboxes[i].click();
    }
}

function showMissingImages() {
    var failed = Object.keys(failedImages);
    if(failed.length === 0) {
        showToast("All images loaded successfully!");
    } else {
        showToast(failed.length + " images failed to load");
        addLog("=== MISSING IMAGES (" + failed.length + ") ===");
        for(var i=0;i<failed.length;i++) {
            addLog("  " + failed[i], true);
        }
    }
}

// Simple storyboard without heavy processing
var canvas = null;
var storyboardImages = [];
var PREVIEW_W = 1080, PREVIEW_H = 1440;

function initCanvas() {
    var canvasEl = document.getElementById("storyboardCanvas");
    if(!canvasEl) return;
    if(canvas) canvas.dispose();
    canvas = new fabric.Canvas("storyboardCanvas");
    canvas.setDimensions({ width: PREVIEW_W, height: PREVIEW_H });
    canvas.backgroundColor = "#ffffff";
    canvas.renderAll();
    addLog("Canvas initialized");
}

function addImageToStoryboard(src) {
    var filename = src.split('/').pop();
    addLog("Adding to storyboard: " + filename);
    
    for(var i=0;i<storyboardImages.length;i++){
        if(storyboardImages[i].src === src){
            showToast("Already in storyboard");
            return;
        }
    }
    
    fabric.Image.fromURL(src, function(img) {
        if(!img) {
            addLog("Failed to create fabric image: " + filename, true);
            showToast("Failed to load: " + filename);
            return;
        }
        
        img.set({
            hasControls: true,
            hasBorders: true,
            lockRotation: true
        });
        
        // Position new images without overlapping
        var margin = 20;
        var x = margin + (storyboardImages.length % 3) * 300;
        var y = margin + Math.floor(storyboardImages.length / 3) * 250;
        img.set({ left: x, top: y });
        
        storyboardImages.push({ src: src, fabricObj: img });
        canvas.add(img);
        canvas.renderAll();
        updateThumbnails();
        updateStoryboardBadge();
        showToast("Image added: " + filename);
        addLog("Added to canvas: " + filename);
    });
}

function updateStoryboardBadge() {
    var b = document.getElementById("storyboardCountBadge");
    if(b) b.innerText = storyboardImages.length;
}

function updateThumbnails() {
    var container = document.getElementById("storyboardThumbnails");
    if(!container) return;
    var html = "";
    for(var i=0;i<storyboardImages.length;i++){
        html += "<img class='storyboard-thumb' src='" + storyboardImages[i].src + "' data-index='" + i + "'>";
    }
    container.innerHTML = html;
    
    var thumbs = document.querySelectorAll(".storyboard-thumb");
    for(var i=0;i<thumbs.length;i++){
        thumbs[i].onclick = function(e){
            e.stopPropagation();
            var idx = parseInt(this.dataset.index);
            canvas.remove(storyboardImages[idx].fabricObj);
            storyboardImages.splice(idx,1);
            canvas.renderAll();
            updateThumbnails();
            updateStoryboardBadge();
            showToast("Image removed");
        };
    }
}

function applyLayout() {
    if(storyboardImages.length === 0) return;
    var tpl = document.getElementById("templateSelect").value;
    var margin = 20;
    var availW = PREVIEW_W - margin * 2;
    
    if(tpl === "grid") {
        var cols = Math.min(3, storyboardImages.length);
        var cellW = (availW - (cols-1)*margin) / cols;
        var y = margin;
        for(var i=0;i<storyboardImages.length;i++){
            var obj = storyboardImages[i].fabricObj;
            var col = i % cols;
            var scale = Math.min(cellW / obj.width, 250 / obj.height);
            obj.scale(scale);
            obj.set({ left: margin + col * (cellW + margin), top: y });
            if(col === cols-1 || i === storyboardImages.length-1) {
                y += obj.height * scale + margin;
            }
        }
    } else if(tpl === "center") {
        var obj = storyboardImages[0].fabricObj;
        var scale = Math.min(availW / obj.width, (PREVIEW_H - margin*2) / obj.height);
        obj.scale(scale);
        obj.set({ 
            left: margin + (availW - obj.width*scale)/2, 
            top: margin + ((PREVIEW_H-margin*2) - obj.height*scale)/2 
        });
    } else if(tpl === "masonry") {
        var cols = 2;
        var colWidth = availW / cols;
        var colHeights = [margin, margin];
        var colX = [margin, margin + colWidth + margin];
        for(var i=0;i<storyboardImages.length;i++){
            var obj = storyboardImages[i].fabricObj;
            var colIdx = colHeights[0] <= colHeights[1] ? 0 : 1;
            var scale = colWidth / obj.width;
            obj.scale(scale);
            obj.set({ left: colX[colIdx], top: colHeights[colIdx] });
            colHeights[colIdx] += obj.height * scale + margin;
        }
    }
    canvas.renderAll();
    addLog("Layout applied: " + tpl);
}

function syncSelectedToStoryboard() {
    var srcs = Array.from(selectedSrcs);
    if(srcs.length === 0){
        showToast("No images selected");
        return;
    }
    addLog("Syncing " + srcs.length + " selected images to storyboard");
    for(var i=0;i<srcs.length;i++) {
        addImageToStoryboard(srcs[i]);
    }
}

function clearAll() {
    if(confirm("Clear all images from storyboard?")){
        for(var i=0;i<storyboardImages.length;i++) canvas.remove(storyboardImages[i].fabricObj);
        storyboardImages = [];
        canvas.renderAll();
        updateThumbnails();
        updateStoryboardBadge();
        showToast("Storyboard cleared");
    }
}

function exportStoryboard() {
    if(storyboardImages.length === 0){
        showToast("No images to export");
        return;
    }
    var dataURL = canvas.toDataURL("image/png");
    var a = document.createElement("a");
    a.download = "storyboard_" + new Date().toISOString().slice(0,19).replace(/:/g, "-") + ".png";
    a.href = dataURL;
    a.click();
    showToast("Exported!");
    addLog("Export complete");
}

// Event listeners
document.getElementById("selectAllBtn").onclick = selectAll;
document.getElementById("deselectAllBtn").onclick = deselectAll;
document.getElementById("syncSelectedBtn").onclick = syncSelectedToStoryboard;
document.getElementById("checkMissingBtn").onclick = showMissingImages;
document.getElementById("debugSave").onclick = saveLogs;
document.getElementById("debugClose").onclick = function(){ document.getElementById("debugPanel").style.display = "none"; };
document.getElementById("openStoryboardBtn").onclick = function(){ document.getElementById("storyboardModal").classList.add("active"); };
document.getElementById("closeStoryboardBtn").onclick = function(){ document.getElementById("storyboardModal").classList.remove("active"); };
document.getElementById("exportStoryboardBtn").onclick = exportStoryboard;
document.getElementById("clearStoryboardBtn").onclick = clearAll;
document.getElementById("applyTemplateBtn").onclick = applyLayout;

document.getElementById("searchInput").addEventListener("input", function(e){
    var q = e.target.value.toLowerCase();
    var filtered = allPosts.filter(function(p){ 
        return p.caption.toLowerCase().indexOf(q) !== -1; 
    });
    renderGallery(filtered);
});

document.getElementById("lightboxClose").onclick = function(){ document.getElementById("lightbox").classList.remove("active"); };
document.getElementById("modalClose").onclick = function(){ document.getElementById("commentsModal").classList.remove("active"); };

// Initialize
initCanvas();
renderGallery(allPosts);
addLog("=== GALLERY v0024 READY ===");
addLog("Select images using checkboxes, then click 'Sync Selected to Storyboard'");
</script>
</body>
</html>'''
    
    return html

def main():
    print("=" * 70)
    print("MR. DOUGLAS GALLERY BUILDER v0024 - Fast & Reliable")
    print("=" * 70)
    
    print("\n[1/3] Loading posts...")
    posts = load_posts()
    posts = add_historic_images(posts)
    print(f"Loaded {len(posts)} posts")
    
    print("[2/3] Generating HTML...")
    html = build_html(posts)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    print(f"Generated {OUTPUT_HTML}")
    
    print("[3/3] Starting server...")
    os.system("pkill -f 'http.server' 2>/dev/null")
    os.system("pkill -f 'run_error_server' 2>/dev/null")
    time.sleep(1)
    
    subprocess.Popen([sys.executable, '-m', 'http.server', '8000'], 
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    print("\n" + "=" * 70)
    print("✅ READY!")
    print("=" * 70)
    print(f"Open: http://localhost:8000/{OUTPUT_HTML.name}")
    print("\nPress Ctrl+C to stop")
    
    webbrowser.open(f'http://localhost:8000/{OUTPUT_HTML.name}')
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        cleanup()

if __name__ == "__main__":
[owner@192.168.1.152-20260513-202357 instagram_sav_a_dc3_extracted]$ python3 build_final_gallery_v0024.py 
======================================================================
MR. DOUGLAS GALLERY BUILDER v0024 - Fast & Reliable
======================================================================

[1/3] Loading posts...
Loaded 188 posts
[2/3] Generating HTML...
Generated index_v0024.html
[3/3] Starting server...

======================================================================
✅ READY!
======================================================================
Open: http://localhost:8000/index_v0024.html

Press Ctrl+C to stop
[owner@192.168.1.152-20260513-202434 instagram_sav_a_dc3_extracted]$ ls -lat
total 121860
-rw-r--r--. 1 owner owner   691873 May 13 20:24 index_v0024.html
drwxr-xr-x. 1 owner owner    13740 May 13 20:24 .
-rw-r--r--. 1 owner owner    25276 May 13 20:23 build_final_gallery_v0024.py
-rw-r--r--. 1 owner owner   706012 May 13 20:16 index_v0023.html
-rw-r--r--. 1 owner owner    39845 May 13 20:16 build_final_gallery_v0023.py
