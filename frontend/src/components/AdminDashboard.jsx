import React, { useEffect, useState } from "react";

export default function AdminDashboard() {
  const [events, setEvents] = useState([]);
  const [users, setUsers] = useState([]);
  const [rules, setRules] = useState("");
  const [score, setScore] = useState(0);

  // Polling for live updates
  useEffect(() => {
    const poll = async () => {
      try {
        const e = await fetch("/admin/events").then(r => r.json());
        const u = await fetch("/admin/users").then(r => r.json());
        const s = await fetch("/admin/score").then(r => r.json());

        setEvents(e);
        setUsers(u.users || []);
        setScore(s.score || 0);
      } catch (err) {
        console.error("Polling error:", err);
      }
    };

    poll();
    const t = setInterval(poll, 3000);
    return () => clearInterval(t);
  }, []);

  const saveRules = async () => {
    await fetch("/admin/rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rules }),
    });
    alert("Rules saved ✅");
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen text-gray-800">

      <h1 className="text-2xl font-bold mb-6">Admin Intelligence Dashboard</h1>

      {/* SCORE */}
      <div className="bg-white shadow rounded-2xl p-4 mb-6">
        <h2 className="text-xl font-semibold mb-2">Current Risk/Activity Score</h2>
        <p className="text-4xl font-bold text-indigo-600">{score}</p>
      </div>

      {/* RULE EDITOR */}
      <div className="bg-white shadow rounded-2xl p-4 mb-6">
        <h2 className="text-xl font-semibold mb-3">Rule Engine</h2>
        <textarea
          className="w-full border rounded p-2 min-h-[120px]"
          placeholder="Example: IF client_upgrade THEN score += 10"
          value={rules}
          onChange={(e) => setRules(e.target.value)}
        />
        <button
          onClick={saveRules}
          className="mt-3 px-4 py-2 bg-indigo-600 text-white rounded-lg"
        >
          Save Rules
        </button>
      </div>

      {/* USERS */}
      <div className="bg-white shadow rounded-2xl p-4 mb-6">
        <h2 className="text-xl font-semibold mb-3">Users</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border">
            <thead className="bg-gray-100">
              <tr>
                <th className="p-2 border">User</th>
                <th className="p-2 border">Events</th>
                <th className="p-2 border">Last Active</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u, i) => (
                <tr key={i}>
                  <td className="p-2 border">{u.user}</td>
                  <td className="p-2 border">{u.events}</td>
                  <td className="p-2 border">{u.last_active}</td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr><td colSpan="3" className="p-2 text-center">No users yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* REAL-TIME EVENTS */}
      <div className="bg-white shadow rounded-2xl p-4">
        <h2 className="text-xl font-semibold mb-3">Live Event Feed</h2>
        <div className="space-y-2 max-h-[300px] overflow-y-auto">
          {events.map((ev, i) => (
            <div key={i} className="p-2 bg-gray-50 border rounded-lg">
              <div className="text-sm font-mono">
                <span className="font-bold">{ev.action}</span> — {ev.user}
              </div>
              <div className="text-xs text-gray-500">{ev.timestamp}</div>
            </div>
          ))}
          {events.length === 0 && (
            <p className="text-sm opacity-60">No events yet</p>
          )}
        </div>
      </div>

    </div>
  );
}
