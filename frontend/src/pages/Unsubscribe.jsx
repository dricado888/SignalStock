import { useEffect, useState } from 'react'
import api from '../utils/api'

export default function Unsubscribe({ token }) {
  const [status, setStatus] = useState('loading')  // 'loading' | 'success' | 'error'
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) { setStatus('error'); setMessage('No unsubscribe token provided.'); return }
    api.get('/auth/unsubscribe', { params: { token } })
      .then(() => { setStatus('success') })
      .catch(err => {
        setStatus('error')
        setMessage(err.response?.data?.detail || 'Invalid or expired unsubscribe link.')
      })
  }, [token])

  return (
    <div className="min-h-screen bg-terminal-bg flex items-center justify-center p-6">
      <div className="max-w-sm w-full bg-terminal-surface border border-terminal-border rounded-xl p-8 text-center">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className="w-2 h-2 rounded-full bg-terminal-cyan" />
          <span className="font-ticker font-bold text-sm tracking-[0.15em] text-terminal-text uppercase">SignalStock</span>
        </div>

        {status === 'loading' && (
          <div className="font-ticker text-xs text-terminal-muted tracking-widest animate-pulse">UNSUBSCRIBING...</div>
        )}

        {status === 'success' && (
          <>
            <div className="w-12 h-12 rounded-full border border-terminal-positive/50 flex items-center justify-center mx-auto mb-5 text-terminal-positive text-xl">
              ✓
            </div>
            <div className="font-ticker text-sm font-bold text-terminal-text tracking-wide mb-2">
              UNSUBSCRIBED
            </div>
            <p className="text-terminal-subtext text-xs mb-6 leading-relaxed">
              You've been removed from all SignalStock email alerts.
              You can re-enable them anytime from your preferences.
            </p>
            <button
              onClick={() => window.location.href = '/'}
              className="font-ticker text-[10px] text-terminal-cyan border border-terminal-cyan/30 px-4 py-2 rounded hover:bg-terminal-cyan/10 transition-colors tracking-widest"
            >
              MANAGE PREFERENCES →
            </button>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="w-12 h-12 rounded-full border border-terminal-negative/50 flex items-center justify-center mx-auto mb-5 text-terminal-negative text-xl">
              ✕
            </div>
            <div className="font-ticker text-sm font-bold text-terminal-text tracking-wide mb-2">
              LINK INVALID
            </div>
            <p className="text-terminal-subtext text-xs mb-6">{message}</p>
            <button
              onClick={() => window.location.href = '/'}
              className="font-ticker text-[10px] text-terminal-cyan border border-terminal-cyan/30 px-4 py-2 rounded hover:bg-terminal-cyan/10 transition-colors tracking-widest"
            >
              GO TO DASHBOARD
            </button>
          </>
        )}
      </div>
    </div>
  )
}
