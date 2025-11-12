# THE13TH Control Core

Standalone Control Core microservice to orchestrate Client Customization and App Intelligence.

Files created:
- control_core_app.py
- core_models.py
- core_utils.py
- .env.example
- requirements.txt
- Dockerfile

Run locally:
```bash
cd control_core
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && export $(cat .env | xargs)
python control_core_app.py
```

APIs:
- POST /api/events  — ingest event (requires X-SYS-API-KEY)
- GET /api/reports/summary — fetch summary from intelligence service
- GET /api/clients — proxy client listing from client service

Security: uses CC_SYS_API_KEY for internal authentication.
