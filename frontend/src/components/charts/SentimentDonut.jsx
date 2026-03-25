import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const COLORS = { positive: '#4ade80', negative: '#f87171', neutral: '#52525b' }
const LABELS = { positive: 'Bullish', negative: 'Bearish', neutral: 'Neutral' }

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const { name, value } = payload[0]
  return (
    <div className="bg-terminal-surface border border-terminal-border rounded px-3 py-2 text-xs font-ticker">
      <span style={{ color: COLORS[name] }}>{LABELS[name]}</span>
      <span className="text-terminal-subtext ml-2">{value}</span>
    </div>
  )
}

export default function SentimentDonut({ counts = {} }) {
  const data = Object.entries(counts)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }))

  const total = data.reduce((s, d) => s + d.value, 0)

  return (
    <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4 h-48 flex flex-col">
      <div className="font-ticker text-[10px] text-terminal-muted tracking-widest mb-3">SENTIMENT</div>
      {total === 0 ? (
        <div className="flex-1 flex items-center justify-center text-terminal-muted text-xs font-ticker">NO DATA</div>
      ) : (
        <div className="flex flex-1 items-center gap-4">
          <ResponsiveContainer width={100} height="100%">
            <PieChart>
              <Pie data={data} innerRadius={28} outerRadius={44} dataKey="value" strokeWidth={0}>
                {data.map(entry => (
                  <Cell key={entry.name} fill={COLORS[entry.name] ?? '#52525b'} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-col gap-2 flex-1">
            {data.map(d => (
              <div key={d.name} className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full" style={{ background: COLORS[d.name] }} />
                  <span className="font-ticker text-[10px] text-terminal-subtext tracking-wide">
                    {LABELS[d.name]?.toUpperCase()}
                  </span>
                </div>
                <span className="font-ticker text-[10px] text-terminal-text">
                  {total ? Math.round(d.value / total * 100) : 0}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
