from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

os.chdir("frontend")
print("Serving dashboard → http://localhost:9000")
HTTPServer(("0.0.0.0", 9000), SimpleHTTPRequestHandler).serve_forever()
