import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { getObjects, getPositions, getTrajectory } from '../api/client'
import EarthScene from '../scene/EarthScene'
import { useKesslerStore } from '../state/store'
import CatalogLoading from './CatalogLoading'

export default function Explore() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')
  const [time, setTime] = useState(new Date())
  const [playing, setPlaying] = useState(false)
  const [showOrbit, setShowOrbit] = useState(true)
  const [listLimit, setListLimit] = useState(100)
  const objects = useQuery({ queryKey: ['objects'], queryFn: getObjects })
  const { selectedObjectId, setSelectedObject } = useKesslerStore()
  useEffect(() => {
    if (objects.data?.items.length && !objects.data.items.some(item => item.catalog_id === selectedObjectId)) setSelectedObject(objects.data.items[0].catalog_id)
  }, [objects.data, selectedObjectId, setSelectedObject])
  useEffect(() => setListLimit(100), [search, category])
  useEffect(() => {
    if (!playing) return
    const timer = window.setInterval(() => setTime(value => new Date(value.getTime() + 60_000)), 1_000)
    return () => window.clearInterval(timer)
  }, [playing])
  const filtered = useMemo(() => (objects.data?.items ?? []).filter(item =>
    (category === 'all' || item.category === category) &&
    (item.name.toLowerCase().includes(search.toLowerCase()) || item.catalog_id.includes(search)),
  ), [objects.data, search, category])
  const selected = objects.data?.items?.find(item => item.catalog_id === selectedObjectId)
  const visibleIds = useMemo(() => filtered.slice(0, 20_000).map(item => item.catalog_id), [filtered])
  const positions = useQuery({
    queryKey: ['positions', objects.data?.catalog_version, visibleIds, time.toISOString().slice(0, 16)],
    queryFn: () => getPositions(visibleIds, time),
    enabled: Boolean(visibleIds.length),
  })
  const trajectory = useQuery({
    queryKey: ['trajectory', selectedObjectId, time.toISOString().slice(0, 16)],
    queryFn: () => getTrajectory(selectedObjectId!, time), enabled: Boolean(selectedObjectId && showOrbit),
  })
  return (
    <section className="workspace explore-grid">
      <div className="globe-panel">
        <EarthScene states={visibleIds.length ? positions.data?.states ?? [] : []} trajectory={showOrbit ? trajectory.data ?? [] : []} />
        <div className="time-controls">
          <button onClick={() => setPlaying(value => !value)}>{playing ? 'Pause' : 'Play'}</button>
          <span>{time.toISOString().replace('.000', '')}</span>
          <button onClick={() => setTime(new Date())}>Now</button>
          <button onClick={() => setShowOrbit(value => !value)}>{showOrbit ? 'Hide orbit' : 'Show orbit'}</button>
        </div>
      </div>
      <aside className="side-panel">
        <div><p className="eyebrow">EXPLORE</p><h1>Orbital catalog</h1></div>
        <CatalogLoading />
        <input aria-label="Search objects" placeholder="Search name or catalog ID" value={search} onChange={event => setSearch(event.target.value)} />
        <select aria-label="Object category" value={category} onChange={event => setCategory(event.target.value)}>
          <option value="all">All categories</option><option value="active">Active satellites</option>
          <option value="debris">Debris</option><option value="rocket_body">Rocket bodies</option><option value="unknown">Unclassified</option>
        </select>
        {objects.isError && <div className="notice error">Catalog unavailable: {objects.error.message}</div>}
        {objects.isPending && <div className="notice">Loading catalog pages…</div>}
        {positions.isFetching && <div className="notice">Calculating orbital positions…</div>}
        {positions.isError && <div className="notice error">Positions unavailable: {positions.error.message}</div>}
        {Boolean(positions.data?.errors.length) && <div className="notice error">{positions.data!.errors.length} objects could not be propagated. {positions.data!.errors[0]}</div>}
        {filtered.length > 20_000 && <div className="notice">Rendering the first 20,000 of {filtered.length.toLocaleString()} matches. Narrow your search to see other objects.</div>}
        {objects.data && <small className="fine-print">{filtered.length.toLocaleString()} matches · {objects.data.items.length.toLocaleString()} catalog objects loaded</small>}
        <div className="object-list">
          {filtered.slice(0, listLimit).map(item => <button className={item.catalog_id === selectedObjectId ? 'selected' : ''} key={item.catalog_id} onClick={() => setSelectedObject(item.catalog_id)}><span>{item.name}</span><small>{item.catalog_id} · {item.category.replace('_', ' ')}</small></button>)}
          {filtered.length > listLimit && <button onClick={() => setListLimit(value => value + 100)}>Show more matches</button>}
          {!objects.isPending && filtered.length === 0 && <div className="empty">No objects match the loaded catalog coverage.</div>}
        </div>
        {selected && <article className="detail"><span className="status-pill stale">{selected.source.includes('Archived') ? 'ARCHIVED DATA' : 'CATALOG DATA'}</span><h2>{selected.name}</h2><dl><dt>NORAD ID</dt><dd>{selected.catalog_id}</dd><dt>Element epoch</dt><dd>{new Date(selected.elements.epoch).toLocaleString()}</dd><dt>Inclination</dt><dd>{(selected.elements.inclination_rad * 180 / Math.PI).toFixed(2)}°</dd><dt>Eccentricity</dt><dd>{selected.elements.eccentricity.toFixed(6)}</dd></dl></article>}
      </aside>
    </section>
  )
}
