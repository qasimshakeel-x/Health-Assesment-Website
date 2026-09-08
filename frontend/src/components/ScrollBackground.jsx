import React, { useRef, useMemo, useEffect, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

// ── Color palette that shifts with scroll ──
function getScrollColor(t) {
  // t = 0..1 normalized scroll position
  // Cycle through: deep green → teal → emerald → soft blue → deep green
  const colors = [
    { r: 0.18, g: 0.49, b: 0.20 },  // #2E7D32 primary green
    { r: 0.00, g: 0.59, b: 0.53 },  // teal
    { r: 0.40, g: 0.73, b: 0.42 },  // #66BB6A bright green
    { r: 0.20, g: 0.47, b: 0.65 },  // muted blue
    { r: 0.51, g: 0.78, b: 0.52 },  // #81C784 light green
  ];
  const idx = t * (colors.length - 1);
  const i = Math.floor(idx);
  const f = idx - i;
  const c1 = colors[Math.min(i, colors.length - 1)];
  const c2 = colors[Math.min(i + 1, colors.length - 1)];
  return {
    r: c1.r + (c2.r - c1.r) * f,
    g: c1.g + (c2.g - c1.g) * f,
    b: c1.b + (c2.b - c1.b) * f,
  };
}

// ── Floating Particles ──
function Particles({ count = 250, scrollProgress }) {
  const mesh = useRef();

  const particles = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const speeds = new Float32Array(count);
    const phases = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 30;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 30;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 20;
      speeds[i] = Math.random() * 0.3 + 0.1;
      phases[i] = Math.random() * Math.PI * 2;
    }
    return { positions, speeds, phases };
  }, [count]);

  const materialRef = useRef();

  useFrame((state) => {
    if (!mesh.current) return;
    const time = state.clock.elapsedTime;
    const sp = scrollProgress.current;
    const positions = mesh.current.geometry.attributes.position.array;

    // Scroll-driven rotation
    mesh.current.rotation.y = sp * 1.2;
    mesh.current.rotation.x = sp * 0.4;

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      // Gentle upward drift
      positions[i3 + 1] += particles.speeds[i] * 0.005;
      // Scroll-responsive lateral sway
      positions[i3] += Math.sin(time * 0.3 + particles.phases[i] + sp * 2) * 0.003;
      positions[i3 + 2] += Math.cos(time * 0.2 + particles.phases[i] + sp * 1.5) * 0.002;
      // Wrap
      if (positions[i3 + 1] > 15) positions[i3 + 1] = -15;
    }
    mesh.current.geometry.attributes.position.needsUpdate = true;

    // Color shift
    const col = getScrollColor(sp);
    if (materialRef.current) {
      materialRef.current.color.setRGB(col.r, col.g, col.b);
    }
  });

  return (
    <points ref={mesh}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={particles.positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        ref={materialRef}
        size={0.06}
        color="#2E7D32"
        transparent
        opacity={0.6}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

// ── DNA Helix ──
function DNAHelix({ scrollProgress }) {
  const groupRef = useRef();
  const mat1Ref = useRef();
  const mat2Ref = useRef();

  const helixPoints = useMemo(() => {
    const points1 = [];
    const points2 = [];
    const count = 80;
    for (let i = 0; i < count; i++) {
      const t = (i / count) * Math.PI * 6;
      const y = (i / count) * 16 - 8;
      const radius = 2;
      points1.push(new THREE.Vector3(Math.cos(t) * radius, y, Math.sin(t) * radius));
      points2.push(new THREE.Vector3(Math.cos(t + Math.PI) * radius, y, Math.sin(t + Math.PI) * radius));
    }
    return { points1, points2 };
  }, []);

  const curve1 = useMemo(() => new THREE.CatmullRomCurve3(helixPoints.points1), [helixPoints]);
  const curve2 = useMemo(() => new THREE.CatmullRomCurve3(helixPoints.points2), [helixPoints]);

  const rungs = useMemo(() => {
    const result = [];
    helixPoints.points1.forEach((p, i) => {
      if (i % 4 !== 0) return;
      const p2 = helixPoints.points2[i];
      if (!p2) return;
      const mid = new THREE.Vector3().addVectors(p, p2).multiplyScalar(0.5);
      const dir = new THREE.Vector3().subVectors(p2, p);
      const len = dir.length();
      result.push({ mid, dir: dir.normalize(), len, key: i });
    });
    return result;
  }, [helixPoints]);

  useFrame((state) => {
    if (!groupRef.current) return;
    const time = state.clock.elapsedTime;
    const sp = scrollProgress.current;

    // Scroll-driven smooth rotation
    groupRef.current.rotation.y = time * 0.08 + sp * 2.0;
    // Gentle tilt on scroll
    groupRef.current.rotation.x = Math.sin(sp * 1.5) * 0.3;
    groupRef.current.rotation.z = Math.cos(sp * 1.2) * 0.15;

    // Color shift
    const col = getScrollColor(sp);
    if (mat1Ref.current) mat1Ref.current.color.setRGB(col.r, col.g, col.b);
    if (mat2Ref.current) mat2Ref.current.color.setRGB(col.r * 1.2, col.g * 1.1, col.b * 0.9);
  });

  return (
    <group ref={groupRef} position={[8, 0, -5]}>
      <mesh>
        <tubeGeometry args={[curve1, 100, 0.03, 8, false]} />
        <meshBasicMaterial ref={mat1Ref} color="#2E7D32" transparent opacity={0.35} />
      </mesh>
      <mesh>
        <tubeGeometry args={[curve2, 100, 0.03, 8, false]} />
        <meshBasicMaterial ref={mat2Ref} color="#66BB6A" transparent opacity={0.3} />
      </mesh>
      {rungs.map((r) => (
        <mesh key={r.key} position={r.mid} quaternion={new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), r.dir)}>
          <cylinderGeometry args={[0.015, 0.015, r.len, 4]} />
          <meshBasicMaterial color="#81C784" transparent opacity={0.15} />
        </mesh>
      ))}
    </group>
  );
}

// ── Floating Wireframe Orbs ──
function FloatingOrbs({ scrollProgress }) {
  const groupRef = useRef();
  const orbRefs = useRef([]);

  const orbs = useMemo(() => {
    return Array.from({ length: 12 }, (_, i) => ({
      position: [(Math.random() - 0.5) * 20, (Math.random() - 0.5) * 20, (Math.random() - 0.5) * 10 - 5],
      scale: Math.random() * 0.3 + 0.1,
      speed: Math.random() * 0.5 + 0.2,
      phase: Math.random() * Math.PI * 2,
    }));
  }, []);

  useFrame((state) => {
    if (!groupRef.current) return;
    const time = state.clock.elapsedTime;
    const sp = scrollProgress.current;

    // Whole group responds to scroll
    groupRef.current.rotation.y = sp * 0.8;
    groupRef.current.rotation.x = sp * 0.3;

    groupRef.current.children.forEach((child, i) => {
      const orb = orbs[i];
      // Gentle float
      child.position.y = orb.position[1] + Math.sin(time * orb.speed + orb.phase) * 0.8;
      child.position.x = orb.position[0] + Math.sin(time * 0.2 + orb.phase + sp) * 0.5;
      // Spin faster on scroll
      child.rotation.x = time * 0.1 + sp * 1.5;
      child.rotation.z = time * 0.15 + sp * 1.0;
      // Pulse scale on scroll
      const pulse = 1 + Math.sin(sp * 3 + orb.phase) * 0.15;
      child.scale.setScalar(orb.scale * pulse);
    });
  });

  return (
    <group ref={groupRef}>
      {orbs.map((orb, i) => (
        <mesh key={i} position={orb.position} scale={orb.scale} ref={(el) => (orbRefs.current[i] = el)}>
          <icosahedronGeometry args={[1, 1]} />
          <meshBasicMaterial
            color={i % 3 === 0 ? '#2E7D32' : i % 3 === 1 ? '#66BB6A' : '#81C784'}
            transparent
            opacity={0.12}
            wireframe
          />
        </mesh>
      ))}
    </group>
  );
}

// ── No camera zoom — camera stays fixed ──
function StaticCamera() {
  return null;
}

// ── Main Export ──
export default function ScrollBackground({ enabled = true }) {
  const scrollProgress = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    const handleScroll = () => {
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      scrollProgress.current = maxScroll > 0 ? window.scrollY / maxScroll : 0;
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [enabled]);

  if (!enabled) return null;

  return (
    <div className="three-canvas-container">
      <Canvas
        camera={{ position: [0, 0, 10], fov: 60 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
        style={{ background: 'transparent' }}
      >
        <color attach="background" args={['#0a0f1a']} />
        <ambientLight intensity={0.5} />
        <StaticCamera />
        <Particles count={250} scrollProgress={scrollProgress} />
        <DNAHelix scrollProgress={scrollProgress} />
        <FloatingOrbs scrollProgress={scrollProgress} />
      </Canvas>
    </div>
  );
}
