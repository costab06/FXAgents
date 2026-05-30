import { useState, useEffect, useCallback } from 'react'
import { listRuns, startRun, deleteRun } from './api'
import RunList from './components/RunList'
import RunForm from './components/RunForm'
import RunDetail from './components/RunDetail'

export default function App() {
  const [runs, setRuns] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const refreshRuns = useCallback(async () => {
    try {
      const data = await listRuns()
      setRuns(data)
    } catch (e) {
      console.error('Failed to list runs', e)
    }
  }, [])

  useEffect(() => {
    refreshRuns()
    const id = setInterval(refreshRuns, 3000)
    return () => clearInterval(id)
  }, [refreshRuns])

  async function handleStart(pair) {
    setError('')
    setLoading(true)
    try {
      const run = await startRun(pair)
      await refreshRuns()
      setSelectedId(run.run_id)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(runId) {
    try {
      await deleteRun(runId)
      if (selectedId === runId) setSelectedId(null)
      await refreshRuns()
    } catch (e) {
      setError(e.message)
    }
  }

  const selectedRun = runs.find((r) => r.run_id === selectedId) || null

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-blue-800 text-white px-6 py-4 shadow-md">
        <h1 className="text-2xl font-bold tracking-tight">FX Agent</h1>
        <p className="text-blue-200 text-sm">Multi-agent FX trading analysis</p>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-72 bg-white border-r border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <RunForm onSubmit={handleStart} loading={loading} />
            {error && <p className="mt-2 text-red-600 text-sm">{error}</p>}
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            <RunList
              runs={runs}
              selectedId={selectedId}
              onSelect={setSelectedId}
              onDelete={handleDelete}
            />
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-6">
          {selectedRun ? (
            <RunDetail run={selectedRun} onRefresh={refreshRuns} />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <div className="text-5xl mb-4">💱</div>
                <p className="text-lg">Enter a currency pair to start analysis</p>
                <p className="text-sm mt-2">e.g. EURUSD, GBPUSD, USDJPY</p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
