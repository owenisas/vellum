import { Canvas, useFrame } from "@react-three/fiber";
import { Suspense, useRef, useMemo } from "react";
import * as THREE from "three";

function ChainPolyhedron() {
  const wire = useRef<THREE.LineSegments>(null);
  const inner = useRef<THREE.Mesh>(null);
  const target = useRef({ x: 0, y: 0 });

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const pointer = state.pointer;
    target.current.x += ((pointer.x * 0.6) - target.current.x) * 0.06;
    target.current.y += ((pointer.y * 0.4) - target.current.y) * 0.06;
    if (wire.current) {
      wire.current.rotation.y = t * 0.18 + target.current.x * 0.6;
      wire.current.rotation.x = -0.18 + Math.sin(t * 0.27) * 0.06 + target.current.y * 0.4;
    }
    if (inner.current) {
      inner.current.rotation.y = -t * 0.07 + target.current.x * 0.3;
      inner.current.rotation.x = Math.cos(t * 0.21) * 0.04 + target.current.y * 0.2;
      const s = 1 + Math.sin(t * 0.6) * 0.012;
      inner.current.scale.setScalar(s);
    }
  });

  const wireGeom = useMemo(() => {
    const geom = new THREE.IcosahedronGeometry(2.4, 1);
    return new THREE.EdgesGeometry(geom);
  }, []);

  return (
    <group>
      <mesh ref={inner}>
        <icosahedronGeometry args={[2.35, 1]} />
        <meshStandardMaterial color="#0A0A0A" metalness={0.7} roughness={0.42} flatShading />
      </mesh>
      <lineSegments ref={wire} geometry={wireGeom}>
        <lineBasicMaterial color="#F2F1EA" transparent opacity={0.78} />
      </lineSegments>
      <Vertices />
    </group>
  );
}

function Vertices() {
  const geom = useMemo(() => new THREE.IcosahedronGeometry(2.42, 1), []);
  const positions = useMemo(() => {
    const arr: [number, number, number][] = [];
    const pos = geom.attributes.position;
    for (let i = 0; i < pos.count; i++) arr.push([pos.getX(i), pos.getY(i), pos.getZ(i)]);
    return arr;
  }, [geom]);
  const ref = useRef<THREE.Group>(null);
  useFrame((state) => {
    if (!ref.current) return;
    ref.current.rotation.y = state.clock.elapsedTime * 0.18 + state.pointer.x * 0.6;
    ref.current.rotation.x = -0.18 + Math.sin(state.clock.elapsedTime * 0.27) * 0.06 + state.pointer.y * 0.4;
  });
  return (
    <group ref={ref}>
      {positions.map((p, i) => (
        <mesh key={i} position={p}>
          <sphereGeometry args={[0.022, 8, 8]} />
          <meshBasicMaterial color={i % 5 === 0 ? "#00D26A" : "#F2F1EA"} />
        </mesh>
      ))}
    </group>
  );
}

function FloatingShards() {
  const ref = useRef<THREE.Group>(null);
  const items = useMemo(
    () => Array.from({ length: 18 }, (_, i) => ({
      seed: i,
      radius: 4.5 + Math.random() * 2.4,
      speed: 0.04 + Math.random() * 0.08,
      size: 0.06 + Math.random() * 0.18,
      phase: Math.random() * Math.PI * 2,
      tilt: Math.random() * Math.PI,
    })),
    [],
  );
  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.elapsedTime;
    ref.current.children.forEach((m, i) => {
      const it = items[i];
      const a = t * it.speed + it.phase;
      m.position.x = Math.cos(a) * it.radius;
      m.position.z = Math.sin(a) * it.radius;
      m.position.y = Math.sin(a * 1.3) * 0.6 - 0.2;
      m.rotation.x = a * 0.6;
      m.rotation.y = a * 0.9;
    });
  });
  return (
    <group ref={ref}>
      {items.map((it) => (
        <mesh key={it.seed} rotation-x={it.tilt}>
          <tetrahedronGeometry args={[it.size, 0]} />
          <meshStandardMaterial color="#F2F1EA" metalness={0.2} roughness={0.6} transparent opacity={0.4} />
        </mesh>
      ))}
    </group>
  );
}

export default function IcosahedronScene() {
  return (
    <Canvas
      camera={{ position: [0, 0, 7.2], fov: 35 }}
      dpr={[1, 1.6]}
      gl={{ antialias: true, alpha: true }}
      style={{ position: "absolute", inset: 0 }}
    >
      <Suspense fallback={null}>
        <ambientLight intensity={0.18} />
        <directionalLight position={[-4, 5, 4]} intensity={1.6} color="#FFFFFF" />
        <directionalLight position={[5, -2, -3]} intensity={0.8} color="#00D26A" />
        <pointLight position={[0, 0, 2]} intensity={0.4} color="#F2F1EA" />
        <ChainPolyhedron />
        <FloatingShards />
        <fog attach="fog" args={["#0A0A0A", 6, 14]} />
      </Suspense>
    </Canvas>
  );
}
