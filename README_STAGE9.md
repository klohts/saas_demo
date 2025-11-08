# Stage 9 — Demo Packaging (THE13TH)

## Run locally
(.venv) $ export DEMO_MODE=true
(.venv) $ uvicorn main:app --reload --host 0.0.0.0 --port 8000

Then open http://127.0.0.1:8000 — you’ll see the DEMO MODE banner.

## One-click Render Deploy
Add this JSON to your repo root:
render-deploy.json

Then visit:
https://render.com/deploy

Paste the repo link and Render will auto-detect settings.

## Demo Client
A "Demo Client" is auto-created on startup when DEMO_MODE=true.
API key is logged in tmp_demo_api_key.txt
