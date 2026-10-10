import { useQuery } from '@tanstack/react-query'
import { getEncounters } from '../api/client'
import { useKesslerStore } from '../state/store'

export default function Approaches({ openPlanner }: { openPlanner: () => void }) {
  const encounters = useQuery({ queryKey: ['encounters'], queryFn: getEncounters })
  const { selectedEncounterId, setSelectedEncounter } = useKesslerStore()
  return <section className="workspace page"><div className="page-heading"><p className="eyebrow">LIVE SCREENING</p><h1>Close Approaches</h1><p>Published SOCRATES candidates and separately labeled Kessler geometry.</p></div>
    {encounters.isError && <div className="notice error">SOCRATES data unavailable: {encounters.error.message}</div>}
    {encounters.data?.items.map(item => <article className={`result-card ${selectedEncounterId === item.encounter_id ? 'selected' : ''}`} key={item.encounter_id} onClick={() => setSelectedEncounter(item.encounter_id)}>
      <div><strong>{item.object_name_1}</strong><span> × </span><strong>{item.object_name_2}</strong></div>
      <div className="metrics"><span><small>TCA</small>{new Date(item.tca).toLocaleString()}</span><span><small>Separation</small>{item.separation_m.toFixed(0)} m</span><span><small>Relative speed</small>{(item.relative_speed_m_s / 1000).toFixed(2)} km/s</span><span><small>SOCRATES MAX_PROB</small>{item.socrates_max_probability?.toExponential(2) ?? 'Unavailable'}</span></div>
      <button onClick={openPlanner}>Open Avoidance Planner</button>
    </article>)}
    {!encounters.isPending && encounters.data?.items.length === 0 && <div className="empty large"><h2>No reported close approaches within available SOCRATES screening coverage.</h2><p>{encounters.data.coverage}</p></div>}
  </section>
}
