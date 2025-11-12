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
