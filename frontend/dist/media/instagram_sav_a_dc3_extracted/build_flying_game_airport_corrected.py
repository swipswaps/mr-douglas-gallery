#!/usr/bin/env python3
"""
Flight simulator – fixed terrain visibility and plane orientation.
"""

import argparse
from pathlib import Path

def generate_html(model_path='models/scene.gltf', terrain_path='skydive_deland.stl'):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mr. Douglas – DeLand Airport (Corrected)</title>
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
        .debug-panel {{
            position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.7);
            color: #0f0; padding: 8px; border-radius: 8px; font-family: monospace;
            font-size: 11px; pointer-events: none; z-index: 10;
        }}
    </style>
</head>
<body>
    <div id="info">
        <strong>✈️ Mr. Douglas – DeLand Airport (Corrected)</strong><br>
        ↑↓ pitch | ←→ roll | Q/E throttle | R reset | P toggle physics
    </div>
    <div class="controls">🖱️ Right‑click for browser menu • Camera follows plane</div>
    <div id="debug" class="debug-panel">Debug: waiting...</div>

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

        // Diagnostic panel
        const debugDiv = document.getElementById('debug');
        function debugLog(msg) {{
            debugDiv.innerHTML = msg + '<br>' + debugDiv.innerHTML;
            console.log(msg);
        }}

        // --- Setup scene ---
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x87CEEB);
        scene.fog = new THREE.Fog(0x87CEEB, 500, 1500);

        const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
        const renderer = new THREE.WebGLRenderer({{ antialias: true, preserveDrawingBuffer: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        document.body.appendChild(renderer.domElement);
        renderer.domElement.addEventListener('contextmenu', (e) => {{}});

        // --- Lighting (stronger ambient and fill) ---
        const ambientLight = new THREE.AmbientLight(0x606070);
        scene.add(ambientLight);
        const sunLight = new THREE.DirectionalLight(0xfff5d1, 1.5);
        sunLight.position.set(100, 200, 50);
        sunLight.castShadow = true;
        sunLight.shadow.mapSize.width = 1024;
        sunLight.shadow.mapSize.height = 1024;
        scene.add(sunLight);
        const fillLight = new THREE.DirectionalLight(0x88aaff, 0.8);
        fillLight.position.set(-50, 20, -50);
        scene.add(fillLight);
        const backLight = new THREE.PointLight(0xffaa66, 0.4);
        backLight.position.set(0, 5, -10);
        scene.add(backLight);

        // --- Fallback ground (a large green plane) ---
        const groundPlane = new THREE.Mesh(
            new THREE.PlaneGeometry(500, 500),
            new THREE.MeshStandardMaterial({{ color: 0x3c9e3c, roughness: 0.8, metalness: 0.1, side: THREE.DoubleSide }})
        );
        groundPlane.rotation.x = -Math.PI / 2;
        groundPlane.position.y = -2;
        groundPlane.receiveShadow = true;
        scene.add(groundPlane);
        debugLog('Ground plane added at y=-2');

        // --- Grid helper (visual reference) ---
        const gridHelper = new THREE.GridHelper(1000, 50, 0x88aaff, 0x335588);
        gridHelper.position.y = -1.8;
        scene.add(gridHelper);

        // --- Load terrain STL (visible on top of ground) ---
        const stlLoader = new STLLoader();
        stlLoader.load('{terrain_path}', (geometry) => {{
            geometry.computeBoundingBox();
            const box = geometry.boundingBox;
            const sizeX = box.max.x - box.min.x;
            const sizeZ = box.max.z - box.min.z;
            const scale = 80 / Math.max(sizeX, sizeZ);
            const material = new THREE.MeshStandardMaterial({{ color: 0x8B5A2B, roughness: 0.6, metalness: 0.05 }});
            const terrain = new THREE.Mesh(geometry, material);
            terrain.scale.set(scale, scale, scale);
            // Position terrain so its lowest point is at y = -2 (top of ground plane)
            const minY = box.min.y * scale;
            terrain.position.set(0, -2 - minY, 0);
            terrain.castShadow = true;
            terrain.receiveShadow = true;
            scene.add(terrain);
            debugLog(`Terrain loaded: scale=${{scale.toFixed(3)}}, y-offset=${{terrain.position.y.toFixed(2)}}`);
        }}, undefined, (err) => debugLog(`TERRAIN ERROR: ${{err.message}}`));

        // --- Load aircraft model ---
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
                // CORRECT ORIENTATION: try different rotations
                // Many glTF models have Y up and -Z forward. This one may be vertical.
                // We'll apply a combination to level it. If still wrong, adjust in console.
                airplane.rotation.x = -Math.PI / 2;   // bring nose down
                airplane.rotation.z = 0;              // no roll
                // Alternative: uncomment next line instead and comment above two
                // airplane.rotation.z = -Math.PI / 2;
                airplane.scale.set(0.5, 0.5, 0.5);
                scene.add(airplane);
                debugLog('Aircraft loaded. If still vertical, open console and type: airplane.rotation.x = 0; airplane.rotation.z = -Math.PI/2');
                // Expose airplane globally for manual adjustment
                window.airplane = airplane;
            }},
            undefined,
            (err) => debugLog(`MODEL ERROR: ${{err.message}}`)
        );

        // --- Physics state (same as before, unchanged) ---
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
                debugLog('Reset position');
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

        setTimeout(() => animate(), 100);
        debugLog('Animation started');
    </script>
</body>
</html>"""
    return html

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='models/scene.gltf')
    parser.add_argument('--terrain', default='skydive_deland.stl')
    parser.add_argument('-o', '--output', default='flying_game_airport_corrected.html')
    args = parser.parse_args()
    Path(args.output).write_text(generate_html(args.model, args.terrain), encoding='utf-8')
    print(f"✅ Generated: {args.output}")

if __name__ == '__main__':
    main()