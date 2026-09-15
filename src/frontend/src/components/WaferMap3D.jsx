import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import {
  RotateCw,
  Layers,
  Maximize2,
  Minimize2,
  Compass,
  Crosshair,
  Info,
  Sparkles,
} from 'lucide-react';
import WaferMap2DFallback from './WaferMap2DFallback';

export default function WaferMap3D({
  lotId,
  defects = [],
  signature = 'random',
  severitySummary = { critical: 0, major: 0, minor: 0 },
}) {
  const mountRef = useRef(null);
  const [viewMode, setViewMode] = useState('3D'); // '3D' | '2D'
  const [isAutoRotate, setIsAutoRotate] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [cameraPreset, setCameraPreset] = useState('iso'); // 'iso' | 'top' | 'side'
  const [hoveredDefect, setHoveredDefect] = useState(null);

  // Refs for Three.js instance to allow camera resets without reloading
  const threeRef = useRef({
    camera: null,
    waferGroup: null,
    renderer: null,
    scene: null,
  });

  // Camera preset handler
  const setPreset = useCallback((preset) => {
    setCameraPreset(preset);
    setIsAutoRotate(false);
    const { camera, waferGroup } = threeRef.current;
    if (!camera || !waferGroup) return;

    if (preset === 'top') {
      // Direct top-down 2D-like view from above
      camera.position.set(0, 22, 0.01);
      camera.lookAt(0, 0, 0);
      waferGroup.rotation.set(0, 0, 0);
    } else if (preset === 'side') {
      // Side edge-profile view to inspect wafer bevel
      camera.position.set(0, 3, 20);
      camera.lookAt(0, 0, 0);
      waferGroup.rotation.set(0.1, 0, 0);
    } else {
      // Standard isometric 3D angle
      camera.position.set(0, 14, 18);
      camera.lookAt(0, 0, 0);
      waferGroup.rotation.set(0, 0, 0);
    }
  }, []);

  useEffect(() => {
    if (viewMode !== '3D' || !mountRef.current) return;

    const container = mountRef.current;
    let width = container.clientWidth || 440;
    let height = container.clientHeight || (isFullscreen ? window.innerHeight - 140 : 420);

    // 1. Scene & Camera
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 1000);
    camera.position.set(0, 14, 18);
    camera.lookAt(0, 0, 0);

    // 2. WebGL Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Store refs
    threeRef.current = { camera, scene, renderer, waferGroup: null };

    // 3. Lighting (Cleanroom spectroscopy lumination)
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.4);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x38bdf8, 2.5);
    dirLight1.position.set(12, 22, 16);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x06b6d4, 1.8);
    dirLight2.position.set(-15, 12, -10);
    scene.add(dirLight2);

    const cyanPoint = new THREE.PointLight(0x06b6d4, 3.5, 60);
    cyanPoint.position.set(0, 8, 0);
    scene.add(cyanPoint);

    // 4. Wafer Group
    const waferGroup = new THREE.Group();
    scene.add(waferGroup);
    threeRef.current.waferGroup = waferGroup;

    const waferRadius = 8.2;
    const waferThickness = 0.32;

    // Create a high-tech die grid texture on the silicon wafer face
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 1024;
    const ctx = canvas.getContext('2d');
    // Dark silicon base
    ctx.fillStyle = '#0d131f';
    ctx.fillRect(0, 0, 1024, 1024);

    // Etched semiconductor die reticle grid lines
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1.2;
    const dieSize = 32;
    for (let x = 0; x < 1024; x += dieSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, 1024);
      ctx.stroke();
    }
    for (let y = 0; y < 1024; y += dieSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(1024, y);
      ctx.stroke();
    }

    const waferTexture = new THREE.CanvasTexture(canvas);
    waferTexture.wrapS = THREE.RepeatWrapping;
    waferTexture.wrapT = THREE.RepeatWrapping;

    // Silicon Wafer Disc Mesh
    const waferGeo = new THREE.CylinderGeometry(waferRadius, waferRadius, waferThickness, 80);
    const waferMat = new THREE.MeshStandardMaterial({
      color: 0x111927,
      map: waferTexture,
      roughness: 0.18,
      metalness: 0.88,
    });
    const waferMesh = new THREE.Mesh(waferGeo, waferMat);
    waferGroup.add(waferMesh);

    // Polished Silicon Bevel Edge Ring
    const bevelGeo = new THREE.RingGeometry(waferRadius - 0.25, waferRadius, 80);
    const bevelMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      roughness: 0.1,
      metalness: 0.95,
      side: THREE.DoubleSide,
    });
    const bevelMesh = new THREE.Mesh(bevelGeo, bevelMat);
    bevelMesh.rotation.x = -Math.PI / 2;
    bevelMesh.position.y = waferThickness / 2 + 0.01;
    waferGroup.add(bevelMesh);

    // SEMI standard wafer notch at 6 o'clock
    const notchGeo = new THREE.BoxGeometry(0.6, 0.45, 0.6);
    const notchMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4 });
    const notch = new THREE.Mesh(notchGeo, notchMat);
    notch.position.set(0, waferThickness / 2, waferRadius - 0.12);
    waferGroup.add(notch);

    // Concentric Reticle Alignment Rings
    [0.25, 0.5, 0.75].forEach((ratio) => {
      const ringGeo = new THREE.RingGeometry(waferRadius * ratio - 0.03, waferRadius * ratio, 80);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0x334155,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.65,
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.rotation.x = -Math.PI / 2;
      ringMesh.position.y = waferThickness / 2 + 0.015;
      waferGroup.add(ringMesh);
    });

    // Signature Classification Highlight Geometry
    if (signature === 'edge-ring') {
      const ringGeo = new THREE.RingGeometry(waferRadius * 0.82, waferRadius * 0.98, 80);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.32,
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.rotation.x = -Math.PI / 2;
      ringMesh.position.y = waferThickness / 2 + 0.02;
      waferGroup.add(ringMesh);
    } else if (signature === 'center-cluster') {
      const centerGeo = new THREE.CircleGeometry(waferRadius * 0.38, 48);
      const centerMat = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.28,
      });
      const centerMesh = new THREE.Mesh(centerGeo, centerMat);
      centerMesh.rotation.x = -Math.PI / 2;
      centerMesh.position.y = waferThickness / 2 + 0.02;
      waferGroup.add(centerMesh);
    } else if (signature === 'donut') {
      const donutGeo = new THREE.RingGeometry(waferRadius * 0.45, waferRadius * 0.70, 80);
      const donutMat = new THREE.MeshBasicMaterial({
        color: 0xf59e0b,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.3,
      });
      const donutMesh = new THREE.Mesh(donutGeo, donutMat);
      donutMesh.rotation.x = -Math.PI / 2;
      donutMesh.position.y = waferThickness / 2 + 0.02;
      waferGroup.add(donutMesh);
    } else if (signature === 'scratch') {
      const lineGeo = new THREE.PlaneGeometry(waferRadius * 1.4, 0.4);
      const lineMat = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.4,
      });
      const lineMesh = new THREE.Mesh(lineGeo, lineMat);
      lineMesh.rotation.x = -Math.PI / 2;
      lineMesh.rotation.z = Math.PI / 4;
      lineMesh.position.y = waferThickness / 2 + 0.025;
      waferGroup.add(lineMesh);
    }

    // 5. Defect Points Cloud
    const pointsGeo = new THREE.BufferGeometry();
    const positions = [];
    const colors = [];

    const colorCritical = new THREE.Color(0xef4444); // Red
    const colorMajor = new THREE.Color(0xf59e0b);    // Amber
    const colorMinor = new THREE.Color(0x06b6d4);    // Cyan

    const maxRender = Math.min(defects.length, 2500);
    for (let i = 0; i < maxRender; i++) {
      const d = defects[i];
      const px = d.x * (waferRadius - 0.45);
      const pz = -d.y * (waferRadius - 0.45);
      const py = waferThickness / 2 + 0.045;

      positions.push(px, py, pz);

      let c = colorMinor;
      if (d.severity === 'critical') c = colorCritical;
      else if (d.severity === 'major') c = colorMajor;

      colors.push(c.r, c.g, c.b);
    }

    pointsGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    pointsGeo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    const pointsMat = new THREE.PointsMaterial({
      size: 0.24,
      vertexColors: true,
      transparent: true,
      opacity: 0.95,
      sizeAttenuation: true,
    });

    const defectPointsMesh = new THREE.Points(pointsGeo, pointsMat);
    waferGroup.add(defectPointsMesh);

    // Interactive 3D Target Reticle for Hovered Defect
    const targetReticleGeo = new THREE.RingGeometry(0.35, 0.45, 32);
    const targetReticleMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0,
    });
    const targetReticle = new THREE.Mesh(targetReticleGeo, targetReticleMat);
    targetReticle.rotation.x = -Math.PI / 2;
    targetReticle.position.y = waferThickness / 2 + 0.06;
    waferGroup.add(targetReticle);

    // 6. Raycasting & Interactive Mouse Controls
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    const raycaster = new THREE.Raycaster();
    raycaster.params.Points.threshold = 0.45;
    const mouse = new THREE.Vector2();

    const onMouseDown = (e) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      // Handle drag rotation
      if (isDragging) {
        const deltaX = e.clientX - previousMousePosition.x;
        const deltaY = e.clientY - previousMousePosition.y;

        waferGroup.rotation.y += deltaX * 0.008;
        waferGroup.rotation.x = Math.max(-0.7, Math.min(0.7, waferGroup.rotation.x + deltaY * 0.004));

        previousMousePosition = { x: e.clientX, y: e.clientY };
      } else {
        // Raycast against defect points
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObject(defectPointsMesh);
        if (intersects.length > 0) {
          const index = intersects[0].index;
          const defect = defects[index];
          if (defect) {
            setHoveredDefect(defect);
            const px = defect.x * (waferRadius - 0.45);
            const pz = -defect.y * (waferRadius - 0.45);
            targetReticle.position.set(px, waferThickness / 2 + 0.06, pz);
            targetReticleMat.opacity = 0.9;
          }
        } else {
          targetReticleMat.opacity = 0;
          setHoveredDefect(null);
        }
      }
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const onWheel = (e) => {
      e.preventDefault();
      camera.position.z = Math.max(10, Math.min(32, camera.position.z + e.deltaY * 0.02));
      camera.position.y = Math.max(4, Math.min(26, camera.position.y + e.deltaY * 0.015));
    };

    const domElement = renderer.domElement;
    domElement.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    domElement.addEventListener('wheel', onWheel, { passive: false });

    // 7. Dynamic ResizeObserver for 100% Responsiveness
    const resizeObserver = new ResizeObserver(() => {
      if (!container) return;
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight || (isFullscreen ? window.innerHeight - 140 : 420);
      if (newWidth > 0 && newHeight > 0) {
        camera.aspect = newWidth / newHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(newWidth, newHeight);
      }
    });
    resizeObserver.observe(container);

    // 8. Animation Loop
    let animId;
    const animate = () => {
      animId = requestAnimationFrame(animate);

      if (isAutoRotate && !isDragging) {
        waferGroup.rotation.y += 0.0025;
      }

      renderer.render(scene, camera);
    };
    animate();

    // 9. Cleanup
    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
      domElement.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      domElement.removeEventListener('wheel', onWheel);
      renderer.dispose();
      waferGeo.dispose();
      waferMat.dispose();
      pointsGeo.dispose();
      pointsMat.dispose();
      waferTexture.dispose();
    };
  }, [viewMode, defects, signature, isAutoRotate, isFullscreen]);

  return (
    <div
      className={`glass-panel rounded-xl p-4 sm:p-5 shadow-glass flex flex-col justify-between transition-all ${
        isFullscreen ? 'fixed inset-4 z-50 bg-canvas/98 border border-cyan/50 backdrop-blur-2xl' : 'w-full'
      }`}
    >
      {/* Top Header & Adaptive Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 mb-2.5">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-cyan" />
          <h3 className="text-xs sm:text-sm font-bold tracking-tight text-white uppercase font-mono truncate">
            3D Wafer Defect Metrology
          </h3>
          <span className="rounded border border-cyan/40 bg-cyan/10 px-2 py-0.5 text-[10px] font-mono font-semibold text-cyan uppercase whitespace-nowrap">
            {lotId} • 300mm
          </span>
        </div>

        {/* View Toggle & Camera Presets */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          {/* Camera View Presets */}
          {viewMode === '3D' && (
            <div className="hidden sm:flex rounded-md border border-border-subtle bg-surface-1 p-0.5 text-[10px] font-mono">
              <button
                onClick={() => setPreset('iso')}
                className={`rounded px-2 py-0.5 transition-colors ${
                  cameraPreset === 'iso' ? 'bg-cyan/20 text-cyan font-bold' : 'text-slate-400 hover:text-white'
                }`}
                title="Isometric 3D Perspective"
              >
                3D Iso
              </button>
              <button
                onClick={() => setPreset('top')}
                className={`rounded px-2 py-0.5 transition-colors ${
                  cameraPreset === 'top' ? 'bg-cyan/20 text-cyan font-bold' : 'text-slate-400 hover:text-white'
                }`}
                title="Perpendicular Top-Down Reticle View"
              >
                Top-Down
              </button>
              <button
                onClick={() => setPreset('side')}
                className={`rounded px-2 py-0.5 transition-colors ${
                  cameraPreset === 'side' ? 'bg-cyan/20 text-cyan font-bold' : 'text-slate-400 hover:text-white'
                }`}
                title="Wafer Edge Profile View"
              >
                Profile
              </button>
            </div>
          )}

          {/* Auto Rotate Toggle */}
          {viewMode === '3D' && (
            <button
              onClick={() => setIsAutoRotate(!isAutoRotate)}
              className={`rounded p-1.5 text-xs font-mono transition-colors ${
                isAutoRotate ? 'bg-cyan/20 text-cyan border border-cyan/40' : 'text-slate-400 hover:text-white'
              }`}
              title="Toggle Auto Orbit Rotation"
            >
              <RotateCw className="h-3.5 w-3.5" />
            </button>
          )}

          {/* Fullscreen Expand Toggle */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="rounded p-1.5 text-xs font-mono text-slate-400 hover:text-cyan border border-border-subtle hover:border-cyan/40 transition-colors"
            title={isFullscreen ? 'Exit Fullscreen' : 'Expand Wafer Inspector'}
          >
            {isFullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>

          {/* 3D vs 2D Fallback Switcher */}
          <div className="flex rounded-md border border-border-subtle bg-surface-1 p-0.5 text-xs font-mono">
            <button
              onClick={() => setViewMode('3D')}
              className={`rounded px-2.5 py-1 transition-colors ${
                viewMode === '3D'
                  ? 'bg-cyan/20 text-cyan border border-cyan/40 font-semibold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              3D Orbit
            </button>
            <button
              onClick={() => setViewMode('2D')}
              className={`rounded px-2.5 py-1 transition-colors ${
                viewMode === '2D'
                  ? 'bg-cyan/20 text-cyan border border-cyan/40 font-semibold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              2D Fallback
            </button>
          </div>
        </div>
      </div>

      {/* Signature & Density Context Bar */}
      <div className="flex items-center justify-between border-b border-border-subtle pb-2 mb-2 text-xs font-mono">
        <div className="flex items-center gap-2">
          <span className="text-slate-400">Classified Signature:</span>
          <span
            className={`rounded px-2 py-0.5 font-bold uppercase ${
              signature === 'random'
                ? 'bg-slate-800 text-slate-300'
                : 'bg-red-500/20 text-red-400 border border-red-500/30 shadow-sm'
            }`}
          >
            {signature}
          </span>
        </div>
        <span className="text-slate-400">
          Inspection Points: <strong className="text-white">{defects.length}</strong>
        </span>
      </div>

      {/* Wafer Canvas / Responsive Container */}
      <div
        className={`relative flex items-center justify-center w-full overflow-hidden rounded-lg bg-surface-deep border border-border-subtle ${
          isFullscreen ? 'flex-1 min-h-[500px]' : 'h-[360px] sm:h-[420px]'
        }`}
      >
        {viewMode === '3D' ? (
          <div ref={mountRef} className="h-full w-full cursor-grab active:cursor-grabbing" />
        ) : (
          <WaferMap2DFallback defects={defects} signature={signature} lotId={lotId} />
        )}

        {/* Live Hovered Defect HUD Overlay */}
        {hoveredDefect && (
          <div className="absolute top-3 left-3 rounded-lg border border-cyan/50 bg-surface-1/95 p-3 text-xs font-mono text-slate-200 shadow-cyan-glow backdrop-blur-md animate-fade-in pointer-events-none max-w-xs">
            <div className="flex items-center gap-1.5 text-cyan font-bold mb-1 border-b border-border-subtle pb-1">
              <Crosshair className="h-3.5 w-3.5" />
              <span>RETICLE INSPECTION HUD</span>
            </div>
            <p className="text-[11px] text-slate-300">
              Type: <strong className="text-white uppercase">{hoveredDefect.defect_type}</strong>
            </p>
            <p className="text-[11px] text-slate-300">
              Severity: <strong className="text-red-400 uppercase">{hoveredDefect.severity}</strong>
            </p>
            <p className="text-[11px] text-slate-300">
              Normalized: [X: {hoveredDefect.x?.toFixed(3)}, Y: {hoveredDefect.y?.toFixed(3)}]
            </p>
            <p className="text-[10px] text-slate-400 mt-1">
              Step: {hoveredDefect.detected_at_step} • {hoveredDefect.wafer_id}
            </p>
          </div>
        )}

        {/* Interactive Floating Hint */}
        <div className="pointer-events-none absolute bottom-3 left-3 hidden sm:flex flex-col gap-0.5 text-[10px] font-mono text-slate-400 bg-surface-1/80 backdrop-blur px-2.5 py-1.5 rounded border border-border-subtle">
          <span>Drag: Orbit 360° | Scroll: Zoom</span>
          <span>Hover defect: Reticle HUD</span>
        </div>
      </div>

      {/* Defect Severity Legend */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-border-subtle pt-2.5 text-xs font-mono">
        <div className="flex items-center gap-3 sm:gap-4">
          <span className="flex items-center gap-1.5 text-red-400">
            <span className="h-2.5 w-2.5 rounded-full bg-red-500 shadow-sm"></span>
            Critical ({severitySummary.critical || 0})
          </span>
          <span className="flex items-center gap-1.5 text-amber">
            <span className="h-2.5 w-2.5 rounded-full bg-amber shadow-sm"></span>
            Major ({severitySummary.major || 0})
          </span>
          <span className="flex items-center gap-1.5 text-cyan">
            <span className="h-2.5 w-2.5 rounded-full bg-cyan shadow-sm"></span>
            Minor ({severitySummary.minor || 0})
          </span>
        </div>
        <span className="text-[11px] text-slate-500 hidden sm:inline">
          SEMI E10 Physical Die Grid & Notch Alignment
        </span>
      </div>
    </div>
  );
}
