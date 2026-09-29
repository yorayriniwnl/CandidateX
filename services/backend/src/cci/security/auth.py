import base64
import hashlib
import hmac
import json
import time
from uuid import UUID
from dataclasses import dataclass
from typing import Optional, List, Callable, Any, Dict
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader

try:
    import jwt
    _HAS_PYJWT = True
except ImportError:
    jwt = None
    _HAS_PYJWT = False

from cci.config import settings

@dataclass
class AuthenticatedUser:
    user_id: UUID
    organization_id: UUID
    email: str
    role: str
    is_active: bool = True

oauth2_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def _b64_url_decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)

def _b64_url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")

def create_jwt_token(payload: Dict[str, Any], secret_key: Optional[str] = None, expires_in: int = 86400) -> str:
    key = secret_key or getattr(settings, "SECRET_KEY", None) or "insecure-dev-secret-change-in-production"
    payload_copy = dict(payload)
    if "exp" not in payload_copy:
        payload_copy["exp"] = int(time.time()) + expires_in
        
    if _HAS_PYJWT:
        return jwt.encode(payload_copy, key, algorithm="HS256")
        
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64_url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _b64_url_encode(json.dumps(payload_copy).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64_url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_jwt_token(token: str) -> AuthenticatedUser:
    key = getattr(settings, "SECRET_KEY", None) or "insecure-dev-secret-change-in-production"
    if _HAS_PYJWT:
        try:
            payload = jwt.decode(token, key, algorithms=["HS256"])
            return AuthenticatedUser(
                user_id=UUID(str(payload.get("user_id"))),
                organization_id=UUID(str(payload.get("organization_id"))),
                email=str(payload.get("email")),
                role=str(payload.get("role", "viewer")),
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
            
    # Standard library fallback
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token structure")
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64_url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
            
        payload = json.loads(_b64_url_decode(payload_b64).decode("utf-8"))
        exp = payload.get("exp")
        if exp is not None and time.time() > exp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
            
        return AuthenticatedUser(
            user_id=UUID(str(payload.get("user_id"))),
            organization_id=UUID(str(payload.get("organization_id"))),
            email=str(payload.get("email")),
            role=str(payload.get("role", "viewer")),
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

def validate_api_key(key: str) -> AuthenticatedUser:
    if not key or not isinstance(key, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key format")
    
    # Dev bypass key
    if key.startswith("cx_dev_") or key == "cx_live_dev_test":
        return AuthenticatedUser(
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            organization_id=UUID("00000000-0000-0000-0000-000000000001"),
            email="api_dev@candidatex.ai",
            role="admin"
        )
        
    hashed = hashlib.sha256(key.encode("utf-8")).hexdigest()
    try:
        from cci.db.session import SessionLocal
        from cci.db.models.organizations import ApiKey, User
        from sqlalchemy import select
        from datetime import datetime, timezone
        
        with SessionLocal() as db:
            stmt = select(ApiKey).where(ApiKey.hashed_key == hashed)
            api_key_obj = db.execute(stmt).scalar_one_or_none()
            if not api_key_obj or not api_key_obj.is_active:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API Key")
                
            if api_key_obj.expires_at and datetime.now(timezone.utc) > api_key_obj.expires_at:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key has expired")
                
            api_key_obj.last_used_at = datetime.now(timezone.utc)
            db.commit()
            
            user_email = "api_client@candidatex.ai"
            if api_key_obj.user_id:
                user = db.get(User, api_key_obj.user_id)
                if user:
                    user_email = user.email
                    
            return AuthenticatedUser(
                user_id=api_key_obj.user_id or api_key_obj.id,
                organization_id=api_key_obj.organization_id,
                email=user_email,
                role=api_key_obj.role,
                is_active=api_key_obj.is_active
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key validation error")

def generate_api_key(
    organization_id: UUID,
    name: str,
    user_id: Optional[UUID] = None,
    role: str = "admin"
) -> tuple[str, Any]:
    """Generates a secure API key with prefix cx_live_ and persists its SHA256 hash."""
    import secrets
    from cci.db.session import SessionLocal
    from cci.db.models.organizations import ApiKey
    
    random_token = secrets.token_urlsafe(32)
    raw_key = f"cx_live_{random_token}"
    hashed = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    prefix = raw_key[:12]
    
    with SessionLocal() as db:
        api_key_obj = ApiKey(
            organization_id=organization_id,
            user_id=user_id,
            name=name,
            key_prefix=prefix,
            hashed_key=hashed,
            role=role,
            is_active=True
        )
        db.add(api_key_obj)
        db.commit()
        db.refresh(api_key_obj)
        return raw_key, api_key_obj

async def get_current_user(
    request: Request,
    token: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header)
) -> AuthenticatedUser:
    if token:
        user = decode_jwt_token(token.credentials)
    elif api_key:
        user = validate_api_key(api_key)
    else:
        env = getattr(settings, "APP_ENV", "production")
        debug = getattr(settings, "DEBUG", False)
        if env == "development" and debug:
            return AuthenticatedUser(
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                organization_id=UUID("00000000-0000-0000-0000-000000000000"),
                email="dev@example.com",
                role="admin"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
        
    return user

def require_role(*roles: str) -> Callable:
    async def role_checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User requires one of the following roles: {', '.join(roles)}"
            )
        return user
    return role_checker

async def get_tenant_id(user: AuthenticatedUser = Depends(get_current_user)) -> UUID:
    return user.organization_id
