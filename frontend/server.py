# frontend/server.py
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path
import os

# Always serve from the dist folder
os.chdir(Path(__file__).parent / "dist")

print("Serving dashboard → http://localhost:9000")
HTTPServer(("0.0.0.0", 9000), SimpleHTTPRequestHandler).serve_forever()