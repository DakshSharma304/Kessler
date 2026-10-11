export type ScienceMetadata = {
  source: string; model: string; model_version: string; availability: string
  assumptions: string[]; warnings: string[]
}

export type StateVector = {
  object_id?: string
  timestamp: string; frame: 'TEME' | 'ITRS' | 'EME2000'
  position_m: [number, number, number]; velocity_m_s: [number, number, number]
  metadata: ScienceMetadata
}

export type OrbitalObject = {
  catalog_id: string; name: string; object_id?: string; category: string; source: string
  elements: { epoch: string; inclination_rad: number; eccentricity: number; mean_motion_rev_day: number }
}

export type VisualizationWindow = {
  timestamps: string[]; frame: 'ITRS'; catalog_version: string; display_only: true; interpolation: string
  tracks: Array<{ object_id: string; positions_m: Array<[number, number, number]>; velocities_m_s: Array<[number, number, number]>; metadata: ScienceMetadata }>
  errors: string[]
}

export const getVisualizationWindow = (ids: string[], start: number, signal?: AbortSignal) =>
  api<VisualizationWindow>('/api/visualization/window', {
    method: 'POST', signal, body: JSON.stringify({ object_ids: ids, start: new Date(start).toISOString() }),
  })

export type Conjunction = {
  encounter_id: string; catalog_id_1: string; catalog_id_2: string
  object_name_1: string; object_name_2: string; tca: string
  separation_m: number; relative_speed_m_s: number; socrates_max_probability?: number
  coverage_note: string
}

export type DatasetStatus = {
  name: string; source_url: string; availability: string; retrieved_at?: string
  dataset_timestamp?: string; record_count: number; parsing_status: string; error?: string; stale: boolean
  next_retry_at?: string
}

export type CatalogStatus = {
  state: 'idle' | 'loading' | 'ready' | 'degraded' | 'failed'
  record_count: number; catalog_version: string; coverage: string; categories: Record<string, number>
  source?: DatasetStatus; error?: string
}

const base = import.meta.env.VITE_API_URL ?? ''

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try { const error = await response.json(); detail = error.error?.message ?? error.detail ?? detail } catch { /* response was not JSON */ }
    throw new Error(detail)
  }
  return response.json()
}

type CatalogPage = { items: OrbitalObject[]; total: number; limit: number; offset: number; catalog_version?: string }

export async function getObjects(): Promise<CatalogPage> {
  const first = await api<CatalogPage>('/api/objects?limit=1000&offset=0')
  const items = [...first.items]
  for (let offset = first.items.length; offset < first.total;) {
    const page = await api<CatalogPage>(`/api/objects?limit=1000&offset=${offset}`)
    if (page.catalog_version !== first.catalog_version) throw new Error('Catalog changed while loading; retrying the snapshot.')
    if (!page.items.length) throw new Error('Catalog pagination ended before all objects were loaded.')
    items.push(...page.items)
    offset += page.items.length
  }
  return { ...first, items }
}
export const getCatalogStatus = () => api<CatalogStatus>('/api/catalog/status')
export const refreshCatalog = () => api<CatalogStatus>('/api/catalog/refresh', { method: 'POST' })
export const getEncounters = () => api<{ items: Conjunction[]; total: number; coverage: string }>('/api/encounters')
export const getStatuses = () => api<DatasetStatus[]>('/api/data/status')
export const getMethods = () => api<Record<string, unknown>>('/api/methods')

export async function getPositions(ids: string[], timestamp: Date): Promise<{ states: StateVector[]; errors: string[] }> {
  const response = await api<Array<{ object_id: string; states: StateVector[]; errors: string[] }>>('/api/positions', {
    method: 'POST', body: JSON.stringify({ object_ids: ids, timestamps: [timestamp.toISOString()], frame: 'ITRS' }),
  })
  return {
    states: response.flatMap(item => item.states.map(state => ({ ...state, object_id: item.object_id }))),
    errors: response.flatMap(item => item.errors.map(error => `${item.object_id}: ${error}`)),
  }
}

export async function getTrajectory(id: string, timestamp: Date): Promise<StateVector[]> {
  const start = new Date(timestamp.getTime() - 45 * 60_000)
  const end = new Date(timestamp.getTime() + 45 * 60_000)
  const response = await api<{ states: StateVector[] }>('/api/trajectories', {
    method: 'POST', body: JSON.stringify({ object_id: id, start: start.toISOString(), end: end.toISOString(), samples: 90, frame: 'ITRS' }),
  })
  return response.states
}
