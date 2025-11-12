# THE13TH — App Intelligence Engine (Phase 1)

Files created under:
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/app_intelligence_app.py
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/models.py
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/requirements.txt
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/.env.example
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/Dockerfile

Quick start:

```bash
cd /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export $(cat .env | xargs)
python app_intelligence_app.py
```

API:
- POST /api/events  (requires header X-SYS-API-KEY)
- GET  /api/insights/recent (requires header X-SYS-API-KEY)
