document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const canvasContainer = document.getElementById('canvas-container');
    const labelsContainer = document.getElementById('plane-labels-container');
    const header = document.querySelector('.header');
    const menuToggle = document.querySelector('.menu-toggle');
    const nav = document.querySelector('.nav');

    // Mobile Navigation Toggle
    if (menuToggle && nav) {
        menuToggle.addEventListener('click', () => {
            nav.classList.toggle('active');
            const icon = menuToggle.querySelector('i');
            if (nav.classList.contains('active')) {
                icon.className = 'fa-solid fa-xmark';
            } else {
                icon.className = 'fa-solid fa-bars';
            }
        });
        
        nav.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                nav.classList.remove('active');
                const icon = menuToggle.querySelector('i');
                if (icon) icon.className = 'fa-solid fa-bars';
            });
        });
    }

    // Header background transition on scroll
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.style.boxShadow = '0 4px 20px rgba(0, 31, 63, 0.08)';
        } else {
            header.style.boxShadow = 'none';
        }
    });

    // FAQ Accordion Toggle
    const faqItems = document.querySelectorAll('.accordion-item');
    faqItems.forEach(item => {
        const headerBtn = item.querySelector('.accordion-header');
        const body = item.querySelector('.accordion-body');
        
        headerBtn.addEventListener('click', () => {
            const isActive = item.classList.contains('active');
            
            // Close all items
            faqItems.forEach(el => {
                el.classList.remove('active');
                el.querySelector('.accordion-body').style.maxHeight = null;
            });
            
            // Toggle clicked item
            if (!isActive) {
                item.classList.add('active');
                body.style.maxHeight = body.scrollHeight + 'px';
            }
        });
    });

    // Count Up Metrics Animation
    const counters = document.querySelectorAll('.counter, .counter-rate');
    const animateCounters = () => {
        counters.forEach(counter => {
            const target = +counter.getAttribute('data-target');
            const isRate = counter.classList.contains('counter-rate');
            const suffix = isRate ? '%' : '+';
            
            let count = 0;
            const speed = target / 60; // complete in ~60 frames
            
            const updateCount = () => {
                count += speed;
                if (count < target) {
                    counter.innerText = Math.floor(count) + suffix;
                    requestAnimationFrame(updateCount);
                } else {
                    counter.innerText = target + suffix;
                }
            };
            updateCount();
        });
    };
    
    // Trigger counters on load (Hero section is visible immediately)
    animateCounters();

    /* ==========================================================================
       THREE.JS 3D PLANES SYSTEM
       ========================================================================== */
    let scene, camera, renderer;
    let planeObjects = [];
    const colorHexes = [0x00BCD4, 0x0084FF, 0xFFD700, 0x2C3E50, 0x001F3F];
    
    // Responsive plane configurations
    const isMobile = window.innerWidth < 768;
    const isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;
    const visiblePlanesCount = isMobile ? 3 : (isTablet ? 5 : 7);

    // Initial values for mouse parallax & scroll physics
    let mouseX = 0, mouseY = 0;
    let targetX = 0, targetY = 0;
    let scrollYOffset = 0;
    let scrollSpeedFactor = 1.0;
    let scrollTimeout;

    // Set up Three.js Scene
    function initThree() {
        const width = canvasContainer.clientWidth;
        const height = canvasContainer.clientHeight;

        scene = new THREE.Scene();
        scene.background = new THREE.Color(0xFFFFFF); // Solid white background

        // Camera setup
        camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
        camera.position.set(0, 0, 32);

        // Renderer setup with shadow support
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        canvasContainer.appendChild(renderer.domElement);

        // Lighting: Clean studio lights
        const ambientLight = new THREE.AmbientLight(0xFFFFFF, 0.85);
        scene.add(ambientLight);

        const dirLight = new THREE.DirectionalLight(0xFFFFFF, 0.65);
        dirLight.position.set(10, 20, 15);
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = 1024;
        dirLight.shadow.mapSize.height = 1024;
        scene.add(dirLight);

        // Floor to receive shadows (gives subtle depth cues to the airplanes)
        const floorGeo = new THREE.PlaneGeometry(100, 100);
        const floorMat = new THREE.ShadowMaterial({ opacity: 0.05 });
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -12;
        floor.receiveShadow = true;
        scene.add(floor);
    }

    // Programmatic low-poly plane mesh creator (no external files needed)
    function createPlaneMesh(color) {
        const planeGroup = new THREE.Group();

        // Material with flat shading for low-poly look
        const bodyMat = new THREE.MeshPhongMaterial({
            color: color,
            flatShading: true,
            shininess: 30
        });
        const metalMat = new THREE.MeshPhongMaterial({
            color: 0xD1D5DB,
            flatShading: true,
            shininess: 70
        });

        // 1. Fuselage (horizontal cylinder)
        const fuseGeo = new THREE.CylinderGeometry(0.4, 0.15, 3.5, 6);
        fuseGeo.rotateX(Math.PI / 2);
        const fuselage = new THREE.Mesh(fuseGeo, bodyMat);
        fuselage.castShadow = true;
        planeGroup.add(fuselage);

        // 2. Main Wings (horizontal thin box)
        const wingGeo = new THREE.BoxGeometry(4.8, 0.06, 0.7);
        const wings = new THREE.Mesh(wingGeo, bodyMat);
        wings.position.set(0, 0.1, 0.3);
        wings.castShadow = true;
        planeGroup.add(wings);

        // 3. Tail Wings (stabilizers)
        const tailHorizGeo = new THREE.BoxGeometry(1.5, 0.04, 0.4);
        const tailHoriz = new THREE.Mesh(tailHorizGeo, bodyMat);
        tailHoriz.position.set(0, 0.1, -1.3);
        tailHoriz.castShadow = true;
        planeGroup.add(tailHoriz);

        const tailVertGeo = new THREE.BoxGeometry(0.04, 0.6, 0.4);
        tailVertGeo.translate(0, 0.3, 0);
        const tailVert = new THREE.Mesh(tailVertGeo, bodyMat);
        tailVert.position.set(0, 0, -1.3);
        tailVert.castShadow = true;
        planeGroup.add(tailVert);

        // 4. Cockpit (glass dome)
        const canopyGeo = new THREE.SphereGeometry(0.3, 8, 8);
        canopyGeo.scale(1, 1, 2.2);
        const canopy = new THREE.Mesh(canopyGeo, metalMat);
        canopy.position.set(0, 0.4, 0.6);
        planeGroup.add(canopy);

        // 5. Propeller Spinner
        const spinGeo = new THREE.ConeGeometry(0.25, 0.5, 6);
        spinGeo.rotateX(Math.PI / 2);
        const spinner = new THREE.Mesh(spinGeo, metalMat);
        spinner.position.set(0, 0, 1.8);
        planeGroup.add(spinner);

        // Propeller Blades (animated rotater)
        const bladeGeo = new THREE.BoxGeometry(1.6, 0.15, 0.02);
        const propeller = new THREE.Mesh(bladeGeo, metalMat);
        propeller.position.set(0, 0, 2.0);
        planeGroup.add(propeller);

        // Store reference to blade for rotation in frame loop
        planeGroup.userData = { propeller: propeller };

        scene.add(planeGroup);
        return planeGroup;
    }

    // Dynamic metrics text loader
    let metricsData = {
        placements: ["AI/ML Specialist", "Data Analytics", "Cloud Architect", "Package: 53 LPA", "Admissions Open"],
        details: ["Placement 95%", "Estd 2009", "JNTUH 7Z", "50+ Partners", "SOE Program"]
    };

    // Spawn flight system
    function spawnPlanes() {
        // Paths: diagonal, curved orbits, circular sweeps
        const pathData = [
            { type: 'diagonal', speed: 0.05, altitude: 4, label: "AI/ML Track", dotClass: "cyan-dot" },
            { type: 'circular', speed: 0.03, altitude: 0, label: "₹53 LPA Avg", dotClass: "gold-dot" },
            { type: 'curve', speed: 0.045, altitude: -4, label: "95% Placements", dotClass: "blue-dot" },
            { type: 'diagonal', speed: 0.035, altitude: 8, label: "Apply Now", dotClass: "cyan-dot" },
            { type: 'circular', speed: 0.025, altitude: -8, label: "50+ Partners", dotClass: "gold-dot" },
            { type: 'curve', speed: 0.052, altitude: 2, label: "JNTUH Approved", dotClass: "blue-dot" },
            { type: 'diagonal', speed: 0.04, altitude: -2, label: "Estd 2009", dotClass: "cyan-dot" }
        ];

        for (let i = 0; i < visiblePlanesCount; i++) {
            const data = pathData[i];
            const color = colorHexes[i % colorHexes.length];
            const mesh = createPlaneMesh(color);

            // Scale planes based on depth to create natural perspective
            const zDepth = data.altitude * 1.5; 
            const scale = 1.0 - (zDepth / 50); // smaller when further
            mesh.scale.set(scale, scale, scale);

            // HTML Overlay Badge setup
            const badge = document.createElement('div');
            badge.className = 'plane-badge';
            badge.innerHTML = `
                <span class="badge-dot ${data.dotClass}"></span>
                <span class="badge-text">${data.label}</span>
                <div class="plane-badge-popup">Double click to slow down</div>
            `;
            labelsContainer.appendChild(badge);

            // Handle interactive plane slowing down on hover/click
            let isSlowed = false;
            badge.addEventListener('mouseenter', () => { isSlowed = true; });
            badge.addEventListener('mouseleave', () => { isSlowed = false; });

            // Initialize plane properties
            planeObjects.push({
                mesh: mesh,
                badgeEl: badge,
                type: data.type,
                baseSpeed: data.speed,
                currentSpeed: data.speed,
                altitude: data.altitude,
                zDepth: zDepth,
                angle: i * (Math.PI * 2 / visiblePlanesCount), // disperse start positions
                progress: Math.random() * 100, // random start progress
                isSlowed: () => isSlowed,
                trailParticles: [], // store trail particle objects
            });
        }
    }

    // Particle Trail generator for planes
    function createTrailParticle(position, colorHex) {
        const geo = new THREE.SphereGeometry(0.12, 4, 4);
        const mat = new THREE.MeshBasicMaterial({
            color: colorHex,
            transparent: true,
            opacity: 0.45
        });
        const particle = new THREE.Mesh(geo, mat);
        particle.position.copy(position);
        scene.add(particle);
        return {
            mesh: particle,
            life: 1.0 // 100% life
        };
    }

    // Fetch live stats from API
    async function fetchLiveMetrics() {
        try {
            const res = await fetch('/api/metrics');
            if (res.ok) {
                const data = await res.json();
                
                // Distribute data to active plane badges
                const liveLabels = [
                    `Avg Package: ${data.avgPackage}`,
                    `Placements: ${data.placementRate}`,
                    `Enrolled: ${data.enrolled}`,
                    `Partners: ${data.partners}`,
                    `${data.admissionStatus.split('/')[0]} Open`,
                    `Microsoft Offer: 53 LPA`,
                    `NNRG Estd 2009`
                ];

                planeObjects.forEach((p, idx) => {
                    if (liveLabels[idx]) {
                        const textEl = p.badgeEl.querySelector('.badge-text');
                        if (textEl) textEl.innerText = liveLabels[idx];
                    }
                });
            }
        } catch (e) {
            console.warn("Failed fetching live metrics from server, using local defaults.", e);
        }
    }

    // Call API updates
    fetchLiveMetrics();
    setInterval(fetchLiveMetrics, 12000); // refresh every 12s

    // Project 3D vector coordinates into 2D DOM screen space
    const tempV = new THREE.Vector3();
    function updatePlaneBadges() {
        const widthHalf = canvasContainer.clientWidth / 2;
        const heightHalf = canvasContainer.clientHeight / 2;

        planeObjects.forEach(p => {
            // Get 3D coordinate
            p.mesh.getWorldPosition(tempV);
            
            // Project to camera viewport
            tempV.project(camera);

            // Translate into screen pixel coordinates
            const x = (tempV.x * widthHalf) + widthHalf;
            const y = -(tempV.y * heightHalf) + heightHalf;

            // Apply to overlay badge styling using GPU-accelerated translate3d
            // Hide if behind the camera
            if (tempV.z > 1) {
                p.badgeEl.style.opacity = 0;
                p.badgeEl.style.pointerEvents = 'none';
            } else {
                p.badgeEl.style.opacity = 1;
                p.badgeEl.style.pointerEvents = 'auto';
                p.badgeEl.style.transform = `translate3d(${x}px, ${y - 30}px, 0)`;
            }
        });
    }

    // Flight animation paths calculations
    function updateFlights() {
        const time = Date.now() * 0.001;

        planeObjects.forEach((p, idx) => {
            // Check if user is hovering to slow down
            const speedMultiplier = p.isSlowed() ? 0.15 : scrollSpeedFactor;
            p.currentSpeed += (p.baseSpeed * speedMultiplier - p.currentSpeed) * 0.1;
            
            p.progress += p.currentSpeed;
            p.angle += p.currentSpeed * 0.2;

            // 1. Calculate next positions based on parametric formulas
            let x = 0, y = 0, z = p.zDepth;
            let rotX = 0, rotY = 0, rotZ = 0;

            if (p.type === 'diagonal') {
                // Diagonal horizontal flight sweep
                x = ((p.progress * 4) % 40) - 20;
                y = p.altitude + Math.sin(p.progress * 0.5) * 1.5;
                
                // Rotate plane to align with flight angle
                rotY = Math.PI / 2;
                rotZ = Math.cos(p.progress * 0.5) * 0.15;
            } else if (p.type === 'circular') {
                // Orbital circular sweeps
                const radius = 12 + Math.cos(time * 0.3) * 2;
                x = Math.cos(p.angle) * radius;
                y = Math.sin(p.angle) * (radius * 0.4) + (p.altitude * 0.5);
                
                // Align plane tangent to circle path
                rotY = -p.angle + Math.PI;
                rotZ = -0.3; // wing bank angle in curve
            } else if (p.type === 'curve') {
                // Wave-like curving sweeps
                x = Math.sin(p.progress * 0.3) * 18;
                y = p.altitude + Math.cos(p.progress * 0.4) * 2.5;
                
                // Align rotation to slope direction
                const nextX = Math.sin((p.progress + 0.1) * 0.3) * 18;
                const nextY = p.altitude + Math.cos((p.progress + 0.1) * 0.4) * 2.5;
                rotY = Math.atan2(nextX - x, 0.1);
                rotX = Math.atan2(nextY - y, 0.1) * 0.5;
            }

            // Apply calculated coordinate position offsets
            // Parallax mouse sway adds dynamic depth translation
            p.mesh.position.set(x + (targetX * (idx + 1) * 0.3), y + (targetY * (idx + 1) * 0.3), z);
            p.mesh.rotation.set(rotX, rotY, rotZ);

            // Rotate propeller rapidly
            if (p.mesh.userData.propeller) {
                p.mesh.userData.propeller.rotation.z += 0.8;
            }

            // 2. Generate and update particle trails
            if (Math.random() < 0.25) {
                const trailColor = colorHexes[idx % colorHexes.length];
                // Spawn trail slightly behind the tail fin location
                const tailPos = new THREE.Vector3(0, 0, -1.8).applyMatrix4(p.mesh.matrixWorld);
                p.trailParticles.push(createTrailParticle(tailPos, trailColor));
            }

            // Update trails lifecycle
            for (let t = p.trailParticles.length - 1; t >= 0; t--) {
                const pt = p.trailParticles[t];
                pt.life -= 0.025; // decay life
                
                if (pt.life <= 0) {
                    scene.remove(pt.mesh);
                    pt.mesh.geometry.dispose();
                    pt.mesh.material.dispose();
                    p.trailParticles.splice(t, 1);
                } else {
                    pt.mesh.material.opacity = pt.life * 0.45;
                    pt.mesh.scale.set(pt.life, pt.life, pt.life);
                }
            }
        });
    }

    // Scroll parallax effect handler
    window.addEventListener('scroll', () => {
        scrollYOffset = window.scrollY;

        // Apply scroll-linked camera movement
        if (camera) {
            // Camera sinks and tilts slightly as we scroll down to section 1
            camera.position.y = -scrollYOffset * 0.02;
            camera.position.z = 32 + scrollYOffset * 0.015;
        }

        // Apply temporary plane flight acceleration during scrolls
        scrollSpeedFactor = 2.5;
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            scrollSpeedFactor = 1.0;
        }, 150);
    });

    // Mouse interactive coordinates tracker (Camera Parallax)
    window.addEventListener('mousemove', (e) => {
        // Normalized coordinates from -1 to 1
        mouseX = (e.clientX / window.innerWidth) * 2 - 1;
        mouseY = -(e.clientY / window.innerHeight) * 2 + 1;
    });

    // Main animation frame loop
    function animate() {
        requestAnimationFrame(animate);

        // Smooth camera mouse follow lerp
        targetX += (mouseX - targetX) * 0.05;
        targetY += (mouseY - targetY) * 0.05;

        if (camera) {
            // Offset camera slightly for mouse parallax
            camera.position.x = targetX * 3;
            camera.rotation.y = -targetX * 0.04;
            camera.rotation.x = targetY * 0.04;
        }

        // Flight calculations updates
        updateFlights();

        // Project positions to update 2D HTML badges
        updatePlaneBadges();

        // Render scene
        renderer.render(scene, camera);
    }

    // Responsive Canvas Resize handler
    window.addEventListener('resize', () => {
        const width = canvasContainer.clientWidth;
        const height = canvasContainer.clientHeight;
        
        if (camera && renderer) {
            camera.aspect = width / height;
            camera.updateProjectionMatrix();
            renderer.setSize(width, height);
        }
    });

    // Initialize flights
    initThree();
    spawnPlanes();
    animate();
});
