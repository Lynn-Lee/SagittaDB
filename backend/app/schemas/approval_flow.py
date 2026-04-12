"""
审批流模板 Pydantic Schema。
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ApprovalFlowNodeCreate(BaseModel):
    order: int = Field(..., ge=1, description="节点序号，从 1 开始")
    node_name: str = Field(..., min_length=1, max_length=100, description="节点名称，如「DBA初审」")
    approver_type: Literal["users", "group", "manager", "user_group", "role", "any_reviewer"] = (
        Field(
            default="any_reviewer",
            description=(
                "审批人类型：\n"
                "  users        — approver_ids 为具体用户 ID，其中任一用户可审批\n"
                "  group        — approver_ids 为资源组 ID，组内任一成员可审批\n"
                "  manager      — 直属上级（自动取申请人 manager_id）\n"
                "  user_group   — approver_group_id 指定用户组，组内任一成员可审批\n"
                "  role         — approver_role_id 指定角色，拥有此角色的任一用户可审批\n"
                "  any_reviewer — 任何拥有 sql_review 权限的用户均可审批"
            ),
        )
    )
    approver_ids: list[int] = Field(
        default_factory=list,
        description="当 approver_type=users/group 时有效，填具体用户或资源组 ID 列表",
    )
    approver_group_id: int | None = Field(
        default=None, description="审批人用户组ID（approver_type=user_group 时使用）"
    )
    approver_role_id: int | None = Field(
        default=None, description="审批人角色ID（approver_type=role 时使用）"
    )

    @field_validator("approver_ids")
    @classmethod
    def ids_required_when_typed(cls, v: list[int], info: object) -> list[int]:
        data = getattr(info, "data", {})
        approver_type = data.get("approver_type", "any_reviewer")
        if approver_type in ("users", "group") and not v:
            raise ValueError(f"approver_type={approver_type} 时必须填写 approver_ids")
        return v


class ApprovalFlowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="流程名称")
    description: str = Field(default="", max_length=500)
    nodes: list[ApprovalFlowNodeCreate] = Field(
        default_factory=list, description="审批节点列表（按 order 排序）"
    )

    @field_validator("nodes")
    @classmethod
    def orders_unique_and_sequential(
        cls, v: list[ApprovalFlowNodeCreate]
    ) -> list[ApprovalFlowNodeCreate]:
        if not v:
            return v
        orders = [n.order for n in v]
        if len(orders) != len(set(orders)):
            raise ValueError("节点 order 必须唯一")
        sorted_orders = sorted(orders)
        if sorted_orders != list(range(1, len(orders) + 1)):
            raise ValueError("节点 order 必须从 1 连续递增（1, 2, 3...）")
        return sorted(v, key=lambda n: n.order)


class ApprovalFlowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    # 传入 nodes 时全量替换；不传则不修改节点
    nodes: list[ApprovalFlowNodeCreate] | None = None

    @field_validator("nodes")
    @classmethod
    def orders_valid(
        cls, v: list[ApprovalFlowNodeCreate] | None
    ) -> list[ApprovalFlowNodeCreate] | None:
        if v is None:
            return v
        if not v:
            return v
        orders = [n.order for n in v]
        if len(orders) != len(set(orders)):
            raise ValueError("节点 order 必须唯一")
        sorted_orders = sorted(orders)
        if sorted_orders != list(range(1, len(orders) + 1)):
            raise ValueError("节点 order 必须从 1 连续递增")
        return sorted(v, key=lambda n: n.order)


class ApprovalFlowNodeOut(BaseModel):
    id: int
    order: int
    node_name: str
    approver_type: str
    approver_ids: list[int]
    approver_group_id: int | None = None
    approver_role_id: int | None = None

    model_config = {"from_attributes": True}


class ApprovalFlowOut(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool
    nodes: list[ApprovalFlowNodeOut]
    created_by: str
    created_at: str

    model_config = {"from_attributes": True}


class ApprovalFlowListItem(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool
    node_count: int
    created_by: str
    created_at: str
