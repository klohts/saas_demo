import re

f = "main.py"
code = open(f).read()

# Add missing FastAPI utilities to the import line
if "Depends" not in code.split("\n")[0]:
    code = re.sub(
        r"from fastapi import FastAPI, Request, HTTPException",
        "from fastapi import FastAPI, Request, HTTPException, Depends",
        code,
        1
    )

# Also ensure RedirectResponse, JSONResponse, Path, json exist
extras = [
    "from fastapi.responses import RedirectResponse, JSONResponse",
    "from pathlib import Path",
    "import json"
]

for line in extras:
    if line not in code:
        code = line + "\n" + code

open(f, "w").write(code)
print("✅ Added missing Depends + other required imports")
