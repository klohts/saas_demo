import React from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function ScoreChart({events}){
  const data = events.slice(0,50).map(ev=>({
    t: new Date(ev.timestamp*1000).toLocaleTimeString(),
    score: (()=>{
      const map = {lead_hot:1, client_upgrade:1, billing_failure:0.85}
      return map[ev.action] ?? 0.2
    })()
  })).reverse()

  return (
    <div style={{height:240}}>
      <h3>Recent Scores</h3>
      <ResponsiveContainer>
        <LineChart data={data}>
          <XAxis dataKey="t" />
          <YAxis domain={[0,1]} />
          <Tooltip />
          <Line type="monotone" dataKey="score" stroke="#6b21a8" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
