import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d    = payload[0].payload
  const icon = d.direction === 'up' ? '▲' : d.direction === 'down' ? '▼' : '→'
  const clr  = d.direction === 'up' ? '#4ade80' : d.direction === 'down' ? '#f87171' : '#52525b'
  return (
    <div className="bg-terminal-surface border border-terminal-border rounded px-3 py-2 text-xs font-ticker">
      <span className="text-terminal-cyan font-bold">${d.ticker}</span>
      <span style={{ color: clr }} className="ml-2 font-bold">
        {icon} {d.change_pct > 0 ? '+' : ''}{d.change_pct?.toFixed(2)}%
      </span>
    </div>
  )
}

export default function TopStocksBar({ data = [] }) {
  const chartData = data.map(d => ({ ...d, absChange: Math.abs(d.change_pct ?? 0) }))

  return (
    <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4 h-48 flex flex-col">
      <div className="font-ticker text-[10px] text-terminal-muted tracking-widest mb-3">TOP MOVERS</div>
      {chartData.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-terminal-muted text-xs font-ticker">NO PRICE DATA</div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
            <XAxis
              type="number"
              tick={{ fill: '#52525b', fontSize: 9, fontFamily: 'JetBrains Mono' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={v => `${v}%`}
            />
            <YAxis
              type="category"
              dataKey="ticker"
              width={40}
              tick={{ fill: '#22d3ee', fontSize: 10, fontFamily: 'JetBrains Mono', fontWeight: 600 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(34,211,238,0.05)' }} />
            <Bar dataKey="absChange" radius={[0, 2, 2, 0]}>
              {chartData.map((d, i) => (
                <Cell
                  key={i}
                  fill={
                    d.direction === 'up'   ? '#4ade80' :
                    d.direction === 'down' ? '#f87171' :
                    '#52525b'
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
