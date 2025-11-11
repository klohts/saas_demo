import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

function App() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 text-gray-800">
      <h1 className="text-3xl font-bold mb-4">THE13TH Event Dashboard</h1>
      <p className="text-gray-600">Event monitoring is live and connected.</p>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
