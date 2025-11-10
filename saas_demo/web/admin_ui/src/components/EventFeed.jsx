import React, { useEffect, useState } from "react";

export default function EventFeed({ events }) {
  const [localEvents, setLocalEvents] = useState([]);

  // ✅ Merge incoming events into local state (no flashing reset)
  useEffect(() => {
    if (!events || events.length === 0) return;

    setLocalEvents(current => {
      const merged = [...events, ...current];   // Prepend new ones
      const seen = new Set();
      return merged.filter(ev => {
        if (seen.has(ev.id)) return false;
        seen.add(ev.id);
        return true;
      });
    });
  }, [events]);

  return (
    <div className="events">
      <h3>Event Feed</h3>
      <ul>
        {localEvents.map(ev => (
          <li key={ev.id} className="event-row">
            <div><strong>{ev.action}</strong> — {ev.user}</div>

            {/* ✅ timestamp is already in milliseconds, no *1000 */}
            <div className="meta">{new Date(ev.timestamp).toLocaleString()}</div>

            <pre className="payload">
              {JSON.stringify(ev.payload || {}, null, 2)}
            </pre>
          </li>
        ))}

        {localEvents.length === 0 && <li>No events yet</li>}
      </ul>
    </div>
  );
}
