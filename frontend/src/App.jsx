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
