THE13TH — MVP (Analytics + Live Feed + Tenant Panel)

How to run locally:
  1. Python deps:
     python -m pip install -U fastapi uvicorn python-dotenv

  2. Frontend (optional dev):
     cd frontend
     npm install
     npm run dev   # -> http://localhost:9000

  3. Start backend:
     uvicorn backend.main_app:app --reload --port 8000

  4. Visit frontend: http://localhost:9000
     Frontend communicates with backend at VITE_API_BASE (see .env.example)

Docker:
  docker build -t the13th-mvp:latest .
  docker run -p 8000:8000 the13th-mvp:latest
