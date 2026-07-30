#!/usr/bin/env python3
"""
Generate flight simulator HTML with built‑in test bridge and debug panel.
Uses models/scene.gltf by default.
"""

import argparse
from pathlib import Path

def generate_game_html(model_path='models/scene.gltf'):
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Mr. Douglas Flight Simulator | Debug + Bridge</title>
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
        .debug {{
            position: absolute;
            bottom: 80px;
            left: 20px;
            background: rgba(0,0,0,0.7);
            color: #ffaa66;
            padding: 8px 12px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 11px;
            pointer-events: none;
            z-index: 10;
            text-align: left;
            max-width: 350px;
        }}
    </style>
</head>
<body>
    <div id="info">
        <strong>✈️ Mr. Douglas – Debug Flight Simulator</strong><br>
        Keyboard: WASD / Arrows (pitch/roll) • Q/E throttle • R reset • P toggle physics
    </div>
    <div class="stats" id="stats">Speed: 0 m/s<br>Throttle: 0%<br>Altitude: 0 m</div>
    <div class="debug" id="debug-panel">Debug: waiting for input...</div>

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

        console.log("Game script started");

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x071a3b);
        scene.fog = new THREE.FogExp2(0x071a3b, 0.002);

        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(0, 2, 5);

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        document.body.appendChild(renderer.domElement);

        const ambientLight = new THREE.AmbientLight(0x404060);
        scene.add(ambientLight);
        const mainLight = new THREE.DirectionalLight(0xffffff, 1.2);
        mainLight.position.set(5, 10, 7);
        mainLight.castShadow = true;
        scene.add(mainLight);
        const fillLight = new THREE.DirectionalLight(0x88aaff, 0.5);
        fillLight.position.set(-3, 1, -4);
        scene.add(fillLight);

        const gridHelper = new THREE.GridHelper(200, 40, 0x88aaff, 0x335588);
        gridHelper.position.y = -2;
        scene.add(gridHelper);

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
                console.log('Aircraft model loaded');
            }},
            undefined,
            (error) => console.error('Model load error:', error)
        );

        let velocity = new THREE.Vector3(0, 0, 0);
        let position = new THREE.Vector3(0, 0, 0);
        let rotation = new THREE.Euler(0, 0, 0, 'YXZ');
        let throttle = 0;
        let propAngle = 0;
        const maxThrottle = 1.0;
        const drag = 0.98;
        const liftFactor = 0.05;
        const controlSensitivity = 0.02;

        const keyState = {{
            ArrowUp: false, ArrowDown: false,
            ArrowLeft: false, ArrowRight: false,
            KeyW: false, KeyS: false,
            KeyA: false, KeyD: false,
            KeyQ: false, KeyE: false,
            KeyR: false, KeyP: false
        }};

        function updateDebugPanel() {{
            const panel = document.getElementById('debug-panel');
            panel.innerHTML = `
                Physics: ${{physicsEnabled ? 'ON' : 'OFF'}}<br>
                Pitch input: ${{keyState.ArrowUp || keyState.KeyW ? '↑' : ''}}${{keyState.ArrowDown || keyState.KeyS ? '↓' : ''}}<br>
                Roll input:  ${{keyState.ArrowLeft || keyState.KeyA ? '←' : ''}}${{keyState.ArrowRight || keyState.KeyD ? '→' : ''}}<br>
                Throttle: ${{throttle.toFixed(2)}}<br>
                Rotation (pitch, yaw, roll): ${{rotation.x.toFixed(2)}}, ${{rotation.y.toFixed(2)}}, ${{rotation.z.toFixed(2)}}
            `;
        }}

        window.addEventListener('keydown', (e) => {{
            const code = e.code;
            if (keyState.hasOwnProperty(code)) keyState[code] = true;
            if (code === 'KeyR') {{
                position.set(0, 1, 0);
                velocity.set(0, 0, 0);
                throttle = 0;
                rotation.set(0, 0, 0);
            }}
            if (code === 'KeyP') physicsEnabled = !physicsEnabled;
            updateDebugPanel();
        }});
        window.addEventListener('keyup', (e) => {{
            if (keyState.hasOwnProperty(e.code)) keyState[e.code] = false;
            updateDebugPanel();
        }});

        // Particle system (cosmetic)
        const particleCount = 800;
        const particlesGeometry = new THREE.BufferGeometry();
        const particlePositions = new Float32Array(particleCount * 3);
        for (let i = 0; i < particleCount; i++) {{
            particlePositions[i*3] = (Math.random() - 0.5) * 60;
            particlePositions[i*3+1] = (Math.random() - 0.5) * 15 + 1;
            particlePositions[i*3+2] = (Math.random() - 0.5) * 60;
        }}
        particlesGeometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
        const particleMaterial = new THREE.PointsMaterial({{ color: 0x88aaff, size: 0.1, transparent: true, opacity: 0.6 }});
        const particleSystem = new THREE.Points(particlesGeometry, particleMaterial);
        scene.add(particleSystem);

        function updateParticles(deltaTime, planePos, planeVel) {{
            const positions = particlesGeometry.attributes.position.array;
            const speed = planeVel.length();
            const windStrength = Math.min(2.0, speed * 0.5);
            for (let i = 0; i < particleCount; i++) {{
                let x = positions[i*3];
                let y = positions[i*3+1];
                let z = positions[i*3+2];
                let vx = -planeVel.x * 0.5 + (Math.random() - 0.5) * windStrength;
                let vz = -planeVel.z * 0.5 + (Math.random() - 0.5) * windStrength;
                let vy = -planeVel.y * 0.3 + (Math.random() - 0.5) * windStrength * 0.5;
                const dy = y - planePos.y;
                if (Math.abs(dy) < 1.5 && Math.abs(x - planePos.x) < 3 && Math.abs(z - planePos.z) < 5) {{
                    vy += 0.5 * (1 - Math.abs(dy)/1.5) * speed;
                }}
                x += vx * deltaTime;
                y += vy * deltaTime;
                z += vz * deltaTime;
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

        let cameraOffset = new THREE.Vector3(-3, 1.5, 5);
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
                if (position.y < -1.5) {{
                    position.y = -1.5;
                    if (velocity.y < 0) velocity.y = 0;
                }}
            }} else {{
                const rotSpeed = 0.05;
                if (pitchInput !== 0) rotation.x += pitchInput * rotSpeed;
                if (rollInput !== 0) rotation.z += rollInput * rotSpeed;
                rotation.x = Math.max(-Math.PI/2, Math.min(Math.PI/2, rotation.x));
                rotation.z = Math.max(-Math.PI/2, Math.min(Math.PI/2, rotation.z));
                const speed = throttle * 10;
                if (airplane) {{
                    const forward = new THREE.Vector3(0,0,-1).applyQuaternion(airplane.quaternion);
                    position.x += forward.x * speed * dt;
                    position.y += forward.y * speed * dt;
                    position.z += forward.z * speed * dt;
                }}
                if (position.y < -1.5) position.y = -1.5;
                velocity.set(0,0,0);
            }}

            if (airplane) {{
                airplane.position.copy(position);
                airplane.rotation.set(rotation.x, rotation.y, rotation.z);
                propAngle += throttle * 20 * dt;
                for (let prop of propellers) prop.rotation.x = propAngle;
            }}

            const quat = new THREE.Quaternion().setFromEuler(rotation);
            const cameraWorldPos = position.clone().add(cameraOffset.clone().applyQuaternion(quat));
            camera.position.lerp(cameraWorldPos, 0.1);
            camera.lookAt(position);

            updateParticles(dt, position, velocity);
            const speed = velocity.length();
            document.getElementById('stats').innerHTML = `
                Speed: ${{speed.toFixed(1)}} m/s<br>
                Throttle: ${{(throttle*100).toFixed(0)}}%<br>
                Altitude: ${{position.y.toFixed(1)}} m
            `;
            updateDebugPanel();

            renderer.render(scene, camera);
            requestAnimationFrame(animate);
        }}

        setTimeout(() => animate(), 100);
        console.log("Animation started");
    </script>
    <!-- Bridge pattern (optional) -->
    <script>
        (function() {{
            if (!window.location.search.includes('test')) return;
            window.testBridge = {{
                getAirplaneRotation: () => {{
                    if (typeof rotation !== 'undefined') return {{ x: rotation.x, y: rotation.y, z: rotation.z }};
                    return null;
                }},
                getThrottle: () => (typeof throttle !== 'undefined') ? throttle : null,
                getPosition: () => (typeof position !== 'undefined') ? {{ x: position.x, y: position.y, z: position.z }} : null,
                getPhysicsEnabled: () => (typeof physicsEnabled !== 'undefined') ? physicsEnabled : null
            }};
            console.log('Test bridge enabled');
        }})();
    </script>
</body>
</html>"""
    return html_template.format(model_path=model_path)

def main():
    parser = argparse.ArgumentParser(description='Generate debug flight sim HTML')
    parser.add_argument('--model', default='models/scene.gltf', help='Path to glTF model')
    parser.add_argument('-o', '--output', default='flying_game_debug.html', help='Output HTML')
    args = parser.parse_args()
    output_path = Path(args.output)
    html = generate_game_html(args.model)
    output_path.write_text(html, encoding='utf-8')
    print(f"✅ Generated: {output_path.resolve()}")

if __name__ == '__main__':
    main()