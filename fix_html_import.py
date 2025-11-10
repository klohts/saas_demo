import re

f = "main.py"
code = open(f).read()

# Ensure HTMLResponse is imported
code = re.sub(
    r"from fastapi.responses import RedirectResponse, JSONResponse",
    "from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse",
    code,
    1
)

# Remove accidental duplicate Depends imports if present
code = re.sub(r", Depends, Depends", ", Depends", code)

open(f, "w").write(code)
print("✅ Added HTMLResponse import and cleaned duplicates")
