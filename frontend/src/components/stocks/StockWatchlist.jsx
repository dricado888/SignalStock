import { useState, useEffect, useRef } from 'react'
import api from '../../utils/api'

const STORAGE_KEY = 'signalstock_watched'

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export default function StockWatchlist({ watched, onChange }) {
  const [search, setSearch]   = useState('')
  const [results, setResults] = useState([])
  const inputRef = useRef(null)

  // Debounced stock search
  useEffect(() => {
    if (!search.trim()) { setResults([]); return }
    const t = setTimeout(() => {
      api.get('/stocks', { params: { q: search, limit: 6 } })
        .then(r => setResults(r.data))
        .catch(() => {})
    }, 280)
    return () => clearTimeout(t)
  }, [search])

  const add = (stock) => {
    if (watched.find(w => w.id === stock.id)) return
    const next = [...watched, stock]
    onChange(next)
    setSearch('')
    setResults([])
    inputRef.current?.focus()
  }

  const remove = (id) => {
    onChange(watched.filter(w => w.id !== id))
  }

  const clearAll = () => {
    onChange([])
    setSearch('')
    setResults([])
  }

  const isWatching = watched.length > 0

  return (
    <div className="border border-terminal-border rounded-lg bg-terminal-surface px-4 py-3 mb-6">
      {/* Header row */}
      <div className="flex items-center justify-between mb-2">
        <span className="font-ticker text-[10px] text-terminal-muted tracking-widest">WATCHLIST</span>
        {isWatching && (
          <div className="flex items-center gap-3">
            <span className="font-ticker text-[10px] text-terminal-cyan tracking-widest">
              FILTERING · {watched.length} {watched.length === 1 ? 'STOCK' : 'STOCKS'}
            </span>
            <button
              onClick={clearAll}
              className="font-ticker text-[9px] text-terminal-muted hover:text-terminal-negative transition-colors tracking-widest"
            >
              CLEAR ALL
            </button>
          </div>
        )}
        {!isWatching && (
          <span className="font-ticker text-[9px] text-terminal-border tracking-widest">ALL STOCKS</span>
        )}
      </div>

      {/* Search input */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search ticker or company to add..."
          className="w-full bg-terminal-bg border border-terminal-border rounded px-3 py-2 text-xs text-terminal-text placeholder:text-terminal-muted focus:outline-none focus:border-terminal-cyan/50 transition-colors font-ticker"
        />

        {/* Dropdown results */}
        {results.length > 0 && (
          <div className="absolute top-full left-0 right-0 z-20 mt-1 border border-terminal-border rounded bg-terminal-surface shadow-lg overflow-hidden">
            {results.map(s => {
              const already = watched.find(w => w.id === s.id)
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => already ? remove(s.id) : add(s)}
                  className={`w-full flex items-center justify-between px-3 py-2 text-xs border-b border-terminal-border last:border-0 transition-colors ${
                    already ? 'bg-terminal-cyan/10' : 'hover:bg-terminal-bg'
                  }`}
                >
                  <span>
                    <span className="font-ticker font-bold text-terminal-cyan mr-2">${s.ticker}</span>
                    <span className="text-terminal-subtext">{s.company_name}</span>
                  </span>
                  {already
                    ? <span className="font-ticker text-[9px] text-terminal-negative">REMOVE</span>
                    : <span className="font-ticker text-[9px] text-terminal-muted">+ ADD</span>
                  }
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Watched chips */}
      {isWatching && (
        <div className="flex flex-wrap gap-1.5 mt-2.5">
          {watched.map(s => (
            <button
              key={s.id}
              type="button"
              onClick={() => remove(s.id)}
              title={s.company_name}
              className="font-ticker text-[10px] font-bold text-terminal-cyan bg-terminal-cyan/10 border border-terminal-cyan/30 px-2 py-0.5 rounded hover:bg-terminal-negative/10 hover:border-terminal-negative/30 hover:text-terminal-negative transition-colors"
            >
              ${s.ticker} ×
            </button>
          ))}
        </div>
      )}

      {!isWatching && (
        <p className="font-ticker text-[9px] text-terminal-border mt-2 tracking-wide">
          Search above to filter the feed by specific stocks · showing all events
        </p>
      )}
    </div>
  )
}

// Export storage helpers for Dashboard to use
export { loadFromStorage, STORAGE_KEY }
