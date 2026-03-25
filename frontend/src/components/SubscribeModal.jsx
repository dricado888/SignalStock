import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import api from '../utils/api'

export default function SubscribeModal({ open, onClose }) {
  const [email, setEmail]       = useState('')
  const [search, setSearch]     = useState('')
  const [results, setResults]   = useState([])
  const [selected, setSelected] = useState([])
  const [step, setStep]         = useState('form') // 'form' | 'success'
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [countdown, setCountdown] = useState(3)

  // Auto-close success screen after 3 seconds
  useEffect(() => {
    if (step !== 'success') return
    setCountdown(3)
    const interval = setInterval(() => setCountdown(c => c - 1), 1000)
    const timeout  = setTimeout(onClose, 3000)
    return () => { clearInterval(interval); clearTimeout(timeout) }
  }, [step, onClose])

  // Reset on open
  useEffect(() => {
    if (open) { setEmail(''); setSearch(''); setSelected([]); setStep('form'); setError('') }
  }, [open])

  // Stock search debounce
  useEffect(() => {
    if (!search.trim()) { setResults([]); return }
    const t = setTimeout(() => {
      api.get('/stocks', { params: { q: search, limit: 6 } }).then(r => setResults(r.data))
    }, 280)
    return () => clearTimeout(t)
  }, [search])

  const toggle = (stock) => {
    setSelected(s =>
      s.find(x => x.id === stock.id) ? s.filter(x => x.id !== stock.id) : [...s, stock]
    )
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!email) { setError('Enter your email'); return }
    if (!selected.length) { setError('Pick at least one stock'); return }
    setLoading(true); setError('')
    try {
      await api.post('/subscribe', { email, stock_ids: selected.map(s => s.id) })
      setStep('success')
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  // Close on backdrop click
  const onBackdrop = (e) => { if (e.target === e.currentTarget) onClose() }

  // Close on Escape
  useEffect(() => {
    const fn = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', fn)
    return () => window.removeEventListener('keydown', fn)
  }, [onClose])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
          onClick={onBackdrop}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.2 }}
            className="w-full max-w-md bg-terminal-surface border border-terminal-border rounded-xl p-6 shadow-2xl"
          >
            {step === 'success' ? (
              <div className="text-center py-6">
                <div className="w-10 h-10 rounded-full border border-terminal-positive flex items-center justify-center mx-auto mb-4 text-terminal-positive text-lg">
                  ✓
                </div>
                <div className="font-ticker text-sm font-bold text-terminal-text mb-2 tracking-wide">
                  CHECK YOUR EMAIL
                </div>
                <p className="text-terminal-subtext text-xs">
                  We've sent a confirmation link to <span className="text-terminal-cyan">{email}</span>.
                  Click it to activate your alerts.
                </p>
                <p className="font-ticker text-[9px] text-terminal-border mt-4 tracking-widest">
                  CLOSING IN {countdown}S...
                </p>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-5">
                  <div>
                    <div className="font-ticker text-xs font-bold text-terminal-text tracking-widest">
                      GET ALERTS
                    </div>
                    <div className="font-ticker text-[10px] text-terminal-muted mt-0.5">
                      Email alerts when events hit your stocks
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    className="text-terminal-muted hover:text-terminal-text transition-colors text-lg leading-none"
                  >
                    ×
                  </button>
                </div>

                <form onSubmit={submit} className="space-y-4">
                  {/* Email */}
                  <div>
                    <label className="font-ticker text-[10px] text-terminal-muted tracking-widest block mb-1.5">
                      EMAIL
                    </label>
                    <input
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="w-full bg-terminal-bg border border-terminal-border rounded px-3 py-2 text-sm text-terminal-text placeholder:text-terminal-muted focus:outline-none focus:border-terminal-cyan/50 transition-colors"
                    />
                  </div>

                  {/* Stock search */}
                  <div>
                    <label className="font-ticker text-[10px] text-terminal-muted tracking-widest block mb-1.5">
                      WATCH STOCKS
                    </label>
                    <input
                      type="text"
                      value={search}
                      onChange={e => setSearch(e.target.value)}
                      placeholder="Search ticker or company..."
                      className="w-full bg-terminal-bg border border-terminal-border rounded px-3 py-2 text-sm text-terminal-text placeholder:text-terminal-muted focus:outline-none focus:border-terminal-cyan/50 transition-colors mb-2"
                    />

                    {/* Search results */}
                    {results.length > 0 && (
                      <div className="border border-terminal-border rounded overflow-hidden mb-2">
                        {results.map(s => {
                          const isSelected = selected.find(x => x.id === s.id)
                          return (
                            <button
                              key={s.id}
                              type="button"
                              onClick={() => toggle(s)}
                              className={`w-full flex items-center justify-between px-3 py-2 text-xs border-b border-terminal-border last:border-0 transition-colors ${
                                isSelected ? 'bg-terminal-cyan/10' : 'hover:bg-terminal-bg'
                              }`}
                            >
                              <span>
                                <span className="font-ticker font-bold text-terminal-cyan mr-2">${s.ticker}</span>
                                <span className="text-terminal-subtext">{s.company_name}</span>
                              </span>
                              {isSelected && <span className="text-terminal-cyan text-xs">✓</span>}
                            </button>
                          )
                        })}
                      </div>
                    )}

                    {/* Selected chips */}
                    {selected.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {selected.map(s => (
                          <button
                            key={s.id}
                            type="button"
                            onClick={() => toggle(s)}
                            className="font-ticker text-[10px] font-bold text-terminal-cyan bg-terminal-cyan/10 border border-terminal-cyan/30 px-2 py-0.5 rounded hover:bg-terminal-negative/10 hover:border-terminal-negative/30 hover:text-terminal-negative transition-colors"
                          >
                            ${s.ticker} ×
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {error && (
                    <div className="font-ticker text-[10px] text-terminal-negative tracking-wide">
                      ✕ {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-terminal-cyan text-terminal-bg font-ticker font-bold text-xs py-2.5 rounded tracking-widest hover:bg-terminal-cyan/90 disabled:opacity-50 transition-colors"
                  >
                    {loading ? 'SUBSCRIBING...' : 'SUBSCRIBE FOR FREE →'}
                  </button>

                  <p className="font-ticker text-[9px] text-terminal-muted text-center tracking-wide">
                    Free forever · Unsubscribe anytime
                  </p>
                </form>
              </>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
