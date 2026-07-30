#!/usr/bin/env python3
"""
Capture flight simulator logs and save as plain text (no database).
"""

import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

def generate_html(model_path='models/scene.gltf'):
    # (same HTML as before – omitted for brevity, but you can copy from previous script)
    # For space, I assume you have the generate_html function from the previous script.
    # If not, I'll include the full HTML again.
    return """<!DOCTYPE html>..."""  # Placeholder – you can reuse the earlier one

def ensure_playwright():
    try:
        import playwright
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

def main():
    ensure_playwright()
    from playwright.sync_api import sync_playwright

    # Write HTML
    html_path = Path("flight_diagnostic_fixed.html")
    html_path.write_text(generate_html(), encoding="utf-8")
    print(f"✅ HTML: {html_path}")

    # Start server
    server = subprocess.Popen([sys.executable, "-m", "http.server", "8000"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    report_lines = []
    report_lines.append(f"=== Flight Simulator Diagnostic Report ===")
    report_lines.append(f"Timestamp: {datetime.now().isoformat()}")
    report_lines.append("")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture console messages
        page.on("console", lambda msg: report_lines.append(f"[{msg.type}] {msg.text}"))

        # Capture failed requests
        page.on("requestfailed", lambda req: report_lines.append(f"[NETWORK ERROR] {req.url} - {req.failure}"))

        url = "http://localhost:8000/flight_diagnostic_fixed.html"
        print(f"Navigating to {url}...")
        response = page.goto(url, wait_until="networkidle", timeout=30000)
        report_lines.append(f"Page loaded: {response.status == 200}")

        time.sleep(5)

        # Get test state
        try:
            state = page.evaluate("window.testState")
            report_lines.append(f"Airplane loaded: {state.get('airplaneLoaded', False) if state else 'unknown'}")
            report_lines.append(f"Terrain loaded: {state.get('terrainLoaded', False) if state else 'unknown'}")
        except:
            report_lines.append("Could not read testState")

        browser.close()

    server.terminate()

    # Save report
    report_path = Path("flight_sim_report.txt")
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n✅ Plain‑text report saved to: {report_path.resolve()}")
    print("📤 Upload that file for analysis.")
    print("\n--- BEGIN REPORT ---")
    print("\n".join(report_lines))
    print("--- END REPORT ---")

if __name__ == "__main__":
    main()