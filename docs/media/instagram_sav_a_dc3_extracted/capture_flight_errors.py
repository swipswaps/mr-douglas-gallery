#!/usr/bin/env python3
"""
Diagnostic tool for flight simulator.
Automatically installs required dependencies, runs a local server,
captures console/network errors, and produces a report.
"""

import subprocess
import sys
import time
import json
from pathlib import Path

def ensure_playwright():
    """Check for playwright, install if missing."""
    try:
        import playwright
    except ImportError:
        print("Playwright not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        print("✅ Playwright installed.")
    else:
        print("✅ Playwright already installed.")

def main():
    ensure_playwright()
    from playwright.sync_api import sync_playwright

    # ----- Start local HTTP server -----
    print("Starting HTTP server on port 8000...")
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)  # give server time to start

    diagnostics = {
        "url": "http://localhost:8000/flying_game_debug.html",
        "console_errors": [],
        "network_errors": [],
        "model_load_success": False,
        "page_loaded": False,
        "airplane_exists": False,
        "screenshot": "flight_sim_screenshot.png",
        "recommendation": ""
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # visible for debugging
            page = browser.new_page()

            # Capture console errors
            page.on("console", lambda msg: 
                diagnostics["console_errors"].append({
                    "type": msg.type,
                    "text": msg.text
                }) if msg.type in ["error", "warning"] else None
            )

            # Capture failed network requests
            page.on("requestfailed", lambda request:
                diagnostics["network_errors"].append({
                    "url": request.url,
                    "failure": str(request.failure) if request.failure else "Unknown"
                })
            )

            print(f"Navigating to {diagnostics['url']}...")
            response = page.goto(diagnostics['url'], wait_until="networkidle")
            diagnostics["page_loaded"] = response.status == 200

            time.sleep(5)  # let model load attempt

            # Inject script to check Three.js airplane object
            try:
                airplane_exists = page.evaluate("""
                    () => {
                        if (typeof airplane !== 'undefined') return airplane !== null;
                        return false;
                    }
                """)
                diagnostics["airplane_exists"] = airplane_exists
            except:
                diagnostics["airplane_exists"] = False

            # Check for successful model load message in console
            load_ok = any("Aircraft model loaded" in e['text'] for e in diagnostics["console_errors"])
            diagnostics["model_load_success"] = load_ok

            # Screenshot
            page.screenshot(path=diagnostics["screenshot"])

            # Determine recommendation
            if not diagnostics["page_loaded"]:
                diag["recommendation"] = "HTML file not found. Ensure flying_game_debug.html exists."
            elif any("Cross-Origin" in e['text'] for e in diagnostics["console_errors"]):
                diagnostics["recommendation"] = "CORS error – page opened with file://. Use http:// (the script should have done this)."
            elif any("404" in str(err['url']) for err in diagnostics["network_errors"]):
                diagnostics["recommendation"] = "Model file 404. Ensure scene.gltf is in the same folder as flying_game_debug.html, or in models/ subfolder and the HTML points correctly."
            elif diagnostics["airplane_exists"] and not diagnostics["model_load_success"]:
                diagnostics["recommendation"] = "Airplane object exists but model load message missing – possibly a silent error. Check console for WebGL issues."
            elif not diagnostics["airplane_exists"]:
                diagnostics["recommendation"] = "Airplane object not found. Likely model load failed. Check network errors above."
            else:
                diagnostics["recommendation"] = "Model loaded and airplane exists. If still invisible, adjust camera or model scale."

            browser.close()

    except Exception as e:
        diagnostics["console_errors"].append({"type": "exception", "text": str(e)})
        diagnostics["recommendation"] = f"Script exception: {e}"

    finally:
        server.terminate()
        server.wait()

    # Save report
    report_path = Path("flight_sim_report.json")
    report_path.write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    print(f"\n✅ Report saved: {report_path.resolve()}")
    print(f"   Screenshot saved: {diagnostics['screenshot']}")
    print("\n📊 Summary:")
    print(f"   Page loaded: {diagnostics['page_loaded']}")
    print(f"   Airplane exists in scene: {diagnostics['airplane_exists']}")
    print(f"   Model load success (console message): {diagnostics['model_load_success']}")
    print(f"   Console errors count: {len(diagnostics['console_errors'])}")
    print(f"   Network errors count: {len(diagnostics['network_errors'])}")
    print(f"\n🔧 Recommendation: {diagnostics['recommendation']}")
    print("\n📤 Upload 'flight_sim_report.json' and the screenshot for analysis.")

if __name__ == "__main__":
    main()