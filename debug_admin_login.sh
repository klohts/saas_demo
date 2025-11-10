#!/bin/bash
echo "=== ADMIN LOGIN DEBUG ==="

# 1. Show expected password from env
if [ -f .env ]; then
  echo "[+] .env file found"
  echo "ADMIN_PASSWORD in .env ->"
  grep ADMIN_PASSWORD .env | sed 's/ADMIN_PASSWORD=/EXPECTED_PASSWORD=/' || echo "⚠️  ADMIN_PASSWORD not set in .env"
else
  echo "⚠️  No .env file found"
fi

# 2. Patch main.py login route to print received password
echo "[+] Patching /admin/login to print submitted password..."

sed -i "/@app.post(\"\\/admin\\/login\")/,/return/ {
  s|pwd = |print(\"🔐 RECEIVED PASSWORD:\", request.form.get('password')); pwd = |
}" main.py

echo "[+] Patch applied."

echo "
✅ Done. Now restart your server:
    uvicorn main:app --reload

Then try logging in again, check your terminal, and paste the output here.
"
