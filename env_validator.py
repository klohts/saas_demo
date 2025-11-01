"""
env_validator.py — Environment Sanity Checker
--------------------------------------------
Run this manually or in CI/CD to validate your .env file before startup.
"""

import os
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AppConfig
from dotenv import load_dotenv

def run_env_validation():
    print("🔍 Validating environment configuration...")
    load_dotenv(override=True)
    print("DEBUG → ENV seen by Pydantic:", {k: os.getenv(k) for k in ['SECRET_KEY','BASE_URL','ALLOWED_ORIGINS','GMAIL_TOKEN_B64']})

    try:
        config = AppConfig.model_validate(os.environ, from_attributes=False)
        print("✅ All environment variables validated successfully!")
        print(f"   -> Environment: {config.APP_ENV}")
        print(f"   -> AI Provider: {config.AI_PROVIDER}")
        if config.AI_PROVIDER == "gemini":
            print("   -> Gemini API key found ✅")
        else:
            print("   -> OpenAI API key found ✅")
    except Exception as e:
        print("❌ Environment validation failed:")
        print(f"   {str(e)}")
        exit(1)

if __name__ == "__main__":
    run_env_validation()
