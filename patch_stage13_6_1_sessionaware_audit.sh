#!/bin/bash
echo "🩹 Applying Stage 13.6.1 — Session-Aware Audit Patch..."

cat > utils/patch_operator_audit_inject.py <<'PYCODE'
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from utils.admin_audit import record_audit

def patch_operator_audit(app):

    async def _require_admin(request: Request):
        if not request.session.get("is_admin"):
            raise HTTPException(status_code=403, detail="Unauthorized")

    @app.post("/admin/reset-logs")
    async def reset_logs_audited(request: Request):
        await _require_admin(request)
        record_audit("Reset Logs executed")
        return RedirectResponse("/admin/tools", status_code=303)

    @app.post("/admin/filter-emails")
    async def filter_emails_audited(request: Request):
        await _require_admin(request)
        record_audit("Filter Failed Emails executed")
        return RedirectResponse("/admin/tools", status_code=303)

    @app.post("/admin/toggle-demo")
    async def toggle_demo_audited(request: Request):
        await _require_admin(request)
        record_audit("Toggle Demo Mode executed")
        return RedirectResponse("/admin/tools", status_code=303)
PYCODE

git add utils/patch_operator_audit_inject.py
git commit -m "Stage 13.6.1 Session-Aware Audit Patch"
git push origin main

echo "✅ Patch applied. Restart app with: uvicorn main:app --reload"
echo "➡ Then log in again at http://127.0.0.1:8000/admin/login and retest /admin/tools"
