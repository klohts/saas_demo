/* Sidebar.jsx for THE13TH (Minimalist Pro SaaS — grey/purple outline buttons) */
import React from 'react'
import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/events', label: 'Event Feed' },
  { to: '/rules', label: 'Rules Editor' },
  { to: '/score', label: 'Score Analytics' },
]

export default function Sidebar(){
  return (
    <aside className="w-72 border-r border-gray-800 bg-[#0b0b0b] flex flex-col p-6">
      <div className="mb-8">
        <div className="text-2xl font-semibold tracking-wide">THE13TH</div>
        <div className="text-sm text-gray-400 mt-1">Admin Intelligence</div>
      </div>

      <nav className="flex-1 space-y-2">
        {navItems.map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            className={({isActive}) =>
              `block w-full text-left px-4 py-2 rounded-md transition-all text-gray-200 ${isActive ? 'border border-purple-500 text-purple-300' : 'border border-transparent hover:border-purple-700'} `
            }
          >
            {it.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-6">
        <button className="w-full px-4 py-2 rounded-md border border-purple-600 text-purple-300 hover:bg-purple-700/10 transition">Connect</button>
      </div>
    </aside>
  )
}
