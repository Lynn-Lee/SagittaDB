"""
角色与用户组 Pydantic Schema。
"""

from pydantic import BaseModel, field_validator


class RoleCreate(BaseModel):
    name: str
    name_cn: str = ""
    description: str = ""
    is_active: bool = True
    permission_codes: list[str] = []

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError("角色标识至少 2 个字符")
        if not v.replace("_", "").isalnum():
            raise ValueError("角色标识只能包含字母、数字和下划线")
        return v


class RoleUpdate(BaseModel):
    name_cn: str | None = None
    description: str | None = None
    is_active: bool | None = None
    permission_codes: list[str] | None = None


class RoleResponse(BaseModel):
    id: int
    name: str
    name_cn: str
    description: str
    is_system: bool
    is_active: bool
    tenant_id: int
    permissions: list[str] = []

    model_config = {"from_attributes": True}


class RoleListResponse(BaseModel):
    total: int
    items: list[RoleResponse]


class UserGroupCreate(BaseModel):
    name: str
    name_cn: str = ""
    description: str = ""
    leader_id: int | None = None
    parent_id: int | None = None
    is_active: bool = True
    resource_group_ids: list[int] = []
    member_ids: list[int] = []

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError("用户组标识至少 2 个字符")
        return v


class UserGroupUpdate(BaseModel):
    name_cn: str | None = None
    description: str | None = None
    leader_id: int | None = None
    parent_id: int | None = None
    is_active: bool | None = None
    resource_group_ids: list[int] | None = None
    member_ids: list[int] | None = None


class UserGroupResponse(BaseModel):
    id: int
    name: str
    name_cn: str
    description: str
    leader_id: int | None
    parent_id: int | None
    is_active: bool
    tenant_id: int
    member_count: int = 0

    model_config = {"from_attributes": True}


class UserGroupListResponse(BaseModel):
    total: int
    items: list[UserGroupResponse]
