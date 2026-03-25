import { EVENT_TYPE_OPTIONS } from '../../utils/formatters'

const SENTIMENTS = [
  { value: '', label: 'ALL SENTIMENTS' },
  { value: 'positive', label: '↑ BULLISH' },
  { value: 'negative', label: '↓ BEARISH' },
  { value: 'neutral',  label: '→ NEUTRAL' },
]

const selectCls = "font-ticker text-xs text-terminal-text bg-terminal-surface border border-terminal-border rounded px-3 py-2 focus:outline-none focus:border-terminal-cyan/50 tracking-wider appearance-none cursor-pointer hover:border-terminal-border/80 transition-colors"

export default function EventFilters({ filters, onChange }) {
  const set = (key) => (e) => onChange({ ...filters, [key]: e.target.value, page: 1 })

  return (
    <div className="flex flex-wrap items-center gap-2 mb-6">
      <select value={filters.event_type || ''} onChange={set('event_type')} className={selectCls}>
        <option value="">ALL EVENTS</option>
        {EVENT_TYPE_OPTIONS.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>

      <select value={filters.sentiment || ''} onChange={set('sentiment')} className={selectCls}>
        {SENTIMENTS.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>

      {(filters.event_type || filters.sentiment) && (
        <button
          onClick={() => onChange({ page: 1 })}
          className="font-ticker text-[10px] text-terminal-muted hover:text-terminal-negative transition-colors tracking-widest px-1"
        >
          CLEAR ✕
        </button>
      )}
    </div>
  )
}
