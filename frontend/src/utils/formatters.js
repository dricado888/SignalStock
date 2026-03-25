import { formatDistanceToNow, format } from 'date-fns'

export const EVENT_TYPE_CONFIG = {
  earnings_report:    { label: 'EARNINGS',     short: 'ERN' },
  merger_acquisition: { label: 'M&A',          short: 'M&A' },
  product_launch:     { label: 'PRODUCT',      short: 'PRD' },
  regulatory_action:  { label: 'REGULATORY',   short: 'REG' },
  executive_change:   { label: 'EXEC CHANGE',  short: 'EXE' },
  lawsuit:            { label: 'LAWSUIT',      short: 'LAW' },
  partnership:        { label: 'PARTNERSHIP',  short: 'PRT' },
  other:              { label: 'MARKET NEWS',  short: 'MKT' },
}

export const SENTIMENT_CONFIG = {
  positive: { label: 'BULLISH', icon: '↑', color: '#4ade80', tw: 'text-terminal-positive' },
  negative: { label: 'BEARISH', icon: '↓', color: '#f87171', tw: 'text-terminal-negative' },
  neutral:  { label: 'NEUTRAL', icon: '→', color: '#a1a1aa', tw: 'text-terminal-subtext'  },
}

export const EVENT_TYPE_OPTIONS = Object.entries(EVENT_TYPE_CONFIG).map(
  ([value, { label }]) => ({ value, label })
)

export function formatRelative(dateStr) {
  if (!dateStr) return '—'
  try { return formatDistanceToNow(new Date(dateStr), { addSuffix: true }) }
  catch { return '—' }
}

export function formatDate(dateStr) {
  if (!dateStr) return '—'
  try { return format(new Date(dateStr), 'MMM d, yyyy HH:mm') }
  catch { return '—' }
}

export function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

// Sector hint detection — scans article title for keywords
const SECTOR_KEYWORDS = [
  { label: 'DEFENSE',  keywords: ['war', 'military', 'nato', 'defense', 'defence', 'pentagon', 'arms', 'weapon', 'missile', 'troops'] },
  { label: 'ENERGY',   keywords: ['oil', 'gas', 'energy', 'solar', 'wind', 'nuclear', 'opec', 'crude', 'pipeline', 'lng', 'refinery'] },
  { label: 'FINANCE',  keywords: ['rate', 'inflation', 'federal reserve', 'fed ', 'mortgage', 'bond', 'treasury', 'interest', 'lending', 'bank'] },
  { label: 'TECH',     keywords: ['chip', 'semiconductor', ' ai ', 'artificial intelligence', 'software', 'cloud', 'cyber', 'data center', 'quantum'] },
  { label: 'HEALTH',   keywords: ['fda', ' drug ', 'pharma', 'vaccine', 'clinical', 'biotech', 'medicare', 'medicaid', 'hospital'] },
  { label: 'RETAIL',   keywords: ['retail store', 'e-commerce', 'brick and mortar', 'consumer staples', 'grocery', 'merchandise', 'department store', 'online shopping', 'shopify', 'walmart', 'amazon', 'target', 'costco', 'retail sales', 'foot traffic', 'same-store sales'] },
]

export function getSectorHints(title) {
  if (!title) return []
  const lower = ` ${title.toLowerCase()} `
  const matches = SECTOR_KEYWORDS.filter(s =>
    s.keywords.some(kw => lower.includes(kw))
  )
  return matches.slice(0, 2).map(s => s.label)
}
