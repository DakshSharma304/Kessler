export type ScienceMetadata = {
  source: string; model: string; model_version: string; availability: string
  assumptions: string[]; warnings: string[]
}

export type StateVector = {
  timestamp: string; frame: 'TEME' | 'ITRS' | 'EME2000'
  position_m: [number, number, number]; velocity_m_s: [number, number, number]
  metadata: ScienceMetadata
}

export type OrbitalObject = {
  catalog_id: string; name: string; object_id?: string; category: string; source: string
  elements: { epoch: string; inclination_rad: number; eccentricity: number; mean_motion_rev_day: number }
}

export type Conjunction = {
  encounter_id: string; catalog_id_1: string; catalog_id_2: string
  object_name_1: string; object_name_2: string; tca: string
  separation_m: number; relative_speed_m_s: number; socrates_max_probability?: number
  coverage_note: string
}

export type DatasetStatus = {
  name: string; source_url: string; availability: string; retrieved_at?: string
  dataset_timestamp?: string; record_count: number; parsing_status: string; error?: string; stale: boolean
}

const base = import.meta.env.VITE_API_URL ?? ''

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try { detail = (await response.json()).detail ?? detail } catch { /* response was not JSON */ }
    throw new Error(detail)
  }
  return response.json()
}

export const getObjects = () => api<{ items: OrbitalObject[]; total: number; limit: number; offset: number }>('/api/objects?limit=1000')
export const getEncounters = () => api<{ items: Conjunction[]; total: number; coverage: string }>('/api/encounters')
export const getStatuses = () => api<DatasetStatus[]>('/api/data/status')
export const getMethods = () => api<Record<string, unknown>>('/api/methods')

export async function getPositions(ids: string[], timestamp: Date): Promise<StateVector[]> {
  const response = await api<Array<{ object_id: string; states: StateVector[]; errors: string[] }>>('/api/positions', {
    method: 'POST', body: JSON.stringify({ object_ids: ids, timestamps: [timestamp.toISOString()], frame: 'ITRS' }),
  })
  return response.flatMap(item => item.states)
}

export async function getTrajectory(id: string, timestamp: Date): Promise<StateVector[]> {
  const start = new Date(timestamp.getTime() - 45 * 60_000)
  const end = new Date(timestamp.getTime() + 45 * 60_000)
  const response = await api<{ states: StateVector[] }>('/api/trajectories', {
    method: 'POST', body: JSON.stringify({ object_id: id, start: start.toISOString(), end: end.toISOString(), samples: 90, frame: 'ITRS' }),
  })
  return response.states
}
