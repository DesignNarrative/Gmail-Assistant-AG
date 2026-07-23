import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from app.core.config import get_settings
import hashlib
import uuid

settings = get_settings()

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> Union[dict, None]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None

def generate_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def generate_state_token() -> str:
    return str(uuid.uuid4())

from cryptography.fernet import Fernet
import base64

def get_encryptor() -> Fernet:
    # Derive a 32-byte key from settings.SECRET_KEY for Fernet
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key_b64 = base64.urlsafe_b64encode(key)
    return Fernet(key_b64)

def encrypt_value(value: str) -> str:
    if not value:
        return ""
    f = get_encryptor()
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted_val: str) -> str:
    if not encrypted_val:
        return ""
    f = get_encryptor()
    try:
        return f.decrypt(encrypted_val.encode()).decode()
    except Exception:
        return ""

def create_state_token(user_id: str) -> str:
    # Set expiration to 15 minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode(
        {"sub": user_id, "type": "oauth_state", "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

def decode_state_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") == "oauth_state":
            return payload.get("sub")
    except Exception:
        return None
    return None
