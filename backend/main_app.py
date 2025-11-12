# backend/main_app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import analytics

app = FastAPI(title="THE13TH-MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9000", "http://127.0.0.1:9000", "https://the13th.onrender.com", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics.router, prefix="/analytics")

@app.get("/health")
def health():
    import datetime
    return {"status":"ok", "timestamp": datetime.datetime.utcnow().isoformat()}
