import { useEffect, useState } from 'react'
import api from '../utils/api'
import { formatDate } from '../utils/formatters'

export default function WatchlistPage() {
  const [watchlist, setWatchlist] = useState([])
  const [search, setSearch]       = useState('')
  const [results, setResults]     = useState([])
  const [loading, setLoading]     = useState(true)
  const [searching, setSearching] = useState(false)
  const [msg, setMsg]             = useState('')

  const fetchWatchlist = () => {
    api.get('/watchlist').then(r => setWatchlist(r.data)).finally(() => setLoading(false))
  }
  useEffect(() => { fetchWatchlist() }, [])

  // Debounced stock search
  useEffect(() => {
    if (!search.trim()) { setResults([]); return }
    const t = setTimeout(() => {
      setSearching(true)
      api.get('/stocks', { params: { q: search, limit: 8 } })
        .then(r => setResults(r.data))
        .finally(() => setSearching(false))
    }, 300)
    return () => clearTimeout(t)
  }, [search])

  const add = async (ticker) => {
    try {
      await api.post('/watchlist', { ticker })
      setMsg(`Added $${ticker}`)
      setSearch(''); setResults([])
      fetchWatchlist()
      setTimeout(() => setMsg(''), 2500)
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Error adding stock')
      setTimeout(() => setMsg(''), 3000)
    }
  }

  const remove = async (stockId, ticker) => {
    await api.delete(`/watchlist/${stockId}`)
    setWatchlist(w => w.filter(s => s.id !== stockId))
    setMsg(`Removed $${ticker}`)
    setTimeout(() => setMsg(''), 2500)
  }

  const isWatched = (ticker) => watchlist.some(s => s.ticker === ticker)

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-900 mb-1">Watchlist</h1>
      <p className="text-slate-500 text-sm mb-8">
        Add stocks to receive email alerts when events are detected.
      </p>

      {/* Toast */}
      {msg && (
        <div className="bg-indigo-50 border border-indigo-200 text-indigo-700 text-sm rounded-lg px-4 py-3 mb-6">
          {msg}
        </div>
      )}

      {/* Add stock */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 mb-8">
        <div className="text-sm font-semibold text-slate-700 mb-3">Add a stock</div>
        <div className="relative">
          <input
            type="text"
            placeholder="Search ticker or company name…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          {searching && (
            <div className="absolute right-3 top-3 text-slate-300 text-xs">searching…</div>
          )}
        </div>

        {results.length > 0 && (
          <div className="mt-2 border border-slate-200 rounded-lg overflow-hidden shadow-sm">
            {results.map(s => (
              <div
                key={s.id}
                className="flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 border-b border-slate-100 last:border-0"
              >
                <div>
                  <span className="font-mono font-bold text-sm text-indigo-600 mr-2">${s.ticker}</span>
                  <span className="text-sm text-slate-600">{s.company_name}</span>
                </div>
                {isWatched(s.ticker) ? (
                  <span className="text-xs text-slate-400">Watching</span>
                ) : (
                  <button
                    onClick={() => add(s.ticker)}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
                  >
                    + Add
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Current watchlist */}
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">
        Watching ({watchlist.length})
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-400">Loading…</div>
      ) : watchlist.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-slate-200 shadow-sm text-slate-400 text-sm">
          No stocks yet. Search above to add one.
        </div>
      ) : (
        <div className="space-y-2">
          {watchlist.map(s => (
            <div
              key={s.id}
              className="bg-white rounded-xl border border-slate-200 shadow-sm px-5 py-4 flex items-center justify-between"
            >
              <div>
                <span className="font-mono font-bold text-indigo-600 text-base mr-2">${s.ticker}</span>
                <span className="text-sm text-slate-600">{s.company_name}</span>
                <div className="text-xs text-slate-400 mt-0.5">Added {formatDate(s.added_at)}</div>
              </div>
              <button
                onClick={() => remove(s.id, s.ticker)}
                className="text-xs text-slate-400 hover:text-red-500 transition-colors font-medium"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
