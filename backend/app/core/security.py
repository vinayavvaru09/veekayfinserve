"""JWT verification for Supabase-issued tokens and credential encryption."""

from typing import Optional

from cryptography.fernet import Fernet
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer()


def verify_supabase_token(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)) -> dict:
    """Verify a Supabase JWT and return the decoded payload."""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(payload: dict = Security(verify_supabase_token)) -> dict:
    """Extract user info from verified JWT payload."""
    user_id: Optional[str] = payload.get("sub")
    email: Optional[str] = payload.get("email")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return {"id": user_id, "email": email}


# --- Credential encryption ---

def _get_fernet() -> Fernet:
    return Fernet(settings.CREDENTIAL_ENCRYPTION_KEY.encode())


def encrypt_credentials(plaintext: str) -> str:
    """Encrypt a credentials string (JSON) for storage."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_credentials(ciphertext: str) -> str:
    """Decrypt stored credentials."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
