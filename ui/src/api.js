const BASE = '/api'

export async function listRuns() {
  const r = await fetch(`${BASE}/runs`)
  if (!r.ok) throw new Error('Failed to list runs')
  return r.json()
}

export async function startRun(pair) {
  const r = await fetch(`${BASE}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pair }),
  })
  if (!r.ok) throw new Error('Failed to start run')
  return r.json()
}

export async function getRun(runId) {
  const r = await fetch(`${BASE}/runs/${runId}`)
  if (!r.ok) throw new Error('Failed to get run')
  return r.json()
}

export async function deleteRun(runId) {
  const r = await fetch(`${BASE}/runs/${runId}`, { method: 'DELETE' })
  if (!r.ok) throw new Error('Failed to delete run')
  return r.json()
}

export function streamRun(runId, onMessage, onDone) {
  const es = new EventSource(`${BASE}/runs/${runId}/stream`)
  es.onmessage = (e) => {
    const data = JSON.parse(e.data)
    onMessage(data)
    if (data.type === 'status' && (data.status === 'completed' || data.status === 'failed')) {
      es.close()
      onDone(data.status)
    }
  }
  es.onerror = () => {
    es.close()
    onDone('failed')
  }
  return es
}
