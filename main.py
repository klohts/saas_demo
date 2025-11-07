# saas_demo/main.py — v4.7.0 (THE13TH, Grey + Purple Edition)
import os, sys, sqlite3, logging, argparse
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

APP_NAME=os.getenv("APP_NAME","saas_demo")
ENV=os.getenv("ENV","production")
DEBUG=os.getenv("DEBUG","true").lower() in ("1","true","yes")
DATABASE_PATH=os.getenv("DATABASE_PATH","./data/app.db")
BIND_HOST=os.getenv("BIND_HOST","0.0.0.0")
PORT=int(os.getenv("PORT","8000"))
DEMO_MODE=os.getenv("DEMO_MODE","true").lower() in ("1","true","yes")
os.makedirs(os.path.dirname(DATABASE_PATH) or ".",exist_ok=True)
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)

app=FastAPI(title=f"THE13TH — {APP_NAME} (v4.7.0)",debug=DEBUG)
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
if os.path.isdir("static"): app.mount("/static",StaticFiles(directory="static"),name="static")

def get_db():
    c=sqlite3.connect(DATABASE_PATH); c.row_factory=sqlite3.Row; return c
def init_db():
    c=get_db(); x=c.cursor()
    x.executescript("""CREATE TABLE IF NOT EXISTS billing(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT,plan TEXT,quota_limit INT DEFAULT 100,quota_used INT DEFAULT 0,
    status TEXT DEFAULT 'active',created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);""")
    c.commit(); c.close()
def create_demo():
    c=get_db(); x=c.cursor()
    x.execute("SELECT COUNT(*) c FROM billing")
    if x.fetchone()["c"]==0:
        x.execute("INSERT INTO billing(client_name,plan,quota_limit,quota_used,status) VALUES (?,?,?,?,?)",
                  ("Demo Client","Free",50,0,"active")); c.commit()
    c.close()

@app.on_event("startup")
async def startup():
    init_db()
    if DEMO_MODE: create_demo()

@app.get("/",response_class=HTMLResponse)
async def root():
    if os.path.exists("static/index.html"): return FileResponse("static/index.html")
    return HTMLResponse("<h1>THE13TH — saas_demo v4.7.0</h1><p>FastAPI is running.</p>")

@app.get("/billing/status")
async def billing_status(client: Optional[str]=None):
    c=get_db(); x=c.cursor()
    if client:
        x.execute("SELECT * FROM billing WHERE client_name=?",(client,))
        r=x.fetchone(); c.close()
        if not r: raise HTTPException(404,"Client not found")
        return dict(r)
    x.execute("SELECT * FROM billing"); rows=x.fetchall(); c.close()
    return {"clients":[dict(r) for r in rows]}

def main_cli():
    import uvicorn
    parser=argparse.ArgumentParser(); parser.add_argument("--init-db",action="store_true")
    args=parser.parse_args()
    if args.init_db: init_db(); create_demo(); print("DB initialized."); sys.exit(0)
    uvicorn.run("main:app",host=BIND_HOST,port=PORT,reload=DEBUG)

if __name__=="__main__": main_cli()
