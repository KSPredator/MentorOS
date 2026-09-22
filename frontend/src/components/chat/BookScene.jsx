import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, OrbitControls } from '@react-three/drei';
import useReducedMotion from '../../lib/useReducedMotion';
import { useUI } from '../../stores/ui';

/**
 * Professional Realistic 3D Study Chamber Hero Scene.
 *
 * Features:
 * - Interactive Cursor Drag to Rotate 360° with physics damping & smooth inertia
 * - Space-like slow Floating & gentle Bobbing with smooth auto-rotation
 * - Realistic Compact Study Book with curved 1-second interval page turning physics
 * - Stacked companion textbooks, stationery pen cup, succulent, and steaming coffee mug
 * - Realistic Seated Human Scholar with breathing posture, head tracking & arm reach
 * - Warm articulated desk lamp casting a focused golden light beam on the book
 * - Widescreen desktop setup with backlit keyboard, mouse & emissive study IDE screen
 * - Seamless Light/Dark responsiveness, WebGL probe, and reduced-motion safety
 */
export default function BookScene() {
  const reduced = useReducedMotion();
  const webgl = useWebGLSupported();
  const dark = useUI((s) => s.dark);
  const [isInteracting, setIsInteracting] = useState(false);

  if (reduced || !webgl) return <StaticGradient />;

  return (
    <SceneErrorBoundary fallback={<StaticGradient />}>
      <div
        className="w-full max-w-3xl h-72 sm:h-84 mb-4 relative animate-scene-in select-none group cursor-grab active:cursor-grabbing"
        aria-hidden="true"
        onMouseDown={() => setIsInteracting(true)}
        onMouseUp={() => setIsInteracting(false)}
        onTouchStart={() => setIsInteracting(true)}
        onTouchEnd={() => setIsInteracting(false)}
      >
        {/* Atmospheric ambient backdrop glow */}
        <div
          className="absolute inset-0 rounded-3xl overflow-hidden pointer-events-none transition-colors duration-500"
          style={{
            background: dark
              ? 'radial-gradient(ellipse at 50% 55%, rgba(14,165,233,0.14), rgba(251,191,36,0.05) 45%, transparent 72%)'
              : 'radial-gradient(ellipse at 50% 55%, rgba(14,165,233,0.12), rgba(254,243,199,0.22) 45%, transparent 72%)',
          }}
        />

        <Canvas
          dpr={[1, 1.5]}
          camera={{ position: [0, 1.05, 4.3], fov: 40 }}
          gl={{
            antialias: true,
            alpha: true,
            powerPreference: 'high-performance',
            toneMapping: THREE.ACESFilmicToneMapping,
            toneMappingExposure: 1.15,
          }}
          style={{ position: 'absolute', inset: 0 }}
          onCreated={({ gl }) => gl.setClearColor(0x000000, 0)}
        >
          {/* Interactive Orbit Controls with smooth auto-float and inertia damping */}
          <OrbitControls
            enableZoom={false}
            enablePan={false}
            autoRotate={!isInteracting}
            autoRotateSpeed={0.55}
            enableDamping
            dampingFactor={0.06}
            maxPolarAngle={Math.PI / 2 - 0.05}
            minPolarAngle={Math.PI / 6}
            target={[0, -0.05, 0]}
            makeDefault
          />

          {/* Environmental Studio Lighting for 4K Sharpness */}
          <ambientLight intensity={dark ? 0.9 : 1.3} color={dark ? '#cbd5e1' : '#ffffff'} />

          {/* Key Sunlight / Studio Rim Light */}
          <directionalLight
            position={[4, 6, 4]}
            intensity={dark ? 1.6 : 2.4}
            color={dark ? '#93c5fd' : '#f8fafc'}
          />

          {/* Sharp Anisotropic Studio Rim Light */}
          <pointLight
            position={[-4, 4, -3]}
            intensity={dark ? 2.2 : 1.5}
            color={dark ? '#93c5fd' : '#e0f2fe'}
            decay={2}
          />

          {/* Gentle Floating in Space */}
          <Float speed={1.15} rotationIntensity={0.04} floatIntensity={0.16}>
            <StudyChamber dark={dark} />
          </Float>

          {/* Warm Dust Motes in Lamp Light Cone */}
          <AmbientDustMotes count={45} dark={dark} />
        </Canvas>

        {/* Floating Rotation Affordance Hint */}
        <div className="absolute bottom-2.5 right-3 pointer-events-none opacity-65 group-hover:opacity-100 transition-opacity duration-300">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-medium tracking-tight bg-panel/85 dark:bg-panel/75 backdrop-blur-md border border-border/80 text-textMuted shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            Drag to rotate 360°
          </span>
        </div>
      </div>
    </SceneErrorBoundary>
  );
}

/** Root 3D composition containing desk, chair, student, lamp, PC, book, and accessories */
function StudyChamber({ dark }) {
  const rootRef = useRef();
  const headRef = useRef();
  const chestRef = useRef();
  const rightArmRef = useRef();
  const rightForearmRef = useRef();
  const pageFlipRef = useRef();
  const pageCurlRef = useRef();
  const steamRef = useRef();

  useFrame((state) => {
    const t = state.clock.elapsedTime;

    // 1-Second interval page turn cycle
    const FLIP_PERIOD = 1.2; // ~1.2s per page turn
    const cycle = (t / FLIP_PERIOD) % 1;
    
    // Smooth non-linear flip progression (0 to 1)
    const p = cycle;
    const easedFlip = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;

    // Page turning rotation across the spine (0 to Math.PI)
    if (pageFlipRef.current) {
      pageFlipRef.current.rotation.y = Math.PI * (1 - easedFlip);
      // Lift page slightly during turn
      const arcLift = Math.sin(easedFlip * Math.PI);
      pageFlipRef.current.position.y = arcLift * 0.06;
      
      // Dynamic page curl bending
      if (pageCurlRef.current) {
        pageCurlRef.current.rotation.z = Math.sin(easedFlip * Math.PI) * 0.35;
      }
    }

    // Right Arm / Hand reaches and follows the turning page
    if (rightArmRef.current && rightForearmRef.current) {
      // Synchronized reach gesture
      const reachPhase = Math.sin(easedFlip * Math.PI);
      rightArmRef.current.rotation.x = -0.45 - reachPhase * 0.18;
      rightArmRef.current.rotation.y = 0.15 - reachPhase * 0.22;
      rightForearmRef.current.rotation.x = -0.35 + reachPhase * 0.25;
      rightForearmRef.current.rotation.z = -reachPhase * 0.2;
    }

    // Natural human breathing & idle movement
    if (chestRef.current) {
      chestRef.current.position.y = -0.02 + Math.sin(t * 1.6) * 0.012;
      chestRef.current.rotation.x = 0.08 + Math.sin(t * 1.6) * 0.015;
    }

    // Attentive head scanning / reading movement
    if (headRef.current) {
      headRef.current.rotation.y = -0.15 + Math.sin(t * 1.1) * 0.08;
      headRef.current.rotation.x = 0.22 + Math.sin(t * 2.2) * 0.03;
    }

    // Coffee mug steam wisp motion
    if (steamRef.current) {
      steamRef.current.position.y = 0.12 + (t * 0.15) % 0.25;
      steamRef.current.scale.setScalar(0.8 + ((t * 0.3) % 0.6));
    }

    // Gentle overall composition breathing
    if (rootRef.current) {
      rootRef.current.rotation.y = Math.sin(t * 0.25) * 0.05;
    }
  });

  return (
    <group ref={rootRef} position={[0, -0.3, 0]}>
      {/* Floor Rug / Pedestal */}
      <FloorRug dark={dark} />

      {/* Modern Study Desk */}
      <StudyDesk dark={dark} />

      {/* Ergonomic Office Chair */}
      <ErgonomicChair dark={dark} />

      {/* Seated Human Scholar */}
      <HumanScholar
        headRef={headRef}
        chestRef={chestRef}
        rightArmRef={rightArmRef}
        rightForearmRef={rightForearmRef}
        dark={dark}
      />

      {/* Articulated Desk Lamp with Warm Glow Beam */}
      <TableLamp dark={dark} />

      {/* Desktop Computer Setup (Monitor, Keyboard, Mouse) */}
      <DesktopSetup dark={dark} />

      {/* Open Book with 1-Second Turning Pages */}
      <OpenStudyBook
        pageFlipRef={pageFlipRef}
        pageCurlRef={pageCurlRef}
        dark={dark}
      />

      {/* Stack of Closed Study Textbooks */}
      <CompanionBookStack dark={dark} />

      {/* Study Desk Accessories (Coffee Mug, Plant, Pen Cup) */}
      <DeskAccessories steamRef={steamRef} dark={dark} />
    </group>
  );
}

/** Floor Rug / Circular Base */
function FloorRug({ dark }) {
  return (
    <group position={[0, -1.02, 0.2]}>
      <mesh receiveShadow>
        <cylinderGeometry args={[2.5, 2.5, 0.04, 48]} />
        <meshStandardMaterial
          color={dark ? '#111827' : '#e2e8f0'}
          roughness={0.9}
          metalness={0.05}
        />
      </mesh>
      {/* Soft Rug Border Rim */}
      <mesh position={[0, 0.025, 0]}>
        <torusGeometry args={[2.48, 0.02, 16, 48]} />
        <meshStandardMaterial
          color={dark ? '#1e293b' : '#cbd5e1'}
          roughness={0.8}
        />
      </mesh>
    </group>
  );
}

/** Modern Study Desk with Wood Top & Metal Frame */
function StudyDesk({ dark }) {
  const woodColor = dark ? '#1e293b' : '#e8e2d8';
  const legColor = dark ? '#0f172a' : '#94a3b8';

  return (
    <group position={[0.1, -0.28, 0]}>
      {/* Tabletop */}
      <mesh position={[0, 0, 0]} castShadow receiveShadow>
        <boxGeometry args={[3.2, 0.07, 1.7]} />
        <meshStandardMaterial
          color={woodColor}
          roughness={0.4}
          metalness={0.1}
        />
      </mesh>

      {/* Beveled Edge Trim */}
      <mesh position={[0, -0.038, 0]}>
        <boxGeometry args={[3.24, 0.02, 1.74]} />
        <meshStandardMaterial
          color={dark ? '#334155' : '#cbd5e1'}
          roughness={0.5}
          metalness={0.3}
        />
      </mesh>

      {/* Sturdy Metal Legs (4 corners) */}
      {[
        [-1.42, -0.52, -0.68],
        [1.42, -0.52, -0.68],
        [-1.42, -0.52, 0.68],
        [1.42, -0.52, 0.68],
      ].map((pos, i) => (
        <group key={i} position={pos}>
          <mesh castShadow>
            <cylinderGeometry args={[0.035, 0.035, 0.98, 16]} />
            <meshStandardMaterial
              color={legColor}
              roughness={0.3}
              metalness={0.8}
            />
          </mesh>
          {/* Leg Base Pad */}
          <mesh position={[0, -0.48, 0]}>
            <cylinderGeometry args={[0.05, 0.05, 0.03, 16]} />
            <meshStandardMaterial color="#0f172a" roughness={0.8} />
          </mesh>
        </group>
      ))}

      {/* Cable/Modesty Beam */}
      <mesh position={[0, -0.2, -0.68]}>
        <boxGeometry args={[2.7, 0.25, 0.03]} />
        <meshStandardMaterial
          color={dark ? '#111827' : '#cbd5e1'}
          roughness={0.6}
        />
      </mesh>
    </group>
  );
}

/** Ergonomic Swivel Study Chair */
function ErgonomicChair({ dark }) {
  const cushionColor = dark ? '#0f172a' : '#334155';
  const frameColor = dark ? '#38bdf8' : '#0284c7';

  return (
    <group position={[-0.48, -0.52, 0.85]} rotation={[0, 0.3, 0]}>
      {/* 5-Star Caster Base */}
      <group position={[0, -0.46, 0]}>
        <mesh>
          <cylinderGeometry args={[0.09, 0.11, 0.06, 16]} />
          <meshStandardMaterial color="#0f172a" metalness={0.9} roughness={0.2} />
        </mesh>
        {/* 5 Spoke Legs */}
        {[0, 1, 2, 3, 4].map((i) => {
          const angle = (i * Math.PI * 2) / 5;
          const x = Math.sin(angle) * 0.28;
          const z = Math.cos(angle) * 0.28;
          return (
            <group key={i} position={[x / 2, -0.01, z / 2]} rotation={[0, angle, 0]}>
              <mesh>
                <boxGeometry args={[0.04, 0.03, 0.3]} />
                <meshStandardMaterial color="#334155" metalness={0.8} roughness={0.3} />
              </mesh>
              {/* Caster Wheel */}
              <mesh position={[0, -0.02, 0.15]}>
                <sphereGeometry args={[0.03, 12, 12]} />
                <meshStandardMaterial color="#09090b" roughness={0.6} />
              </mesh>
            </group>
          );
        })}
      </group>

      {/* Hydraulic Lift Piston */}
      <mesh position={[0, -0.24, 0]}>
        <cylinderGeometry args={[0.03, 0.035, 0.4, 16]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.9} roughness={0.15} />
      </mesh>

      {/* Seat Cushion */}
      <mesh position={[0, -0.02, 0]} castShadow>
        <boxGeometry args={[0.72, 0.09, 0.68]} />
        <meshStandardMaterial
          color={cushionColor}
          roughness={0.75}
          metalness={0.1}
        />
      </mesh>

      {/* Ergonomic Curved Backrest */}
      <group position={[0, 0.42, 0.32]} rotation={[-0.1, 0, 0]}>
        <mesh castShadow>
          <boxGeometry args={[0.64, 0.78, 0.07]} />
          <meshStandardMaterial
            color={cushionColor}
            roughness={0.7}
            metalness={0.15}
          />
        </mesh>
        {/* Lumbar Accent Frame */}
        <mesh position={[0, -0.15, 0.04]}>
          <boxGeometry args={[0.55, 0.12, 0.02]} />
          <meshStandardMaterial
            color={frameColor}
            emissive={frameColor}
            emissiveIntensity={0.25}
            roughness={0.4}
          />
        </mesh>
        {/* Adjustable Headrest */}
        <mesh position={[0, 0.46, -0.02]} rotation={[0.08, 0, 0]}>
          <boxGeometry args={[0.36, 0.18, 0.06]} />
          <meshStandardMaterial color={cushionColor} roughness={0.75} />
        </mesh>
      </group>

      {/* Left Armrest */}
      <group position={[-0.38, 0.16, 0.02]}>
        <mesh position={[0, -0.12, 0]}>
          <cylinderGeometry args={[0.02, 0.02, 0.26, 12]} />
          <meshStandardMaterial color="#475569" metalness={0.7} />
        </mesh>
        <mesh position={[0, 0.02, 0]}>
          <boxGeometry args={[0.07, 0.03, 0.36]} />
          <meshStandardMaterial color="#1e293b" roughness={0.6} />
        </mesh>
      </group>

      {/* Right Armrest */}
      <group position={[0.38, 0.16, 0.02]}>
        <mesh position={[0, -0.12, 0]}>
          <cylinderGeometry args={[0.02, 0.02, 0.26, 12]} />
          <meshStandardMaterial color="#475569" metalness={0.7} />
        </mesh>
        <mesh position={[0, 0.02, 0]}>
          <boxGeometry args={[0.07, 0.03, 0.36]} />
          <meshStandardMaterial color="#1e293b" roughness={0.6} />
        </mesh>
      </group>
    </group>
  );
}

/** Realistic Seated Human Scholar / Student */
function HumanScholar({ headRef, chestRef, rightArmRef, rightForearmRef, dark }) {
  const hoodieColor = dark ? '#1e293b' : '#0369a1';
  const hoodieTrimColor = dark ? '#38bdf8' : '#0ea5e9';
  const pantsColor = dark ? '#0f172a' : '#1e293b';
  const skinColor = '#f5cba7';
  const hairColor = '#1f1614';
  const sneakerSoleColor = '#ffffff';
  const sneakerUpperColor = dark ? '#334155' : '#f1f5f9';
  const sneakerAccentColor = '#0ea5e9';

  return (
    <group position={[-0.48, -0.42, 0.82]} rotation={[0, 0.28, 0]}>
      {/* Lower Body: Hips, Ergonomic Seated Pelvis, Thighs, Calves & Designer Sneakers */}
      <group position={[0, 0, 0]}>
        {/* Pelvis & Hip Flexor Base */}
        <mesh position={[0, 0.04, 0]} castShadow>
          <cylinderGeometry args={[0.22, 0.2, 0.18, 20]} />
          <meshStandardMaterial color={pantsColor} roughness={0.8} />
        </mesh>

        {/* Left Leg (Thigh, Knee Joint, Calf & Sneaker) */}
        <group position={[-0.14, 0.02, 0]}>
          {/* Left Thigh extending towards desk */}
          <group position={[0, 0, -0.22]} rotation={[1.54, 0, 0.05]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.088, 0.076, 0.44, 18]} />
              <meshStandardMaterial color={pantsColor} roughness={0.85} />
            </mesh>
            {/* Denim Fabric Creases at Hip */}
            <mesh position={[0, 0.15, 0.02]}>
              <torusGeometry args={[0.082, 0.012, 8, 16]} />
              <meshStandardMaterial color={pantsColor} roughness={0.9} />
            </mesh>
          </group>

          {/* Left Knee Joint */}
          <mesh position={[0, -0.01, -0.44]}>
            <sphereGeometry args={[0.075, 14, 14]} />
            <meshStandardMaterial color={pantsColor} roughness={0.85} />
          </mesh>

          {/* Left Shin / Calf dropping to floor */}
          <group position={[0, -0.25, -0.44]} rotation={[-0.08, 0, 0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.072, 0.06, 0.44, 18]} />
              <meshStandardMaterial color={pantsColor} roughness={0.85} />
            </mesh>
            {/* Pant Cuff */}
            <mesh position={[0, -0.19, 0]}>
              <cylinderGeometry args={[0.066, 0.066, 0.04, 18]} />
              <meshStandardMaterial color={pantsColor} roughness={0.9} />
            </mesh>

            {/* Designer Sneaker (Contoured Sole, Upper, Tongue, Laces) */}
            <group position={[0, -0.24, 0.07]} rotation={[0.08, 0, 0]}>
              {/* White Outsole */}
              <mesh position={[0, -0.032, 0]} castShadow>
                <boxGeometry args={[0.13, 0.038, 0.3]} />
                <meshStandardMaterial color={sneakerSoleColor} roughness={0.4} />
              </mesh>
              {/* Midsole Accent Stripe */}
              <mesh position={[0, -0.018, 0]}>
                <boxGeometry args={[0.134, 0.012, 0.29]} />
                <meshStandardMaterial color={sneakerAccentColor} roughness={0.5} />
              </mesh>
              {/* Shoe Upper */}
              <mesh position={[0, 0.02, -0.01]}>
                <boxGeometry args={[0.12, 0.065, 0.26]} />
                <meshStandardMaterial color={sneakerUpperColor} roughness={0.6} />
              </mesh>
              {/* Toe Cap Curve */}
              <mesh position={[0, 0.01, 0.11]}>
                <sphereGeometry args={[0.055, 14, 14]} />
                <meshStandardMaterial color={sneakerSoleColor} roughness={0.4} />
              </mesh>
              {/* Shoe Tongue & Laces */}
              <mesh position={[0, 0.055, 0.02]} rotation={[-0.4, 0, 0]}>
                <boxGeometry args={[0.07, 0.045, 0.14]} />
                <meshStandardMaterial color="#ffffff" roughness={0.5} />
              </mesh>
            </group>
          </group>
        </group>

        {/* Right Leg (Thigh, Knee Joint, Calf & Sneaker) */}
        <group position={[0.14, 0.02, 0]}>
          {/* Right Thigh extending towards desk */}
          <group position={[0, 0, -0.22]} rotation={[1.54, 0, -0.05]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.088, 0.076, 0.44, 18]} />
              <meshStandardMaterial color={pantsColor} roughness={0.85} />
            </mesh>
            {/* Denim Fabric Creases at Hip */}
            <mesh position={[0, 0.15, 0.02]}>
              <torusGeometry args={[0.082, 0.012, 8, 16]} />
              <meshStandardMaterial color={pantsColor} roughness={0.9} />
            </mesh>
          </group>

          {/* Right Knee Joint */}
          <mesh position={[0, -0.01, -0.44]}>
            <sphereGeometry args={[0.075, 14, 14]} />
            <meshStandardMaterial color={pantsColor} roughness={0.85} />
          </mesh>

          {/* Right Shin / Calf dropping to floor */}
          <group position={[0, -0.25, -0.44]} rotation={[-0.08, 0, 0]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.072, 0.06, 0.44, 18]} />
              <meshStandardMaterial color={pantsColor} roughness={0.85} />
            </mesh>
            {/* Pant Cuff */}
            <mesh position={[0, -0.19, 0]}>
              <cylinderGeometry args={[0.066, 0.066, 0.04, 18]} />
              <meshStandardMaterial color={pantsColor} roughness={0.9} />
            </mesh>

            {/* Designer Sneaker */}
            <group position={[0, -0.24, 0.07]} rotation={[0.08, 0, 0]}>
              {/* White Outsole */}
              <mesh position={[0, -0.032, 0]} castShadow>
                <boxGeometry args={[0.13, 0.038, 0.3]} />
                <meshStandardMaterial color={sneakerSoleColor} roughness={0.4} />
              </mesh>
              {/* Midsole Accent Stripe */}
              <mesh position={[0, -0.018, 0]}>
                <boxGeometry args={[0.134, 0.012, 0.29]} />
                <meshStandardMaterial color={sneakerAccentColor} roughness={0.5} />
              </mesh>
              {/* Shoe Upper */}
              <mesh position={[0, 0.02, -0.01]}>
                <boxGeometry args={[0.12, 0.065, 0.26]} />
                <meshStandardMaterial color={sneakerUpperColor} roughness={0.6} />
              </mesh>
              {/* Toe Cap Curve */}
              <mesh position={[0, 0.01, 0.11]}>
                <sphereGeometry args={[0.055, 14, 14]} />
                <meshStandardMaterial color={sneakerSoleColor} roughness={0.4} />
              </mesh>
              {/* Shoe Tongue & Laces */}
              <mesh position={[0, 0.055, 0.02]} rotation={[-0.4, 0, 0]}>
                <boxGeometry args={[0.07, 0.045, 0.14]} />
                <meshStandardMaterial color="#ffffff" roughness={0.5} />
              </mesh>
            </group>
          </group>
        </group>
      </group>

      {/* Upper Body (Torso, Hoodie, Arms & Head) with Anatomical Breathing Pivot */}
      <group ref={chestRef} position={[0, 0.26, 0.02]} rotation={[0.1, -0.15, 0]}>
        {/* Torso: Ribbed Waist Hem */}
        <mesh position={[0, 0.02, 0]} castShadow>
          <cylinderGeometry args={[0.2, 0.21, 0.06, 20]} />
          <meshStandardMaterial color={hoodieColor} roughness={0.8} />
        </mesh>

        {/* Mid-Torso / Abdominal Curvature */}
        <mesh position={[0, 0.14, 0]} castShadow>
          <cylinderGeometry args={[0.22, 0.2, 0.18, 20]} />
          <meshStandardMaterial color={hoodieColor} roughness={0.75} />
        </mesh>

        {/* Upper Chest & Shoulders in Contoured Hoodie */}
        <mesh position={[0, 0.28, 0.01]} castShadow>
          <cylinderGeometry args={[0.24, 0.22, 0.18, 20]} />
          <meshStandardMaterial color={hoodieColor} roughness={0.75} />
        </mesh>

        {/* Shoulder Deltoid Caps for smooth organic sleeve transition */}
        <mesh position={[-0.26, 0.32, 0]}>
          <sphereGeometry args={[0.085, 16, 16]} />
          <meshStandardMaterial color={hoodieColor} roughness={0.75} />
        </mesh>
        <mesh position={[0.26, 0.32, 0]}>
          <sphereGeometry args={[0.085, 16, 16]} />
          <meshStandardMaterial color={hoodieColor} roughness={0.75} />
        </mesh>

        {/* Folded Hoodie Cowl / Collar draped around back of neck */}
        <group position={[0, 0.38, 0.02]} rotation={[0.35, 0, 0]}>
          <mesh castShadow>
            <torusGeometry args={[0.13, 0.048, 14, 24, Math.PI * 1.3]} />
            <meshStandardMaterial color={hoodieColor} roughness={0.8} />
          </mesh>
          {/* Inner Collar Accent */}
          <mesh position={[0, 0, -0.01]}>
            <torusGeometry args={[0.11, 0.02, 10, 20]} />
            <meshStandardMaterial color={hoodieTrimColor} roughness={0.6} />
          </mesh>
        </group>

        {/* Hanging Hoodie Drawstrings with metallic aglets */}
        <group position={[0, 0.32, -0.14]}>
          {/* Left String */}
          <group position={[-0.06, 0, 0]} rotation={[0.15, 0, -0.05]}>
            <mesh position={[0, -0.09, 0]}>
              <cylinderGeometry args={[0.005, 0.005, 0.18, 8]} />
              <meshStandardMaterial color="#ffffff" roughness={0.5} />
            </mesh>
            {/* Metal Aglet Tip */}
            <mesh position={[0, -0.185, 0]}>
              <cylinderGeometry args={[0.007, 0.007, 0.02, 10]} />
              <meshStandardMaterial color="#cbd5e1" metalness={0.9} roughness={0.2} />
            </mesh>
          </group>

          {/* Right String */}
          <group position={[0.06, 0, 0]} rotation={[0.15, 0, 0.05]}>
            <mesh position={[0, -0.09, 0]}>
              <cylinderGeometry args={[0.005, 0.005, 0.18, 8]} />
              <meshStandardMaterial color="#ffffff" roughness={0.5} />
            </mesh>
            {/* Metal Aglet Tip */}
            <mesh position={[0, -0.185, 0]}>
              <cylinderGeometry args={[0.007, 0.007, 0.02, 10]} />
              <meshStandardMaterial color="#cbd5e1" metalness={0.9} roughness={0.2} />
            </mesh>
          </group>
        </group>

        {/* Left Arm: Resting naturally on desk / near keyboard mat */}
        <group position={[-0.27, 0.32, 0]}>
          {/* Upper Arm with Bicep Contour */}
          <mesh position={[-0.05, -0.16, -0.12]} rotation={[0.72, 0.22, -0.24]} castShadow>
            <cylinderGeometry args={[0.068, 0.056, 0.36, 16]} />
            <meshStandardMaterial color={hoodieColor} roughness={0.75} />
          </mesh>
          {/* Elbow Joint */}
          <mesh position={[-0.07, -0.28, -0.22]}>
            <sphereGeometry args={[0.058, 14, 14]} />
            <meshStandardMaterial color={hoodieColor} roughness={0.75} />
          </mesh>
          {/* Forearm in Hoodie Sleeve resting on desk */}
          <mesh position={[-0.07, -0.32, -0.38]} rotation={[1.44, 0, 0.28]} castShadow>
            <cylinderGeometry args={[0.056, 0.046, 0.34, 16]} />
            <meshStandardMaterial color={hoodieColor} roughness={0.75} />
          </mesh>
          {/* Ribbed Sleeve Cuff */}
          <mesh position={[-0.05, -0.33, -0.52]} rotation={[1.44, 0, 0.28]}>
            <cylinderGeometry args={[0.05, 0.05, 0.035, 16]} />
            <meshStandardMaterial color={hoodieTrimColor} roughness={0.7} />
          </mesh>
          {/* Smartwatch / Wristband */}
          <mesh position={[-0.045, -0.33, -0.54]} rotation={[1.44, 0, 0.28]}>
            <torusGeometry args={[0.042, 0.008, 8, 16]} />
            <meshStandardMaterial color="#0f172a" metalness={0.8} roughness={0.2} />
          </mesh>
          {/* Anatomical Left Hand & Relaxed Curved Fingers */}
          <group position={[-0.03, -0.33, -0.59]}>
            {/* Palm */}
            <mesh castShadow>
              <boxGeometry args={[0.075, 0.03, 0.08]} />
              <meshStandardMaterial color={skinColor} roughness={0.55} />
            </mesh>
            {/* Thumb */}
            <mesh position={[0.038, 0.005, -0.01]} rotation={[0, 0.4, 0]}>
              <boxGeometry args={[0.025, 0.024, 0.05]} />
              <meshStandardMaterial color={skinColor} roughness={0.55} />
            </mesh>
            {/* 4 Relaxed Curved Fingers */}
            {[-0.025, -0.008, 0.009, 0.026].map((x, i) => (
              <mesh key={i} position={[x, -0.006, -0.055]} rotation={[0.25, 0, 0]}>
                <boxGeometry args={[0.015, 0.022, 0.045]} />
                <meshStandardMaterial color={skinColor} roughness={0.55} />
              </mesh>
            ))}
          </group>
        </group>

        {/* Right Arm: Synchronized note-taking & page-turning gesture */}
        <group ref={rightArmRef} position={[0.27, 0.32, 0]}>
          {/* Upper Arm */}
          <mesh position={[0.06, -0.16, -0.14]} rotation={[0.66, -0.24, 0.28]} castShadow>
            <cylinderGeometry args={[0.068, 0.056, 0.36, 16]} />
            <meshStandardMaterial color={hoodieColor} roughness={0.75} />
          </mesh>
          {/* Elbow Joint */}
          <mesh position={[0.08, -0.28, -0.24]}>
            <sphereGeometry args={[0.058, 14, 14]} />
            <meshStandardMaterial color={hoodieColor} roughness={0.75} />
          </mesh>
          {/* Forearm reaching to open study textbook */}
          <group ref={rightForearmRef} position={[0.09, -0.3, -0.34]}>
            <mesh rotation={[1.36, 0, -0.24]} castShadow>
              <cylinderGeometry args={[0.056, 0.046, 0.36, 16]} />
              <meshStandardMaterial color={hoodieColor} roughness={0.75} />
            </mesh>
            {/* Ribbed Sleeve Cuff */}
            <mesh position={[0.015, -0.03, -0.16]} rotation={[1.36, 0, -0.24]}>
              <cylinderGeometry args={[0.05, 0.05, 0.035, 16]} />
              <meshStandardMaterial color={hoodieTrimColor} roughness={0.7} />
            </mesh>
            {/* Right Hand holding drafting stylus / pen */}
            <group position={[0.025, -0.035, -0.22]}>
              {/* Palm */}
              <mesh castShadow>
                <boxGeometry args={[0.075, 0.028, 0.085]} />
                <meshStandardMaterial color={skinColor} roughness={0.55} />
              </mesh>
              {/* Index & Thumb pinching stylus */}
              <mesh position={[-0.02, 0.01, -0.04]} rotation={[0.3, -0.2, 0]}>
                <boxGeometry args={[0.018, 0.022, 0.05]} />
                <meshStandardMaterial color={skinColor} roughness={0.55} />
              </mesh>
              {/* Other fingers curled naturally */}
              <mesh position={[0.01, -0.008, -0.04]} rotation={[0.4, 0, 0]}>
                <boxGeometry args={[0.04, 0.024, 0.045]} />
                <meshStandardMaterial color={skinColor} roughness={0.55} />
              </mesh>
              {/* Slim Drafting Stylus / Pen in Hand */}
              <group position={[-0.015, 0.015, -0.03]} rotation={[0.5, -0.4, 0.6]}>
                {/* Pen Barrel */}
                <mesh>
                  <cylinderGeometry args={[0.006, 0.006, 0.22, 10]} />
                  <meshStandardMaterial color="#0f172a" metalness={0.8} roughness={0.2} />
                </mesh>
                {/* Gold Nib / Tip */}
                <mesh position={[0, -0.115, 0]}>
                  <coneGeometry args={[0.006, 0.02, 10]} />
                  <meshStandardMaterial color="#f59e0b" metalness={0.9} roughness={0.15} />
                </mesh>
              </group>
            </group>
          </group>
        </group>

        {/* Anatomical Head, Jawline, Nose, Hair, Glasses & Studio Headphones */}
        <group ref={headRef} position={[0, 0.52, -0.02]}>
          {/* Anatomical Neck */}
          <mesh position={[0, -0.06, 0]} castShadow>
            <cylinderGeometry args={[0.068, 0.08, 0.14, 20]} />
            <meshStandardMaterial color={skinColor} roughness={0.55} />
          </mesh>

          {/* Cranium / Head Sphere */}
          <mesh position={[0, 0.12, 0]} castShadow>
            <sphereGeometry args={[0.16, 24, 24]} />
            <meshStandardMaterial color={skinColor} roughness={0.55} />
          </mesh>

          {/* Sculpted Jawline & Chin */}
          <mesh position={[0, 0.04, -0.06]} rotation={[0.32, 0, 0]} castShadow>
            <boxGeometry args={[0.13, 0.1, 0.14]} />
            <meshStandardMaterial color={skinColor} roughness={0.55} />
          </mesh>

          {/* Nose Bridge */}
          <mesh position={[0, 0.09, -0.16]} rotation={[0.15, 0, 0]}>
            <coneGeometry args={[0.022, 0.055, 12]} />
            <meshStandardMaterial color={skinColor} roughness={0.55} />
          </mesh>

          {/* Ear Structures */}
          <mesh position={[-0.155, 0.1, 0]} rotation={[0, 0, 0.15]}>
            <sphereGeometry args={[0.035, 10, 10]} />
            <meshStandardMaterial color={skinColor} roughness={0.55} />
          </mesh>
          <mesh position={[0.155, 0.1, 0]} rotation={[0, 0, -0.15]}>
            <sphereGeometry args={[0.035, 10, 10]} />
            <meshStandardMaterial color={skinColor} roughness={0.55} />
          </mesh>

          {/* High-Fidelity Layered Hair */}
          <group position={[0, 0.17, 0.01]}>
            {/* Base Hair Volume */}
            <mesh castShadow>
              <sphereGeometry args={[0.175, 24, 24]} />
              <meshStandardMaterial color={hairColor} roughness={0.85} />
            </mesh>
            {/* Top Volumetric Sweep */}
            <mesh position={[0, 0.05, 0.02]} rotation={[-0.1, 0.1, 0]} castShadow>
              <boxGeometry args={[0.22, 0.08, 0.22]} />
              <meshStandardMaterial color={hairColor} roughness={0.85} />
            </mesh>
            {/* Front Textured Bangs Sweeping Across Forehead */}
            <mesh position={[-0.02, 0.04, -0.12]} rotation={[0.42, 0.12, -0.1]}>
              <boxGeometry args={[0.18, 0.06, 0.12]} />
              <meshStandardMaterial color={hairColor} roughness={0.85} />
            </mesh>
            {/* Sideburns */}
            <mesh position={[-0.155, -0.04, -0.06]}>
              <boxGeometry args={[0.02, 0.08, 0.04]} />
              <meshStandardMaterial color={hairColor} roughness={0.85} />
            </mesh>
            <mesh position={[0.155, -0.04, -0.06]}>
              <boxGeometry args={[0.02, 0.08, 0.04]} />
              <meshStandardMaterial color={hairColor} roughness={0.85} />
            </mesh>
          </group>

          {/* Titanium Wireframe Study Glasses with Translucent Lenses */}
          <group position={[0, 0.105, -0.16]}>
            {/* Left Rim */}
            <mesh position={[-0.062, 0, 0]}>
              <torusGeometry args={[0.042, 0.007, 10, 24]} />
              <meshStandardMaterial color="#d97706" metalness={0.9} roughness={0.15} />
            </mesh>
            {/* Left Lens */}
            <mesh position={[-0.062, 0, 0]}>
              <circleGeometry args={[0.038, 20]} />
              <meshStandardMaterial
                color="#bae6fd"
                transparent
                opacity={0.3}
                roughness={0.1}
                metalness={0.8}
                side={THREE.DoubleSide}
              />
            </mesh>

            {/* Right Rim */}
            <mesh position={[0.062, 0, 0]}>
              <torusGeometry args={[0.042, 0.007, 10, 24]} />
              <meshStandardMaterial color="#d97706" metalness={0.9} roughness={0.15} />
            </mesh>
            {/* Right Lens */}
            <mesh position={[0.062, 0, 0]}>
              <circleGeometry args={[0.038, 20]} />
              <meshStandardMaterial
                color="#bae6fd"
                transparent
                opacity={0.3}
                roughness={0.1}
                metalness={0.8}
                side={THREE.DoubleSide}
              />
            </mesh>

            {/* Bridge */}
            <mesh position={[0, 0.01, 0]}>
              <boxGeometry args={[0.04, 0.006, 0.006]} />
              <meshStandardMaterial color="#d97706" metalness={0.9} roughness={0.15} />
            </mesh>
            {/* Left Temple */}
            <mesh position={[-0.105, 0.01, 0.08]} rotation={[0, -0.1, 0]}>
              <boxGeometry args={[0.006, 0.006, 0.16]} />
              <meshStandardMaterial color="#d97706" metalness={0.9} roughness={0.15} />
            </mesh>
            {/* Right Temple */}
            <mesh position={[0.105, 0.01, 0.08]} rotation={[0, 0.1, 0]}>
              <boxGeometry args={[0.006, 0.006, 0.16]} />
              <meshStandardMaterial color="#d97706" metalness={0.9} roughness={0.15} />
            </mesh>
          </group>

          {/* Pro Studio Over-Ear Headphones */}
          <group position={[0, 0.13, 0]}>
            {/* Arched Padded Headband */}
            <mesh rotation={[0, 0, Math.PI / 2]}>
              <torusGeometry args={[0.195, 0.018, 12, 24, Math.PI]} />
              <meshStandardMaterial color="#0f172a" metalness={0.7} roughness={0.3} />
            </mesh>
            {/* Top Leatherette Cushion */}
            <mesh position={[0, 0.19, 0]}>
              <boxGeometry args={[0.18, 0.02, 0.045]} />
              <meshStandardMaterial color="#1e293b" roughness={0.6} />
            </mesh>

            {/* Left Earcup with Memory Foam Cushion */}
            <group position={[-0.19, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
              {/* Outer Housing */}
              <mesh>
                <cylinderGeometry args={[0.075, 0.075, 0.04, 24]} />
                <meshStandardMaterial color="#0284c7" metalness={0.5} roughness={0.3} />
              </mesh>
              {/* Leather Cushion Ring */}
              <mesh position={[0, -0.025, 0]}>
                <torusGeometry args={[0.06, 0.016, 12, 24]} />
                <meshStandardMaterial color="#0f172a" roughness={0.7} />
              </mesh>
              {/* Glowing Accent Ring LED */}
              <mesh position={[0, 0.022, 0]}>
                <torusGeometry args={[0.052, 0.007, 8, 20]} />
                <meshStandardMaterial
                  color="#38bdf8"
                  emissive="#38bdf8"
                  emissiveIntensity={1.2}
                />
              </mesh>
            </group>

            {/* Right Earcup with Memory Foam Cushion */}
            <group position={[0.19, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
              {/* Outer Housing */}
              <mesh>
                <cylinderGeometry args={[0.075, 0.075, 0.04, 24]} />
                <meshStandardMaterial color="#0284c7" metalness={0.5} roughness={0.3} />
              </mesh>
              {/* Leather Cushion Ring */}
              <mesh position={[0, -0.025, 0]}>
                <torusGeometry args={[0.06, 0.016, 12, 24]} />
                <meshStandardMaterial color="#0f172a" roughness={0.7} />
              </mesh>
              {/* Glowing Accent Ring LED */}
              <mesh position={[0, 0.022, 0]}>
                <torusGeometry args={[0.052, 0.007, 8, 20]} />
                <meshStandardMaterial
                  color="#38bdf8"
                  emissive="#38bdf8"
                  emissiveIntensity={1.2}
                />
              </mesh>
            </group>
          </group>
        </group>
      </group>
    </group>
  );
}

/** Articulated Study Table Lamp with Focused Warm Beam */
function TableLamp({ dark }) {
  const lampColor = dark ? '#f59e0b' : '#d97706';

  return (
    <group position={[-1.15, -0.24, -0.15]} rotation={[0, 0.4, 0]}>
      {/* Heavy Circular Base */}
      <mesh castShadow>
        <cylinderGeometry args={[0.14, 0.16, 0.04, 24]} />
        <meshStandardMaterial color="#0f172a" metalness={0.8} roughness={0.2} />
      </mesh>

      {/* Lower Arm angled up-back */}
      <group position={[0, 0.02, 0]} rotation={[0.4, 0, 0]}>
        <mesh position={[0, 0.22, 0]}>
          <cylinderGeometry args={[0.016, 0.016, 0.44, 12]} />
          <meshStandardMaterial color="#475569" metalness={0.9} roughness={0.15} />
        </mesh>
        {/* Elbow Joint Knob */}
        <mesh position={[0, 0.44, 0]}>
          <sphereGeometry args={[0.035, 12, 12]} />
          <meshStandardMaterial color={lampColor} metalness={0.7} roughness={0.2} />
        </mesh>

        {/* Upper Arm angled down-forward towards book */}
        <group position={[0, 0.44, 0]} rotation={[-1.1, 0, 0]}>
          <mesh position={[0, 0.22, 0]}>
            <cylinderGeometry args={[0.016, 0.016, 0.46, 12]} />
            <meshStandardMaterial color="#475569" metalness={0.9} roughness={0.15} />
          </mesh>
          {/* Head Joint */}
          <mesh position={[0, 0.46, 0]}>
            <sphereGeometry args={[0.032, 12, 12]} />
            <meshStandardMaterial color={lampColor} metalness={0.7} />
          </mesh>

          {/* Conical Lampshade pointing down at book */}
          <group position={[0, 0.46, 0]} rotation={[0.4, 0, 0]}>
            <mesh position={[0, 0.08, 0]} castShadow>
              <coneGeometry args={[0.15, 0.2, 20, 1, true]} />
              <meshStandardMaterial
                color="#0f172a"
                side={THREE.DoubleSide}
                metalness={0.8}
                roughness={0.25}
              />
            </mesh>

            {/* Glowing Internal Light Bulb */}
            <mesh position={[0, 0.03, 0]}>
              <sphereGeometry args={[0.045, 16, 16]} />
              <meshStandardMaterial
                color="#fef08a"
                emissive="#fbbf24"
                emissiveIntensity={2.5}
              />
            </mesh>

            {/* Realistic Focused Desk Lamp Light Beam */}
            <pointLight
              position={[0, -0.05, 0]}
              intensity={dark ? 3.4 : 2.2}
              color="#fbbf24"
              distance={4.2}
              decay={1.6}
            />
          </group>
        </group>
      </group>
    </group>
  );
}

/** Desktop Setup: Slim Monitor, Backlit Keyboard, Mouse & Mat */
function DesktopSetup({ dark }) {
  return (
    <group position={[0.75, -0.24, -0.15]} rotation={[0, -0.32, 0]}>
      {/* Large Extended Desk Mat */}
      <mesh position={[0, 0.005, 0.42]}>
        <boxGeometry args={[1.65, 0.008, 0.72]} />
        <meshStandardMaterial
          color={dark ? '#09090b' : '#475569'}
          roughness={0.85}
        />
      </mesh>

      {/* Monitor Metallic Stand Base */}
      <mesh position={[0, 0.015, 0]}>
        <boxGeometry args={[0.34, 0.015, 0.22]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.9} roughness={0.15} />
      </mesh>
      {/* Stand Neck */}
      <mesh position={[0, 0.24, -0.04]} rotation={[-0.08, 0, 0]}>
        <boxGeometry args={[0.08, 0.45, 0.04]} />
        <meshStandardMaterial color="#64748b" metalness={0.85} roughness={0.2} />
      </mesh>

      {/* Ultra-Slim Widescreen Monitor */}
      <group position={[0, 0.44, 0]}>
        {/* Monitor Frame & Back Housing */}
        <mesh castShadow>
          <boxGeometry args={[1.42, 0.82, 0.035]} />
          <meshStandardMaterial color="#0f172a" metalness={0.7} roughness={0.3} />
        </mesh>
        {/* Glowing Display Screen (MentorOS IDE & Knowledge Analytics) */}
        <mesh position={[0, 0, 0.019]}>
          <planeGeometry args={[1.36, 0.76]} />
          <meshStandardMaterial
            color="#0284c7"
            emissive="#0284c7"
            emissiveIntensity={dark ? 0.75 : 0.45}
            roughness={0.2}
          />
        </mesh>
        {/* Screen Content Graphic Simulation (UI Panels & Code Lines) */}
        <ScreenContentGraphic />

        {/* Dynamic Cool Screen Light illuminating desk & student */}
        <pointLight
          position={[0, 0, 0.25]}
          intensity={dark ? 1.4 : 0.8}
          color="#38bdf8"
          distance={3}
          decay={1.8}
        />
      </group>

      {/* Backlit Mechanical Keyboard */}
      <group position={[-0.05, 0.02, 0.38]}>
        {/* Keyboard Chassis */}
        <mesh>
          <boxGeometry args={[0.68, 0.022, 0.24]} />
          <meshStandardMaterial color="#1e293b" metalness={0.5} roughness={0.5} />
        </mesh>
        {/* Glowing Keycaps Bed */}
        <mesh position={[0, 0.015, 0]}>
          <boxGeometry args={[0.64, 0.015, 0.21]} />
          <meshStandardMaterial
            color="#0ea5e9"
            emissive="#0ea5e9"
            emissiveIntensity={0.35}
            roughness={0.4}
          />
        </mesh>
      </group>

      {/* Ergonomic Wireless Mouse */}
      <mesh position={[0.48, 0.025, 0.42]}>
        <boxGeometry args={[0.1, 0.035, 0.16]} />
        <meshStandardMaterial color="#0f172a" roughness={0.4} metalness={0.3} />
      </mesh>
    </group>
  );
}

/** Simulated Screen UI (IDE lines, learning charts) */
function ScreenContentGraphic() {
  const lines = useMemo(() => [
    { y: 0.24, x: -0.3, w: 0.5, c: '#7dd3fc' },
    { y: 0.16, x: -0.22, w: 0.65, c: '#38bdf8' },
    { y: 0.08, x: -0.35, w: 0.4, c: '#a78bfa' },
    { y: 0.0, x: -0.15, w: 0.78, c: '#34d399' },
    { y: -0.08, x: -0.28, w: 0.55, c: '#f472b6' },
    { y: -0.16, x: -0.2, w: 0.68, c: '#7dd3fc' },
    { y: -0.24, x: -0.32, w: 0.45, c: '#38bdf8' },
  ], []);

  return (
    <group position={[0, 0, 0.021]}>
      {/* Sidebar Panel on Screen */}
      <mesh position={[-0.52, 0, 0]}>
        <planeGeometry args={[0.26, 0.72]} />
        <meshBasicMaterial color="#082f49" />
      </mesh>
      {/* Code / Text Lines */}
      {lines.map((l, i) => (
        <mesh key={i} position={[l.x, l.y, 0]}>
          <planeGeometry args={[l.w, 0.028]} />
          <meshBasicMaterial color={l.c} />
        </mesh>
      ))}
      {/* Mini Radar / Knowledge Chart on right of screen */}
      <mesh position={[0.42, 0.08, 0]}>
        <planeGeometry args={[0.36, 0.36]} />
        <meshBasicMaterial color="#0369a1" />
      </mesh>
    </group>
  );
}

/** Realistic Compact Open Study Book with Smooth Curved 1-Second Turning Pages */
function OpenStudyBook({ pageFlipRef, pageCurlRef, dark }) {
  // Realistic compact study textbook dimensions (~6" x 9" scale)
  const PAGE_W = 0.28;
  const PAGE_H = 0.38;
  const HALF_W = PAGE_W / 2;

  return (
    <group position={[-0.22, -0.23, 0.36]} rotation={[0.06, 0.18, 0]}>
      {/* Hardcover Leather / Linen Bound Outer Casing */}
      <mesh position={[0, -0.018, 0]} castShadow receiveShadow>
        <boxGeometry args={[PAGE_W * 2 + 0.05, 0.024, PAGE_H + 0.04]} />
        <meshStandardMaterial
          color={dark ? '#0f172a' : '#1e293b'}
          roughness={0.65}
          metalness={0.2}
        />
      </mesh>

      {/* Gold-Embossed Spine Ribs */}
      <group position={[0, -0.005, 0]}>
        <mesh>
          <boxGeometry args={[0.035, 0.028, PAGE_H + 0.04]} />
          <meshStandardMaterial color="#f59e0b" metalness={0.8} roughness={0.2} />
        </mesh>
      </group>

      {/* Left Static Page Block with fine paper bevel */}
      <group position={[-PAGE_W / 2 - 0.008, 0, 0]} rotation={[0, 0, 0.025]}>
        {/* Paper stack */}
        <mesh castShadow receiveShadow>
          <boxGeometry args={[PAGE_W, 0.026, PAGE_H]} />
          <meshStandardMaterial color="#faf8f5" roughness={0.8} />
        </mesh>
        {/* Gold header / page lines */}
        <BookPageLines width={PAGE_W} height={PAGE_H} isLeft />
      </group>

      {/* Right Static Page Block */}
      <group position={[PAGE_W / 2 + 0.008, 0, 0]} rotation={[0, 0, -0.025]}>
        {/* Paper stack */}
        <mesh castShadow receiveShadow>
          <boxGeometry args={[PAGE_W, 0.026, PAGE_H]} />
          <meshStandardMaterial color="#faf8f5" roughness={0.8} />
        </mesh>
        {/* Inscribed study notes lines */}
        <BookPageLines width={PAGE_W} height={PAGE_H} isLeft={false} />
      </group>

      {/* Two-Segment Dynamic Curved Turning Page Pivot across Spine */}
      <group ref={pageFlipRef} position={[0, 0.016, 0]}>
        {/* Inner page segment (Spine to Mid) */}
        <group position={[HALF_W / 2, 0, 0]}>
          <mesh castShadow>
            <boxGeometry args={[HALF_W, 0.003, PAGE_H]} />
            <meshStandardMaterial
              color="#fffbeb"
              roughness={0.7}
              side={THREE.DoubleSide}
            />
          </mesh>
        </group>

        {/* Outer page segment with dynamic bend curl (Mid to Edge) */}
        <group ref={pageCurlRef} position={[HALF_W, 0, 0]}>
          <group position={[HALF_W / 2, 0, 0]}>
            <mesh castShadow>
              <boxGeometry args={[HALF_W, 0.003, PAGE_H]} />
              <meshStandardMaterial
                color="#fffdf0"
                roughness={0.7}
                side={THREE.DoubleSide}
              />
            </mesh>
            {/* Turning page inscribed notes */}
            <BookPageLines width={HALF_W * 1.8} height={PAGE_H} isLeft={false} />
          </group>
        </group>
      </group>

      {/* Silk Satin Bookmark Ribbon */}
      <mesh position={[0, 0.012, PAGE_H / 2 + 0.06]} rotation={[0.45, 0, 0]}>
        <boxGeometry args={[0.02, 0.004, 0.16]} />
        <meshStandardMaterial color="#0ea5e9" roughness={0.3} metalness={0.4} />
      </mesh>
    </group>
  );
}

/** Inscribed Study Notes Lines on Realistic Book Pages */
function BookPageLines({ width, height, isLeft }) {
  const lines = useMemo(() => [
    { y: height * 0.32, w: width * 0.45, c: '#0ea5e9', h: 0.014 }, // Chapter Header
    { y: height * 0.22, w: width * 0.82, c: '#64748b', h: 0.008 },
    { y: height * 0.14, w: width * 0.78, c: '#94a3b8', h: 0.008 },
    { y: height * 0.06, w: width * 0.85, c: '#94a3b8', h: 0.008 },
    { y: -height * 0.02, w: width * 0.72, c: '#64748b', h: 0.008 },
    { y: -height * 0.10, w: width * 0.80, c: '#94a3b8', h: 0.008 },
    { y: -height * 0.18, w: width * 0.65, c: '#0ea5e9', h: 0.008 },
    { y: -height * 0.26, w: width * 0.75, c: '#94a3b8', h: 0.008 },
  ], [width, height]);

  return (
    <group position={[0, 0.014, 0]}>
      {lines.map((l, i) => (
        <mesh
          key={i}
          position={[isLeft ? -width * 0.04 : width * 0.04, 0, l.y]}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          <planeGeometry args={[l.w, l.h]} />
          <meshBasicMaterial color={l.c} />
        </mesh>
      ))}
    </group>
  );
}

/** Stack of Closed Study Textbooks on the Desk */
function CompanionBookStack({ dark }) {
  return (
    <group position={[0.62, -0.23, 0.42]} rotation={[0, -0.18, 0]}>
      {/* Bottom Textbook: Deep Navy Blue */}
      <group position={[0, 0, 0]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[0.34, 0.045, 0.46]} />
          <meshStandardMaterial
            color={dark ? '#1e1b4b' : '#1e293b'}
            roughness={0.6}
            metalness={0.2}
          />
        </mesh>
        {/* Gold spine title bar */}
        <mesh position={[-0.171, 0, 0]}>
          <planeGeometry args={[0.01, 0.38]} />
          <meshBasicMaterial color="#f59e0b" />
        </mesh>
      </group>

      {/* Middle Textbook: Deep Emerald Green */}
      <group position={[0.015, 0.042, 0.01]} rotation={[0, 0.08, 0]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[0.32, 0.04, 0.44]} />
          <meshStandardMaterial
            color={dark ? '#064e3b' : '#047857'}
            roughness={0.6}
            metalness={0.2}
          />
        </mesh>
        <mesh position={[-0.161, 0, 0]}>
          <planeGeometry args={[0.01, 0.36]} />
          <meshBasicMaterial color="#f59e0b" />
        </mesh>
      </group>

      {/* Top Textbook: Warm Terracotta / Amber */}
      <group position={[-0.01, 0.082, -0.01]} rotation={[0, -0.06, 0]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[0.3, 0.038, 0.42]} />
          <meshStandardMaterial
            color={dark ? '#7c2d12' : '#c2410c'}
            roughness={0.6}
            metalness={0.2}
          />
        </mesh>
        <mesh position={[-0.151, 0, 0]}>
          <planeGeometry args={[0.01, 0.34]} />
          <meshBasicMaterial color="#fcd34d" />
        </mesh>
      </group>
    </group>
  );
}

/** Desk Accessories: Steaming Coffee Mug, Succulent Plant, Pen Cup */
function DeskAccessories({ steamRef, dark }) {
  return (
    <group>
      {/* Ceramic Coffee Mug */}
      <group position={[-0.68, -0.2, 0.52]}>
        {/* Mug Body */}
        <mesh castShadow>
          <cylinderGeometry args={[0.07, 0.06, 0.13, 20]} />
          <meshStandardMaterial
            color={dark ? '#f8fafc' : '#0284c7'}
            roughness={0.25}
          />
        </mesh>
        {/* Mug Handle */}
        <mesh position={[-0.08, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
          <torusGeometry args={[0.04, 0.012, 10, 16]} />
          <meshStandardMaterial color={dark ? '#f8fafc' : '#0284c7'} />
        </mesh>
        {/* Coffee Liquid */}
        <mesh position={[0, 0.05, 0]}>
          <cylinderGeometry args={[0.062, 0.062, 0.01, 16]} />
          <meshStandardMaterial color="#451a03" roughness={0.3} />
        </mesh>
        {/* Rising Steam Wisp */}
        <mesh ref={steamRef} position={[0, 0.12, 0]}>
          <sphereGeometry args={[0.035, 12, 12]} />
          <meshStandardMaterial
            color="#ffffff"
            transparent
            opacity={0.35}
            roughness={1}
          />
        </mesh>
      </group>

      {/* Modern Faceted Succulent Plant */}
      <group position={[1.35, -0.19, 0.25]}>
        {/* Geometric Pot */}
        <mesh castShadow>
          <cylinderGeometry args={[0.09, 0.065, 0.14, 6]} />
          <meshStandardMaterial
            color="#f8fafc"
            roughness={0.3}
            metalness={0.1}
          />
        </mesh>
        {/* Soil */}
        <mesh position={[0, 0.065, 0]}>
          <cylinderGeometry args={[0.08, 0.08, 0.01, 12]} />
          <meshStandardMaterial color="#292524" roughness={0.9} />
        </mesh>
        {/* Succulent Leaves */}
        {[0, 1, 2, 3, 4].map((i) => {
          const a = (i * Math.PI * 2) / 5;
          return (
            <mesh
              key={i}
              position={[Math.sin(a) * 0.04, 0.1, Math.cos(a) * 0.04]}
              rotation={[0.35, a, 0]}
            >
              <sphereGeometry args={[0.035, 8, 8]} />
              <meshStandardMaterial color="#10b981" roughness={0.6} />
            </mesh>
          );
        })}
      </group>

      {/* Stationery Pen Cup */}
      <group position={[-1.25, -0.19, 0.35]}>
        {/* Wireframe / Ceramic Cup */}
        <mesh castShadow>
          <cylinderGeometry args={[0.065, 0.06, 0.15, 16, 1, true]} />
          <meshStandardMaterial
            color="#334155"
            metalness={0.7}
            roughness={0.3}
            side={THREE.DoubleSide}
          />
        </mesh>
        <mesh position={[0, -0.07, 0]}>
          <cylinderGeometry args={[0.06, 0.06, 0.01, 16]} />
          <meshStandardMaterial color="#334155" metalness={0.7} />
        </mesh>
        {/* Colorful Study Pens & Pencils */}
        <mesh position={[-0.02, 0.05, 0]} rotation={[0.15, 0, 0.2]}>
          <cylinderGeometry args={[0.008, 0.008, 0.24, 8]} />
          <meshStandardMaterial color="#0ea5e9" metalness={0.5} />
        </mesh>
        <mesh position={[0.02, 0.06, 0.01]} rotation={[-0.2, 0, -0.15]}>
          <cylinderGeometry args={[0.008, 0.008, 0.26, 8]} />
          <meshStandardMaterial color="#f59e0b" metalness={0.5} />
        </mesh>
        <mesh position={[0, 0.04, -0.02]} rotation={[0.05, 0, -0.22]}>
          <cylinderGeometry args={[0.008, 0.008, 0.22, 8]} />
          <meshStandardMaterial color="#10b981" metalness={0.5} />
        </mesh>
      </group>
    </group>
  );
}

/** Ambient Floating Dust Motes in Light Cone */
function AmbientDustMotes({ count = 40, dark }) {
  const points = useMemo(() => {
    const p = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      // Cluster primarily around the desk lamp cone
      p[i * 3] = (Math.random() - 0.4) * 2.8;
      p[i * 3 + 1] = -0.4 + Math.random() * 1.6;
      p[i * 3 + 2] = (Math.random() - 0.2) * 2.2;
    }
    return p;
  }, [count]);

  const pointsRef = useRef();

  useFrame((state) => {
    if (!pointsRef.current) return;
    const t = state.clock.elapsedTime;
    const pos = pointsRef.current.geometry.attributes.position.array;
    for (let i = 0; i < count; i++) {
      pos[i * 3 + 1] += Math.sin(t * 0.8 + i) * 0.0015;
      pos[i * 3] += Math.cos(t * 0.5 + i) * 0.001;
    }
    pointsRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[points, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.03}
        color={dark ? '#fef08a' : '#38bdf8'}
        transparent
        opacity={dark ? 0.6 : 0.45}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

/** Error boundary to gracefully catch any WebGL rendering issues */
class SceneErrorBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed) return this.props.fallback;
    return this.props.children;
  }
}

/** WebGL Capability probe */
function useWebGLSupported() {
  return useMemo(() => {
    try {
      const canvas = document.createElement('canvas');
      return !!(
        window.WebGLRenderingContext &&
        (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
      );
    } catch {
      return false;
    }
  }, []);
}

/** Static CSS Fallback graphic — animated "MentorOS" typewriter wordmark.
 *  Shown instead of the 3D chamber (Motion Off or WebGL unavailable).
 *  The typing loop is JS-driven so it deliberately keeps playing even when
 *  the global motion-off kill-switch disables CSS animations. */
function StaticGradient() {
  return (
    <div
      className="w-full max-w-3xl h-72 sm:h-84 mb-4 rounded-3xl relative overflow-hidden flex items-center justify-center border border-border/60 shadow-sm animate-scene-in select-none"
      style={{
        background:
          'radial-gradient(ellipse at 50% 50%, rgba(14,165,233,0.16), rgba(251,191,36,0.07) 50%, transparent 75%)',
      }}
      aria-hidden="true"
    >
      <TypingWordmark text="MentorOS" />
    </div>
  );
}

/** Slow, looping type-then-backspace wordmark. */
function TypingWordmark({ text }) {
  const [count, setCount] = useState(0);
  const [phase, setPhase] = useState('type');

  useEffect(() => {
    let id;
    switch (phase) {
      case 'type':
        if (count < text.length) id = setTimeout(() => setCount((c) => c + 1), 160);
        else id = setTimeout(() => setPhase('hold'), 2400);
        break;
      case 'hold':
        id = setTimeout(() => setPhase('delete'), 350);
        break;
      case 'delete':
        if (count > 0) id = setTimeout(() => setCount((c) => c - 1), 75);
        else id = setTimeout(() => setPhase('idle'), 0);
        break;
      default:
        id = setTimeout(() => setPhase('type'), 1600);
        break;
    }
    return () => clearTimeout(id);
  }, [phase, count, text]);

  return (
    <div className="text-center px-6">
      <div className="inline-flex items-baseline">
        <span
          className="wordmark-shine font-display font-extrabold text-5xl sm:text-7xl tracking-tight leading-none bg-clip-text text-transparent"
          style={{
            backgroundImage:
              'linear-gradient(100deg, var(--color-accent) 0%, #38bdf8 35%, #818cf8 70%, #c084fc 100%)',
            filter: 'drop-shadow(0 0 18px rgba(14,165,233,0.35))',
          }}
        >
          {text.slice(0, count)}
        </span>
        <span className="wordmark-caret" />
      </div>
    </div>
  );
}
