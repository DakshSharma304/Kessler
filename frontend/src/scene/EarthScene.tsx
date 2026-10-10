import { Canvas } from '@react-three/fiber'
import { OrbitControls, Stars } from '@react-three/drei'
import { useMemo } from 'react'
import type { StateVector } from '../api/client'

const EARTH_RADIUS_M = 6_378_137

function scaled(position: [number, number, number]) {
  return [position[0] / EARTH_RADIUS_M, position[2] / EARTH_RADIUS_M, -position[1] / EARTH_RADIUS_M] as [number, number, number]
}

function CatalogPoints({ states }: { states: StateVector[] }) {
  const positions = useMemo(() => new Float32Array(states.flatMap(state => scaled(state.position_m))), [states])
  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color="#79dcff" size={0.035} sizeAttenuation />
    </points>
  )
}

function OrbitLine({ states }: { states: StateVector[] }) {
  const positions = useMemo(() => new Float32Array(states.flatMap(state => scaled(state.position_m))), [states])
  if (states.length < 2) return null
  return (
    <line>
      <bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry>
      <lineBasicMaterial color="#f3bd74" transparent opacity={0.8} />
    </line>
  )
}

export default function EarthScene({ states, trajectory }: { states: StateVector[]; trajectory: StateVector[] }) {
  if (typeof WebGLRenderingContext === 'undefined') return <div className="globe-fallback" role="img" aria-label="Interactive Earth visualization">3D globe available in WebGL browsers</div>
  return (
    <Canvas camera={{ position: [0, 0.5, 3.3], fov: 42 }} aria-label="Interactive Earth visualization">
      <ambientLight intensity={0.55} />
      <directionalLight position={[4, 2, 4]} intensity={2.2} />
      <mesh><sphereGeometry args={[1, 64, 64]} /><meshStandardMaterial color="#102b3a" roughness={0.7} metalness={0.1} /></mesh>
      <mesh><sphereGeometry args={[1.006, 36, 36]} /><meshBasicMaterial color="#4eb6db" wireframe transparent opacity={0.11} /></mesh>
      <CatalogPoints states={states} />
      <OrbitLine states={trajectory} />
      <Stars radius={80} depth={20} count={900} factor={1.5} fade speed={0.2} />
      <OrbitControls enablePan={false} minDistance={1.55} maxDistance={8} />
    </Canvas>
  )
}
