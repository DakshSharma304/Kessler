import { useQuery } from '@tanstack/react-query'
import { lazy, Suspense, useState } from 'react'
import { api } from './api/client'

const Approaches = lazy(() => import('./features/Approaches'))
const Avoidance = lazy(() => import('./features/Avoidance'))
const Cleanup = lazy(() => import('./features/Cleanup'))
const Explore = lazy(() => import('./features/Explore'))
const Methods = lazy(() => import('./features/Methods'))

export type Health = { status: string; version: string; datasets: { objects: number; encounters: number } }
type Section = 'Explore' | 'Close Approaches' | 'Avoidance Planner' | 'Cleanup Planner' | 'Data & Methods'

export async function fetchHealth(): Promise<Health> { return api<Health>('/api/health') }

export default function App() {
  const [section, setSection] = useState<Section>('Explore')
  const health = useQuery({ queryKey: ['health'], queryFn: fetchHealth, refetchInterval: 30_000 })
  const content = {
    Explore: <Explore />,
    'Close Approaches': <Approaches openPlanner={() => setSection('Avoidance Planner')} />,
    'Avoidance Planner': <Avoidance />,
    'Cleanup Planner': <Cleanup />,
    'Data & Methods': <Methods />,
  }[section]
  const sections = Object.keys({ Explore: 1, 'Close Approaches': 1, 'Avoidance Planner': 1, 'Cleanup Planner': 1, 'Data & Methods': 1 }) as Section[]
  return <main className="app-shell">
    <header className="topbar"><button className="brand" onClick={() => setSection('Explore')}><span className="mark">K</span><strong>KESSLER</strong></button><nav>{sections.map(item => <button key={item} className={section === item ? 'active' : ''} onClick={() => setSection(item)}>{item}</button>)}</nav><div className={`service-state ${health.isError ? 'error' : ''}`}><i />{health.isPending ? 'CONNECTING' : health.isError ? 'OFFLINE' : `${health.data.datasets.objects} OBJECTS`}</div></header>
    <Suspense fallback={<div className="empty large">Loading interface…</div>}>{content}</Suspense>
    <footer>Research prototype · Catalog data and modeled results carry explicit provenance · Not operational flight software</footer>
  </main>
}
