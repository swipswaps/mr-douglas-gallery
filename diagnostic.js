(function() {
    console.clear();
    console.log('=== 🔍 AUTO-DIAGNOSTIC SCRIPT START ===');

    console.log('[CHECK] Debug flag (window.__DEBUG_ACTIVE__):', window.__DEBUG_ACTIVE__ || '❌ NOT FOUND (old script)');

    const images = document.querySelectorAll('img');
    console.log('[CHECK] Images found:', images.length);

    const canvases = document.querySelectorAll('canvas');
    console.log('[CHECK] Canvases found:', canvases.length);
    canvases.forEach((c, i) => console.log(`  Canvas ${i}: ${c.width}x${c.height}, Position: (${c.offsetLeft}, ${c.offsetTop})`));

    const selectedEl = document.querySelector('[data-selected="true"], .selected, .active, [class*="selected"]');
    console.log('[CHECK] Currently selected element in DOM:', selectedEl ? selectedEl.tagName : 'None');

    if (images.length === 0) {
        console.error('[ERROR] No images found on page.');
        console.log('=== AUTO-DIAGNOSTIC SCRIPT END ===');
        return;
    }

    const targetImg = images[0];
    console.log('[ACTION] Simulating click on image:', targetImg.src.split('/').pop() || targetImg.src);
    targetImg.click();

    setTimeout(() => {
        console.log('--- [POST-CLICK REPORT] ---');

        const domHandles = document.querySelectorAll('[class*="handle"], [class*="resize"], .corner-handle, .edge-handle, [data-handle]');
        console.log('[RESULT] DOM Resize Handles found:', domHandles.length);
        if (domHandles.length === 0) console.warn('[WARN] ❌ No DOM handles detected.');

        const overlayCanvases = document.querySelectorAll('canvas[style*="overlay"], canvas[style*="absolute"], canvas:not([style*="display:none"])');
        const visibleOverlays = Array.from(overlayCanvases).filter(c => c.offsetParent !== null);
        console.log('[RESULT] Visible overlay canvases (potential handles):', visibleOverlays.length);

        let state = window.__EDITOR_STATE__ || window.__LAYOUT_STATE__ || window.editorState || window.__STATE__;
        if (state) {
            console.log('[STATE] Editor state object found:', state);
            if (state.resizeTargetId) console.log('[STATE] 🔑 resizeTargetId =', state.resizeTargetId);
            else console.warn('[STATE] ❌ resizeTargetId is MISSING or undefined.');
        } else {
            console.warn('[STATE] ❌ No global state object found (__EDITOR_STATE__). Searching window for "resize"...');
            const keys = Object.keys(window).filter(k => k.toLowerCase().includes('resize'));
            console.log('[STATE] Window keys containing "resize":', keys.slice(0, 15));
        }

        const rect = targetImg.getBoundingClientRect();
        console.log('[GEOMETRY] Clicked Image Rect:', {
            x: Math.round(rect.x), y: Math.round(rect.y),
            width: Math.round(rect.width), height: Math.round(rect.height),
            viewport: `${window.innerWidth}x${window.innerHeight}`
        });

        let frameworkFound = false;
        for (let key in targetImg) {
            if (key.startsWith('__reactInternalInstance') || key.startsWith('__vue__')) {
                console.log('[FRAMEWORK] Found internal prop:', key);
                frameworkFound = true;
                break;
            }
        }
        if (!frameworkFound) console.log('[FRAMEWORK] No React/Vue internals detected on the image node.');

        console.log('=== ✅ AUTO-DIAGNOSTIC SCRIPT END ===');
        console.log('📋 Please copy EVERYTHING from this console output and paste it in the chat.');
    }, 600);
})();
