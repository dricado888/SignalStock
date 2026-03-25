import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-terminal-surface border border-terminal-border rounded px-3 py-2 text-xs font-ticker">
      <div className="text-terminal-muted">{label}</div>
      <div className="text-terminal-cyan">{payload[0].value} events</div>
    </div>
  )
}

export default function EventsLine({ data = [] }) {
  const formatted = data.map(d => ({
    ...d,
    label: (() => { try { return format(new Date(d.date), 'MMM d') } catch { return d.date } })(),
  }))

  return (
    <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4 h-48 flex flex-col">
      <div className="font-ticker text-[10px] text-terminal-muted tracking-widest mb-3">EVENTS / 7 DAYS</div>
      {data.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-terminal-muted text-xs font-ticker">NO DATA</div>
      ) : (
        <>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={formatted} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
              <XAxis
                dataKey="label"
                tick={{ fill: '#52525b', fontSize: 9, fontFamily: 'JetBrains Mono' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#52525b', fontSize: 9, fontFamily: 'JetBrains Mono' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#22d3ee"
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3, fill: '#22d3ee', strokeWidth: 0 }}
              />
            </LineChart>
          </ResponsiveContainer>
          {data.length <= 1 && (
            <div className="font-ticker text-[9px] text-terminal-border text-center mt-1 tracking-wide">
              BUILDS UP AS EVENTS ARE PROCESSED DAILY
            </div>
          )}
        </>
      )}
    </div>
  )
}
