import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App.jsx"
import "./index.css"

function useEventWebSocket(path = '/ws/events') {
  const [events, setEvents] = useState([])
  const wsRef = useRef(null)
  const reconnectRef = useRef(0)

  useEffect(() => {
    let mounted = true
    const connect = () => {
      const loc = window.location
      const protocol = loc.protocol === 'https:' ? 'wss' : 'ws'
      const host = loc.host
      const url = `${protocol}://${host}${path}`
      wsRef.current = new WebSocket(url)

      wsRef.current.onopen = () => {
        reconnectRef.current = 0
        console.info('WS connected:', url)
      }

      wsRef.current.onmessage = (e) => {
        if (!mounted) return
        try {
          const msg = JSON.parse(e.data)
          setEvents(prev => [msg, ...prev].slice(0, 200))
        } catch {}
      }

      wsRef.current.onclose = () => {
        if (!mounted) return
        const backoff = Math.min(10000, 1000 * (1 + reconnectRef.current))
        reconnectRef.current += 1
        setTimeout(connect, backoff)
      }

      wsRef.current.onerror = () => {
        try { wsRef.current.close() } catch {}
      }
    }

    connect()
    return () => { mounted = false; try { wsRef.current?.close() } catch {} }
  }, [path])
  return events
}

function Dashboard() {
  const events = useEventWebSocket('/ws/events')

  return (
    <div className="min-h-screen bg-orange-300 flex flex-col items-center py-10 text-gray-800">
      <h1 className="text-3xl font-bold mb-2">THE13TH Event Dashboard</h1>
      <p className="text-sm mb-6">Event monitoring is live and connected.</p>

      <div className="w-full max-w-3xl bg-white rounded-lg shadow p-4 overflow-auto">
        <div className="flex justify-between mb-3">
          <h2 className="font-semibold">Live Events</h2>
          <span className="text-xs text-gray-500">{events.length} events</span>
        </div>

        <div className="space-y-2 max-h-[500px] overflow-y-auto">
          {events.length === 0 ? (
            <div className="text-sm text-gray-500">No events yet...</div>
          ) : (
            events.map((ev, i) => (
              <div key={i} className="border p-2 rounded text-sm bg-gray-50">
                <div className="text-xs text-gray-500">{ev.timestamp ?? new Date().toISOString()}</div>
                <div className="font-medium">{ev.type}</div>
                <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(ev.data, null, 2)}</pre>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
