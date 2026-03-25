import { motion } from 'framer-motion'
import { EVENT_TYPE_CONFIG, SENTIMENT_CONFIG, formatRelative, getSectorHints } from '../../utils/formatters'

const SECTOR_ICONS = { DEFENSE: '🛡', ENERGY: '⚡', FINANCE: '🏦', TECH: '💻', HEALTH: '🩺', RETAIL: '🛒' }

export default function EventCard({ event, index = 0 }) {
  const typeCfg      = EVENT_TYPE_CONFIG[event.event_type] ?? EVENT_TYPE_CONFIG.other
  const sentimentCfg = SENTIMENT_CONFIG[event.sentiment]   ?? SENTIMENT_CONFIG.neutral
  const stocks       = Array.isArray(event.stocks) ? event.stocks : []
  const pubDate      = event.published_at || event.classified_at
  // Show sector hints on market news OR events with no linked stocks
  const showSectors    = event.event_type === 'other' || stocks.length === 0
  const sectors        = showSectors ? getSectorHints(event.article_title) : []
  const isMarketSignal = stocks.length === 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.04 }}
      className="group relative bg-terminal-surface border border-terminal-border rounded-lg p-4 hover:border-terminal-cyan/40 hover:shadow-cyan-glow transition-all duration-200 cursor-default"
    >
      {/* Top row: event type + sentiment */}
      <div className="flex items-center justify-between mb-3">
        <span className="font-ticker text-[10px] font-semibold text-terminal-muted tracking-widest">
          {typeCfg.label}
        </span>
        <span className={`font-ticker text-[10px] font-bold tracking-widest flex items-center gap-1 ${sentimentCfg.tw}`}>
          <span>{sentimentCfg.icon}</span>
          {sentimentCfg.label}
        </span>
      </div>

      {/* Tickers */}
      {stocks.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {stocks.map(s => (
            <span
              key={s.ticker}
              title={s.company_name}
              className="font-ticker text-xs font-bold text-terminal-cyan"
            >
              ${s.ticker}
            </span>
          ))}
        </div>
      )}

      {/* Article title */}
      <p className="text-sm font-medium text-terminal-text leading-snug mb-3 line-clamp-2">
        {event.article_title}
      </p>

      {/* Sector hints */}
      {sectors.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {sectors.map(s => (
            <span
              key={s}
              className="font-ticker text-[9px] text-terminal-muted border border-terminal-border rounded px-1.5 py-0.5 tracking-widest"
            >
              {SECTOR_ICONS[s]} {s}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[10px] font-ticker text-terminal-muted tracking-wide">
          {event.article_source && (
            <span className="uppercase">{event.article_source}</span>
          )}
          {event.article_source && <span>·</span>}
          <span>{formatRelative(pubDate)}</span>
        </div>
        <a
          href={event.article_url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-ticker text-[10px] text-terminal-muted hover:text-terminal-cyan transition-colors tracking-widest"
        >
          READ →
        </a>
      </div>

      {/* Left-edge glow on hover — cyan for direct exposure, muted for market signals */}
      <div className={`absolute left-0 top-1/4 bottom-1/4 w-px transition-colors duration-200 rounded-full ${
        isMarketSignal
          ? 'bg-terminal-muted/0 group-hover:bg-terminal-muted/50'
          : 'bg-terminal-cyan/0 group-hover:bg-terminal-cyan/60'
      }`} />
    </motion.div>
  )
}
