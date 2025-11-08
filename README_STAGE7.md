# Stage 7 — Client Module (THE13TH)

## Run locally
(.venv) $ export ADMIN_KEY=the13th-admin
(.venv) $ uvicorn main:app --reload --host 0.0.0.0 --port 8000

## Create client
curl -X POST -H "Content-Type: application/json" -H "X-ADMIN-KEY: the13th-admin" \
  -d '{"name":"Demo Client","plan":"Free"}' http://127.0.0.1:8000/api/admin/clients

## Use client API key
curl -H "X-API-Key: <client_api_key>" http://127.0.0.1:8000/api/hello

## Check billing
curl "http://127.0.0.1:8000/billing/status?api_key=<client_api_key>"
