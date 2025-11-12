import os
from textwrap import dedent

BASE_DIR = "saas_onboarding"

FILES = {
    f"{BASE_DIR}/app/__init__.py": "",
    f"{BASE_DIR}/app/config.py": dedent("""\
        from pydantic import BaseSettings, Field

        class Settings(BaseSettings):
            APP_NAME: str = "AI Automation Onboarding"
            ENV: str = "development"
            SECRET_KEY: str = Field(..., env="SECRET_KEY")
            DATABASE_URL: str = Field("sqlite+aiosqlite:///./data.db", env="DATABASE_URL")
            STRIPE_API_KEY: str = Field(..., env="STRIPE_API_KEY")
            STRIPE_WEBHOOK_SECRET: str = Field(None, env="STRIPE_WEBHOOK_SECRET")
            DOMAIN: str = Field("http://localhost:8000", env="DOMAIN")
            ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
            RATE_LIMIT: str = "200/hour"

            class Config:
                env_file = ".env"
                env_file_encoding = "utf-8"

        settings = Settings()
    """),
    f"{BASE_DIR}/app/db.py": dedent("""\
        from sqlmodel import SQLModel
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from .config import settings

        engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def init_db() -> None:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
    """),
    f"{BASE_DIR}/app/models.py": dedent("""\
        from typing import Optional
        from sqlmodel import SQLModel, Field
        from datetime import datetime

        class User(SQLModel, table=True):
            id: Optional[int] = Field(default=None, primary_key=True)
            email: str = Field(index=True, nullable=False, unique=True)
            hashed_password: str
            stripe_customer_id: Optional[str] = None
            stripe_subscription_id: Optional[str] = None
            is_active: bool = Field(default=True)
            created_at: datetime = Field(default_factory=datetime.utcnow)
            plan: Optional[str] = None
            config_json: Optional[str] = None
    """),
    f"{BASE_DIR}/app/schemas.py": dedent("""\
        from pydantic import BaseModel, EmailStr, constr
        from typing import Optional

        class UserCreate(BaseModel):
            email: EmailStr
            password: constr(min_length=8)

        class UserRead(BaseModel):
            id: int
            email: EmailStr
            plan: Optional[str] = None
            is_active: bool

        class Token(BaseModel):
            access_token: str
            token_type: str = "bearer"

        class CheckoutSessionCreate(BaseModel):
            price_id: str
    """),
    f"{BASE_DIR}/app/auth.py": dedent("""\
        from datetime import datetime, timedelta
        from typing import Optional
        from passlib.context import CryptContext
        from jose import jwt, JWTError
        from fastapi import HTTPException, status, Depends
        from fastapi.security import OAuth2PasswordBearer
        from .config import settings

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
        ALGORITHM = "HS256"

        def hash_password(password: str) -> str:
            return pwd_context.hash(password)

        def verify_password(plain: str, hashed: str) -> bool:
            return pwd_context.verify(plain, hashed)

        def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
            expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
            to_encode = {"exp": expire, "sub": str(subject)}
            return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

        def decode_access_token(token: str) -> str:
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
                sub: str = payload.get("sub")
                if sub is None:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")
                return sub
            except JWTError:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalid")

        async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
            return decode_access_token(token)
    """),
    f"{BASE_DIR}/app/services/stripe_service.py": dedent("""\
        import stripe
        from fastapi import HTTPException
        from typing import Dict
        from ..config import settings

        stripe.api_key = settings.STRIPE_API_KEY

        def create_checkout_session(customer_email: str, price_id: str, success_url: str, cancel_url: str) -> Dict:
            try:
                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    mode="subscription",
                    customer_email=customer_email,
                    line_items=[{"price": price_id, "quantity": 1}],
                    success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
                    cancel_url=cancel_url,
                )
                return session
            except stripe.error.StripeError as e:
                raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

        def construct_event(payload: bytes, sig_header: str):
            if not settings.STRIPE_WEBHOOK_SECRET:
                raise RuntimeError("Stripe webhook secret not configured")
            try:
                event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
                return event
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid payload")
            except stripe.error.SignatureVerificationError:
                raise HTTPException(status_code=400, detail="Invalid signature")
    """),
    f"{BASE_DIR}/Dockerfile": dedent("""\
        FROM python:3.11-slim
        WORKDIR /app
        RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt
        COPY . .
        ENV PYTHONUNBUFFERED=1
        ENV PORT=8000
        EXPOSE 8000
        CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    """),
    f"{BASE_DIR}/requirements.txt": dedent("""\
        fastapi>=0.95
        uvicorn[standard]>=0.22
        sqlmodel>=0.0.8
        sqlalchemy>=1.4
        aiosqlite>=0.17
        python-jose>=3.3.0
        passlib[bcrypt]>=1.7
        stripe>=5.0.0
        jinja2>=3.1
        python-multipart>=0.0.6
        slowapi>=0.1.4
        python-dotenv>=1.0.0
    """),
    f"{BASE_DIR}/.env.example": dedent("""\
        SECRET_KEY=replace-with-a-secure-random-string
        DOMAIN=http://localhost:8000
        DATABASE_URL=sqlite+aiosqlite:///./data.db
        STRIPE_API_KEY=sk_test_xxx
        STRIPE_WEBHOOK_SECRET=whsec_xxx
        PRICE_STARTER_ID=price_XXXXXXXX
        PRICE_PRO_ID=price_XXXXXXXX
        PRICE_AGENCY_ID=price_XXXXXXXX
    """),
    f"{BASE_DIR}/README.md": dedent("""\
        # AI Automation — Onboarding & Stripe Layer

        ## Setup
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        uvicorn app.main:app --reload
        ```
        Then open: http://localhost:8000/signup
    """),
    f"{BASE_DIR}/app/templates/base.html": dedent("""\
        <!doctype html>
        <html>
          <head>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width,initial-scale=1"/>
            <title>{{ title or "AI Automation" }}</title>
            <script src="https://cdn.tailwindcss.com"></script>
          </head>
          <body class="bg-gray-50 text-gray-900">
            <nav class="bg-white shadow p-4 mb-6">
              <div class="max-w-4xl mx-auto flex justify-between items-center">
                <div class="text-lg font-semibold">AI Automation</div>
                <div>
                  <a href="/" class="text-sm mr-4">Home</a>
                  <a href="/signup" class="text-sm">Sign up</a>
                </div>
              </div>
            </nav>
            <main class="max-w-4xl mx-auto p-4">
              {% block content %}{% endblock %}
            </main>
          </body>
        </html>
    """),
    f"{BASE_DIR}/app/templates/signup.html": dedent("""\
        {% extends "base.html" %}
        {% block content %}
        <h1 class="text-2xl font-bold mb-4">Create an account</h1>
        <form method="post" action="/signup" class="space-y-4">
          <div><label>Email</label><input name="email" type="email" required class="w-full border p-2 rounded"/></div>
          <div><label>Password</label><input name="password" type="password" minlength="8" required class="w-full border p-2 rounded"/></div>
          <div><label>Plan</label>
            <select name="plan" class="w-full border p-2 rounded">
              <option value="starter">Starter — $29/mo</option>
              <option value="pro">Pro — $297/mo</option>
              <option value="agency">Agency — $2500/mo</option>
            </select>
          </div>
          <button type="submit" class="px-4 py-2 bg-indigo-600 text-white rounded">Create & Subscribe</button>
        </form>
        <p class="text-sm mt-4">Already have an account? <a href="/login" class="text-indigo-600">Log in</a></p>
        {% endblock %}
    """),
    f"{BASE_DIR}/app/templates/login.html": dedent("""\
        {% extends "base.html" %}
        {% block content %}
        <h1 class="text-2xl font-bold mb-4">Log in</h1>
        <form method="post" action="/login" class="space-y-4">
          <div><label>Email</label><input name="email" type="email" required class="w-full border p-2 rounded"/></div>
          <div><label>Password</label><input name="password" type="password" required class="w-full border p-2 rounded"/></div>
          <button type="submit" class="px-4 py-2 bg-indigo-600 text-white rounded">Log in</button>
        </form>
        <p class="text-sm mt-4">No account? <a href="/signup" class="text-indigo-600">Create one</a></p>
        {% endblock %}
    """),
    f"{BASE_DIR}/app/templates/dashboard.html": dedent("""\
        {% extends "base.html" %}
        {% block content %}
        <h1 class="text-2xl font-bold mb-4">Dashboard</h1>
        <p>Hello <strong>{{ user_email }}</strong></p>
        <p>Plan: <strong>{{ plan }}</strong></p>
        <div class="bg-white p-4 rounded shadow mt-4">
          <h2 class="font-semibold mb-2">Client Config</h2>
          <pre class="text-xs bg-gray-100 p-2 rounded">{{ config_json }}</pre>
        </div>
        <a href="/logout" class="mt-4 inline-block px-3 py-2 bg-red-500 text-white rounded">Logout</a>
        {% endblock %}
    """)
}


def create_structure():
    dirs = [
        f"{BASE_DIR}/app/services",
        f"{BASE_DIR}/app/templates",
        f"{BASE_DIR}/app/static",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    for path, content in FILES.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Created: {path}")


if __name__ == "__main__":
    create_structure()
    print(f"\n🎯 All files successfully created inside '{BASE_DIR}/'.")
