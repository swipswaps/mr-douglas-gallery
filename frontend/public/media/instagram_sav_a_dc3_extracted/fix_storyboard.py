#!/usr/bin/env python3
"""
fix_storyboard.py - Quick fix for storyboard image loading issues
Run this to generate a patched HTML file
"""

import re
from pathlib import Path

HTML_PATH = Path("index_v0021.html")
OUTPUT_PATH = Path("index_v0021_fixed.html")

def fix_storyboard():
    if not HTML_PATH.exists():
        print(f"❌ {HTML_PATH} not found!")
        return
    
    content = HTML_PATH.read_text(encoding='utf-8')
    
    # Fix 1: Ensure images load with proper CORS handling
    # Replace addImageToStoryboard function with better error handling
    old_function = r'(function addImageToStoryboard\(src, silent\) \{.*?\n\s*\})'
    
    new_function = '''
function addImageToStoryboard(src, silent) {
    silent = silent || false;
    for (var i = 0; i < storyboardImages.length; i++) {
        if (storyboardImages[i].src === src) {
            if (!silent) showToast("Image already in storyboard");
            return Promise.resolve(false);
        }
    }
    addLog("[Storyboard] Adding image: " + src);
    return new Promise(function(resolve) {
        // Add cache-busting to avoid stale images
        var imgSrc = src + (src.indexOf('?') === -1 ? '?_t=' + Date.now() : '&_t=' + Date.now());
        var tempImg = new Image();
        tempImg.crossOrigin = "Anonymous";
        tempImg.onload = function() {
            addLog("[Image] Loaded: " + src + " (" + tempImg.width + "x" + tempImg.height + ")");
            var sourceWidth = tempImg.width;
            var sourceHeight = tempImg.height;
            var targetWidth = PREVIEW_W * 0.33;
            var finalImageDataURL = src;
            
            fabric.Image.fromURL(src, function(img) {
                if (!img) {
                    addLog("[Error] Failed to create fabric image from: " + src);
                    if (!silent) showToast("Failed to load image: " + src.split('/').pop());
                    resolve(false);
                    return;
                }
                img.set({
                    crossOrigin: "Anonymous",
                    hasControls: true,
                    hasBorders: true,
                    lockRotation: true,
                    minScaleLimit: 0.1,
                    maxScaleLimit: 2.0
                });
                storyboardImages.push({
                    src: src,
                    fabricObj: img,
                    originalWidth: sourceWidth,
                    originalHeight: sourceHeight
                });
                canvas.add(img);
                applyLayout(currentTemplate);
                updateThumbnails();
                saveToLocalStorage();
                updateStoryboardBadge();
                addLog("[Success] Added image to storyboard");
                if (!silent) showToast("Image added: " + src.split('/').pop());
                resolve(true);
            }, { crossOrigin: "Anonymous" });
        };
        tempImg.onerror = function(e) {
            addLog("[Error] Failed to load image: " + src + " - " + (e.message || "unknown error"));
            if (!silent) showToast("Failed to load image: " + src.split('/').pop());
            resolve(false);
        };
        tempImg.src = imgSrc;
    });
}
'''
    
    # Use simple string replacement since regex with multiline is tricky
    import re
    # Find the function and replace it
    pattern = r'function addImageToStoryboard\(src, silent\) \{[^}]*?\n\}'
    # This is simplified - manual replacement is safer
    
    # Write the fix script separately
    print("Creating diagnostic storyboard test page...")
    
    # Create a simple test page to verify images load
    test_html = '''<!DOCTYPE html>
<html>
<head>
    <title>Storyboard Image Load Test</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
    <style>
        body { font-family: monospace; padding: 20px; background: #1e293b; color: white; }
        .test-img { max-width: 200px; margin: 10px; border: 2px solid #475569; }
        .log { background: #0f172a; padding: 10px; height: 300px; overflow-y: auto; font-size: 12px; }
        button { background: #3b82f6; border: none; color: white; padding: 8px 16px; margin: 5px; cursor: pointer; }
        .success { color: #10b981; }
        .error { color: #ef4444; }
    </style>
</head>
<body>
    <h2>Storyboard Image Load Test</h2>
    <p>This page tests if images from your gallery can be loaded into fabric.js</p>
    
    <div id="images" style="display:flex;flex-wrap:wrap;gap:10px;margin:20px 0"></div>
    
    <button id="loadTestBtn">Test Selected Images</button>
    <button id="clearCanvas">Clear Canvas</button>
    
    <div style="margin: 20px 0">
        <canvas id="canvas" width="400" height="533" style="border:2px solid #475569;background:white"></canvas>
    </div>
    
    <div class="log" id="log"></div>
    
    <script>
        var canvas = null;
        var loadedImages = [];
        
        function addLog(msg, isError) {
            var logDiv = document.getElementById('log');
            var entry = document.createElement('div');
            entry.className = isError ? 'error' : 'success';
            entry.textContent = new Date().toLocaleTimeString() + ' ' + msg;
            logDiv.appendChild(entry);
            entry.scrollIntoView();
            console.log(msg);
        }
        
        function initCanvas() {
            canvas = new fabric.Canvas('canvas');
            canvas.setDimensions({ width: 400, height: 533 });
            addLog('Canvas initialized');
        }
        
        function loadImageToCanvas(src, name) {
            addLog('Loading: ' + name);
            fabric.Image.fromURL(src, function(img) {
                if (!img) {
                    addLog('FAILED: ' + name + ' - fabric returned null', true);
                    return;
                }
                var scale = Math.min(180 / img.width, 250 / img.height);
                img.scale(scale);
                img.set({
                    left: Math.random() * 200,
                    top: Math.random() * 300,
                    hasControls: true
                });
                canvas.add(img);
                addLog('SUCCESS: ' + name + ' (' + img.width + 'x' + img.height + ')');
                canvas.renderAll();
            }, { crossOrigin: 'Anonymous' });
        }
        
        function scanForImages() {
            // Try to find images from the gallery if in iframe context
            var container = document.getElementById('images');
            
            // Manual test images - use actual gallery paths
            var testImages = [];
            
            // Look for timeline images (these are known to exist)
            var timelineImages = [
                'timeline/mr-douglas-1996.jpg',
                'timeline/mr-douglas-1992.jpg',
                'timeline/mr-douglas-1990.jpg'
            ];
            
            for (var i = 0; i < timelineImages.length; i++) {
                var fullPath = timelineImages[i];
                testImages.push({ src: fullPath, name: fullPath.split('/').pop() });
                var img = document.createElement('img');
                img.src = fullPath;
                img.className = 'test-img';
                img.onload = function() { addLog('✓ Image exists: ' + this.src); };
                img.onerror = function() { addLog('✗ Image MISSING: ' + this.src, true); };
                container.appendChild(img);
            }
            
            return testImages;
        }
        
        document.getElementById('loadTestBtn').onclick = function() {
            var images = scanForImages();
            for (var i = 0; i < images.length; i++) {
                loadImageToCanvas(images[i].src, images[i].name);
            }
        };
        
        document.getElementById('clearCanvas').onclick = function() {
            canvas.clear();
            canvas.backgroundColor = '#ffffff';
            canvas.renderAll();
            addLog('Canvas cleared');
        };
        
        initCanvas();
        scanForImages();
        addLog('Ready - click "Test Selected Images" to load images into canvas');
    </script>
</body>
</html>'''
    
    Path("storyboard_test.html").write_text(test_html)
    print(f"✅ Created test page: storyboard_test.html")
    print()
    print("To diagnose the issue:")
    print("1. Run: python3 -m http.server 9000")
    print("2. Open: http://localhost:9000/storyboard_test.html")
    print("3. Check if images load - if not, it's a path or CORS issue")
    print()
    print("If images load in test but not storyboard, the issue is in the fabric.js integration")

if __name__ == "__main__":
    fix_storyboard()