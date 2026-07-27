#!/usr/bin/env python3
"""
Comprehensive flight simulator diagnostic tool.
Generates a corrected HTML, runs it via Playwright, captures all logs,
and saves everything into a SQLite database for upload.
"""

import subprocess
import sys
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime

# ------------------------------------------------------------
# 1. Generate the corrected HTML (no rotation, fallback terrain)
# ------------------------------------------------------------
def generate_html(model_path='models/scene.gltf'):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mr. Douglas – Fixed Diagnostic</title>
    <style>
        body {{ margin: 0; overflow: hidden; font-family: monospace; }}
        #info {{
            position: absolute; top: 20px; left: 20px; background: rgba(0,0,0,0.7); color: white;
            padding: 8px 15px; border-radius: 8px; pointer-events: none; z-index: 10;
        }}
        .controls {{
            position: absolute; bottom: 20px; left: 20px; background: rgba(0,0,0,0.6);
            color: #ccc; padding: 8px 12px; border-radius: 8px; pointer-events: none; z-index: 10;
        }}
    </style>
</head>
<body>
    <div id="info">
        <strong>✈️ Mr. Douglas – Diagnostic Mode</strong><br>
        ↑↓ pitch | ←→ roll | Q/E throttle | R reset | P toggle physics
    </div>
    <div class="controls">🖱️ Right‑click for browser menu • Camera follows plane</div>

    <script type="importmap">
        {{
            "imports": {{
                "three": "https://unpkg.com/three@0.128.0/build/three.module.js",
                "three/addons/": "https://unpkg.com/three@0.128.0/examples/jsm/"
            }}
        }}
    </script>

    <script type="module">
        import * as THREE from 'three';
        import {{ GLTFLoader }} from 'three/addons/loaders/GLTFLoader.js';
        import {{ STLLoader }} from 'three/addons/loaders/STLLoader.js';

        window.testState = {{ airplaneLoaded: false, terrainLoaded: false }};

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x87CEEB);

        const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true, preserveDrawingBuffer: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        document.body.appendChild(renderer.domElement);
        renderer.domElement.addEventListener('contextmenu', (e) => {{}});

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x606070);
        scene.add(ambientLight);
        const sunLight = new THREE.DirectionalLight(0xfff5d1, 1.5);
        sunLight.position.set(100, 200, 50);
        sunLight.castShadow = true;
        scene.add(sunLight);
        const fillLight = new THREE.DirectionalLight(0x88aaff, 0.8);
        fillLight.position.set(-50, 20, -50);
        scene.add(fillLight);

        // Ground plane (green)
        const groundPlane = new THREE.Mesh(
            new THREE.PlaneGeometry(500, 500),
            new THREE.MeshStandardMaterial({{ color: 0x3c9e3c, roughness: 0.8, side: THREE.DoubleSide }})
        );
        groundPlane.rotation.x = -Math.PI / 2;
        groundPlane.position.y = -2;
        groundPlane.receiveShadow = true;
        scene.add(groundPlane);

        // Grid helper for reference
        const gridHelper = new THREE.GridHelper(1000, 50, 0x88aaff, 0x335588);
        gridHelper.position.y = -1.8;
        scene.add(gridHelper);

        // Simple fallback terrain (always visible)
        const fallbackTerrain = new THREE.Mesh(
            new THREE.BoxGeometry(200, 1, 200),
            new THREE.MeshStandardMaterial({{ color: 0x8B5A2B, roughness: 0.7 }})
        );
        fallbackTerrain.position.set(0, -2, 0);
        fallbackTerrain.receiveShadow = true;
        scene.add(fallbackTerrain);
        console.log('Fallback terrain added');

        // Try to load actual terrain STL (optional)
        const stlLoader = new STLLoader();
        stlLoader.load('skydive_deland.stl',
            (geometry) => {{
                const material = new THREE.MeshStandardMaterial({{ color: 0x8B5A2B, roughness: 0.6 }});
                const terrain = new THREE.Mesh(geometry, material);
                terrain.scale.set(0.1, 0.1, 0.1);
                terrain.position.set(0, -2, 0);
                terrain.castShadow = true;
                scene.add(terrain);
                window.testState.terrainLoaded = true;
                console.log('Actual terrain loaded (scaled)');
            }},
            undefined,
            (err) => console.warn('STL load skipped (optional):', err.message)
        );

        // Aircraft model – no rotation correction (model is already level)
        let airplane = null;
        let propellers = [];
        let physicsEnabled = true;
        const loader = new GLTFLoader();
        loader.load('{model_path}',
            (gltf) => {{
                airplane = gltf.scene;
                airplane.traverse((child) => {{
                    if (child.isMesh) {{
                        child.castShadow = true;
                        child.receiveShadow = true;
                        if (child.name.toLowerCase().includes('prop')) propellers.push(child);
                    }}
                }});
                // No rotation – the glTF is already oriented correctly
                airplane.scale.set(0.5, 0.5, 0.5);
                scene.add(airplane);
                window.testState.airplaneLoaded = true;
                console.log('Aircraft loaded (level orientation)');
                window.airplane = airplane;
            }},
            undefined,
            (err) => console.error('Aircraft load error:', err)
        );

        // Physics (same as working version)
        const startPos = new THREE.Vector3(0, 3, 0);
        let velocity = new THREE.Vector3(0, 0, 0);
        let position = startPos.clone();
        let rotation = new THREE.Euler(0, 0, 0, 'YXZ');
        let throttle = 0;
        let propAngle = 0;
        const maxThrottle = 1.0;
        const drag = 0.98;
        const liftFactor = 0.05;
        const controlSensitivity = 0.02;

        const keyState = {{
            ArrowUp: false, ArrowDown: false, ArrowLeft: false, ArrowRight: false,
            KeyW: false, KeyS: false, KeyA: false, KeyD: false,
            KeyQ: false, KeyE: false, KeyR: false, KeyP: false
        }};

        window.addEventListener('keydown', (e) => {{
            const code = e.code;
            if (keyState.hasOwnProperty(code)) keyState[code] = true;
            if (code === 'KeyR') {{
                position.copy(startPos);
                velocity.set(0, 0, 0);
                throttle = 0;
                rotation.set(0, 0, 0);
            }}
            if (code === 'KeyP') physicsEnabled = !physicsEnabled;
        }});
        window.addEventListener('keyup', (e) => {{
            if (keyState.hasOwnProperty(e.code)) keyState[e.code] = false;
        }});

        let cameraOffset = new THREE.Vector3(0, 1.5, 6);
        function updateCamera() {{
            if (!airplane) return;
            const quat = airplane.quaternion;
            const worldOffset = cameraOffset.clone().applyQuaternion(quat);
            camera.position.lerp(position.clone().add(worldOffset), 0.05);
            camera.lookAt(position);
        }}

        let lastTime = performance.now();
        function animate() {{
            const now = performance.now();
            let dt = Math.min(0.033, (now - lastTime) / 1000);
            lastTime = now;
            if (dt < 0.01) dt = 0.016;

            if (keyState.KeyQ) throttle -= 1.0 * dt;
            if (keyState.KeyE) throttle += 1.0 * dt;
            throttle = Math.max(0, Math.min(maxThrottle, throttle));

            let pitchInput = (keyState.ArrowUp || keyState.KeyW ? 1 : (keyState.ArrowDown || keyState.KeyS ? -1 : 0));
            let rollInput = (keyState.ArrowRight || keyState.KeyD ? 1 : (keyState.ArrowLeft || keyState.KeyA ? -1 : 0));

            if (physicsEnabled) {{
                const thrust = throttle * 15.0;
                const pitchRate = pitchInput * controlSensitivity * (0.5 + throttle*0.5);
                const rollRate = rollInput * controlSensitivity * (0.5 + throttle*0.5);
                rotation.x += pitchRate * dt;
                rotation.z += rollRate * dt;
                rotation.x = Math.max(-Math.PI/2.5, Math.min(Math.PI/2.5, rotation.x));
                rotation.z = Math.max(-Math.PI/2.5, Math.min(Math.PI/2.5, rotation.z));

                const quat = new THREE.Quaternion().setFromEuler(rotation);
                const localThrustDir = new THREE.Vector3(0, 0, -1);
                const worldThrust = localThrustDir.clone().applyQuaternion(quat).multiplyScalar(thrust);
                let worldAcc = worldThrust.clone();
                worldAcc.y -= 9.8 * dt;
                const speed = velocity.length();
                const lift = speed * speed * liftFactor * (pitchInput * 0.5 + 0.2);
                worldAcc.y += lift;
                velocity.x += worldAcc.x * dt;
                velocity.y += worldAcc.y * dt;
                velocity.z += worldAcc.z * dt;
                velocity.multiplyScalar(1 - drag * dt);
                position.x += velocity.x * dt;
                position.y += velocity.y * dt;
                position.z += velocity.z * dt;
                if (position.y < -1) position.y = -1;
            }} else {{
                const rotSpeed = 0.05;
                if (pitchInput !== 0) rotation.x += pitchInput * rotSpeed;
                if (rollInput !== 0) rotation.z += rollInput * rotSpeed;
                rotation.x = Math.max(-Math.PI/2, Math.min(Math.PI/2, rotation.x));
                rotation.z = Math.max(-Math.PI/2, Math.min(Math.PI/2, rotation.z));
                const speed = throttle * 10;
                if (airplane) {{
                    const quat = new THREE.Quaternion().setFromEuler(rotation);
                    const forward = new THREE.Vector3(0,0,-1).applyQuaternion(quat);
                    position.x += forward.x * speed * dt;
                    position.y += forward.y * speed * dt;
                    position.z += forward.z * speed * dt;
                }}
                if (position.y < -1) position.y = -1;
                velocity.set(0,0,0);
            }}

            if (airplane) {{
                airplane.position.copy(position);
                airplane.rotation.set(rotation.x, rotation.y, rotation.z);
                propAngle += throttle * 20 * dt;
                for (let prop of propellers) prop.rotation.x = propAngle;
            }}

            updateCamera();
            renderer.render(scene, camera);
            requestAnimationFrame(animate);
        }}
        animate();
        console.log('Simulation started');
    </script>
</body>
</html>"""

# ------------------------------------------------------------
# 2. Capture logs via Playwright and save to SQLite
# ------------------------------------------------------------
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

    # Generate the HTML file
    html_content = generate_html()
    html_path = Path("flight_diagnostic_fixed.html")
    html_path.write_text(html_content, encoding="utf-8")
    print(f"✅ HTML generated: {html_path}")

    # Start HTTP server
    print("Starting HTTP server on port 8000...")
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)

    # Initialize SQLite database
    db_path = Path("flight_sim_report.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS console_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            text TEXT,
            timestamp TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS network_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            failure TEXT,
            timestamp TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS screenshot (
            id INTEGER PRIMARY KEY,
            image BLOB
        )
    """)
    conn.commit()

    diagnostics = {
        "console": [],
        "network": [],
        "airplane_loaded": False,
        "terrain_loaded": False,
        "page_loaded": False
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # headless for automation
            page = browser.new_page()

            # Capture console messages
            def on_console(msg):
                entry = (msg.type, msg.text, datetime.now().isoformat())
                diagnostics["console"].append(entry)
                c.execute("INSERT INTO console_logs (type, text, timestamp) VALUES (?, ?, ?)", entry)
                conn.commit()
            page.on("console", on_console)

            # Capture failed network requests
            def on_request_failed(request):
                entry = (request.url, str(request.failure), datetime.now().isoformat())
                diagnostics["network"].append(entry)
                c.execute("INSERT INTO network_errors (url, failure, timestamp) VALUES (?, ?, ?)", entry)
                conn.commit()
            page.on("requestfailed", on_request_failed)

            url = "http://localhost:8000/flight_diagnostic_fixed.html"
            print(f"Navigating to {url}...")
            response = page.goto(url, wait_until="networkidle", timeout=30000)
            diagnostics["page_loaded"] = response.status == 200

            # Wait for scene to settle
            time.sleep(5)

            # Check testState from page
            try:
                state = page.evaluate("window.testState")
                if state:
                    diagnostics["airplane_loaded"] = state.get("airplaneLoaded", False)
                    diagnostics["terrain_loaded"] = state.get("terrainLoaded", False)
                else:
                    diagnostics["airplane_loaded"] = page.evaluate("typeof airplane !== 'undefined' && airplane !== null")
                    diagnostics["terrain_loaded"] = page.evaluate("typeof window.testState !== 'undefined' && window.testState.terrainLoaded")
            except Exception as e:
                print(f"Error evaluating testState: {e}")
                diagnostics["airplane_loaded"] = False
                diagnostics["terrain_loaded"] = False

            # Take screenshot and store as BLOB
            screenshot_bytes = page.screenshot(full_page=False)
            c.execute("INSERT INTO screenshot (id, image) VALUES (1, ?)", (screenshot_bytes,))
            conn.commit()
            print("Screenshot captured")

            browser.close()

    except Exception as e:
        print(f"Exception during capture: {e}")
        c.execute("INSERT INTO console_logs (type, text, timestamp) VALUES (?, ?, ?)",
                  ("exception", str(e), datetime.now().isoformat()))
        conn.commit()
    finally:
        server.terminate()
        server.wait()

    # Write metadata
    c.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", ("page_loaded", str(diagnostics["page_loaded"])))
    c.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", ("airplane_loaded", str(diagnostics["airplane_loaded"])))
    c.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", ("terrain_loaded", str(diagnostics["terrain_loaded"])))
    c.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", ("console_count", str(len(diagnostics["console"]))))
    c.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", ("network_errors_count", str(len(diagnostics["network"]))))
    conn.commit()
    conn.close()

    print(f"\n✅ All logs saved to {db_path.resolve()}")
    print(f"   Page loaded: {diagnostics['page_loaded']}")
    print(f"   Airplane loaded (Three.js object): {diagnostics['airplane_loaded']}")
    print(f"   Terrain loaded: {diagnostics['terrain_loaded']}")
    print(f"   Console messages: {len(diagnostics['console'])}")
    print(f"   Network errors: {len(diagnostics['network'])}")
    print("\n📤 Please upload the file 'flight_sim_report.db' for analysis.")

if __name__ == "__main__":
    main()