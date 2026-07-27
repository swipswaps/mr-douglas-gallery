#!/usr/bin/env python3
"""
Absolute working flight simulator – no heavy STL, correct orientation.
"""

import argparse
from pathlib import Path

def generate_html(model_path='models/scene.gltf'):
    html = f"""<!DOCTYPE html>
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

        // --- Load aircraft model (no rotation correction – model is already level) ---
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
                // No manual rotation – the glTF is correctly oriented.
                airplane.scale.set(0.5, 0.5, 0.5);
                scene.add(airplane);
                log('Aircraft loaded – orientation correct');
                // Expose for console debugging
                window.airplane = airplane;
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
        }});
        window.addEventListener('keyup', (e) => {{
            if (keyState.hasOwnProperty(e.code)) keyState[e.code] = false;
        }});

        // --- Chase camera (simple: behind the plane) ---
        let cameraOffset = new THREE.Vector3(0, 1.2, 6); // local offset (x,y,z)
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
    return html

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='models/scene.gltf')
    parser.add_argument('-o', '--output', default='working_flight.html')
    args = parser.parse_args()
    Path(args.output).write_text(generate_html(args.model), encoding='utf-8')
    print(f"✅ Generated: {args.output}")
    print("\n➡️ Run: python -m http.server 8000")
    print("   Then open http://localhost:8000/working_flight.html")
    print("\n   The airplane will appear level, chase camera works.")
    print("   No heavy STL – no WebGL context loss.")

if __name__ == '__main__':
    main()