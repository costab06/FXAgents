const STEPS = [
  { key: 'analysts',         label: 'Analysts (Macro, Carry, Technical, Sentiment, News)' },
  { key: 'research_debate',  label: 'Research Debate' },
  { key: 'trader',           label: 'Trader' },
  { key: 'risk_debate',      label: 'Risk Analysis' },
  { key: 'fund_manager',     label: 'Fund Manager' },
]

function inferCompletedSteps(logs) {
  const completed = new Set()
  const lc = logs.map((l) => l.toLowerCase())
  if (lc.some((l) => l.includes('research debate'))) completed.add('analysts')
  if (lc.some((l) => l.includes('trade recommendation'))) completed.add('research_debate')
  if (lc.some((l) => l.includes('risk analysis'))) completed.add('trader')
  if (lc.some((l) => l.includes('fund manager'))) completed.add('risk_debate')
  if (lc.some((l) => l.includes('analysis complete'))) completed.add('fund_manager')
  return completed
}

export default function LiveLog({ status, log }) {
  const completed = inferCompletedSteps(log || [])
  const activeIdx = status === 'running'
    ? STEPS.findIndex((s) => !completed.has(s.key))
    : -1

  return (
    <div className="space-y-1">
      {STEPS.map((step, i) => {
        const done = completed.has(step.key)
        const active = i === activeIdx
        return (
          <div key={step.key} className="flex items-center gap-3 text-sm py-1">
            {done ? (
              <span className="text-green-500 font-bold w-4">✓</span>
            ) : active ? (
              <span className="text-blue-500 w-4 animate-spin inline-block">◌</span>
            ) : (
              <span className="text-gray-300 w-4">○</span>
            )}
            <span className={done ? 'text-gray-700' : active ? 'text-blue-700 font-medium' : 'text-gray-400'}>
              {step.label}
            </span>
            {done && <span className="text-xs text-green-500 ml-auto">Done</span>}
            {active && <span className="text-xs text-blue-500 ml-auto animate-pulse">Running…</span>}
          </div>
        )
      })}
    </div>
  )
}
