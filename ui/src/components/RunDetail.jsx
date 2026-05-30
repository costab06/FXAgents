import { useEffect, useState } from 'react'
import { getRun, streamRun } from '../api'
import LiveLog from './LiveLog'

function DirectionBadge({ direction }) {
  if (!direction) return null
  const color = direction === 'buy'
    ? 'bg-green-500 text-white'
    : direction === 'sell'
    ? 'bg-red-500 text-white'
    : 'bg-gray-300 text-gray-800'
  return (
    <span className={`px-3 py-1 rounded-full font-bold text-lg ${color}`}>
      {direction.toUpperCase()}
    </span>
  )
}

function Section({ title, data }) {
  if (!data || Object.keys(data).length === 0) return null
  return (
    <div className="mb-6">
      <h3 className="text-base font-semibold text-blue-800 border-b border-blue-100 pb-1 mb-3">
        {title}
      </h3>
      {data.key_points?.length > 0 && (
        <div className="bg-blue-50 rounded-md p-3 mb-3">
          <ul className="space-y-1">
            {data.key_points.map((p, i) => (
              <li key={i} className="text-sm text-gray-700">• {p}</li>
            ))}
          </ul>
        </div>
      )}
      {data.summary && <p className="text-sm text-gray-600 mb-3">{data.summary}</p>}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        {Object.entries(data)
          .filter(([k]) => !['key_points', 'summary'].includes(k))
          .map(([k, v]) => {
            if (v === null || v === undefined || v === '') return null
            const label = k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
            if (Array.isArray(v)) {
              return (
                <div key={k} className="col-span-2">
                  <span className="text-xs font-semibold text-gray-500">{label}:</span>
                  <ul className="ml-3">
                    {v.map((item, i) => (
                      <li key={i} className="text-xs text-gray-600">- {item}</li>
                    ))}
                  </ul>
                </div>
              )
            }
            return (
              <div key={k}>
                <span className="text-xs font-semibold text-gray-500">{label}: </span>
                <span className="text-xs text-gray-700">{String(v)}</span>
              </div>
            )
          })}
      </div>
    </div>
  )
}

export default function RunDetail({ run, onRefresh }) {
  const [detail, setDetail] = useState(null)
  const [streaming, setStreaming] = useState(false)

  useEffect(() => {
    async function load() {
      const data = await getRun(run.run_id)
      setDetail(data)
    }
    load()
  }, [run.run_id, run.status])

  useEffect(() => {
    if (run.status !== 'running' && run.status !== 'pending') return
    setStreaming(true)
    const es = streamRun(
      run.run_id,
      () => {},
      async () => {
        setStreaming(false)
        const data = await getRun(run.run_id)
        setDetail(data)
        onRefresh()
      }
    )
    return () => es.close()
  }, [run.run_id, run.status])

  if (!detail) {
    return <div className="text-gray-400 text-sm">Loading…</div>
  }

  const result = detail.result || {}
  const final = result.final_decision || {}
  const isComplete = detail.status === 'completed'

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-3xl font-bold text-gray-800">{detail.pair}</h2>
          <p className="text-gray-400 text-sm">{detail.date}</p>
        </div>
        <div className="flex items-center gap-4">
          <DirectionBadge direction={final.final_direction} />
          {isComplete && (
            <a
              href={`/api/runs/${detail.run_id}/pdf`}
              download={`${detail.pair}_${detail.date}.pdf`}
              className="bg-blue-700 text-white text-sm px-4 py-2 rounded-md
                         hover:bg-blue-800 transition-colors"
            >
              Download PDF
            </a>
          )}
        </div>
      </div>

      {/* Trade summary bar */}
      {isComplete && final.entry_price && (
        <div className="bg-gray-100 rounded-lg p-4 mb-6 grid grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-xs text-gray-500">Entry</div>
            <div className="font-semibold">{Number(final.entry_price).toFixed(5)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Stop Loss</div>
            <div className="font-semibold text-red-600">{final.stop_loss_pips} pips</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Take Profit</div>
            <div className="font-semibold text-green-600">{final.take_profit_pips} pips</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">R/R Ratio</div>
            <div className="font-semibold">{final.risk_reward_ratio}</div>
          </div>
        </div>
      )}

      {/* Progress (while running) */}
      {(detail.status === 'running' || detail.status === 'pending') && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
          <h3 className="font-semibold text-gray-700 mb-3">Pipeline Progress</h3>
          <LiveLog status={detail.status} log={detail.log} />
        </div>
      )}

      {/* Error */}
      {detail.status === 'failed' && detail.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-700 text-sm">
          {detail.error}
        </div>
      )}

      {/* Results */}
      {isComplete && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <Section title="Final Decision" data={result.final_decision} />
          <Section title="Trade Recommendation" data={result.trade_recommendation} />
          <Section title="Macro Analysis" data={result.macro_analysis} />
          <Section title="Carry Analysis" data={result.carry_analysis} />
          <Section title="Technical Analysis" data={result.technical_analysis} />
          <Section title="Sentiment Analysis" data={result.sentiment_analysis} />
          <Section title="News Analysis" data={result.news_analysis} />
          <Section title="Research Debate Conclusion" data={result.debate_conclusion} />
          <Section title="Risk Conclusion" data={result.risk_conclusion} />
        </div>
      )}
    </div>
  )
}
