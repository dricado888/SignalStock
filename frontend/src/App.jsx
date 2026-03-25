import { useState } from 'react'
import Header from './components/layout/Header'
import Dashboard from './pages/Dashboard'
import SubscribeModal from './components/SubscribeModal'
import PreferencesModal from './components/PreferencesModal'
import Unsubscribe from './pages/Unsubscribe'

// Check if we're on the /unsubscribe path
const path   = window.location.pathname
const search = new URLSearchParams(window.location.search)
const isUnsubscribePage = path === '/unsubscribe' || path.startsWith('/unsubscribe')
const unsubscribeToken  = search.get('token') || ''

export default function App() {
  const [subscribeOpen,   setSubscribeOpen]   = useState(false)
  const [preferencesOpen, setPreferencesOpen] = useState(false)

  // Render unsubscribe page if URL matches
  if (isUnsubscribePage) {
    return <Unsubscribe token={unsubscribeToken} />
  }

  return (
    <div className="min-h-screen bg-terminal-bg">
      <Header
        onSubscribe={() => setSubscribeOpen(true)}
        onManageAlerts={() => setPreferencesOpen(true)}
      />
      <Dashboard onSubscribe={() => setSubscribeOpen(true)} />
      <SubscribeModal  open={subscribeOpen}   onClose={() => setSubscribeOpen(false)} />
      <PreferencesModal open={preferencesOpen} onClose={() => setPreferencesOpen(false)} />
    </div>
  )
}
