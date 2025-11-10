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
