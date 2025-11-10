import re

f = "main.py"
code = open(f).read()

# Ensure FastAPI is imported
if "from fastapi import FastAPI" not in code:
    code = code.replace(
        "from fastapi import Request, HTTPException",
        "from fastapi import FastAPI, Request, HTTPException"
    )

open(f, "w").write(code)
print("✅ Added FastAPI import")
