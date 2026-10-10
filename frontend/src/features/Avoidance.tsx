import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type StateVector } from '../api/client'

type Reference = { id: string; participants: string[]; published_probability: number; calculated_probability: number; states: [StateVector, StateVector]; mode: string }
type Job = { status: string; progress: number; current_stage: string; error?: string; result?: { status: string; evaluated_candidates: number; solutions: Array<Record<string, number | string | string[]>>; warnings: string[] } }

async function waitForJob(id: string): Promise<Job> {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const job = await api<Job>(`/api/jobs/${id}`)
    if (job.status === 'complete' || job.status === 'failed') return job
    await new Promise(resolve => window.setTimeout(resolve, 250))
  }
  throw new Error('Optimization exceeded the browser wait budget')
}

export default function Avoidance() {
  const references = useQuery({ queryKey: ['references'], queryFn: () => api<Reference[]>('/api/reference-encounters') })
  const [maxDv, setMaxDv] = useState(0.5)
  const [minimumSeparation, setMinimumSeparation] = useState(500)
  const [job, setJob] = useState<Job>()
  const [error, setError] = useState('')
  const [running, setRunning] = useState(false)
  const run = async () => {
    const reference = references.data?.[0]
    if (!reference) { setError('Historical covariance reference is unavailable.'); return }
    setRunning(true); setError(''); setJob({ status: 'queued', progress: 0, current_stage: 'queued' })
    try {
      const submitted = await api<{ job_id: string }>('/api/maneuvers/optimize', { method: 'POST', body: JSON.stringify({
        state_1: reference.states[0], state_2: reference.states[1],
        constraints: { max_delta_v_m_s: maxDv, warning_time_seconds: 86400, earliest_burn_seconds_before_tca: 3600, latest_burn_seconds_before_tca: 21600, minimum_separation_m: minimumSeparation, allowed_directions: ['radial', 'along_track', 'normal'], candidate_count: 18 },
      }) })
      const complete = await waitForJob(submitted.job_id)
      setJob(complete)
      if (complete.error) setError(complete.error)
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) }
    finally { setRunning(false) }
  }
  return <section className="workspace page"><div className="page-heading"><p className="eyebrow">HYPOTHETICAL INTERVENTION</p><h1>Avoidance Planner</h1><p>Dynamic Earth gravity + J2 propagation using the archived NASA CARA Terra / Iridium-33-debris validation state. No historical maneuver is implied.</p></div>
    <div className="planner-grid"><div className="control-card"><label>Maximum Δv <strong>{maxDv.toFixed(2)} m/s</strong><input type="range" min="0.05" max="2" step="0.05" value={maxDv} onChange={e => setMaxDv(Number(e.target.value))} /></label><label>Minimum nominal separation <strong>{minimumSeparation} m</strong><input type="range" min="100" max="5000" step="100" value={minimumSeparation} onChange={e => setMinimumSeparation(Number(e.target.value))} /></label><button className="primary" disabled={running || references.isPending} onClick={run}>{running ? `Computing · ${job?.current_stage ?? 'starting'}` : 'Find Best Maneuvers'}</button><p className="fine-print">Probability is not optimized because covariance propagation after a maneuver is not implemented. Results use nominal clearance and remain UNSCREENED against third objects.</p>{error && <div className="notice error">{error}</div>}</div>
    <div className="results"><h2>Candidate tradeoffs</h2>{!job?.result && <div className="empty">Configure constraints and run a fresh calculation.</div>}{job?.result && <><p>{job.result.evaluated_candidates} candidates numerically propagated · {job.result.status.replaceAll('_', ' ')}</p>{job.result.solutions.map((solution, index) => <article className="solution" key={index}><strong>Solution {index + 1}</strong><span>Δv {Number(solution.delta_v_magnitude_m_s).toFixed(3)} m/s</span><span>Clearance {Number(solution.modified_separation_m).toFixed(0)} m</span><span>Burn lead {Math.round(Number(solution.burn_seconds_before_tca) / 3600)} h</span><span className="status-pill warning">UNSCREENED</span></article>)}{job.result.warnings.map(item => <p className="fine-print" key={item}>{item}</p>)}</>}</div></div>
  </section>
}
