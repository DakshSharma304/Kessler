import { useQuery } from '@tanstack/react-query'
import { getMethods, getStatuses } from '../api/client'

export default function Methods() {
  const statuses = useQuery({ queryKey: ['statuses'], queryFn: getStatuses })
  const methods = useQuery({ queryKey: ['methods'], queryFn: getMethods })
  const models = (methods.data?.models ?? []) as Array<{ name: string; use: string; frame?: string }>
  const limitations = (methods.data?.limitations ?? []) as string[]
  return <section className="workspace page"><div className="page-heading"><p className="eyebrow">PROVENANCE & LIMITATIONS</p><h1>Data & Methods</h1><p>What is measured, published, calculated, assumed, and unavailable.</p></div>
    <div className="method-grid"><article className="panel"><h2>Source status</h2>{statuses.data?.map(item => <div className="source-row" key={item.name}><span className={`status-pill ${item.availability}`}>{item.availability}</span><div><strong>{item.name.toUpperCase()}</strong><small>{item.record_count} records · {item.parsing_status}</small>{item.error && <small>{item.error}</small>}<a href={item.source_url} target="_blank" rel="noreferrer">Source documentation ↗</a></div></div>)}</article><article className="panel"><h2>Scientific models</h2>{models.map(model => <div className="method" key={model.name}><strong>{model.name}</strong><p>{model.use}</p><small>{model.frame}</small></div>)}</article><article className="panel"><h2>Important limitations</h2><ul>{limitations.map(item => <li key={item}>{item}</li>)}</ul></article></div>
  </section>
}
