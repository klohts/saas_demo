#!/usr/bin/env python3
# ============================================
# Day 8: Admin Dashboard Integration Bundle — THE13TH
# ============================================
# Purpose: Connect multi-tenant backend (Day7) to the React dashboard (frontend)
# Outcome: Real-time tenant management panel in THE13TH dashboard
# Auto: Creates component, updates App.jsx, commits, pushes, triggers Render deploy

import os
import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# --------------------------------------------
# Configuration
# --------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
FRONTEND_COMPONENTS = FRONTEND_SRC / "components"
APP_JSX = FRONTEND_SRC / "App.jsx"
DEPLOY_HOOK = "https://api.render.com/deploy/srv-d4a6l07gi27c739spc0g?key=ZBnxoh-Us8o"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("Day8AdminDashboard")

# --------------------------------------------
# Ensure component directory
# --------------------------------------------
FRONTEND_COMPONENTS.mkdir(parents=True, exist_ok=True)

# --------------------------------------------
# 1️⃣ Create AdminTenantPanel.jsx
# --------------------------------------------
tenant_panel_code = """import React, { useEffect, useState } from "react";

export default function AdminTenantPanel() {
  const [tenants, setTenants] = useState([]);
  const [newTenant, setNewTenant] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchTenants = async () => {
    try {
      const res = await fetch("/api/tenants");
      const data = await res.json();
      setTenants(data);
    } catch (err) {
      console.error("Failed to load tenants", err);
    }
  };

  const addTenant = async (e) => {
    e.preventDefault();
    if (!newTenant.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("/api/tenants", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newTenant }),
      });
      if (res.ok) {
        setNewTenant("");
        await fetchTenants();
      }
    } catch (err) {
      console.error("Error adding tenant", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTenants();
  }, []);

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
          {tenants.map((t) => (
            <tr key={t.id} className="border-b border-gray-100">
              <td className="py-2 font-mono text-sm text-gray-600">{t.id}</td>
              <td className="py-2">{t.name}</td>
              <td className="py-2 text-gray-500 text-sm">{new Date(t.created_at).toLocaleString()}</td>
            </tr>
          ))}
          {tenants.length === 0 && (
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
"""
tenant_panel_path = FRONTEND_COMPONENTS / "AdminTenantPanel.jsx"
if not tenant_panel_path.exists():
    tenant_panel_path.write_text(tenant_panel_code)
    logger.info(f"✅ Created {tenant_panel_path}")
else:
    logger.info(f"⏭️ Skipping existing {tenant_panel_path}")

# --------------------------------------------
# 2️⃣ Patch App.jsx to include the AdminTenantPanel
# --------------------------------------------
if APP_JSX.exists():
    app_code = APP_JSX.read_text()
    if "AdminTenantPanel" not in app_code:
        import_line = 'import AdminTenantPanel from "./components/AdminTenantPanel";'
        inject_line = "<AdminTenantPanel />"
        if "return (" in app_code:
            updated = app_code.replace(
                "return (",
                f"{import_line}\n\nreturn (\n    {inject_line}\n"
            )
            APP_JSX.write_text(updated)
            logger.info(f"✅ Patched App.jsx with AdminTenantPanel")
else:
    logger.warning(f"⚠️ App.jsx not found at {APP_JSX}")

# --------------------------------------------
# 3️⃣ Git commit and push
# --------------------------------------------
def git_commit_and_push():
    try:
        subprocess.run(["git", "add", "."], cwd=REPO_ROOT, check=True)
        commit_msg = f"chore: Day8 admin dashboard integration — {datetime.utcnow().isoformat()}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_ROOT, check=True)
        subprocess.run(["git", "push"], cwd=REPO_ROOT, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Git error: {e}")
        return False

committed = git_commit_and_push()

# --------------------------------------------
# 4️⃣ Trigger Render deploy
# --------------------------------------------
def trigger_render():
    try:
        import requests
        r = requests.post(DEPLOY_HOOK)
        if r.status_code == 200:
            logger.info(f"🚀 Render deploy triggered successfully: {r.text}")
        else:
            logger.warning(f"⚠️ Render trigger failed: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"❌ Failed to trigger Render deploy: {e}")

trigger_render()

logger.info("🎯 Day 8 bundle complete — Admin dashboard integrated with tenants system.")
