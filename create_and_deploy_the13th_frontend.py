#!/usr/bin/env python3
"""
create_and_deploy_the13th_frontend.py
Creates + deploys THE13TH frontend (React + Tailwind + Vite) to Render automatically.
"""

import os
import subprocess
import textwrap
import json
import requests
from pathlib import Path

# --- CONFIG ----------------------------------------------------------------
BASE_DIR = Path.home() / "AIAutomationProjects" / "the13th-frontend"
SRC_DIR = BASE_DIR / "src" / "components"

RENDER_DEPLOY_HOOK = "https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g"
API_BASE = "https://the13th.onrender.com/api"

# --- FILE DEFINITIONS ------------------------------------------------------
FILES = {
    "package.json": textwrap.dedent("""\
        {
          "name": "the13th-frontend",
          "version": "0.1.0",
          "private": true,
          "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview"
          },
          "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0"
          },
          "devDependencies": {
            "vite": "^5.0.0",
            "@vitejs/plugin-react": "^4.0.0"
          }
        }
    """),

    "vite.config.js": textwrap.dedent("""\
        import { defineConfig } from 'vite'
        import react from '@vitejs/plugin-react'

        export default defineConfig({
          plugins: [react()],
          server: { port: 5173 },
        })
    """),

    "index.html": textwrap.dedent("""\
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>THE13TH — Admin Dashboard</title>
            <script src="https://cdn.tailwindcss.com"></script>
          </head>
          <body class="bg-gray-50 text-gray-900">
            <div id="root"></div>
            <script type="module" src="/src/main.jsx"></script>
          </body>
        </html>
    """),

    "src/main.jsx": textwrap.dedent("""\
        import React from 'react'
        import { createRoot } from 'react-dom/client'
        import App from './App'
        import './styles.css'

        const root = createRoot(document.getElementById('root'))
        root.render(<App />)
    """),

    "src/styles.css": "body { font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Arial; }\n",

    "src/App.jsx": textwrap.dedent(f"""\
        import React, {{ useEffect, useState, useMemo }} from 'react'
        import EventTable from './components/EventTable'

        const API_BASE = import.meta.env.VITE_API_BASE || '{API_BASE}'

        export default function App() {{
          const [events, setEvents] = useState([])
          const [error, setError] = useState(null)
          const [q, setQ] = useState('')
          const [since, setSince] = useState('')

          const fetchEvents = async () => {{
            setError(null)
            try {{
              const res = await fetch(`{{API_BASE}}/events`)
              if (!res.ok) throw new Error(await res.text())
              const data = await res.json()
              setEvents(Array.isArray(data) ? data : data.events || [])
            }} catch (err) {{
              setError(err.message)
            }}
          }}

          useEffect(() => {{
            fetchEvents()
            const id = setInterval(fetchEvents, 10000)
            return () => clearInterval(id)
          }}, [])

          const filtered = useMemo(() => {{
            return events.filter(ev => {{
              if (q && !JSON.stringify(ev).toLowerCase().includes(q.toLowerCase())) return false
              if (since) {{
                const d = new Date(ev.timestamp || ev.created_at || ev.time || ev.ts)
                if (isNaN(d) || d < new Date(since)) return false
              }}
              return true
            }}).slice(0, 500)
          }}, [events, q, since])

          return (
            <div className="min-h-screen p-6">
              <header className="max-w-6xl mx-auto mb-6">
                <div className="flex items-center justify-between">
                  <h1 className="text-2xl font-semibold">THE13TH — Admin Dashboard</h1>
                  <div className="text-sm text-gray-600">API: <code className="bg-white px-2 py-1 rounded">{{API_BASE}}</code></div>
                </div>
              </header>

              <main className="max-w-6xl mx-auto bg-white p-4 rounded shadow-sm">
                <div className="flex gap-3 items-center mb-4">
                  <input className="border p-2 rounded flex-1" placeholder="search events (json)" value={{q}} onChange={{e => setQ(e.target.value)}} />
                  <input type="date" className="border p-2 rounded" value={{since}} onChange={{e => setSince(e.target.value)}} />
                  <button onClick={{() => fetchEvents()}} className="bg-indigo-600 text-white px-4 py-2 rounded">Refresh</button>
                </div>

                {{error && <div className="text-red-600 mb-4">{{error}}</div>}}
                <EventTable events={{filtered}} />
              </main>

              <footer className="max-w-6xl mx-auto mt-6 text-xs text-gray-500">Built for THE13TH · Configurable via VITE_API_BASE.</footer>
            </div>
          )
        }}
    """),

    "src/components/EventTable.jsx": textwrap.dedent("""\
        import React from 'react'

        export default function EventTable({ events = [] }) {
          if (!events.length) return <div className="p-4 text-gray-600">No events yet.</div>

          return (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="text-xs text-gray-600 border-b">
                    <th className="py-2 px-2">Time</th>
                    <th className="py-2 px-2">Source</th>
                    <th className="py-2 px-2">Type</th>
                    <th className="py-2 px-2">User / Email</th>
                    <th className="py-2 px-2">Payload (preview)</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((ev, i) => {
                    const time = ev.timestamp || ev.created_at || ev.time || ''
                    const source = ev.source || ev.app || 'unknown'
                    const type = ev.action || ev.event_type || ev.type || 'event'
                    const user = ev.user || ev.email || ev.actor || ''
                    const payload = JSON.stringify(ev.payload || ev, null, 0)
                    return (
                      <tr key={i} className="align-top border-b hover:bg-gray-50">
                        <td className="py-2 px-2 text-sm text-gray-600">{new Date(time).toLocaleString()}</td>
                        <td className="py-2 px-2 text-sm">{source}</td>
                        <td className="py-2 px-2 text-sm">{type}</td>
                        <td className="py-2 px-2 text-sm">{user}</td>
                        <td className="py-2 px-2 text-xs"><pre className="whitespace-pre-wrap">{payload.slice(0, 300)}</pre></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )
        }
    """),

    "Dockerfile": textwrap.dedent("""\
        FROM node:20-alpine AS builder
        WORKDIR /app
        COPY package.json package-lock.json* ./
        RUN npm ci --silent || npm i --silent
        COPY . .
        RUN npm run build

        FROM nginx:stable-alpine
        COPY --from=builder /app/dist /usr/share/nginx/html
        EXPOSE 80
        CMD ["nginx", "-g", "daemon off;"]
    """),

    "README.md": textwrap.dedent(f"""\
        # THE13TH Frontend (Admin Dashboard)

        ## Local Development
        ```bash
        npm install
        export VITE_API_BASE={API_BASE}
        npm run dev
        ```
    """),
}

# --- SCRIPT LOGIC ----------------------------------------------------------
def main():
    print(f"🚀 Creating THE13TH Frontend at {BASE_DIR}")
    os.makedirs(SRC_DIR, exist_ok=True)

    for path, content in FILES.items():
        file_path = BASE_DIR / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)
        print(f"✅ Created {file_path.relative_to(BASE_DIR)}")

    print("📦 Installing dependencies…")
    subprocess.run(["npm", "install"], cwd=BASE_DIR, check=True)

    print("🏗️  Building production bundle…")
    subprocess.run(["npm", "run", "build"], cwd=BASE_DIR, check=True)

    print("🚀 Triggering Render deployment…")
    try:
        resp = requests.post(RENDER_DEPLOY_HOOK, timeout=10)
        if resp.status_code == 200:
            print("✅ Render deployment triggered successfully!")
        else:
            print(f"⚠️ Render deployment request returned {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"❌ Failed to trigger Render deploy: {e}")

    print("\nAll done! Visit your frontend dashboard after deploy finishes:")
    print("👉 https://the13th.onrender.com (backend)")
    print("👉 https://the13th-frontend.onrender.com (frontend, once deployed)")

if __name__ == "__main__":
    main()
