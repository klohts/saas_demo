import React, { useEffect, useState } from "react";

export default function AdminTenantPanel({ onSelect }) {
  const [tenants, setTenants] = useState([]);
  const [newTenant, setNewTenant] = useState("");
  const [loading, setLoading] = useState(false);

  // -------------------------------------------------------------
  // SAFE tenant fetcher
  // -------------------------------------------------------------
  const fetchTenants = async () => {
    try {
      const url = `${window.location.origin}/api/tenants`;
      const res = await fetch(url);

      if (!res.ok) {
        console.error("Failed to fetch tenants:", res.status, res.statusText);
        setTenants([]);
        return;
      }

      const data = await res.json();

      // MUST be an array — anything else breaks .map()
      if (!Array.isArray(data)) {
        console.warn("Invalid tenants response (expected array). Got:", data);
        setTenants([]);
        return;
      }

      setTenants(data);
    } catch (err) {
      console.error("Failed to load tenants:", err);
      setTenants([]);
    }
  };

  // -------------------------------------------------------------
  // Add a new tenant
  // -------------------------------------------------------------
  const addTenant = async (e) => {
    e.preventDefault();
    if (!newTenant.trim()) return;

    setLoading(true);

    try:
    try {
      const url = `${window.location.origin}/api/tenants`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newTenant }),
      });

      if (res.ok) {
        setNewTenant("");
        await fetchTenants();
      } else {
        console.error("Add tenant failed:", res.status, res.statusText);
      }
    } catch (err) {
      console.error("Error adding tenant:", err);
    } finally {
      setLoading(false);
    }
  };

  // -------------------------------------------------------------
  // Initial load
  // -------------------------------------------------------------
  useEffect(() => {
    fetchTenants();
  }, []);

  // -------------------------------------------------------------
  // UI
  // -------------------------------------------------------------
  return (
    <div className="p-6 bg-white rounded-2xl shadow-md mt-6">
      <h2 className="text-2xl font-bold mb-4 text-gray-800">Client Management</h2>

      <form onSubmit={addTenant} className="flex gap-3 mb-6">
        <input
          type="text"
          value={newTenant}
          onChange={(e) => setNewTenant(e.target.value)}
          placeholder="Enter new client name"
          className="flex-1 border rounded-lg px-4 py-2 text-gray-800"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition"
        >
          {loading ? "Adding..." : "Add Client"}
        </button>
      </form>

      <table className="w-full text-left border-t border-gray-200">
        <thead>
          <tr className="text-gray-700 border-b border-gray-200">
            <th className="py-2">Tenant ID</th>
            <th className="py-2">Name</th>
            <th className="py-2">Created</th>
          </tr>
        </thead>

        <tbody>
          {(tenants || []).map((t) => (
            <tr
              key={t.id}
              className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
              onClick={() => onSelect && onSelect(t)}
            >
              <td className="py-2 font-mono text-sm text-gray-600">{t.id}</td>
              <td className="py-2">{t.name}</td>
              <td className="py-2 text-gray-500 text-sm">
                {t.created_at ? new Date(t.created_at).toLocaleString() : "--"}
              </td>
            </tr>
          ))}

          {(tenants || []).length === 0 && (
            <tr>
              <td colSpan="3" className="py-3 text-center text-gray-500">
                No clients yet — add one above.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
