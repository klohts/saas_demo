from fastapi import FastAPI
from backend.routes.analytics import router as analytics_router

from backend.routes.real_estate import router as real_estate_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="THE13TH")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics_router, prefix="/analytics")
app.include_router(real_estate_router, prefix="/api/real-estate")

@app.get("/")
def home():
    return {"status": "ok"}
