from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_gmail_demo

app = FastAPI(
    title="AI Email SaaS",
    description="AI-powered Gmail automation assistant.",
    version="1.0.0",
)

# ✅ Enable CORS for client apps and Zapier
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    """Root endpoint for quick check."""
    return {"message": "Welcome to AI Email SaaS!"}

@app.get("/health")
def health_check():
    """Basic uptime check."""
    return {"status": "ok", "message": "Server running"}

@app.post("/generate-reply")
def generate_reply_mock():
    """Mock email reply endpoint."""
    return {"message": "Reply generated (mocked)."}

# ✅ Import and mount Gmail demo router explicitly
app.include_router(routes_gmail_demo.router, prefix="", tags=["Gmail Demo"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
