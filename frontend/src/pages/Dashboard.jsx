import { useEffect, useState, useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import api from '../utils/api'
import EventCard from '../components/events/EventCard'
import EventFilters from '../components/events/EventFilters'
import SentimentDonut from '../components/charts/SentimentDonut'
import StockPriceCard from '../components/charts/StockPriceCard'
import TopStocksBar from '../components/charts/TopStocksBar'
import StockWatchlist, { loadFromStorage, STORAGE_KEY } from '../components/stocks/StockWatchlist'

function StatPill({ label, value, accent }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className={`font-ticker font-bold text-lg tabular-nums ${accent ? 'text-terminal-cyan' : 'text-terminal-text'}`}>
        {value ?? '—'}
      </span>
      <span className="font-ticker text-[10px] text-terminal-muted tracking-widest uppercase">{label}</span>
    </div>
  )
}

export default function Dashboard({ onSubscribe }) {
  const [stats, setStats]           = useState(null)
  const [filters, setFilters]       = useState({ page: 1 })
  const [showNeutral, setShowNeutral] = useState(false)
  const [watched, setWatched]       = useState(() => loadFromStorage())
  const [prices, setPrices]         = useState([])
  const priceIntervalRef            = useRef(null)

  // Per-section state
  const [directEvents, setDirectEvents] = useState([])
  const [directPages,  setDirectPages]  = useState(1)
  const [directPage,   setDirectPage]   = useState(1)
  const [directTotal,  setDirectTotal]  = useState(0)
  const [directLoading, setDirectLoading] = useState(true)

  const [marketEvents, setMarketEvents] = useState([])
  const [marketPages,  setMarketPages]  = useState(1)
  const [marketPage,   setMarketPage]   = useState(1)
  const [marketTotal,  setMarketTotal]  = useState(0)
  const [marketLoading, setMarketLoading] = useState(true)

  // Load stats once
  useEffect(() => {
    api.get('/events/stats').then(r => setStats(r.data)).catch(() => {})
  }, [])

  // Persist watched to localStorage
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(watched)) } catch {}
  }, [watched])

  // Compute tickers to show in price widget
  const priceTickers = watched.length > 0
    ? watched.map(w => w.ticker)
    : (stats?.top_stocks ?? []).slice(0, 5).map(s => s.ticker)

  // Fetch live prices; re-run when tickers change
  useEffect(() => {
    if (!priceTickers.length) { setPrices([]); return }
    const fetchPrices = () => {
      api.get('/stocks/prices', { params: { tickers: priceTickers.join(',') } })
        .then(r => setPrices(r.data))
        .catch(() => {})
    }
    fetchPrices()
    if (priceIntervalRef.current) clearInterval(priceIntervalRef.current)
    priceIntervalRef.current = setInterval(fetchPrices, 60000)
    return () => clearInterval(priceIntervalRef.current)
  }, [priceTickers.join(',')])  // eslint-disable-line react-hooks/exhaustive-deps

  const handleWatchedChange = (next) => {
    setWatched(next)
    setFilters(f => ({ ...f, page: 1 }))
  }

  // Fetch one section independently
  const fetchSection = useCallback((hasStocks, page, setItems, setTotalPages, setTotal, setLoad) => {
    setLoad(true)
    // Destructure `page` out of filters so it doesn't overwrite the section-specific page number
    const { page: _filterPage, ...otherFilters } = filters
    const params = { limit: 15, page, has_stocks: hasStocks, ...otherFilters }
    // Exclude neutral by default unless user explicitly selected a sentiment or toggled it on
    if (!showNeutral && !filters.sentiment) params.exclude_neutral = true
    if (watched.length > 0) params.tickers = watched.map(w => w.ticker).join(',')
    // Remove empty params
    Object.keys(params).forEach(k => { if (params[k] === '' || params[k] === undefined) delete params[k] })
    api.get('/events', { params })
      .then(r => { setItems(r.data.events); setTotalPages(r.data.pages); setTotal(r.data.total) })
      .catch(() => {})
      .finally(() => setLoad(false))
  }, [filters, watched, showNeutral])

  useEffect(() => {
    fetchSection(true,  directPage, setDirectEvents, setDirectPages, setDirectTotal, setDirectLoading)
    fetchSection(false, marketPage, setMarketEvents, setMarketPages, setMarketTotal, setMarketLoading)
  }, [fetchSection, directPage, marketPage])

  // Reset section pages when filters / watched / neutral toggle change
  useEffect(() => {
    setDirectPage(1)
    setMarketPage(1)
  }, [filters, watched, showNeutral])

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-6">

      {/* Stat bar */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex flex-wrap items-center gap-6 border border-terminal-border rounded-lg px-5 py-3 mb-6 bg-terminal-surface"
      >
        <StatPill label="Events" value={stats?.total_events?.toLocaleString()} />
        <div className="w-px h-4 bg-terminal-border" />
        <StatPill label="Stocks Tracked" value={stats?.total_stocks} />
        <div className="w-px h-4 bg-terminal-border" />
        <StatPill label="Today" value={stats?.today_count} accent />
        <div className="w-px h-4 bg-terminal-border" />
        <StatPill label="Bullish" value={stats ? `${stats.bullish_pct}%` : '—'} accent />
      </motion.div>

      {/* Stock Watchlist */}
      <StockWatchlist watched={watched} onChange={handleWatchedChange} />

      {/* Charts row */}
      {stats && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6"
        >
          <SentimentDonut counts={stats.sentiment_counts} />
          <StockPriceCard tickers={priceTickers} prices={prices} />
          <TopStocksBar data={prices.slice().sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct))} />
        </motion.div>
      )}

      {/* Section label + filters */}
      <div className="flex items-center justify-between mb-4">
        <div className="font-ticker text-[10px] text-terminal-muted tracking-widest">
          LIVE EVENTS
          {!directLoading && !marketLoading && (
            <span className="ml-2 text-terminal-border">· {(directTotal + marketTotal).toLocaleString()} total</span>
          )}
        </div>
        <button
          onClick={() => setShowNeutral(v => !v)}
          className={`font-ticker text-[9px] tracking-widest px-2 py-1 rounded border transition-colors ${
            showNeutral
              ? 'border-terminal-muted/40 text-terminal-muted bg-terminal-surface hover:text-terminal-negative'
              : 'border-terminal-border/40 text-terminal-border hover:text-terminal-muted'
          }`}
        >
          {showNeutral ? '× HIDE NEUTRAL' : '+ INCLUDE NEUTRAL'}
        </button>
      </div>

      <EventFilters filters={filters} onChange={setFilters} />

      {/* Sections */}
      {(() => {
        const paginationBtns = (page, pages, setPage, accentClass) => pages > 1 && (
          <div className="flex items-center gap-3 mt-5">
            <button
              disabled={page <= 1}
              onClick={() => setPage(p => p - 1)}
              className={`font-ticker text-[10px] disabled:opacity-30 transition-colors tracking-widest px-3 py-1.5 border border-terminal-border rounded ${accentClass}`}
            >
              ← PREV
            </button>
            <span className="font-ticker text-[10px] text-terminal-muted tabular-nums">{page} / {pages}</span>
            <button
              disabled={page >= pages}
              onClick={() => setPage(p => p + 1)}
              className={`font-ticker text-[10px] disabled:opacity-30 transition-colors tracking-widest px-3 py-1.5 border border-terminal-border rounded ${accentClass}`}
            >
              NEXT →
            </button>
          </div>
        )

        const initialLoad = directLoading && !directEvents.length && marketLoading && !marketEvents.length

        if (initialLoad) return (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} className="h-36 bg-terminal-surface border border-terminal-border rounded-lg animate-pulse" />
            ))}
          </div>
        )

        return (
          <div>
            {/* DIRECT EXPOSURE */}
            <div className={`mb-8 ${directLoading ? 'opacity-50 pointer-events-none transition-opacity duration-150' : ''}`}>
              <div className="flex items-center justify-between bg-terminal-cyan/8 border border-terminal-cyan/20 rounded px-3 py-2 mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="w-0.5 h-4 bg-terminal-cyan rounded-full" />
                  <span className="font-ticker text-xs font-bold text-terminal-cyan tracking-widest">DIRECT EXPOSURE</span>
                </div>
                <span className="font-ticker text-[10px] font-bold bg-terminal-cyan/20 text-terminal-cyan px-2 py-0.5 rounded tracking-widest">
                  {directTotal} {directTotal === 1 ? 'EVENT' : 'EVENTS'}
                </span>
              </div>
              {directEvents.length === 0 && !directLoading ? (
                <div className="py-8 text-center font-ticker text-[10px] text-terminal-border tracking-widest">
                  NO DIRECT EXPOSURE EVENTS
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {directEvents.map((e, i) => <EventCard key={e.id} event={e} index={i} />)}
                </div>
              )}
              {paginationBtns(directPage, directPages, setDirectPage, 'text-terminal-muted hover:text-terminal-cyan hover:border-terminal-cyan/40')}
            </div>

            {/* MARKET SIGNALS */}
            <div className={`mb-8 ${marketLoading ? 'opacity-50 pointer-events-none transition-opacity duration-150' : ''}`}>
              <div className="flex items-center justify-between bg-terminal-amber/8 border border-terminal-amber/20 rounded px-3 py-2 mb-2">
                <div className="flex items-center gap-2.5">
                  <div className="w-0.5 h-4 bg-terminal-amber rounded-full" />
                  <span className="font-ticker text-xs font-bold text-terminal-amber tracking-widest">MARKET SIGNALS</span>
                </div>
                <span className="font-ticker text-[10px] font-bold bg-terminal-amber/20 text-terminal-amber px-2 py-0.5 rounded tracking-widest">
                  {marketTotal} {marketTotal === 1 ? 'EVENT' : 'EVENTS'}
                </span>
              </div>
              <p className="font-ticker text-[9px] text-terminal-muted tracking-wide mb-4 px-1">
                Macro &amp; sector events that may affect multiple stocks
              </p>
              {marketEvents.length === 0 && !marketLoading ? (
                <div className="py-8 text-center font-ticker text-[10px] text-terminal-border tracking-widest">
                  NO MARKET SIGNAL EVENTS
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {marketEvents.map((e, i) => <EventCard key={e.id} event={e} index={i} />)}
                </div>
              )}
              {paginationBtns(marketPage, marketPages, setMarketPage, 'text-terminal-muted hover:text-terminal-amber hover:border-terminal-amber/40')}
            </div>
          </div>
        )
      })()}
    </div>
  )
}
