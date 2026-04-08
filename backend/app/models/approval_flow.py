"""
审批流模板模型。

设计原则：
- ApprovalFlow  — 管理员定义的可复用审批流模板
- ApprovalFlowNode — 模板中的每个审批节点（顺序执行）
- 工单创建时，把模板节点**快照**进 WorkflowAudit.audit_auth_groups_info，
  此后模板变更不影响在途工单。
"""
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ApprovalFlow(BaseModel):
    """审批流模板主表。"""
    __tablename__ = "approval_flow"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="流程名称")
    description: Mapped[str] = mapped_column(String(500), default="", comment="流程说明")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    created_by: Mapped[str] = mapped_column(String(30), default="", comment="创建人用户名")
    created_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sql_users.id", ondelete="SET NULL"), nullable=True
    )

    nodes: Mapped[list["ApprovalFlowNode"]] = relationship(
        "ApprovalFlowNode",
        back_populates="flow",
        cascade="all, delete-orphan",
        order_by="ApprovalFlowNode.order",
    )

    __table_args__ = (
        Index("ix_approval_flow_tenant", "tenant_id"),
        Index("ix_approval_flow_active", "is_active"),
    )


class ApprovalFlowNode(BaseModel):
    """审批流节点表（每个节点代表一级审批）。"""
    __tablename__ = "approval_flow_node"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flow_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("approval_flow.id", ondelete="CASCADE"), nullable=False
    )

    # 节点序号（从 1 开始，同一 flow 内唯一）
    order: Mapped[int] = mapped_column(Integer, nullable=False, comment="节点序号")
    node_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="节点名称")

    # 审批人类型：
    #   users        — approver_ids 是具体用户 ID 列表，其中任一用户可审批
    #   group        — approver_ids 是资源组 ID 列表，组内任一成员可审批
    #   any_reviewer — 任何拥有 sql_review 权限的用户均可审批（无需指定 IDs）
    approver_type: Mapped[str] = mapped_column(
        String(20), default="any_reviewer", comment="审批人类型: users|group|any_reviewer"
    )
    # JSON 字符串，存储用户ID或资源组ID列表，如 "[1, 2, 3]"
    approver_ids: Mapped[str] = mapped_column(Text, default="[]", comment="审批人/组ID列表JSON")

    flow: Mapped["ApprovalFlow"] = relationship("ApprovalFlow", back_populates="nodes")

    __table_args__ = (
        UniqueConstraint("flow_id", "order", name="uq_flow_node_order"),
        Index("ix_approval_flow_node_flow", "flow_id"),
    )
