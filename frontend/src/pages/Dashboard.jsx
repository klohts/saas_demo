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
