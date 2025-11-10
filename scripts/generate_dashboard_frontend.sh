#!/usr/bin/env bash
set -euo pipefail

# Script: generate_dashboard_frontend.sh
# Purpose: Create React + Tailwind Minimalist Pro SaaS dashboard files for THE13TH
# Place this script at: saas_demo/scripts/generate_dashboard_frontend.sh
# Run: (from project root) bash scripts/generate_dashboard_frontend.sh

ROOT_DIR="$(pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend/src"
SCRIPT_PATH="$ROOT_DIR/scripts/generate_dashboard_frontend.sh"

mkdir -p "$FRONTEND_DIR/components"
mkdir -p "$FRONTEND_DIR/pages"

cat > "$FRONTEND_DIR/App.jsx" <<'EOF'
/* App.jsx generated: mounts layout + routes for THE13TH */
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import EventFeedPage from './pages/EventFeed'
import RulesEditorPage from './pages/RulesEditor'
import ScoreAnalytics from './pages/ScoreAnalytics'

export default function App(){
  return (
    <BrowserRouter>
      <div className="min-h-screen flex bg-[#0d0d0d] text-gray-200">
        <Sidebar />
        <main className="flex-1 p-6">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace/>} />
            <Route path="/dashboard" element={<Dashboard/>} />
            <Route path="/events" element={<EventFeedPage/>} />
            <Route path="/rules" element={<RulesEditorPage/>} />
            <Route path="/score" element={<ScoreAnalytics/>} />
            <Route path="*" element={<Navigate to="/dashboard" replace/>} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
EOF

cat > "$FRONTEND_DIR/components/Sidebar.jsx" <<'EOF'
/* Sidebar.jsx for THE13TH (Minimalist Pro SaaS — grey/purple outline buttons) */
import React from 'react'
import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/events', label: 'Event Feed' },
  { to: '/rules', label: 'Rules Editor' },
  { to: '/score', label: 'Score Analytics' },
]

export default function Sidebar(){
  return (
    <aside className="w-72 border-r border-gray-800 bg-[#0b0b0b] flex flex-col p-6">
      <div className="mb-8">
        <div className="text-2xl font-semibold tracking-wide">THE13TH</div>
        <div className="text-sm text-gray-400 mt-1">Admin Intelligence</div>
      </div>

      <nav className="flex-1 space-y-2">
        {navItems.map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            className={({isActive}) =>
              `block w-full text-left px-4 py-2 rounded-md transition-all text-gray-200 ${isActive ? 'border border-purple-500 text-purple-300' : 'border border-transparent hover:border-purple-700'} `
            }
          >
            {it.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-6">
        <button className="w-full px-4 py-2 rounded-md border border-purple-600 text-purple-300 hover:bg-purple-700/10 transition">Connect</button>
      </div>
    </aside>
  )
}
EOF

cat > "$FRONTEND_DIR/components/ScoreChart.jsx" <<'EOF'
/* ScoreChart.jsx — simple placeholder chart using CSS */
import React from 'react'

export default function ScoreChart({score=0}){
  return (
    <div className="bg-gray-900 border border-gray-800 p-4 rounded-md">
      <div className="text-sm text-gray-400">Current Score</div>
      <div className="text-3xl font-bold text-purple-300">{score}</div>
      <div className="mt-3 h-2 bg-gray-800 rounded overflow-hidden">
        <div className="h-full bg-gradient-to-r from-purple-600 to-purple-400" style={{width: Math.min(100, Math.max(0, score)) + '%'}} />
      </div>
    </div>
  )
}
EOF

cat > "$FRONTEND_DIR/components/EventFeed.jsx" <<'EOF'
/* EventFeed.jsx — live list of events */
import React from 'react'

export default function EventFeed({events=[]}){
  return (
    <div className="bg-gray-900 border border-gray-800 p-4 rounded-md space-y-3">
      {events.length===0 ? (
        <div className="text-sm text-gray-500">No events yet</div>
      ) : events.map((ev,i)=> (
        <div key={i} className="p-2 bg-gray-800 border border-gray-700 rounded">
          <div className="text-sm font-mono text-gray-300">{ev.action} — <span className="text-gray-400">{ev.user}</span></div>
          <div className="text-xs text-gray-500">{ev.timestamp}</div>
        </div>
      ))}
    </div>
  )
}
EOF

cat > "$FRONTEND_DIR/components/RulesEditor.jsx" <<'EOF'
/* RulesEditor.jsx — simple rules textarea */
import React, {useState} from 'react'

export default function RulesEditor({initial=''}){
  const [val, setVal] = useState(initial)
  return (
    <div className="bg-gray-900 border border-gray-800 p-4 rounded-md">
      <label className="text-sm text-gray-400">Rule Engine</label>
      <textarea value={val} onChange={(e)=>setVal(e.target.value)} className="w-full mt-2 p-2 rounded bg-[#080808] border border-gray-700 text-gray-200 min-h-[120px]" />
      <div className="mt-3 flex gap-2">
        <button className="px-3 py-1 rounded border border-purple-600 text-purple-300 hover:bg-purple-700/10">Save Rules</button>
        <button className="px-3 py-1 rounded border border-gray-700 text-gray-300">Reset</button>
      </div>
    </div>
  )
}
EOF

cat > "$FRONTEND_DIR/pages/Dashboard.jsx" <<'EOF'
/* Dashboard.jsx — main dashboard page */
import React, {useEffect, useState} from 'react'
import ScoreChart from '../components/ScoreChart'
import EventFeed from '../components/EventFeed'
import RulesEditor from '../components/RulesEditor'

export default function Dashboard(){
  const [events,setEvents] = useState([])
  const [score,setScore] = useState(0)

  useEffect(()=>{
    // lightweight poll for demo (connect to backend later via api.js)
    const t = setInterval(async ()=>{
      try{
        const r = await fetch('/admin/intel').then(r=>r.json())
        setEvents(r.events?.slice(0,8) || [])
        // compute a simple score for demo
        setScore(Math.floor((r.events?.length || 0) % 100))
      }catch(e){/* ignore */}
    },3000)
    return ()=>clearInterval(t)
  },[])

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <RulesEditor />
        </div>
        <div className="col-span-1">
          <ScoreChart score={score} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold mb-3">Live Event Feed</h3>
          <EventFeed events={events} />
        </div>

        <div>
          <h3 className="text-lg font-semibold mb-3">Recent Actions</h3>
          <div className="bg-gray-900 border border-gray-800 p-4 rounded-md text-sm text-gray-400">No recent actions</div>
        </div>
      </div>
    </div>
  )
}
EOF

cat > "$FRONTEND_DIR/pages/EventFeed.jsx" <<'EOF'
/* pages/EventFeed.jsx */
import React from 'react'
import EventFeed from '../components/EventFeed'
export default function EventFeedPage(){
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">Event Feed</h2>
      <EventFeed events={[]} />
    </div>
  )
}
EOF

cat > "$FRONTEND_DIR/pages/RulesEditor.jsx" <<'EOF'
/* pages/RulesEditor.jsx */
import React from 'react'
import RulesEditor from '../components/RulesEditor'
export default function RulesEditorPage(){
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">Rules Editor</h2>
      <RulesEditor />
    </div>
  )
}
EOF

cat > "$FRONTEND_DIR/pages/ScoreAnalytics.jsx" <<'EOF'
/* pages/ScoreAnalytics.jsx */
import React from 'react'
export default function ScoreAnalytics(){
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">Score Analytics</h2>
      <div className="bg-gray-900 border border-gray-800 p-4 rounded-md text-sm text-gray-400">Analytics coming soon</div>
    </div>
  )
}
EOF

cat > "$FRONTEND_DIR/api.js" <<'EOF'
/* api.js — small helper for backend calls and websocket */
export async function fetchIntel(){
  const r = await fetch('/admin/intel')
  return r.json()
}

export function connectWS(onMessage){
  try{
    const wsProto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${wsProto}://${location.host}/intel/stream`)
    ws.onmessage = (ev)=>{
      try{ onMessage(JSON.parse(ev.data)) }catch(e){/* ignore */}
    }
    return ws
  }catch(e){
    return null
  }
}
EOF

# create index.css theme override (merge with existing index.css if present)
CSS_PATH="$FRONTEND_DIR/index.css"
if [ -f "$CSS_PATH" ]; then
  echo "# appending theme variables to existing index.css"
  cat >> "$CSS_PATH" <<'EOF'

/* THE13TH theme tokens */
:root{
  --bg: #0d0d0d;
  --muted: #9ca3af;
  --accent: #7c3aed;
  --accent-2: #9f7aea;
}

/* small helpers */
.bg-app{ background-color: var(--bg); }
.text-accent{ color: var(--accent); }
EOF
else
  cat > "$CSS_PATH" <<'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

:root{
  --bg: #0d0d0d;
  --muted: #9ca3af;
  --accent: #7c3aed;
  --accent-2: #9f7aea;
}

.bg-app{ background-color: var(--bg); }
.text-accent{ color: var(--accent); }
EOF
fi

# make script executable
chmod +x "$SCRIPT_PATH"

echo "Created frontend dashboard files under: $FRONTEND_DIR"
echo "Run the dev server from frontend with: npm run dev (or build with npm run build)"
