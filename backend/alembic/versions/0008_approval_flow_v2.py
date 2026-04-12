"""v2 审批流扩展：ApprovalFlowNode 新增 manager/user_group/role 审批人类型

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-12
"""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ApprovalFlowNode 新增列 ───────────────────────────────
    op.add_column(
        "approval_flow_node",
        sa.Column("approver_group_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "approval_flow_node",
        sa.Column("approver_role_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_afn_approver_group_id",
        "approval_flow_node",
        "user_group",
        ["approver_group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_afn_approver_role_id",
        "approval_flow_node",
        "role",
        ["approver_role_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_afn_approver_role_id", "approval_flow_node", type_="foreignkey")
    op.drop_constraint("fk_afn_approver_group_id", "approval_flow_node", type_="foreignkey")
    op.drop_column("approval_flow_node", "approver_role_id")
    op.drop_column("approval_flow_node", "approver_group_id")
