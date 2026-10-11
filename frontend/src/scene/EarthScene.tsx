import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Stars } from '@react-three/drei'
import { useCallback, useEffect, useMemo, useRef, useState, type RefObject } from 'react'
import { BufferAttribute, BufferGeometry, ShaderMaterial } from 'three'
import type { StateVector } from '../api/client'
import { EARTH_RADIUS_M, segmentAt, type AnimationWindow } from './interpolation'

function scaled(position: [number, number, number]) {
  return [position[0] / EARTH_RADIUS_M, position[2] / EARTH_RADIUS_M, -position[1] / EARTH_RADIUS_M] as [number, number, number]
}

function CatalogPoints({ animation, clock, onFps }: { animation: AnimationWindow; clock: RefObject<number>; onFps: (fps: number) => void }) {
  const segment = useRef(-1)
  const frames = useRef({ start: 0, count: 0 })
  const geometry = useMemo(() => {
    const value = new BufferGeometry()
    value.setAttribute('position', new BufferAttribute(animation.positions[0].slice(), 3))
    value.setAttribute('startVelocity', new BufferAttribute(animation.velocities[0].slice(), 3))
    value.setAttribute('endPosition', new BufferAttribute(animation.positions[1].slice(), 3))
    value.setAttribute('endVelocity', new BufferAttribute(animation.velocities[1].slice(), 3))
    return value
  }, [animation])
  const material = useMemo(() => new ShaderMaterial({
    uniforms: { fraction: { value: 0 }, duration: { value: 300 }, pointScale: { value: 1 } },
    vertexShader: `
      attribute vec3 startVelocity;
      attribute vec3 endPosition;
      attribute vec3 endVelocity;
      uniform float fraction;
      uniform float duration;
      uniform float pointScale;
      void main() {
        float u = fraction, u2 = u*u, u3 = u2*u;
        vec3 p = (2.0*u3-3.0*u2+1.0)*position + (u3-2.0*u2+u)*duration*startVelocity
          + (-2.0*u3+3.0*u2)*endPosition + (u3-u2)*duration*endVelocity;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = max(1.0, pointScale / max(0.01, -mv.z));
      }`,
    fragmentShader: `void main() {
      if (length(gl_PointCoord - vec2(0.5)) > 0.5) discard;
      gl_FragColor = vec4(0.4745, 0.8627, 1.0, 1.0);
    }`,
  }), [])
  useEffect(() => () => geometry.dispose(), [geometry])
  useEffect(() => () => material.dispose(), [material])
  useFrame(state => {
    const current = segmentAt(animation.times, clock.current)
    if (current.index !== segment.current) {
      segment.current = current.index
      // Reuse four GL buffers across segment changes; replacing BufferAttributes
      // repeatedly can orphan their old GL buffers until context destruction.
      const sources = [animation.positions[current.index], animation.velocities[current.index], animation.positions[current.index + 1], animation.velocities[current.index + 1]]
      const attributes = ['position', 'startVelocity', 'endPosition', 'endVelocity']
      attributes.forEach((name, index) => {
        const attribute = geometry.getAttribute(name) as BufferAttribute
        attribute.array.set(sources[index]); attribute.needsUpdate = true
      })
    }
    material.uniforms.fraction.value = current.fraction
    material.uniforms.duration.value = current.duration
    material.uniforms.pointScale.value = (animation.ids.length > 1000 ? .008 : .035) * state.size.height * state.gl.getPixelRatio() / 2
    const now = performance.now()
    if (!frames.current.start) frames.current.start = now
    frames.current.count++
    if (now - frames.current.start >= 1000) {
      onFps(frames.current.count * 1000 / (now - frames.current.start))
      frames.current = { start: now, count: 0 }
    }
  })
  return (
    <points geometry={geometry} material={material} frustumCulled={false} />
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

export default function EarthScene({ animation, clock, trajectory, onFps }: {
  animation?: AnimationWindow; clock: RefObject<number>; trajectory: StateVector[]; onFps: (fps: number) => void
}) {
  const [dpr, setDpr] = useState(1)
  const reportFps = useCallback((fps: number) => {
    onFps(fps)
    // Bound fill cost on high-DPI/software GPUs. Resolution is reduced only when
    // the measured renderer cannot sustain the target; orbital sampling is unchanged.
    if (fps < 22) setDpr(value => Math.max(.5, value - .15))
  }, [onFps])
  if (typeof WebGLRenderingContext === 'undefined') return <div className="globe-fallback" role="img" aria-label="Interactive Earth visualization">3D globe available in WebGL browsers</div>
  return (
    <Canvas dpr={dpr} camera={{ position: [0, 0.5, 3.3], fov: 42 }} aria-label="Interactive Earth visualization">
      <ambientLight intensity={0.55} />
      <directionalLight position={[4, 2, 4]} intensity={2.2} />
      <mesh><sphereGeometry args={[1, 48, 48]} /><meshLambertMaterial color="#102b3a" /></mesh>
      <mesh><sphereGeometry args={[1.006, 24, 24]} /><meshBasicMaterial color="#4eb6db" wireframe transparent opacity={0.11} /></mesh>
      {animation && <CatalogPoints animation={animation} clock={clock} onFps={reportFps} />}
      <OrbitLine states={trajectory} />
      <Stars radius={80} depth={20} count={900} factor={1.5} fade speed={0.2} />
      <OrbitControls enablePan={false} minDistance={1.55} maxDistance={8} />
    </Canvas>
  )
}
