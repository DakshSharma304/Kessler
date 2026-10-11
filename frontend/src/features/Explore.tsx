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
  const filtered = useMemo(() => (objects.data?.items ?? []).filter(item =>
    (category === 'all' || item.category === category) &&
    (item.name.toLowerCase().includes(search.toLowerCase()) || item.catalog_id.includes(search)),
  ), [objects.data, search, category])
  const selected = objects.data?.items?.find(item => item.catalog_id === selectedObjectId)
  const visibleIds = useMemo(() => filtered.slice(0, 20_000).map(item => item.catalog_id), [filtered])
  const positions = useQuery({
    queryKey: ['positions', objects.data?.catalog_version, visibleIds, time.toISOString()],
    queryFn: () => getPositions(visibleIds, time),
    enabled: Boolean(visibleIds.length),
    // Keep the last completed snapshot during time updates, not across catalog/filter changes.
    placeholderData: (previous, previousQuery) => {
      const previousIds = previousQuery?.queryKey[2] as string[] | undefined
      return previousQuery?.queryKey[1] === objects.data?.catalog_version &&
        previousIds?.length === visibleIds.length && previousIds.every((id, index) => id === visibleIds[index])
        ? previous : undefined
    },
  })
  const trajectory = useQuery({
    queryKey: ['trajectory', selectedObjectId, objects.data?.catalog_version, time.toISOString()],
    queryFn: () => getTrajectory(selectedObjectId!, time), enabled: Boolean(selectedObjectId && showOrbit),
    placeholderData: (previous, previousQuery) => previousQuery?.queryKey[1] === selectedObjectId &&
      previousQuery?.queryKey[2] === objects.data?.catalog_version ? previous : undefined,
  })
  useEffect(() => {
    // Pace playback to completed requests; a slow backend must not accumulate requests
    // for a new timestamp every second and leave the current snapshot perpetually pending.
    if (!playing || !visibleIds.length || positions.isFetching || (showOrbit && trajectory.isFetching)) return
    const timer = window.setTimeout(() => setTime(value => new Date(value.getTime() + 60_000)), 1_000)
    return () => window.clearTimeout(timer)
  }, [playing, visibleIds.length, positions.isFetching, trajectory.isFetching, showOrbit, time])
  const displayedStates = visibleIds.length ? positions.data?.states ?? [] : []
  return (
    <section className="workspace explore-grid">
      <div className="globe-panel">
        <EarthScene states={displayedStates} trajectory={showOrbit ? trajectory.data ?? [] : []} />
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
        <small className="fine-print" aria-label="Orbital position snapshot">Position snapshot: {displayedStates.length.toLocaleString()} objects{displayedStates[0] && ` · ${displayedStates[0].timestamp}`} · playback advances 1 minute per completed step</small>
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
