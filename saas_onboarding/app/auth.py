from datetime import datetime, timedelta
import logging
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
    """Hash password safely for bcrypt (72-byte limit)."""
    if len(password.encode("utf-8")) > 72:
        password = password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logging.error("Password hashing failed", exc_info=True)
        raise


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
