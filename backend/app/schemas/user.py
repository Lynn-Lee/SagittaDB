"""
用户与资源组 Pydantic Schema。
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


# ─── 用户 ─────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str = ""
    email: str = ""
    phone: str = ""
    is_superuser: bool = False
    resource_group_ids: list[int] = []

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError("用户名至少 2 个字符")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("用户名只能包含字母、数字、下划线和连字符")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码长度不能少于 8 位")
        return v


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    resource_group_ids: Optional[list[int]] = None


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    email: str
    phone: str
    is_active: bool
    is_superuser: bool
    auth_type: str
    totp_enabled: bool
    tenant_id: int
    resource_groups: list[int] = []

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    total: int
    items: list[UserResponse]


class GrantPermissionRequest(BaseModel):
    permission_codes: list[str]


# ─── 资源组 ───────────────────────────────────────────────────

class ResourceGroupCreate(BaseModel):
    group_name: str
    group_name_cn: str = ""
    ding_webhook: str = ""
    feishu_webhook: str = ""

    @field_validator("group_name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError("资源组名称至少 2 个字符")
        return v


class ResourceGroupUpdate(BaseModel):
    group_name_cn: Optional[str] = None
    ding_webhook: Optional[str] = None
    feishu_webhook: Optional[str] = None
    is_active: Optional[bool] = None


class ResourceGroupResponse(BaseModel):
    id: int
    group_name: str
    group_name_cn: str
    ding_webhook: str
    feishu_webhook: str
    is_active: bool
    tenant_id: int
    member_count: int = 0
    instance_count: int = 0

    model_config = {"from_attributes": True}


class ResourceGroupListResponse(BaseModel):
    total: int
    items: list[ResourceGroupResponse]
