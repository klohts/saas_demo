from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="THE13TH", version="1.0")

# Serve built frontend
dist_dir = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.exists(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")

@app.get("/healthz")
async def healthz():
    return JSONResponse({"status": "ok", "app": "THE13TH"})
