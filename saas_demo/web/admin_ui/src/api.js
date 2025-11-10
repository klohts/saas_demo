const API_BASE = "" // same origin

async function getIntel() {
  const res = await fetch(`${API_BASE}/admin/intel`)
  return res.json()
}

async function postEvent(evt) {
  const res = await fetch(`${API_BASE}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(evt)
  })
  return res.json()
}

// ✅ Add fallback functions so the UI never crashes
async function getEvents() {
  const data = await getIntel()
  return data.events || []
}

async function getActions() {
  const data = await getIntel()
  return data.actions || []
}

async function putRules() {
  // not implemented yet, return safe default
  return { rules: {} }
}

export default {
  getIntel,
  postEvent,
  getEvents,   // ✅ added
  getActions,  // ✅ added
  putRules     // ✅ stub to prevent crash
}
