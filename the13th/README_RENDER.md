# THE13TH — Render Staging Deployment Guide

## Steps to Deploy

1. Add `.env.production` locally (do not commit).
2. In Render Dashboard:
   - Create **Web Service**
   - Environment = **Docker**
   - Dockerfile path = `the13th/Dockerfile`
   - Build Command: *(leave empty)*
   - Start Command: *(leave empty)*

3. Add environment variables manually under **Environment**.
4. Enable Auto Deploy from GitHub → branch `main`.
5. Test health endpoint:
   ```bash
   curl -s https://the13th.onrender.com/healthz
   ```
6. Local test before pushing:
   ```bash
   docker build -t the13th:staging -f the13th/Dockerfile .
   docker run --env-file the13th/.env.example -p 8000:8000 the13th:staging
   curl http://localhost:8000/healthz
   ```
