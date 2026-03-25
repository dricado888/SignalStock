import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import api from '../utils/api'

const EVENT_TYPES = [
  { key: 'earnings_report',    label: 'Earnings Report' },
  { key: 'merger_acquisition', label: 'Merger & Acquisition' },
  { key: 'product_launch',     label: 'Product Launch' },
  { key: 'regulatory_action',  label: 'Regulatory Action' },
  { key: 'executive_change',   label: 'Executive Change' },
  { key: 'lawsuit',            label: 'Lawsuit' },
  { key: 'partnership',        label: 'Partnership' },
  { key: 'other',              label: 'Market News' },
]

const DEFAULT_PREFS = {
  email_enabled: true,
  notify_positive: true,
  notify_negative: true,
  notify_neutral: false,
  notify_event_types: EVENT_TYPES.filter(e => e.key !== 'other').map(e => e.key),
}

function Toggle({ checked, onChange, label, sublabel }) {
  return (
    <label className="flex items-center justify-between cursor-pointer gap-3">
      <div>
        <div className="font-ticker text-xs text-terminal-text">{label}</div>
        {sublabel && <div className="font-ticker text-[9px] text-terminal-muted mt-0.5">{sublabel}</div>}
      </div>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative w-8 h-4 rounded-full transition-colors ${checked ? 'bg-terminal-cyan' : 'bg-terminal-border'}`}
      >
        <span
          className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${checked ? 'translate-x-4' : 'translate-x-0.5'}`}
        />
      </button>
    </label>
  )
}

export default function PreferencesModal({ open, onClose }) {
  const [step, setStep]       = useState('login')  // 'login' | 'prefs' | 'saved'
  const [email, setEmail]     = useState('')
  const [password, setPassword] = useState('')
  const [prefs, setPrefs]     = useState(DEFAULT_PREFS)
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(false)
  const [token, setToken]     = useState(() => localStorage.getItem('ss_token') || '')

  // If already logged in, load prefs directly
  useEffect(() => {
    if (!open) return
    setError('')
    const saved = localStorage.getItem('ss_token')
    if (saved) { setToken(saved); setStep('prefs') }
    else { setStep('login') }
  }, [open])

  const loadPrefs = useCallback(async (t) => {
    try {
      const r = await api.get('/preferences', { headers: { Authorization: `Bearer ${t}` } })
      setPrefs(r.data)
    } catch {
      setPrefs(DEFAULT_PREFS)
    }
  }, [])

  useEffect(() => {
    if (step === 'prefs' && token) loadPrefs(token)
  }, [step, token, loadPrefs])

  const login = async (e) => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const r = await api.post('/auth/login', { email, password })
      const t = r.data.token
      localStorage.setItem('ss_token', t)
      setToken(t)
      setStep('prefs')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  const save = async () => {
    setLoading(true); setError('')
    try {
      await api.put('/preferences', prefs, { headers: { Authorization: `Bearer ${token}` } })
      setStep('saved')
      setTimeout(() => { setStep('prefs') }, 1500)
    } catch (err) {
      if (err.response?.status === 401) {
        localStorage.removeItem('ss_token'); setToken(''); setStep('login')
      } else {
        setError('Failed to save. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const unsubscribeAll = async () => {
    setLoading(true)
    try {
      await api.put('/preferences', { ...prefs, email_enabled: false }, { headers: { Authorization: `Bearer ${token}` } })
      setPrefs(p => ({ ...p, email_enabled: false }))
    } catch { setError('Failed to unsubscribe.') }
    finally { setLoading(false) }
  }

  const toggleEventType = (key) => {
    setPrefs(p => ({
      ...p,
      notify_event_types: p.notify_event_types.includes(key)
        ? p.notify_event_types.filter(k => k !== key)
        : [...p.notify_event_types, key],
    }))
  }

  const onBackdrop = (e) => { if (e.target === e.currentTarget) onClose() }

  useEffect(() => {
    const fn = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', fn)
    return () => window.removeEventListener('keydown', fn)
  }, [onClose])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
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
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
              <div>
                <div className="font-ticker text-xs font-bold text-terminal-text tracking-widest">
                  {step === 'login' ? 'SIGN IN TO MANAGE ALERTS' : 'EMAIL PREFERENCES'}
                </div>
                <div className="font-ticker text-[10px] text-terminal-muted mt-0.5">
                  {step === 'login' ? 'Use your SignalStock account' : 'Control what alerts you receive'}
                </div>
              </div>
              <button onClick={onClose} className="text-terminal-muted hover:text-terminal-text transition-colors text-lg leading-none">×</button>
            </div>

            {/* Login step */}
            {step === 'login' && (
              <form onSubmit={login} className="space-y-4">
                <div>
                  <label className="font-ticker text-[10px] text-terminal-muted tracking-widest block mb-1.5">EMAIL</label>
                  <input
                    type="email" value={email} onChange={e => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="w-full bg-terminal-bg border border-terminal-border rounded px-3 py-2 text-sm text-terminal-text placeholder:text-terminal-muted focus:outline-none focus:border-terminal-cyan/50 transition-colors"
                  />
                </div>
                <div>
                  <label className="font-ticker text-[10px] text-terminal-muted tracking-widest block mb-1.5">PASSWORD</label>
                  <input
                    type="password" value={password} onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-terminal-bg border border-terminal-border rounded px-3 py-2 text-sm text-terminal-text placeholder:text-terminal-muted focus:outline-none focus:border-terminal-cyan/50 transition-colors"
                  />
                </div>
                {error && <div className="font-ticker text-[10px] text-terminal-negative tracking-wide">✕ {error}</div>}
                <button
                  type="submit" disabled={loading}
                  className="w-full bg-terminal-cyan text-terminal-bg font-ticker font-bold text-xs py-2.5 rounded tracking-widest hover:bg-terminal-cyan/90 disabled:opacity-50 transition-colors"
                >
                  {loading ? 'SIGNING IN...' : 'SIGN IN →'}
                </button>
              </form>
            )}

            {/* Preferences step */}
            {(step === 'prefs' || step === 'saved') && (
              <div className="space-y-5">
                {/* Global toggle */}
                <div className="bg-terminal-bg border border-terminal-border rounded-lg p-4">
                  <Toggle
                    checked={prefs.email_enabled}
                    onChange={v => setPrefs(p => ({ ...p, email_enabled: v }))}
                    label="Email alerts enabled"
                    sublabel={prefs.email_enabled ? 'You will receive alert emails' : 'All alert emails are paused'}
                  />
                </div>

                {prefs.email_enabled && (
                  <>
                    {/* Sentiment filters */}
                    <div>
                      <div className="font-ticker text-[9px] text-terminal-muted tracking-widest mb-2">NOTIFY FOR SENTIMENT</div>
                      <div className="bg-terminal-bg border border-terminal-border rounded-lg p-4 space-y-3">
                        <Toggle checked={prefs.notify_positive} onChange={v => setPrefs(p => ({ ...p, notify_positive: v }))} label="Bullish events" sublabel="Positive market signals" />
                        <Toggle checked={prefs.notify_negative} onChange={v => setPrefs(p => ({ ...p, notify_negative: v }))} label="Bearish events" sublabel="Negative market signals" />
                        <Toggle checked={prefs.notify_neutral}  onChange={v => setPrefs(p => ({ ...p, notify_neutral: v  }))} label="Neutral events"  sublabel="Informational signals" />
                      </div>
                    </div>

                    {/* Event type filters */}
                    <div>
                      <div className="font-ticker text-[9px] text-terminal-muted tracking-widest mb-2">NOTIFY FOR EVENT TYPES</div>
                      <div className="bg-terminal-bg border border-terminal-border rounded-lg p-4 grid grid-cols-2 gap-3">
                        {EVENT_TYPES.map(({ key, label }) => (
                          <Toggle
                            key={key}
                            checked={prefs.notify_event_types.includes(key)}
                            onChange={() => toggleEventType(key)}
                            label={label}
                          />
                        ))}
                      </div>
                    </div>
                  </>
                )}

                {error && <div className="font-ticker text-[10px] text-terminal-negative tracking-wide">✕ {error}</div>}

                {step === 'saved' && (
                  <div className="font-ticker text-[10px] text-terminal-positive tracking-wide text-center">✓ PREFERENCES SAVED</div>
                )}

                <div className="flex gap-3">
                  <button
                    onClick={save} disabled={loading || step === 'saved'}
                    className="flex-1 bg-terminal-cyan text-terminal-bg font-ticker font-bold text-xs py-2.5 rounded tracking-widest hover:bg-terminal-cyan/90 disabled:opacity-50 transition-colors"
                  >
                    {loading ? 'SAVING...' : step === 'saved' ? '✓ SAVED' : 'SAVE PREFERENCES'}
                  </button>
                  <button
                    onClick={unsubscribeAll} disabled={loading || !prefs.email_enabled}
                    className="font-ticker text-[10px] text-terminal-negative border border-terminal-negative/30 px-3 rounded hover:bg-terminal-negative/10 disabled:opacity-30 transition-colors tracking-wide"
                  >
                    UNSUBSCRIBE ALL
                  </button>
                </div>

                <button
                  onClick={() => { localStorage.removeItem('ss_token'); setToken(''); setStep('login'); setEmail(''); setPassword('') }}
                  className="w-full font-ticker text-[9px] text-terminal-muted hover:text-terminal-subtext transition-colors tracking-widest"
                >
                  SIGN OUT
                </button>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
