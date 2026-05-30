import { useState } from 'react'

const COMMON_PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD']

export default function RunForm({ onSubmit, loading }) {
  const [pair, setPair] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    const p = pair.trim().toUpperCase().replace('/', '').replace('-', '')
    if (p.length >= 6) onSubmit(p)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <label className="block text-sm font-semibold text-gray-700">Currency Pair</label>
      <input
        type="text"
        value={pair}
        onChange={(e) => setPair(e.target.value)}
        placeholder="e.g. EURUSD"
        maxLength={8}
        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm
                   focus:outline-none focus:ring-2 focus:ring-blue-500 uppercase"
      />
      <div className="flex flex-wrap gap-1">
        {COMMON_PAIRS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPair(p)}
            className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700
                       hover:bg-blue-100 border border-blue-200"
          >
            {p}
          </button>
        ))}
      </div>
      <button
        type="submit"
        disabled={loading || pair.trim().length < 6}
        className="w-full bg-blue-700 text-white rounded-md py-2 text-sm font-semibold
                   hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed
                   transition-colors"
      >
        {loading ? 'Starting…' : 'Analyse Pair'}
      </button>
    </form>
  )
}
