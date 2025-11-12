import React, { useEffect, useState } from 'react'
import axios from 'axios'
import Stats from './components/Stats'
import Events from './components/Events'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export default function App(){
  const [summary, setSummary] = useState(null)
  const [events, setEvents] = useState([])

  useEffect(()=>{ fetchSummary(); fetchEvents(); }, [])

  async function fetchSummary(){
    try{
      const r = await axios.get(`${API_BASE}/api/insights/summary`, { headers: { 'X-SYS-API-KEY': 'supersecret_sys_key' }})
      setSummary(r.data)
    }catch(e){ console.error(e) }
  }
  async function fetchEvents(){
    try{
      const r = await axios.get(`${API_BASE}/api/insights/recent?limit=50`, { headers: { 'X-SYS-API-KEY': 'supersecret_sys_key' }})
      setEvents(r.data.events)
    }catch(e){ console.error(e) }
  }

  return (
    <div className="p-6 font-sans">
      <h1 className="text-2xl mb-4">THE13TH Intelligence Dashboard</h1>
      <Stats data={summary} />
      <Events events={events} />
    </div>
  )
}
