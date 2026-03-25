import { useEffect, useState, useCallback } from 'react'
import api from '../utils/api'
import EventCard from '../components/events/EventCard'
import EventFilters from '../components/events/EventFilters'

export default function EventsPage() {
  const [events, setEvents]   = useState([])
  const [total, setTotal]     = useState(0)
  const [pages, setPages]     = useState(1)
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ page: 1 })

  const fetchEvents = useCallback(() => {
    setLoading(true)
    const params = { limit: 20, ...filters }
    // Remove empty strings so API doesn't get empty filter params
    Object.keys(params).forEach(k => { if (params[k] === '') delete params[k] })
    api.get('/events', { params })
      .then(r => {
        setEvents(r.data.events)
        setTotal(r.data.total)
        setPages(r.data.pages)
      })
      .finally(() => setLoading(false))
  }, [filters])

  useEffect(() => { fetchEvents() }, [fetchEvents])

  const goToPage = (p) => setFilters(f => ({ ...f, page: p }))

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-baseline justify-between mb-1">
        <h1 className="text-2xl font-bold text-slate-900">Events</h1>
        {!loading && (
          <span className="text-sm text-slate-400">{total.toLocaleString()} total</span>
        )}
      </div>
      <p className="text-slate-500 text-sm mb-6">All detected market events</p>

      <EventFilters filters={filters} onChange={setFilters} />

      {loading ? (
        <div className="text-center py-20 text-slate-400">Loading events…</div>
      ) : events.length === 0 ? (
        <div className="text-center py-20 text-slate-400">
          No events match your filters.
        </div>
      ) : (
        <>
          <div className="grid md:grid-cols-2 gap-4 mb-8">
            {events.map(e => <EventCard key={e.id} event={e} />)}
          </div>

          {/* Pagination */}
          {pages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                disabled={filters.page <= 1}
                onClick={() => goToPage(filters.page - 1)}
                className="px-4 py-2 text-sm rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 transition-colors"
              >
                ← Prev
              </button>
              <span className="text-sm text-slate-500 px-3">
                Page {filters.page} of {pages}
              </span>
              <button
                disabled={filters.page >= pages}
                onClick={() => goToPage(filters.page + 1)}
                className="px-4 py-2 text-sm rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 transition-colors"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
