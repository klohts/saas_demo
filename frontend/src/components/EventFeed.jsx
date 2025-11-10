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
