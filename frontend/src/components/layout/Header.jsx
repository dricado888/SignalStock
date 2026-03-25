import { motion } from 'framer-motion'

export default function Header({ onSubscribe, onManageAlerts }) {
  return (
    <header className="sticky top-0 z-50 border-b border-terminal-border bg-terminal-bg/90 backdrop-blur-sm">
      <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-terminal-cyan animate-pulse" />
          <span className="font-ticker font-bold text-sm tracking-[0.15em] text-terminal-text uppercase">
            SignalStock
          </span>
          <span className="hidden sm:block text-terminal-muted text-xs tracking-widest uppercase">
            · Market Intelligence
          </span>
        </div>

        {/* Right: live indicator + CTA */}
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-terminal-muted font-ticker">
            <span className="w-1.5 h-1.5 rounded-full bg-terminal-positive animate-pulse" />
            LIVE
          </div>
          <button
            onClick={onManageAlerts}
            className="hidden sm:block font-ticker text-[10px] text-terminal-muted hover:text-terminal-subtext transition-colors tracking-widest"
          >
            MANAGE ALERTS
          </button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={onSubscribe}
            className="flex items-center gap-2 px-4 py-1.5 border border-terminal-cyan/50 rounded text-terminal-cyan text-xs font-ticker font-semibold hover:bg-terminal-cyan/10 transition-colors tracking-wide"
          >
            GET ALERTS
            <span className="text-base leading-none">→</span>
          </motion.button>
        </div>
      </div>
    </header>
  )
}
