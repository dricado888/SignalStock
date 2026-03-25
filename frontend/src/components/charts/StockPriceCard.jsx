import { useState, useEffect } from 'react'

const DIR_ICON  = { up: '▲', down: '▼', flat: '→' }
const DIR_CLASS = { up: 'text-terminal-positive', down: 'text-terminal-negative', flat: 'text-terminal-muted' }

export default function StockPriceCard({ tickers = [], prices = [] }) {
  const [countdown, setCountdown] = useState(60)

  // Countdown to next refresh
  useEffect(() => {
    setCountdown(60)
    const t = setInterval(() => setCountdown(c => (c <= 1 ? 60 : c - 1)), 1000)
    return () => clearInterval(t)
  }, [prices])

  const noKey     = tickers.length > 0 && prices.length === 0
  const noTickers = tickers.length === 0

  return (
    <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4 h-48 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="font-ticker text-[10px] text-terminal-muted tracking-widest">LIVE PRICES</span>
        {prices.length > 0 && (
          <span className="font-ticker text-[9px] text-terminal-border tracking-widest">↻ {countdown}s</span>
        )}
      </div>

      {/* Body */}
      {noTickers ? (
        <div className="flex-1 flex items-center justify-center">
          <span className="font-ticker text-[10px] text-terminal-border text-center tracking-wide leading-relaxed">
            ADD STOCKS TO WATCHLIST<br />TO SEE LIVE PRICES
          </span>
        </div>
      ) : noKey ? (
        <div className="flex-1 flex items-center justify-center">
          <span className="font-ticker text-[10px] text-terminal-border text-center tracking-wide leading-relaxed">
            PRICE DATA UNAVAILABLE<br />SET FINNHUB_API_KEY
          </span>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
          {prices.map(p => (
            <div key={p.ticker} className="flex items-center justify-between">
              <span className="font-ticker text-xs font-bold text-terminal-cyan w-14 shrink-0">
                ${p.ticker}
              </span>
              <span className="font-ticker text-xs text-terminal-text tabular-nums flex-1 text-right mr-3">
                {p.price != null ? p.price.toFixed(2) : '—'}
              </span>
              <span className={`font-ticker text-xs font-bold tabular-nums w-20 text-right ${DIR_CLASS[p.direction] ?? 'text-terminal-muted'}`}>
                {DIR_ICON[p.direction] ?? '→'} {p.change_pct != null ? `${p.change_pct > 0 ? '+' : ''}${p.change_pct.toFixed(2)}%` : '—'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
