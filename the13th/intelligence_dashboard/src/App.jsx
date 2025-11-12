import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Stats from './components/Stats';
import Events from './components/Events';
import Pricing from './pages/Pricing';
import './styles.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export default function App() {
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState([]);
  const [view, setView] = useState(window.location.pathname === '/pricing' ? 'pricing' : 'dashboard');

  useEffect(() => {
    if (view === 'dashboard') {
      fetchSummary();
      fetchEvents();
    }
  }, [view]);

  async function fetchSummary() {
    try {
      const r = await axios.get(`${API_BASE}/api/insights/summary`, {
        headers: { 'X-SYS-API-KEY': 'supersecret_sys_key' }
      });
      setSummary(r.data);
    } catch (e) {
      console.error('Summary fetch failed', e);
    }
  }

  async function fetchEvents() {
    try {
      const r = await axios.get(`${API_BASE}/api/insights/recent?limit=50`, {
        headers: { 'X-SYS-API-KEY': 'supersecret_sys_key' }
      });
      setEvents(r.data.events);
    } catch (e) {
      console.error('Events fetch failed', e);
    }
  }

  function navigateTo(v) {
    setView(v);
    window.history.pushState({}, '', v === 'pricing' ? '/pricing' : '/');
  }

  return (
    <div className="container">
      <div className="navbar">
  <div className="nav-title" onClick={() => navigateTo('dashboard')}>
    THE13TH Intelligence Dashboard
  </div>
  <div className="nav-links">
    <button
      className={`nav-btn ${view === 'dashboard' ? 'active' : ''}`}
      onClick={() => navigateTo('dashboard')}
    >
      Dashboard
    </button>
    <button
      className={`nav-btn ${view === 'pricing' ? 'active' : ''}`}
      onClick={() => navigateTo('pricing')}
    >
      Pricing
    </button>
  </div>
</div>

      {view === 'pricing' ? (
        <Pricing />
      ) : (
        <>
          <Stats data={summary} />
          <div className="card">
            <Events events={events} />
          </div>
        </>
      )}
    </div>
  );
}
