# THE13TH — Day 6: Client Customization (Render staging bundle)

Files created/updated by this bundle (location: /home/hp/AIAutomationProjects/saas_demo/the13th):

- client_customization.json  — per-tenant branding & config (JSON)
- client_theme.json          — default theme values
- app/customization.py       — FastAPI router for customization endpoints (add to app)
- .env.production           — production env (RENDER_DEPLOY_HOOK stored here)
- README_RENDER_CLIENT_CUSTOMIZATION.md — this document

How to wire into your existing FastAPI app (app/main.py):

```py
from fastapi import FastAPI
from app.customization import router as customization_router
app = FastAPI()
app.include_router(customization_router, prefix="/api/customization")
```

Security:
- Admin updates are protected by HTTP Basic. Set ADMIN_USER and ADMIN_PASS in your .env.production.

Auto-deploy:
- This script will attempt to trigger a Render deploy if RENDER_DEPLOY_HOOK is present in environment or passed with --hook.

