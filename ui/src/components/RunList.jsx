function statusColor(status) {
  switch (status) {
    case 'completed': return 'text-green-600'
    case 'failed': return 'text-red-600'
    case 'running': return 'text-blue-600'
    default: return 'text-gray-400'
  }
}

function directionBadge(direction) {
  if (!direction) return null
  const color = direction === 'buy'
    ? 'bg-green-100 text-green-800'
    : direction === 'sell'
    ? 'bg-red-100 text-red-800'
    : 'bg-gray-100 text-gray-600'
  return (
    <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${color}`}>
      {direction.toUpperCase()}
    </span>
  )
}

export default function RunList({ runs, selectedId, onSelect, onDelete }) {
  if (!runs.length) {
    return <p className="text-xs text-gray-400 text-center mt-4">No runs yet</p>
  }

  return (
    <ul className="space-y-1">
      {runs.map((run) => (
        <li key={run.run_id}>
          <div
            className={`group flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer
              ${selectedId === run.run_id ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-50'}`}
            onClick={() => onSelect(run.run_id)}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm">{run.pair}</span>
                {directionBadge(run.direction)}
              </div>
              <div className="text-xs text-gray-400">{run.date}</div>
              <div className={`text-xs font-medium ${statusColor(run.status)}`}>
                {run.status}
                {run.confidence != null && run.status === 'completed' &&
                  ` · ${(run.confidence * 100).toFixed(0)}%`}
              </div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(run.run_id) }}
              className="ml-2 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100
                         transition-opacity text-lg leading-none"
              title="Delete run"
            >
              ×
            </button>
          </div>
        </li>
      ))}
    </ul>
  )
}
