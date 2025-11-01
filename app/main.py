from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_gmail_demo
from app.core.auth_guard import verify_api_key

app = FastAPI(title="AI Gmail Reply SaaS")

# CORS middleware for cross-domain requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check route
@app.get("/health")
def health():
    return {"status": "ok", "message": "Server running"}

# Register Gmail demo route
app.include_router(routes_gmail_demo.router)

# Root route with auth guard
@app.get("/")
def root(x_api_key: str = None):
    if not verify_api_key(x_api_key):
        return {"detail": "Unauthorized"}
    return {"message": "Welcome to AI Gmail Reply SaaS"}
# force redeploy Sat Nov  1 12:46:35 WAT 2025
# redeploy check Sat Nov  1 13:14:53 WAT 2025
