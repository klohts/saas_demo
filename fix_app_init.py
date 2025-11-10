import re

f = "main.py"
code = open(f).read()

# If FastAPI app is missing, insert it right after imports
if "app = FastAPI()" not in code:
    code = re.sub(
        r"(from fastapi import .*\n)",
        r"\1\napp = FastAPI()\n",
        code,
        count=1
    )

open(f, "w").write(code)
print("✅ Ensured FastAPI app is initialized")
