import re

file = "main.py"

with open(file, "r") as f:
    code = f.read()

# Add COOKIE_SECURE definition near the top if missing
if "COOKIE_SECURE" not in code:
    code = re.sub(
        r"(from fastapi import FastAPI)",
        r"\1\nCOOKIE_SECURE = bool(int(__import__('os').getenv('COOKIE_SECURE','0')))",
        code,
        count=1
    )

with open(file, "w") as f:
    f.write(code)

print("✅ COOKIE_SECURE patched into main.py")
print("Restart with: uvicorn main:app --reload")
