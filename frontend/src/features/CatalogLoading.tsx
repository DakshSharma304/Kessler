import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { getCatalogStatus, refreshCatalog } from '../api/client'

export function useCatalogLoading() {
  const client = useQueryClient()
  const version = useRef<string | undefined>(undefined)
  const query = useQuery({
    queryKey: ['catalog-status'], queryFn: getCatalogStatus,
    refetchInterval: query => query.state.data?.state === 'loading' ? 1000 : 30_000,
    retry: false,
  })
  useEffect(() => {
    const next = query.data?.catalog_version
    if (next && query.data?.state !== 'loading' && next !== version.current) {
      version.current = next
      for (const key of ['objects', 'health', 'positions', 'trajectory', 'statuses']) void client.invalidateQueries({ queryKey: [key] })
    }
  }, [query.data?.catalog_version, query.data?.state, client])
  const refresh = useMutation({
    mutationFn: refreshCatalog,
    onSuccess: data => {
      client.setQueryData(['catalog-status'], data)
      for (const key of ['objects', 'health', 'positions', 'trajectory', 'statuses']) void client.invalidateQueries({ queryKey: [key] })
    },
    onSettled: () => { void client.invalidateQueries({ queryKey: ['catalog-status'] }) },
  })
  return { ...query, refresh }
}

export default function CatalogLoading() {
  const catalog = useCatalogLoading()
  const status = catalog.data
  const busy = catalog.refresh.isPending || status?.state === 'loading'
  const retryAt = status?.source?.next_retry_at
  const coolingDown = Boolean(retryAt && Date.parse(retryAt) > Date.now())
  const archived = status?.source?.parsing_status === 'archived_fixture'
  return <div className="catalog-loading" aria-live="polite">
    <strong>{busy ? 'Loading live catalog…' : archived ? 'Archived fallback — live catalog not loaded' : status?.state === 'ready' ? 'Catalog loaded' : 'Live catalog unavailable or stale'}</strong>
    {status && <><p>{status.record_count.toLocaleString()} objects · {status.coverage}</p>
      {status.source?.retrieved_at && <small>Last download: {new Date(status.source.retrieved_at).toLocaleString()}</small>}
      {(status.error || status.source?.error) && <p className="catalog-error">{status.error ?? status.source?.error}</p>}
      {coolingDown && <small>Next permitted retry: {new Date(retryAt!).toLocaleString()}. Cached data stays available.</small>}
    </>}
    {catalog.isError && <p className="catalog-error">Cannot check catalog loading: {catalog.error.message}</p>}
    {catalog.refresh.isError && <p className="catalog-error">Refresh failed: {catalog.refresh.error.message}</p>}
    <button disabled={busy || coolingDown} onClick={() => catalog.refresh.mutate()}>{busy ? 'Loading catalog…' : status?.state === 'ready' ? 'Refresh catalog' : 'Retry live catalog'}</button>
  </div>
}
