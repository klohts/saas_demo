import re, os

target = "main.py"
code = open(target).read()

# 1. Remove broken '\nCOOKIE_SECURE' lines
code = re.sub(r"\\\\nCOOKIE_SECURE.*\\n", "\\n", code)

# 2. Remove any stray COOKIE_SECURE definitions
code = re.sub(r"COOKIE_SECURE.*?=.*?\\n", "", code)

# 3. Inject a clean COOKIE_SECURE line below imports
inject = 'COOKIE_SECURE = bool(int(__import__("os").getenv("COOKIE_SECURE","0")))\\n'

if "COOKIE_SECURE" not in code:
    code = re.sub(r"(from fastapi import .+\\n)", r"\\1" + inject, code, 1)

open(target, "w").write(code)
print("✅ COOKIE_SECURE cleaned and re-injected successfully.")
