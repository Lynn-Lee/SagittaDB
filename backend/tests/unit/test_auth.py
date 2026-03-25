"""
Sprint 1 认证与用户服务单元测试。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    encrypt_field, decrypt_field,
)
from app.schemas.user import UserCreate


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pwd = "MySecret@2024"
        hashed = hash_password(pwd)
        assert hashed != pwd
        assert verify_password(pwd, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct_password")
        assert not verify_password("wrong_password", hashed)

    def test_empty_password(self):
        hashed = hash_password("password123")
        assert not verify_password("", hashed)


class TestJWT:
    def test_create_and_decode_access_token(self):
        payload = {"sub": "42", "username": "testuser", "tenant_id": 1}
        token = create_access_token(payload)
        decoded = decode_token(token)
        assert decoded["sub"] == "42"
        assert decoded["username"] == "testuser"
        assert decoded["type"] == "access"
        assert decoded["tenant_id"] == 1

    def test_refresh_token_type(self):
        token = create_refresh_token({"sub": "1", "tenant_id": 1})
        decoded = decode_token(token)
        assert decoded["type"] == "refresh"

    def test_invalid_token_raises(self):
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_token("not.a.valid.token")

    def test_tenant_id_auto_filled(self):
        """未传 tenant_id 时自动填入配置中的默认值。"""
        token = create_access_token({"sub": "1"})
        decoded = decode_token(token)
        assert "tenant_id" in decoded


class TestFieldEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        original = "my_database_password_123!"
        encrypted = encrypt_field(original)
        assert encrypted != original
        assert decrypt_field(encrypted) == original

    def test_empty_string_passthrough(self):
        assert encrypt_field("") == ""
        assert decrypt_field("") == ""

    def test_different_values_different_ciphertext(self):
        e1 = encrypt_field("password1")
        e2 = encrypt_field("password2")
        assert e1 != e2

    def test_decrypt_unencrypted_returns_original(self):
        """兼容旧数据：解密未加密的明文时原样返回。"""
        plain = "old_plain_password"
        result = decrypt_field(plain)
        assert result == plain


class TestUserCreateSchema:
    def test_valid_user(self):
        u = UserCreate(username="jiali", password="SecurePass@1")
        assert u.username == "jiali"

    def test_short_username_rejected(self):
        with pytest.raises(Exception):
            UserCreate(username="a", password="password123")

    def test_short_password_rejected(self):
        with pytest.raises(Exception):
            UserCreate(username="validuser", password="short")

    def test_invalid_username_chars(self):
        with pytest.raises(Exception):
            UserCreate(username="user name!", password="password123")
