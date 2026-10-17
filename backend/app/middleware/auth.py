"""JWT Authentication middleware — python-jose, HS256 with role-based access."""
import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional
from functools import wraps
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from backend.app.models.database import get_db, User

logger = logging.getLogger(__name__)

_ENVIRONMENT = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "development").strip().lower()
_WEAK_SECRETS = {"", "change-me-in-production", "change-me", "changeme", "secret", "test-secret"}


def _resolve_jwt_secret() -> str:
    """JWT secret resolve — production mein strong secret ZAROORI (fail-fast), dev mein warn.

    Pehle default "change-me-in-production" chup-chaap use hota tha, jis se koi bhi
    token forge kar sakta tha. Ab:
      - production/prod: missing/weak secret → RuntimeError (server boot hi fail)
      - development: weak/missing → warning (sessions stable rakhne ke liye value rakhte hain)
    """
    secret = os.getenv("JWT_SECRET", "").strip()
    is_strong = bool(secret) and secret not in _WEAK_SECRETS and len(secret) >= 32
    if is_strong:
        return secret
    if _ENVIRONMENT in ("production", "prod"):
        raise RuntimeError(
            "JWT_SECRET missing/weak. Production requires a strong (>=32 char) secret. "
            "Generate one: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    if secret:
        logger.warning(
            "JWT_SECRET is weak (dev only). Set a strong secret before production."
        )
        return secret
    logger.warning("JWT_SECRET not set — generating an ephemeral dev secret (tokens reset on restart).")
    return secrets.token_urlsafe(48)


JWT_SECRET = _resolve_jwt_secret()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again."
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get the current authenticated user."""
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_role(*allowed_roles):
    """Dependency factory that restricts access to specific roles."""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker
