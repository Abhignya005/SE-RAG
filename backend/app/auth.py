import base64
import hashlib
import hmac
import os
import secrets
import time
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.mongodb import get_db

_bearer = HTTPBearer(auto_error=False)
_algorithm = "HS256"


def _secret() -> bytes:
    value = os.getenv("JWT_SECRET")
    if not value or value == "change-me":
        raise RuntimeError("JWT_SECRET must be configured with a non-default value")
    return value.encode()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_text, digest_text = encoded.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _encode(payload: dict) -> str:
    import json
    header = {"alg": _algorithm, "typ": "JWT"}
    parts = []
    for value in (header, payload):
        raw = json.dumps(value, separators=(",", ":")).encode()
        parts.append(base64.urlsafe_b64encode(raw).rstrip(b"=").decode())
    signing_input = ".".join(parts).encode()
    signature = hmac.new(_secret(), signing_input, hashlib.sha256).digest()
    parts.append(base64.urlsafe_b64encode(signature).rstrip(b"=").decode())
    return ".".join(parts)


def _decode(token: str) -> dict:
    import json
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}".encode()
        signature = base64.urlsafe_b64decode(encoded_signature + "===")
        expected = hmac.new(_secret(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload + "==="))
        if payload.get("exp", 0) < int(time.time()):
            raise ValueError("expired token")
        return payload
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


def issue_token(user: dict) -> str:
    return _encode({
        "sub": user["user_id"],
        "username": user["username"],
        "role": user.get("role", "developer"),
        "exp": int(time.time()) + int(os.getenv("JWT_EXPIRE_SECONDS", "3600")),
    })


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required")
    payload = _decode(credentials.credentials)
    user = await get_db().users.find_one({"user_id": payload.get("sub")})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def new_user(username: str, password: str) -> dict:
    return {
        "user_id": str(uuid4()),
        "username": username,
        "password_hash": hash_password(password),
        "role": "developer",
    }
