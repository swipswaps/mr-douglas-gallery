#!/usr/bin/env python3
"""
Generate working flight simulator (no heavy STL), capture evidence,
and save to SQLite database.
"""

import subprocess
import sys
import time
import sqlite3
from pathlib import Path
from datetime import datetime

# ------------------------------------------------------------
# 1. Generate the working HTML (same as working_flight.html)
# ------------------------------------------------------------
def generate_working_html(model_path='models/scene.gltf'):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mr. Douglas – Working Flight Simulator</title>
    <style>
        body {{ margin: 0; overflow: hidden; font-family: monospace; }}
        #info {{
            position: absolute; top: 20px; left: 20px; background: rgba(0,0,0,0.7);
            color: white; padding: 8px 15px; border-radius: 8px; pointer-events: none; z-index: 10;
        }}
        .controls {{
            position: absolute; bottom: 20px; left: 20px; background: rgba(0,0,0,0.6);
            color: #ccc; padding: 8px 12px; border-radius: 8px; pointer-events: none; z-index: 10;
        }}
        .debug {{
            position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.7);
            color: #0f0; padding: 8px; border-radius: 8px; font-size: 12px; pointer-events: none;
        }}
    </style>
</head>
<body>
    <div id="info">✈️ Mr. Douglas – Working</div>
    <div class="controls">↑↓ pitch | ←→ roll | Q/E throttle | R reset | P physics | Camera follows plane</div>
    <div class="debug" id="debug"></div>

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

        const debugDiv = document.getElementById('debug');
        function log(msg) {{
            debugDiv.innerHTML = msg + '<br>' + debugDiv.innerHTML;
            console.log(msg);
        }}

        // --- Scene setup ---
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x87CEEB);
        scene.fog = new THREE.Fog(0x87CEEB, 300, 800);

        const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
        camera.position.set(0, 4, 8);
        camera.lookAt(0, 0, 0);

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        document.body.appendChild(renderer.domElement);
        // Allow right-click
        renderer.domElement.addEventListener('contextmenu', (e) => {{}});
        // Ensure canvas can receive keyboard events
        renderer.domElement.setAttribute('tabindex', '0');
        renderer.domElement.style.outline = 'none';
        renderer.domElement.focus();

        // --- Lighting ---
        const ambientLight = new THREE.AmbientLight(0x606070);
        scene.add(ambientLight);
        const sunLight = new THREE.DirectionalLight(0xfff5d1, 1.2);
        sunLight.position.set(50, 100, 30);
        sunLight.castShadow = true;
        sunLight.shadow.mapSize.width = 1024;
        sunLight.shadow.mapSize.height = 1024;
        scene.add(sunLight);
        const fillLight = new THREE.DirectionalLight(0x88aaff, 0.6);
        fillLight.position.set(-30, 20, -30);
        scene.add(fillLight);

        // --- Simple ground (green plane + grid) ---
        const groundPlane = new THREE.Mesh(
            new THREE.PlaneGeometry(400, 400),
            new THREE.MeshStandardMaterial({{ color: 0x3c9e3c, roughness: 0.8, side: THREE.DoubleSide }})
        );
        groundPlane.rotation.x = -Math.PI / 2;
        groundPlane.position.y = -2;
        groundPlane.receiveShadow = true;
        scene.add(groundPlane);

        const gridHelper = new THREE.GridHelper(400, 40, 0x88aaff, 0x335588);
        gridHelper.position.y = -1.9;
        scene.add(gridHelper);

        // --- Load aircraft model (no rotation correction) ---
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
                airplane.scale.set(0.5, 0.5, 0.5);
                scene.add(airplane);
                log('Aircraft loaded – orientation correct');
                window.airplane = airplane;
                window.__testState = {{ airplaneLoaded: true }};
            }},
            undefined,
            (err) => log(`MODEL ERROR: ${{err.message}}`)
        );

        // --- Physics state (start above ground) ---
        let position = new THREE.Vector3(0, 3, 0);
        let velocity = new THREE.Vector3(0, 0, 0);
        let rotation = new THREE.Euler(0, 0, 0, 'YXZ');
        let throttle = 0;
        let propAngle = 0;
        const maxThrottle = 1.0;
        const drag = 0.98;
        const liftFactor = 0.03;
        const controlSensitivity = 0.03;

        const keyState = {{
            ArrowUp: false, ArrowDown: false, ArrowLeft: false, ArrowRight: false,
            KeyW: false, KeyS: false, KeyA: false, KeyD: false,
            KeyQ: false, KeyE: false, KeyR: false, KeyP: false
        }};

        window.addEventListener('keydown', (e) => {{
            const code = e.code;
            if (keyState.hasOwnProperty(code)) keyState[code] = true;
            if (code === 'KeyR') {{
                position.set(0, 3, 0);
                velocity.set(0, 0, 0);
                throttle = 0;
                rotation.set(0, 0, 0);
                log('Reset position');
            }}
            if (code === 'KeyP') physicsEnabled = !physicsEnabled;
            e.preventDefault(); // prevent arrow keys from scrolling
        }});
        window.addEventListener('keyup', (e) => {{
            if (keyState.hasOwnProperty(e.code)) keyState[e.code] = false;
        }});

        // --- Chase camera (simple: behind the plane) ---
        let cameraOffset = new THREE.Vector3(0, 1.2, 6);
        function updateCamera() {{
            if (!airplane) return;
            const quat = airplane.quaternion;
            const worldOffset = cameraOffset.clone().applyQuaternion(quat);
            camera.position.lerp(position.clone().add(worldOffset), 0.1);
            camera.lookAt(position);
        }}

        let lastTime = performance.now();

        function animate() {{
            const now = performance.now();
            let dt = Math.min(0.033, (now - lastTime) / 1000);
            lastTime = now;
            if (dt < 0.01) dt = 0.016;

            // Throttle
            if (keyState.KeyQ) throttle -= 1.0 * dt;
            if (keyState.KeyE) throttle += 1.0 * dt;
            throttle = Math.max(0, Math.min(maxThrottle, throttle));

            let pitchInput = (keyState.ArrowUp || keyState.KeyW ? 1 : (keyState.ArrowDown || keyState.KeyS ? -1 : 0));
            let rollInput = (keyState.ArrowRight || keyState.KeyD ? 1 : (keyState.ArrowLeft || keyState.KeyA ? -1 : 0));

            if (physicsEnabled) {{
                const thrust = throttle * 12.0;
                const pitchRate = pitchInput * controlSensitivity * (0.5 + throttle*0.5);
                const rollRate = rollInput * controlSensitivity * (0.5 + throttle*0.5);
                rotation.x += pitchRate * dt;
                rotation.z += rollRate * dt;
                rotation.x = Math.max(-Math.PI/2.2, Math.min(Math.PI/2.2, rotation.x));
                rotation.z = Math.max(-Math.PI/2.2, Math.min(Math.PI/2.2, rotation.z));

                const quat = new THREE.Quaternion().setFromEuler(rotation);
                const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(quat);
                const worldThrust = forward.multiplyScalar(thrust);
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
                // Direct rotation (debug)
                const rotSpeed = 0.05;
                if (pitchInput !== 0) rotation.x += pitchInput * rotSpeed;
                if (rollInput !== 0) rotation.z += rollInput * rotSpeed;
                rotation.x = Math.max(-Math.PI/2, Math.min(Math.PI/2, rotation.x));
                rotation.z = Math.max(-Math.PI/2, Math.min(Math.PI/2, rotation.z));
                const speed = throttle * 12;
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
        log('Simulation started – use arrow keys and Q/E');
    </script>
</body>
</html>"""

# ------------------------------------------------------------
# 2. Capture evidence using Playwright
# ------------------------------------------------------------
def ensure_playwright():
    try:
        import playwright
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

def main():
    ensure_playwright()
    from playwright.sync_api import sync_playwright

    # Generate working HTML
    html_content = generate_working_html()
    html_path = Path("working_flight_evidence.html")
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

    # DB to store evidence
    db_path = Path("working_flight_evidence.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS console_logs (type TEXT, text TEXT, timestamp TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS airplane_state (timestamp TEXT, pos_x REAL, pos_y REAL, pos_z REAL, rot_x REAL, rot_y REAL, rot_z REAL)")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # visible for debugging, set to True for CI
            page = browser.new_page()

            # Capture console
            def on_console(msg):
                c.execute("INSERT INTO console_logs VALUES (?, ?, ?)",
                          (msg.type, msg.text, datetime.now().isoformat()))
                conn.commit()
            page.on("console", on_console)

            url = "http://localhost:8000/working_flight_evidence.html"
            print(f"Navigating to {url}...")
            response = page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Simulate some basic controls to prove they work
            print("Simulating ArrowUp key...")
            page.keyboard.down('ArrowUp')
            time.sleep(0.5)
            page.keyboard.up('ArrowUp')
            time.sleep(1)

            # Get airplane state
            state = page.evaluate("""
                () => {
                    if (window.airplane) {
                        const pos = window.airplane.position;
                        const rot = window.airplane.rotation;
                        return { x: pos.x, y: pos.y, z: pos.z, rotX: rot.x, rotY: rot.y, rotZ: rot.z };
                    }
                    return null;
                }
            """)
            if state:
                timestamp = datetime.now().isoformat()
                c.execute("INSERT INTO airplane_state VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (timestamp, state['x'], state['y'], state['z'], state['rotX'], state['rotY'], state['rotZ']))
                conn.commit()
                print(f"✅ Airplane state captured: pos=({state['x']:.2f}, {state['y']:.2f}, {state['z']:.2f}) rot=({state['rotX']:.2f}, {state['rotY']:.2f}, {state['rotZ']:.2f})")
            else:
                print("❌ Airplane state not found – model may not have loaded")

            # Take screenshot
            screenshot_path = Path("working_flight_screenshot.png")
            page.screenshot(path=str(screenshot_path))
            # Store screenshot as BLOB
            with open(screenshot_path, "rb") as f:
                screenshot_blob = f.read()
            c.execute("CREATE TABLE screenshot (id INTEGER PRIMARY KEY, image BLOB)")
            c.execute("INSERT INTO screenshot (id, image) VALUES (1, ?)", (screenshot_blob,))
            conn.commit()
            print(f"Screenshot saved to {screenshot_path} and embedded in DB")

            # Write metadata
            c.execute("INSERT OR REPLACE INTO metadata VALUES ('page_loaded', 'True')")
            c.execute("INSERT OR REPLACE INTO metadata VALUES ('airplane_loaded', 'True' if state else 'False')")
            c.execute("INSERT OR REPLACE INTO metadata VALUES ('controls_simulated', 'ArrowUp was sent')")
            conn.commit()

            browser.close()

    except Exception as e:
        c.execute("INSERT INTO console_logs VALUES ('exception', ?, ?)", (str(e), datetime.now().isoformat()))
        conn.commit()
        print(f"❌ Exception: {e}")
    finally:
        server.terminate()
        server.wait()

    # Print summary
    print(f"\n✅ Database saved to {db_path.resolve()}")
    print("📊 Evidence summary:")
    c.execute("SELECT key, value FROM metadata")
    for row in c.fetchall():
        print(f"   {row[0]}: {row[1]}")
    c.execute("SELECT COUNT(*) FROM console_logs")
    print(f"   Console logs captured: {c.fetchone()[0]}")
    conn.close()

if __name__ == "__main__":
    main()