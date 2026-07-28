#!/usr/bin/env python3
"""
Generate final flight simulator with working physics, airport terrain,
and a built-in debug log downloader.
"""

import argparse
from pathlib import Path

def generate_html(model_path='models/scene.gltf'):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Mr. Douglas – Final Airport Flight</title>
    <style>
        body {{ margin: 0; overflow: hidden; font-family: 'Segoe UI', monospace; }}
        #info {{
            position: absolute; top: 20px; left: 20px; background: rgba(0,0,0,0.7);
            color: white; padding: 8px 15px; border-radius: 8px; pointer-events: none; z-index: 10;
            font-size: 14px;
        }}
        .controls {{
            position: absolute; bottom: 20px; left: 20px; background: rgba(0,0,0,0.6);
            color: #ccc; padding: 8px 12px; border-radius: 8px; pointer-events: none; z-index: 10;
            font-family: monospace; font-size: 12px;
        }}
        .debug-btn {{
            position: absolute; bottom: 20px; right: 20px; background: #2c3e50; color: white;
            border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; z-index: 20;
            font-family: monospace; font-size: 12px;
        }}
        .debug-btn:hover {{ background: #1e2a36; }}
    </style>
</head>
<body>
    <div id="info">✈️ Mr. Douglas – DeLand Airport (Final)</div>
    <div class="controls">↑↓ pitch | ←→ roll | Q/E throttle | R reset | P physics | Camera follows plane</div>
    <button id="debugBtn" class="debug-btn">📋 Save Debug Logs (TXT)</button>

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

        // ------------------------------------------------------------
        // DEBUG LOG COLLECTOR (stores all console messages)
        // ------------------------------------------------------------
        let debugLogs = [];
        const originalConsole = {{
            log: console.log,
            warn: console.warn,
            error: console.error
        }};
        console.log = (...args) => {{
            debugLogs.push({ type: 'log', text: args.join(' ') });
            originalConsole.log.apply(console, args);
        }};
        console.warn = (...args) => {{
            debugLogs.push({ type: 'warn', text: args.join(' ') });
            originalConsole.warn.apply(console, args);
        }};
        console.error = (...args) => {{
            debugLogs.push({ type: 'error', text: args.join(' ') });
            originalConsole.error.apply(console, args);
        }};

        // Helper to capture additional state
        function captureState() {{
            const state = {{
                airplane: window.airplane ? {{
                    pos: window.airplane.position,
                    rot: window.airplane.rotation
                }} : null,
                physics: {{ throttle: window.throttle, physicsEnabled: window.physicsEnabled }}
            }};
            return state;
        }}

        // Save logs to file
        document.getElementById('debugBtn').addEventListener('click', () => {{
            const logs = debugLogs.map(l => `[${{l.type}}] ${{l.text}}`).join('\\n');
            const state = captureState();
            let content = `=== FLIGHT SIMULATOR DEBUG LOG ===\\n`;
            content += `Time: ${{new Date().toISOString()}}\\n\\n`;
            content += `--- CONSOLE LOGS ---\\n${{logs}}\\n\\n`;
            content += `--- AIRPLANE STATE ---\\n`;
            if (state.airplane) {{
                content += `Position: x=${{state.airplane.pos.x.toFixed(2)}}, y=${{state.airplane.pos.y.toFixed(2)}}, z=${{state.airplane.pos.z.toFixed(2)}}\\n`;
                content += `Rotation: x=${{state.airplane.rot.x.toFixed(2)}}, y=${{state.airplane.rot.y.toFixed(2)}}, z=${{state.airplane.rot.z.toFixed(2)}}\\n`;
            }} else {{
                content += `Airplane not loaded\\n`;
            }}
            content += `\\n--- PHYSICS ---\\n`;
            content += `Throttle: ${{state.physics.throttle}}\\n`;
            content += `Physics enabled: ${{state.physics.physicsEnabled}}\\n`;
            
            // Capture screenshot using canvas.toDataURL
            const canvas = document.querySelector('canvas');
            if (canvas) {{
                const screenshot = canvas.toDataURL('image/png');
                content += `\\n--- SCREENSHOT (embedded as base64) ---\\n`;
                content += screenshot + '\\n';
            }}
            
            const blob = new Blob([content], {{ type: 'text/plain' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `flight_debug_${{Date.now()}}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }});

        // ------------------------------------------------------------
        // SCENE SETUP (identical to working_flight.html)
        // ------------------------------------------------------------
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x87CEEB);
        scene.fog = new THREE.Fog(0x87CEEB, 300, 800);

        const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
        camera.position.set(0, 4, 8);
        camera.lookAt(0, 0, 0);

        const renderer = new THREE.WebGLRenderer({{ antialias: true, preserveDrawingBuffer: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        document.body.appendChild(renderer.domElement);
        
        // Enable right-click (do NOT prevent default)
        renderer.domElement.addEventListener('contextmenu', (e) => {{}});
        // Ensure canvas can receive keyboard events
        renderer.domElement.tabIndex = 0;
        renderer.domElement.style.outline = 'none';
        renderer.domElement.focus();

        // --- Lighting (strong) ---
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

        // --- Airport Terrain (textured ground with runway) ---
        // Create a canvas texture with grass and runway
        const canvasTex = document.createElement('canvas');
        canvasTex.width = 1024;
        canvasTex.height = 1024;
        const ctx = canvasTex.getContext('2d');
        // Grass background
        ctx.fillStyle = '#3c9e3c';
        ctx.fillRect(0, 0, canvasTex.width, canvasTex.height);
        // Runway (light grey)
        ctx.fillStyle = '#888888';
        ctx.fillRect(canvasTex.width * 0.35, canvasTex.height * 0.45, canvasTex.width * 0.3, canvasTex.height * 0.1);
        // Runway white markings
        ctx.fillStyle = '#ffffff';
        for (let i = 0; i < 6; i++) {{
            ctx.fillRect(canvasTex.width * 0.45, canvasTex.height * (0.47 + i * 0.01), canvasTex.width * 0.1, canvasTex.height * 0.005);
        }}
        // Taxiway edge
        ctx.fillStyle = '#aaaaaa';
        ctx.fillRect(canvasTex.width * 0.32, canvasTex.height * 0.44, canvasTex.width * 0.36, 4);
        ctx.fillRect(canvasTex.width * 0.32, canvasTex.height * 0.56, canvasTex.width * 0.36, 4);
        const groundTexture = new THREE.CanvasTexture(canvasTex);
        groundTexture.wrapS = THREE.RepeatWrapping;
        groundTexture.wrapT = THREE.RepeatWrapping;
        groundTexture.repeat.set(8, 8);
        
        const groundPlane = new THREE.Mesh(
            new THREE.PlaneGeometry(800, 800),
            new THREE.MeshStandardMaterial({{ map: groundTexture, roughness: 0.8, metalness: 0.1 }})
        );
        groundPlane.rotation.x = -Math.PI / 2;
        groundPlane.position.y = -2;
        groundPlane.receiveShadow = true;
        scene.add(groundPlane);
        
        // Reference grid (optional)
        const gridHelper = new THREE.GridHelper(800, 40, 0x88aaff, 0x335588);
        gridHelper.position.y = -1.9;
        scene.add(gridHelper);

        // ------------------------------------------------------------
        // AIRCRAFT MODEL (no rotation correction – same as working version)
        // ------------------------------------------------------------
        let airplane = null;
        let propellers = [];
        let physicsEnabled = true;
        window.physicsEnabled = physicsEnabled;
        window.throttle = 0;

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
                console.log('Aircraft loaded – orientation correct');
                window.airplane = airplane;
            }},
            undefined,
            (err) => console.error('Model load error:', err)
        );

        // ------------------------------------------------------------
        // FLIGHT PHYSICS (exactly as working_flight.html)
        // ------------------------------------------------------------
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
                console.log('Reset position');
            }}
            if (code === 'KeyP') {{
                physicsEnabled = !physicsEnabled;
                window.physicsEnabled = physicsEnabled;
                console.log(`Physics toggled: ${{physicsEnabled ? 'ON' : 'OFF'}}`);
            }}
            e.preventDefault(); // prevent arrow keys from scrolling
        }});
        window.addEventListener('keyup', (e) => {{
            if (keyState.hasOwnProperty(e.code)) keyState[e.code] = false;
        }});

        // Update throttle variable globally for debug button
        function updateThrottle() {{
            window.throttle = throttle;
            requestAnimationFrame(updateThrottle);
        }}
        updateThrottle();

        // Chase camera (behind the plane)
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
                // Direct rotation (debug mode)
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
        console.log('Flight simulator ready – use arrow keys, Q/E throttle, R reset, P physics');
    </script>
</body>
</html>"""
    return html

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='models/scene.gltf')
    parser.add_argument('-o', '--output', default='airport_final.html')
    args = parser.parse_args()
    Path(args.output).write_text(generate_html(args.model), encoding='utf-8')
    print(f"✅ Generated: {args.output}")
    print("\n➡️ Run: python -m http.server 8000")
    print("   Then open http://localhost:8000/airport_final.html")
    print("\n   The airplane will be level over a runway texture.")
    print("   Controls: arrow keys, Q/E throttle, R reset, P physics.")
    print("\n   Click the 'Save Debug Logs' button to download a .txt file with all console messages,")
    print("   airplane state, and a screenshot. Upload that file for analysis.")

if __name__ == '__main__':
    main()