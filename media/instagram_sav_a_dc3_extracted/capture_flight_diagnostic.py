#!/usr/bin/env python3
"""
Diagnostic: captures console errors, network logs, and scene state
from the flight simulator. Run this after starting a local HTTP server.
"""

import json
import subprocess
import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

def ensure_playwright():
    try:
        import playwright
    except ImportError:
        print("Installing playwright...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

def main():
    ensure_playwright()
    from playwright.sync_api import sync_playwright

    # Start local server
    print("Starting HTTP server on port 8000...")
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)

    diagnostics = {
        "url": "http://localhost:8000/flying_game_airport_fixed.html",
        "console": [],
        "network": [],
        "airplane_exists": False,
        "terrain_exists": False,
        "page_loaded": False,
        "screenshot": "flight_diagnostic.png"
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # Collect console messages
            page.on("console", lambda msg: diagnostics["console"].append({
                "type": msg.type,
                "text": msg.text
            }))

            # Collect failed requests (404 etc.)
            page.on("requestfailed", lambda req: diagnostics["network"].append({
                "url": req.url,
                "failure": req.failure
            }))

            # Also collect successful requests for model/terrain
            page.on("response", lambda resp: None)  # placeholder; we only need failures for now

            print(f"Navigating to {diagnostics['url']}...")
            response = page.goto(diagnostics['url'], wait_until="networkidle", timeout=30000)
            diagnostics["page_loaded"] = response.status == 200

            # Wait for loading attempts
            time.sleep(5)

            # Inject script to inspect Three.js scene
            try:
                airplane_exists = page.evaluate("""
                    () => {
                        if (typeof airplane !== 'undefined') return airplane !== null;
                        return false;
                    }
                """)
                diagnostics["airplane_exists"] = airplane_exists
            except Exception as e:
                diagnostics["airplane_exists"] = f"error: {e}"

            try:
                terrain_exists = page.evaluate("""
                    () => {
                        if (typeof terrainMesh !== 'undefined') return terrainMesh !== null;
                        return false;
                    }
                """)
                diagnostics["terrain_exists"] = terrain_exists
            except Exception as e:
                diagnostics["terrain_exists"] = f"error: {e}"

            # Take screenshot
            page.screenshot(path=diagnostics["screenshot"])

            browser.close()

    except Exception as e:
        diagnostics["console"].append({"type": "exception", "text": str(e)})

    finally:
        server.terminate()
        server.wait()

    # Save report
    report_path = Path("flight_diagnostic.json")
    report_path.write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    print(f"\n✅ Diagnostic saved: {report_path.resolve()}")
    print(f"   Screenshot: {diagnostics['screenshot']}")
    print("\n📊 Summary:")
    print(f"   Page loaded: {diagnostics['page_loaded']}")
    print(f"   Airplane exists: {diagnostics['airplane_exists']}")
    print(f"   Terrain exists: {diagnostics['terrain_exists']}")
    print(f"   Console errors: {len([m for m in diagnostics['console'] if m['type']=='error'])}")
    print(f"   Network failures: {len(diagnostics['network'])}")
    print("\n📤 Upload 'flight_diagnostic.json' for analysis.")

if __name__ == "__main__":
    main()