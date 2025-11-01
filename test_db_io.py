# test_db_io.py
"""
Verifies full DB I/O:
1. Connects using DATABASE_URL (.env or Render)
2. Creates 'clients' table if it doesn't exist
3. Inserts a test record
4. Reads it back
5. Cleans up the test data
"""

import os
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# Handle Render SSL if needed
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif "render.com" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require"

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)

def main():
    print(f"\n🔍 Testing full DB I/O\n→ Using: {DATABASE_URL}\n")

    try:
        with engine.begin() as conn:
            # Ensure table exists
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS clients (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            );
            """))
            print("✅ Table 'clients' verified or created")

            # Insert unique record
            test_name = f"TestUser-{uuid.uuid4().hex[:6]}"
            test_email = f"{test_name.lower()}@example.com"
            conn.execute(
                text("INSERT INTO clients (name, email) VALUES (:name, :email)"),
                {"name": test_name, "email": test_email}
            )
            print(f"✅ Inserted: {test_name} ({test_email})")

            # Read back
            result = conn.execute(
                text("SELECT id, name, email FROM clients WHERE email=:email"),
                {"email": test_email}
            ).fetchone()

            if result:
                print(f"✅ Retrieved: id={result.id}, name={result.name}, email={result.email}")
            else:
                print("❌ Record not found after insert!")

            # Clean up
            conn.execute(
                text("DELETE FROM clients WHERE email=:email"),
                {"email": test_email}
            )
            print("🧹 Cleaned up test record\n")

            print("🎯 FULL DB I/O TEST PASSED\n")

    except SQLAlchemyError as e:
        print(f"❌ Database error: {str(e)}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
