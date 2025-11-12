import React from 'react'
export default function Stats({data}){
  if(!data) return <div>Loading summary...</div>
  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      <div className="p-4 border rounded">Total Events<br/><strong>{data.total_events}</strong></div>
      <div className="p-4 border rounded">Unique Clients<br/><strong>{data.unique_clients}</strong></div>
      <div className="p-4 border rounded">Top Action<br/><strong>{data.top_actions?.[0]?.action || '-'}</strong></div>
    </div>
  )
}
