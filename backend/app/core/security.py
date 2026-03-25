"""
安全模块：JWT 签发/验证 + 密码哈希 + 字段加密。
直接使用 bcrypt 库，绕过 passlib 1.7.4 的 detect_wrap_bug 兼容性问题。
"""
import base64
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import settings

# ─── 密码哈希 ─────────────────────────────────────────────────

def _prepare_password(password: str) -> bytes:
    """SHA-256 预处理，输出固定 44 字节，彻底规避 bcrypt 72字节限制。"""
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)   # 44 bytes，远低于 72


def hash_password(password: str) -> str:
    """哈希密码，返回字符串存入数据库。"""
    hashed = bcrypt.hashpw(_prepare_password(password), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码。"""
    try:
        return bcrypt.checkpw(
            _prepare_password(plain_password),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ─── JWT ──────────────────────────────────────────────────────

def create_access_token(data: dict[str, Any]) -> str:
    payload = data.copy()
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({"exp": expire, "type": "access"})
    if "tenant_id" not in payload:
        payload["tenant_id"] = settings.TENANT_ID
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    payload = data.copy()
    expire = datetime.now(UTC) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload.update({"exp": expire, "type": "refresh"})
    if "tenant_id" not in payload:
        payload["tenant_id"] = settings.TENANT_ID
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# ─── 字段级加密（用于 Instance.password 等敏感字段）──────────

from cryptography.fernet import Fernet  # noqa: E402


def _get_fernet() -> Fernet:
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_field(value: str) -> str:
    """加密敏感字段（实例密码、SSH密钥等）。"""
    if not value:
        return value
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_field(value: str) -> str:
    """解密敏感字段，兼容未加密的旧数据。"""
    if not value:
        return value
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except Exception:
        return value
