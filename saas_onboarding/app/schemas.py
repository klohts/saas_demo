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
