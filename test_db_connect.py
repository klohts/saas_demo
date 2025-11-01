# test_db_connect.py
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

load_dotenv()  # load .env if it exists

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

print(f"\n🔍 Checking database connection...")
print(f"→ DATABASE_URL: {DATABASE_URL}")

# Handle SSL for Render
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif "render.com" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require"

try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.scalar()
        print(f"✅ Connected successfully!\n   DB Version: {version}")
        if DATABASE_URL.startswith("sqlite"):
            print("   (Running with local SQLite)")
        else:
            print("   (Connected to remote PostgreSQL)")
except OperationalError as e:
    print(f"❌ Connection failed!\n   {str(e.orig)}")
    sys.exit(1)
except Exception as e:
    print(f"⚠️ Unexpected error: {e}")
    sys.exit(1)
