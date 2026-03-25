"""
认证模块 Pydantic Schema。
"""
from pydantic import BaseModel, EmailStr, field_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class TwoFAVerifyRequest(BaseModel):
    totp_code: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码长度不能少于 8 位")
        return v


class UserMeResponse(BaseModel):
    id: int
    username: str
    display_name: str
    email: str
    is_superuser: bool
    is_active: bool
    auth_type: str
    totp_enabled: bool
    permissions: list[str]
    resource_groups: list[int]
    tenant_id: int

    model_config = {"from_attributes": True}
