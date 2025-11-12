import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Stats from './components/Stats';
import Events from './components/Events';
import './styles.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export default function App() {
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState([]);
  const [time, setTime] = useState(new Date().toLocaleTimeString());

  useEffect(() => {
    fetchSummary();
    fetchEvents();
    const interval = setInterval(() => setTime(new Date().toLocaleTimeString()), 60000);
    return () => clearInterval(interval);
  }, []);

  async function fetchSummary() {
    try {
      const r = await axios.get(`${API_BASE}/api/insights/summary`, {
        headers: { 'X-SYS-API-KEY': 'supersecret_sys_key' }
      });
      setSummary(r.data);
    } catch (e) { console.error(e); }
  }

  async function fetchEvents() {
    try {
      const r = await axios.get(`${API_BASE}/api/insights/recent?limit=50`, {
        headers: { 'X-SYS-API-KEY': 'supersecret_sys_key' }
      });
      setEvents(r.data.events);
    } catch (e) { console.error(e); }
  }

  return (
    <div className="container">
      <div className="navbar">
        <div className="nav-title">THE13TH Intelligence Dashboard</div>
        <div className="nav-time">Last Updated: {time}</div>
      </div>
      <Stats data={summary} />
      <div className="card">
        <Events events={events} />
      </div>
    </div>
  );
}
