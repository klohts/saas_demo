import React, { useEffect, useState, useRef } from "react";
import EventFeed from "./components/EventFeed";
import ScoreChart from "./components/ScoreChart";
import RulesEditor from "./components/RulesEditor";
import api from "./api";

export default function App() {
  const [events, setEvents] = useState([]);
  const [actions, setActions] = useState([]);
  const [rules, setRules] = useState({});
  const wsRef = useRef(null);

  // ✅ Build WebSocket URL safely
  const wsUrl = `${window.location.origin.replace(/^http/, "ws")}/intel/stream`;

  // ✅ Load API data safely on boot
  useEffect(() => {
    (async () => {
      try {
        if (api.getEvents) {
          const ev = await api.getEvents();
          setEvents(ev || []);
        }

        if (api.getRules) {
          const r = await api.getRules();
          setRules(r?.rules || {});
        }
      } catch (err) {
        console.error("❌ API boot error:", err);
      }
    })();
  }, []);

  // ✅ WebSocket with auto-reconnect and live UI updates
  useEffect(() => {
    let ws;
    let reconnectTimer;

    function connect() {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => console.log("✅ WebSocket connected");

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("📩 WS Payload received:", data);

          // ✅ Fix: Prevent Invalid Date
          const safeEvents = (data.events || []).map(e => ({
            ...e,
            timestamp: e.timestamp || Date.now()
          }));

          // ✅ Replace events immediately (no append loops)
          setEvents(safeEvents);

          // ✅ Update actions if new events exist
          if (data.new && safeEvents.length > 0) {
            const latest = safeEvents[0];
            setActions(prev => [
              {
                time: latest.timestamp,
                payload: latest.payload || null,
                action: latest.action || null
              },
              ...prev.slice(0, 20) // limit action history
            ]);
          }

          console.log("✅ UI Updated Live:", safeEvents);
        } catch (err) {
          console.error("❌ WS parse error:", err);
        }
      };

      ws.onclose = () => {
        console.warn("⚠️ WebSocket closed, retrying in 2s...");
        reconnectTimer = setTimeout(connect, 2000);
      };

      ws.onerror = (err) => {
        console.error("❌ WebSocket error:", err);
        ws.close();
      };

      wsRef.current = ws;
    }

    connect();
    return () => {
      clearTimeout(reconnectTimer);
      if (wsRef.current) wsRef.current.close();
    };
  }, [wsUrl]);

  const onUpdateRules = async (newRules) => {
    try {
      if (!api.putRules) return;
      const res = await api.putRules(newRules);
      setRules(res?.rules || {});
    } catch (err) {
      console.error("❌ Failed updating rules:", err);
    }
  };

  return (
    <div className="app-root">
      <header className="header">
        <h1>THE13TH Intelligence Dashboard</h1>
        <div className="status">Worker: <span>Online</span></div>
      </header>

      <main className="grid">
        <section className="left">
          <RulesEditor rules={rules} onSave={onUpdateRules} />
          <EventFeed events={events} />
        </section>

        <aside className="right">
          <ScoreChart events={events} />
          <div className="actions">
            <h3>Recent Actions</h3>
            <ul>
              {actions.length === 0 && <li>No actions recorded yet</li>}
              {actions.map((a, idx) => (
                <li key={idx}>
                  <strong>Event {a.payload?.event_id || "—"}</strong> —{" "}
                  {a.payload?.details?.status || a.action || "Unknown"}
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </main>
    </div>
  );
}
