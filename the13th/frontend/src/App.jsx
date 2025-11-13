import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";

import TenantProfile from "./components/TenantProfile";
import AdminTenantPanel from "./components/AdminTenantPanel";
import Dashboard from "./pages/Dashboard";

export default function App() {
  const [selectedTenant, setSelectedTenant] = React.useState(null);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-brand-grayBg p-8">
        {/* Simple Nav */}
        <nav className="mb-8 flex gap-6">
          <Link to="/" className="text-brand-purple font-semibold">
            Clients
          </Link>
          <Link to="/dashboard" className="text-brand-purple font-semibold">
            Dashboard
          </Link>
        </nav>

        <Routes>
          {/* Dashboard page */}
          <Route path="/dashboard" element={<Dashboard />} />

          {/* Root page */}
          <Route
            path="/"
            element={
              !selectedTenant ? (
                <AdminTenantPanel onSelect={setSelectedTenant} />
              ) : (
                <TenantProfile
                  tenantId={selectedTenant.id}
                  onClose={() => setSelectedTenant(null)}
                />
              )
            }
          />

          {/* Optional catch-all: redirect to / */}
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
