#!/usr/bin/env python3
"""
Generate a simple 3D flying game with CFD airflow visualisation and spinning rotors.
Requires the DC-3 model (scene.gltf + scene.bin) in the 'models' folder.
"""

import argparse
from pathlib import Path

def generate_game_html(model_path='models/scene.gltf'):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Mr. Douglas Flight Simulator | CFD Airflow</title>
    <style>
        body {{ margin: 0; overflow: hidden; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        #info {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 8px 15px;
            border-radius: 8px;
            backdrop-filter: blur(5px);
            pointer-events: none;
            z-index: 10;
            font-size: 14px;
        }}
        #controls {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(0,0,0,0.6);
            color: #ccc;
            padding: 8px 12px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 12px;
            pointer-events: none;
            z-index: 10;
        }}
        .stats {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.6);
            color: #0f0;
            padding: 8px 12px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 12px;
            pointer-events: none;
            z-index: 10;
            text-align: right;
        }}
    </style>
</head>
<body>
    <div id="info">
        <strong>✈️ Mr. Douglas – CFD Flight Simulator</strong><br>
        Drag mouse to look around • Keyboard: WASD / Arrows (pitch/roll) • Q/E throttle • R reset
    </div>
    <div id="controls">
        🎮 Controls:<br>
        ↑↓ : Pitch (nose up/down)<br>
        ←→ : Roll<br>
        Q/E : Throttle up/down<br>
        R   : Reset position<br>
        🧭 Airflow particles show CFD streamlines
    </div>
    <div class="stats" id="stats">
        Speed: 0 m/s<br>
        Throttle: 0%<br>
        Altitude: 0 m
    </div>

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
        import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
        import {{ GLTFLoader }} from 'three/addons/loaders/GLTFLoader.js';

        // --- Setup scene ---
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x071a3b);
        scene.fog = new THREE.FogExp2(0x071a3b, 0.002);

        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(0, 2, 5);

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        document.body.appendChild(renderer.domElement);

        // --- Simple controls for flying (no OrbitControls – we'll follow plane) ---
        // We'll implement a chase camera that follows the plane with offset.

        // --- Lighting ---
        const ambientLight = new THREE.AmbientLight(0x404060);
        scene.add(ambientLight);
        const mainLight = new THREE.DirectionalLight(0xffffff, 1.2);
        mainLight.position.set(5, 10, 7);
        mainLight.castShadow = true;
        scene.add(mainLight);
        const fillLight = new THREE.DirectionalLight(0x88aaff, 0.5);
        fillLight.position.set(-3, 1, -4);
        scene.add(fillLight);

        // --- Ground grid ---
        const gridHelper = new THREE.GridHelper(200, 40, 0x88aaff, 0x335588);
        gridHelper.position.y = -2;
        scene.add(gridHelper);

        // --- Simple terrain? just a large plane with grass texture? optional, but not needed.

        // --- Load aircraft model ---
        let airplane = null;
        let propellers = []; // store propeller meshes for rotation
        const loader = new GLTFLoader();
        loader.load('{model_path}',
            (gltf) => {{
                airplane = gltf.scene;
                airplane.traverse((child) => {{
                    if (child.isMesh) {{
                        child.castShadow = true;
                        child.receiveShadow = true;
                        // Find propeller parts by name (common names: "propeller", "prop", "blade")
                        if (child.name.toLowerCase().includes('prop')) {{
                            propellers.push(child);
                        }}
                    }}
                }});
                airplane.scale.set(0.5, 0.5, 0.5);
                scene.add(airplane);
                console.log('✅ Aircraft loaded');
            }},
            undefined,
            (error) => console.error('Model load error:', error)
        );

        // --- Physics variables ---
        let velocity = new THREE.Vector3(0, 0, 0);
        let position = new THREE.Vector3(0, 0, 0);
        let rotation = new THREE.Euler(0, 0, 0, 'YXZ');
        let throttle = 0;
        const maxThrottle = 1.0;
        const drag = 0.98;
        const liftFactor = 0.05;
        const controlSensitivity = 0.02;

        // Keyboard state
        const keyState = {{
            ArrowUp: false, ArrowDown: false,
            ArrowLeft: false, ArrowRight: false,
            KeyW: false, KeyS: false,
            KeyA: false, KeyD: false,
            KeyQ: false, KeyE: false,
            KeyR: false
        }};

        window.addEventListener('keydown', (e) => {{
            const code = e.code;
            if (keyState.hasOwnProperty(code)) keyState[code] = true;
            if (code === 'KeyR') {{
                // Reset position and velocity
                position.set(0, 1, 0);
                velocity.set(0, 0, 0);
                throttle = 0;
                rotation.set(0, 0, 0);
            }}
        }});
        window.addEventListener('keyup', (e) => {{
            const code = e.code;
            if (keyState.hasOwnProperty(code)) keyState[code] = false;
        }});

        // --- Particle system for CFD airflow (streamlines) ---
        const particleCount = 800;
        const particlesGeometry = new THREE.BufferGeometry();
        const particlePositions = new Float32Array(particleCount * 3);
        const particleVelocities = [];
        // Initialize particles in a box around origin
        for (let i = 0; i < particleCount; i++) {{
            particlePositions[i*3] = (Math.random() - 0.5) * 60;
            particlePositions[i*3+1] = (Math.random() - 0.5) * 15 + 1;
            particlePositions[i*3+2] = (Math.random() - 0.5) * 60;
            particleVelocities.push(new THREE.Vector3(
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 1,
                (Math.random() - 0.5) * 2
            ));
        }}
        particlesGeometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
        const particleMaterial = new THREE.PointsMaterial({{ color: 0x88aaff, size: 0.1, transparent: true, opacity: 0.6 }});
        const particleSystem = new THREE.Points(particlesGeometry, particleMaterial);
        scene.add(particleSystem);

        // Helper: update particle positions based on wind field around airplane
        function updateParticles(deltaTime, planePos, planeVel) {{
            const positions = particlesGeometry.attributes.position.array;
            const speed = planeVel.length();
            const windStrength = Math.min(2.0, speed * 0.5);
            for (let i = 0; i < particleCount; i++) {{
                let x = positions[i*3];
                let y = positions[i*3+1];
                let z = positions[i*3+2];
                // Simple flow field: particles flow opposite to plane's velocity, plus turbulence
                let vx = -planeVel.x * 0.5 + (Math.random() - 0.5) * windStrength;
                let vz = -planeVel.z * 0.5 + (Math.random() - 0.5) * windStrength;
                let vy = -planeVel.y * 0.3 + (Math.random() - 0.5) * windStrength * 0.5;
                // Also add upward lift near wings
                const dy = y - planePos.y;
                if (Math.abs(dy) < 1.5 && Math.abs(x - planePos.x) < 3 && Math.abs(z - planePos.z) < 5) {{
                    vy += 0.5 * (1 - Math.abs(dy)/1.5) * speed;
                }}
                x += vx * deltaTime;
                y += vy * deltaTime;
                z += vz * deltaTime;
                // Reset if outside bounds
                if (Math.abs(x) > 50 || Math.abs(y) > 20 || Math.abs(z) > 50) {{
                    x = (Math.random() - 0.5) * 60;
                    y = (Math.random() - 0.5) * 15 + 1;
                    z = (Math.random() - 0.5) * 60;
                }}
                positions[i*3] = x;
                positions[i*3+1] = y;
                positions[i*3+2] = z;
            }}
            particlesGeometry.attributes.position.needsUpdate = true;
        }}

        // --- Chase camera (third person) ---
        let cameraOffset = new THREE.Vector3(-3, 1.5, 5); // behind and above

        // --- Main animation loop ---
        let lastTime = performance.now();
        let propAngle = 0;

        function animate() {{
            const now = performance.now();
            let dt = Math.min(0.033, (now - lastTime) / 1000);
            lastTime = now;
            if (dt < 0.01) dt = 0.016;

            // --- Throttle control ---
            if (keyState.KeyQ || keyState.KeyQ) throttle -= 0.5 * dt;
            if (keyState.KeyE || keyState.KeyE) throttle += 0.5 * dt;
            throttle = Math.max(0, Math.min(maxThrottle, throttle));
            const thrust = throttle * 15.0; // m/s^2

            // --- Pitch (up/down) using ArrowUp/ArrowDown or W/S ---
            let pitchInput = 0;
            if (keyState.ArrowUp || keyState.KeyW) pitchInput = 1;
            if (keyState.ArrowDown || keyState.KeyS) pitchInput = -1;
            // --- Roll using ArrowLeft/ArrowRight or A/D ---
            let rollInput = 0;
            if (keyState.ArrowLeft || keyState.KeyA) rollInput = -1;
            if (keyState.ArrowRight || keyState.KeyD) rollInput = 1;

            // Apply controls (angular acceleration)
            const pitchRate = pitchInput * controlSensitivity * throttle;
            const rollRate = rollInput * controlSensitivity * throttle;
            rotation.x += pitchRate * dt;
            rotation.z += rollRate * dt;
            // Limit pitch and roll
            rotation.x = Math.max(-Math.PI/3, Math.min(Math.PI/3, rotation.x));
            rotation.z = Math.max(-Math.PI/3, Math.min(Math.PI/3, rotation.z));

            // --- Compute acceleration in local frame, then rotate to world ---
            // Acceleration: thrust forward, gravity, lift, drag
            const localAcc = new THREE.Vector3(0, 0, -thrust); // forward is -Z in glTF?
            // Convert local acceleration to world using airplane's rotation
            const quat = new THREE.Quaternion().setFromEuler(rotation);
            const worldAcc = localAcc.clone().applyQuaternion(quat);
            // Add gravity
            worldAcc.y -= 9.8 * dt;
            // Add lift proportional to speed squared and angle of attack (simplified)
            const speed = velocity.length();
            const lift = speed * speed * liftFactor * (pitchInput * 0.5 + 0.2);
            worldAcc.y += lift;
            // Update velocity
            velocity.x += worldAcc.x * dt;
            velocity.y += worldAcc.y * dt;
            velocity.z += worldAcc.z * dt;
            // Drag
            velocity.multiplyScalar(1 - drag * dt);
            // Update position
            position.x += velocity.x * dt;
            position.y += velocity.y * dt;
            position.z += velocity.z * dt;
            // Keep above ground
            if (position.y < -1.5) {{
                position.y = -1.5;
                if (velocity.y < 0) velocity.y = 0;
            }}

            // --- Update airplane object position and rotation ---
            if (airplane) {{
                airplane.position.copy(position);
                airplane.rotation.set(rotation.x, rotation.y, rotation.z);
                // Spin propellers
                propAngle += throttle * 20 * dt;
                for (let prop of propellers) {{
                    prop.rotation.x = propAngle;
                }}
            }}

            // --- Update chase camera ---
            // Simple follow: camera relative to plane's orientation
            const cameraWorldPos = position.clone().add(cameraOffset.clone().applyQuaternion(quat));
            camera.position.lerp(cameraWorldPos, 0.1);
            camera.lookAt(position);

            // --- Update CFD particle system ---
            updateParticles(dt, position, velocity);

            // --- Update stats UI ---
            document.getElementById('stats').innerHTML = `
                Speed: ${{speed.toFixed(1)}} m/s<br>
                Throttle: ${{(throttle*100).toFixed(0)}}%<br>
                Altitude: ${{position.y.toFixed(1)}} m
            `;

            renderer.render(scene, camera);
            requestAnimationFrame(animate);
        }}

        // Wait a bit for model to load, but start animation anyway
        setTimeout(() => {{
            animate();
        }}, 100);
    </script>
</body>
</html>"""
    return html

def main():
    parser = argparse.ArgumentParser(description='Generate CFD flying game with DC-3 model')
    parser.add_argument('--model', default='models/scene.gltf', help='Path to glTF model relative to current folder')
    parser.add_argument('-o', '--output', default='flying_game.html', help='Output HTML file')
    args = parser.parse_args()

    # Ensure the model path is correct
    model_path = args.model
    output_path = Path(args.output)

    html = generate_game_html(model_path)
    output_path.write_text(html, encoding='utf-8')
    print(f"✅ Flying game generated: {output_path.resolve()}")
    print("\n➡️ To play, serve the folder with:")
    print("   python -m http.server 8000")
    print("   Then open http://localhost:8000/flying_game.html")
    print("\n🎮 Controls: Arrow keys/WASD for pitch/roll, Q/E throttle, R reset.")
    print("🌀 Rotors spin, particle trails show CFD airflow.\n")

if __name__ == '__main__':
    main()