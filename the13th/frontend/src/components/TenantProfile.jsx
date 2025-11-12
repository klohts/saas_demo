import React, { useEffect, useState } from "react";

export default function TenantProfile({ tenantId, onClose }) {
  const [tenant, setTenant] = useState(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});

  const fetchTenant = async () => {
    const res = await fetch(`/api/tenants/${tenantId}`);
    if (res.ok) setTenant(await res.json());
  };

  const saveTenant = async () => {
    const res = await fetch(`/api/tenants/${tenantId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    if (res.ok) {
      setEditing(false);
      await fetchTenant();
    }
  };

  useEffect(() => { fetchTenant(); }, [tenantId]);

  if (!tenant) return <div className="p-4">Loading...</div>;

  return (
    <div className="p-6 bg-white rounded-2xl shadow-md mt-6 border border-gray-200">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Tenant Profile</h2>
        <button onClick={onClose} className="text-sm text-gray-500 hover:text-gray-700">✕ Close</button>
      </div>

      <div className="flex items-center gap-4 mb-4">
        {tenant.logo_url && <img src={tenant.logo_url} alt="Logo" className="w-16 h-16 rounded-lg" />}
        <div>
          <h3 className="text-xl font-semibold" style={{color: tenant.color || '#2563eb'}}>{tenant.name}</h3>
          <p className="text-gray-600">{tenant.tagline || "No tagline yet"}</p>
        </div>
      </div>

      {editing ? (
        <div className="space-y-3">
          <input className="border px-3 py-2 w-full" placeholder="Name"
            defaultValue={tenant.name} onChange={e=>setForm({...form, name:e.target.value})}/>
          <input className="border px-3 py-2 w-full" placeholder="Logo URL"
            defaultValue={tenant.logo_url} onChange={e=>setForm({...form, logo_url:e.target.value})}/>
          <input className="border px-3 py-2 w-full" placeholder="Color"
            defaultValue={tenant.color} onChange={e=>setForm({...form, color:e.target.value})}/>
          <input className="border px-3 py-2 w-full" placeholder="Tagline"
            defaultValue={tenant.tagline} onChange={e=>setForm({...form, tagline:e.target.value})}/>
          <button onClick={saveTenant} className="bg-blue-600 text-white px-4 py-2 rounded-lg">Save</button>
        </div>
      ) : (
        <button onClick={()=>setEditing(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg">Edit</button>
      )}
    </div>
  );
}
