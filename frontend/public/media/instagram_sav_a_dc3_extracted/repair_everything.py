#!/usr/bin/env python3
"""
Fix timeline image paths (add /timeline/ prefix) and replace storyboard
with a faster, non‑freezing version.
"""

import re
from pathlib import Path

HTML_PATH = Path("index_cloud.html")
BACKUP_PATH = Path("index_cloud_before_repair.html")

# 1. Fix timeline image URLs (add /timeline/ prefix where missing)
def fix_timeline_paths(content):
    # Look for timeline items: they have src="filename.jpg" (with no folder)
    # But we want src="timeline/filename.jpg"
    # We'll replace src="mr-douglas-...jpg" or src="united-...jpg" etc.
    # Only do this for img tags inside .timeline-card or timeline container.
    pattern = r'(<img[^>]*src=")(?!timeline/)([^"]+\.jpg)"'
    def repl(match):
        prefix = match.group(1)
        filename = match.group(2)
        # Only if the filename matches known timeline images? Safer to just add timeline/ if not present
        if not filename.startswith('timeline/') and not filename.startswith('/timeline/'):
            return f'{prefix}timeline/{filename}"'
        return match.group(0)
    return re.sub(pattern, repl, content)

# 2. A much more efficient storyboard (no mutation observer flood)
LIGHT_STORYBOARD = """
<!-- ========== LIGHTWEIGHT STORYBOARD ========== -->
<style>
.storyboard-btn{position:fixed;bottom:20px;right:20px;background:#3b82f6;color:white;border:none;border-radius:50px;padding:12px 24px;font-size:1rem;font-weight:bold;cursor:pointer;z-index:1000;box-shadow:0 4px 12px rgba(0,0,0,0.3);}
.storyboard-btn:hover{background:#2563eb;}
.storyboard-modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:2000;overflow:auto;}
.storyboard-modal.active{display:flex;flex-direction:column;}
.storyboard-container{background:#1e293b;margin:20px auto;padding:20px;border-radius:16px;max-width:95%;width:1200px;}
.storyboard-toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;}
.storyboard-canvas-wrapper{background:#0f172a;border-radius:12px;padding:12px;text-align:center;overflow-x:auto;}
#storyboardCanvas{border:2px solid #475569;border-radius:8px;background:white;}
.storyboard-controls{display:flex;gap:10px;justify-content:center;margin:15px 0;}
.storyboard-controls button{background:#3b82f6;border:none;color:white;padding:8px 16px;border-radius:8px;cursor:pointer;}
.storyboard-controls button.danger{background:#ef4444;}
.storyboard-controls button.success{background:#10b981;}
.storyboard-image-list{background:#0f172a;border-radius:12px;padding:12px;margin-top:20px;}
.storyboard-thumbnails{display:flex;gap:12px;overflow-x:auto;padding:8px;}
.storyboard-thumb{width:80px;height:80px;object-fit:cover;border-radius:8px;cursor:pointer;border:2px solid transparent;}
.storyboard-thumb:hover{border-color:#3b82f6;transform:scale(1.05);}
.close-modal{background:#475569;color:white;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;}
</style>
<button class="storyboard-btn" id="openStoryboardBtn">🎨 Open Storyboard (36x48")</button>
<div id="storyboardModal" class="storyboard-modal"><div class="storyboard-container"><div class="storyboard-toolbar"><h3 style="color:white;">📸 Storyboard Builder – 36×48" @ 300 DPI</h3><button class="close-modal" id="closeStoryboardBtn">✖ Close</button></div><div class="storyboard-canvas-wrapper"><canvas id="storyboardCanvas" width="1080" height="1440" style="width:100%; height:auto; max-width:1080px;"></canvas></div><div class="storyboard-controls"><button id="exportStoryboardBtn" class="success">⬇ Export PNG (10800×14400) – 300 DPI</button><button id="clearStoryboardBtn" class="danger">🗑 Clear All</button></div><div class="storyboard-image-list"><strong style="color:white;">📁 Images (click to remove):</strong><div class="storyboard-thumbnails" id="storyboardThumbnails"></div></div></div></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.0/fabric.min.js"></script>
<script>
(function(){
    window.storyboardImages = [];
    window.displayCanvas = null;
    const targetW=10800, targetH=14400, scale=10;
    function loadImage(src){return new Promise((resolve,reject)=>{let i=new Image();i.crossOrigin="Anonymous";i.onload=()=>resolve(i);i.onerror=reject;i.src=src;});}
    window.addImageToStoryboard=async function(src){
        if(window.storyboardImages.some(i=>i.src===src)){alert("Already added");return;}
        try{
            let img=await loadImage(src);
            let dispW=200, dispH=dispW/(img.width/img.height);
            let newImg={src:src,width:img.width,height:img.height,left:50,top:50,scaleX:dispW/img.width,scaleY:dispH/img.height};
            window.storyboardImages.push(newImg);
            if(window.displayCanvas){
                let fImg=new fabric.Image(img,{left:50,top:50,scaleX:dispW/img.width,scaleY:dispH/img.height,hasControls:true,hasBorders:true,lockRotation:true});
                newImg.fabricObject=fImg;
                window.displayCanvas.add(fImg);
                window.displayCanvas.renderAll();
            }
            updateThumbs();
        }catch(e){alert("Failed: "+e.message);}
    };
    function updateThumbs(){
        let c=document.getElementById('storyboardThumbnails');if(!c)return;
        c.innerHTML=window.storyboardImages.map((img,idx)=>`<img class="storyboard-thumb" src="${img.src}" data-index="${idx}">`).join('');
        document.querySelectorAll('.storyboard-thumb').forEach(th=>th.onclick=e=>{let idx=parseInt(th.dataset.index);if(!isNaN(idx)){if(window.displayCanvas&&window.storyboardImages[idx].fabricObject)window.displayCanvas.remove(window.storyboardImages[idx].fabricObject);window.storyboardImages.splice(idx,1);window.displayCanvas?.renderAll();updateThumbs();}});
    }
    window.exportStoryboard=async function(){
        if(!window.storyboardImages.length){alert("No images");return;}
        let off=document.createElement('canvas');off.width=targetW;off.height=targetH;
        let ctx=off.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,targetW,targetH);
        for(let item of window.storyboardImages){
            try{
                let img=await loadImage(item.src);
                let left=(item.left||0)*scale,top=(item.top||0)*scale;
                let w=img.width*(item.scaleX||1)*scale,h=img.height*(item.scaleY||1)*scale;
                ctx.drawImage(img,left,top,w,h);
            }catch(e){}
        }
        let a=document.createElement('a');a.download='storyboard_36x48_300dpi.png';a.href=off.toDataURL('image/png');a.click();
    };
    function clearAll(){if(confirm("Clear all?")){window.storyboardImages=[];window.displayCanvas?.clear();window.displayCanvas?.renderAll();updateThumbs();}}
    function init(){
        let can=document.getElementById('storyboardCanvas');if(!can)return;
        window.displayCanvas=new fabric.Canvas('storyboardCanvas');
        window.displayCanvas.setDimensions({width:1080,height:1440});
        window.displayCanvas.on('object:modified',e=>{let obj=e.target;let idx=window.storyboardImages.findIndex(i=>i.fabricObject===obj);if(idx!==-1){window.storyboardImages[idx].left=obj.left;window.storyboardImages[idx].top=obj.top;window.storyboardImages[idx].scaleX=obj.scaleX;window.storyboardImages[idx].scaleY=obj.scaleY;}});
        window.displayCanvas.renderAll();updateThumbs();
        document.getElementById('openStoryboardBtn').onclick=()=>document.getElementById('storyboardModal').classList.add('active');
        document.getElementById('closeStoryboardBtn').onclick=()=>document.getElementById('storyboardModal').classList.remove('active');
        document.getElementById('exportStoryboardBtn').onclick=()=>window.exportStoryboard();
        document.getElementById('clearStoryboardBtn').onclick=clearAll;
        window.onclick=e=>{if(e.target===document.getElementById('storyboardModal'))document.getElementById('storyboardModal').classList.remove('active');};
    }
    function addButtons(){
        function addBtn(img,src){
            if(!src||img.parentElement.querySelector('.storyboard-add-btn'))return;
            let btn=document.createElement('button');
            btn.className='storyboard-add-btn';
            btn.innerHTML='📌 Add to Storyboard';
            btn.style.cssText='position:absolute;bottom:8px;right:8px;background:#3b82f6;color:white;border:none;border-radius:20px;padding:4px 12px;font-size:0.7rem;cursor:pointer;z-index:10;';
            btn.onclick=e=>{e.stopPropagation();window.addImageToStoryboard(src);};
            let cont=img.closest('.card, .timeline-card')||img.parentElement;
            if(getComputedStyle(cont).position==='static')cont.style.position='relative';
            cont.appendChild(btn);
        }
        document.querySelectorAll('.card img, .timeline-card img, .carousel-item, .card-media').forEach(img=>{if(img.src&&!img.src.startsWith('data:'))addBtn(img,img.src);});
    }
    let check=setInterval(()=>{if(typeof fabric!=='undefined'){clearInterval(check);init();addButtons();}},200);
})();
</script>
<!-- ========== END STORYBOARD ========== -->
"""

def apply_repair():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup
    with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Fix timeline image paths
    content = fix_timeline_paths(content)
    
    # Remove any existing storyboard and inject the light version
    # Remove from <!-- ========== STORYBOARD BUILDER to END STORYBOARD
    pattern = r'<!-- ========== STORYBOARD BUILDER.*?<!-- ========== END STORYBOARD ========== -->'
    content = re.sub(pattern, LIGHT_STORYBOARD, content, flags=re.DOTALL)
    
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Repaired timeline paths and replaced storyboard with lightweight version.")
    print("📁 Backup saved as", BACKUP_PATH)
    print("💡 Hard refresh (Ctrl+Shift+R). Images should load, page should be fast.")

if __name__ == "__main__":
    apply_repair()