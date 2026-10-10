import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi } from 'vitest'
import App from '../src/App'

test('renders service status from the backend', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => ({
    ok: true,
    json: async () => url.includes('/api/objects')
      ? { items: [], total: 0, limit: 1000, offset: 0 }
      : { status: 'ok', version: '0.1.0', datasets: { objects: 0, encounters: 0 } },
  })))
  render(<QueryClientProvider client={new QueryClient()}><App /></QueryClientProvider>)
  expect(screen.getByText('KESSLER')).toBeInTheDocument()
  expect(await screen.findByText('0 OBJECTS')).toBeInTheDocument()
  expect(await screen.findByText('Orbital catalog')).toBeInTheDocument()
})
