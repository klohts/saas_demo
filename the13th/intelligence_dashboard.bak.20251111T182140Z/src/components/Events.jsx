import React from 'react'
export default function Events({events}){
  return (
    <div>
      <h2 className="text-xl mb-2">Recent Events</h2>
      <table className="min-w-full border-collapse">
        <thead><tr><th className="border p-2">Time</th><th className="border p-2">Client</th><th className="border p-2">Action</th><th className="border p-2">User</th></tr></thead>
        <tbody>
          {events.map(e=> (
            <tr key={e.id}><td className="border p-2">{new Date(e.created_at).toLocaleString()}</td><td className="border p-2">{e.client_id}</td><td className="border p-2">{e.action}</td><td className="border p-2">{e.user}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
