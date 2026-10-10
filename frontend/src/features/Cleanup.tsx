import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, getObjects } from '../api/client'

type Portfolio = { selected: Array<{ candidate: { object_id: string; name: string; effort: number }; marginal_benefit: number; reason: string }>; total_effort: number; remaining_budget: number; modeled_benefit: number; assumptions: string[] }

export default function Cleanup() {
  const objects = useQuery({ queryKey: ['objects'], queryFn: getObjects })
  const [budget, setBudget] = useState(2)
  const [priority, setPriority] = useState('balanced')
  const [result, setResult] = useState<Portfolio>()
  const [error, setError] = useState('')
  const optimize = async () => {
    setError('')
    const candidates = (objects.data?.items ?? []).map((item, index) => ({ object_id: item.catalog_id, name: item.name, effort: 1 + index % 3, persistence: Math.min(1, item.elements.mean_motion_rev_day / 16), exposure: 0.5, consequence: 0.3, data_quality: 'low' }))
    if (!candidates.length) { setError('No catalog objects are available for proxy assessment.'); return }
    try { setResult(await api<Portfolio>('/api/cleanup/optimize', { method: 'POST', body: JSON.stringify({ candidates, edges: [], budget, priority, max_objects: 20 }) })) }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) }
  }
  return <section className="workspace page"><div className="page-heading"><p className="eyebrow">LONG-TERM PORTFOLIO</p><h1>Cleanup Planner</h1><p>Budget-constrained, deterministic marginal-benefit selection. Scores are transparent model proxies, not mission costs or calibrated collision damages.</p></div>
    <div className="planner-grid"><div className="control-card"><label>Effort budget <strong>{budget}</strong><input type="range" min="1" max="20" value={budget} onChange={event => setBudget(Number(event.target.value))} /></label><label>Priority<select value={priority} onChange={event => setPriority(event.target.value)}><option value="balanced">Balanced</option><option value="persistence">Persistence</option><option value="exposure">Exposure</option><option value="consequence">Consequence</option></select></label><button className="primary" onClick={optimize}>Optimize cleanup portfolio</button>{error && <div className="notice error">{error}</div>}</div><div className="results"><h2>Selected portfolio</h2>{!result && <div className="empty">Run the optimizer to calculate a portfolio.</div>}{result?.selected.map(item => <article className="solution" key={item.candidate.object_id}><strong>{item.candidate.name}</strong><span>Effort {item.candidate.effort}</span><span>Marginal proxy benefit {item.marginal_benefit.toFixed(2)}</span><small>{item.reason}</small></article>)}{result && <p>Used {result.total_effort.toFixed(1)} · Remaining {result.remaining_budget.toFixed(1)}</p>}</div></div>
  </section>
}
