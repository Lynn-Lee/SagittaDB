"""v2 查询权限扩展：QueryPrivilege + QueryPrivilegeApply 新增 user_group_id/scope_type/resource_group_id

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-12
"""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── QueryPrivilege 新增列 ──────────────────────────────────
    # user_id 改为 nullable（用户组授权时 user_id 为空）
    op.alter_column("query_privilege", "user_id", nullable=True)

    # instance_id 改为 nullable（scope_type=resource_group 时不需要 instance_id）
    op.alter_column("query_privilege", "instance_id", nullable=True)

    op.add_column("query_privilege", sa.Column("user_group_id", sa.Integer(), nullable=True))
    op.add_column(
        "query_privilege",
        sa.Column(
            "resource_group_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.add_column(
        "query_privilege",
        sa.Column(
            "scope_type",
            sa.String(20),
            nullable=False,
            server_default="instance",
        ),
    )

    op.create_foreign_key(
        "fk_qp_user_group_id",
        "query_privilege",
        "user_group",
        ["user_group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_qp_resource_group_id",
        "query_privilege",
        "resource_group",
        ["resource_group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_priv_user_group", "query_privilege", ["user_group_id"])
    op.create_index("ix_priv_scope_type", "query_privilege", ["scope_type"])
    op.create_index("ix_priv_resource_group", "query_privilege", ["resource_group_id"])

    # ── QueryPrivilegeApply 新增列 ──────────────────────────────
    # instance_id 改为 nullable
    op.alter_column("query_privilege_apply", "instance_id", nullable=True)

    op.add_column("query_privilege_apply", sa.Column("user_group_id", sa.Integer(), nullable=True))
    op.add_column(
        "query_privilege_apply",
        sa.Column(
            "resource_group_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.add_column(
        "query_privilege_apply",
        sa.Column(
            "scope_type",
            sa.String(20),
            nullable=False,
            server_default="instance",
        ),
    )

    op.create_foreign_key(
        "fk_qpa_user_group_id",
        "query_privilege_apply",
        "user_group",
        ["user_group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_qpa_resource_group_id",
        "query_privilege_apply",
        "resource_group",
        ["resource_group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_qpa_user_group", "query_privilege_apply", ["user_group_id"])
    op.create_index("ix_qpa_scope_type", "query_privilege_apply", ["scope_type"])

    # ── 数据迁移：旧记录 scope_type 补值 ──────────────────────
    # 旧 QueryPrivilege 记录：instance_id 非空 → scope_type = instance
    # 旧 QueryPrivilegeApply 记录：group_id 复制到 resource_group_id
    op.execute("UPDATE query_privilege SET scope_type = 'instance' WHERE instance_id IS NOT NULL")
    op.execute(
        "UPDATE query_privilege_apply SET resource_group_id = group_id, scope_type = 'instance' "
        "WHERE instance_id IS NOT NULL"
    )


def downgrade() -> None:
    # QueryPrivilegeApply 回滚
    op.drop_index("ix_qpa_scope_type", "query_privilege_apply")
    op.drop_index("ix_qpa_user_group", "query_privilege_apply")
    op.drop_constraint("fk_qpa_resource_group_id", "query_privilege_apply", type_="foreignkey")
    op.drop_constraint("fk_qpa_user_group_id", "query_privilege_apply", type_="foreignkey")
    op.drop_column("query_privilege_apply", "scope_type")
    op.drop_column("query_privilege_apply", "resource_group_id")
    op.drop_column("query_privilege_apply", "user_group_id")
    op.alter_column("query_privilege_apply", "instance_id", nullable=False)

    # QueryPrivilege 回滚
    op.drop_index("ix_priv_resource_group", "query_privilege")
    op.drop_index("ix_priv_scope_type", "query_privilege")
    op.drop_index("ix_priv_user_group", "query_privilege")
    op.drop_constraint("fk_qp_resource_group_id", "query_privilege", type_="foreignkey")
    op.drop_constraint("fk_qp_user_group_id", "query_privilege", type_="foreignkey")
    op.drop_column("query_privilege", "scope_type")
    op.drop_column("query_privilege", "resource_group_id")
    op.drop_column("query_privilege", "user_group_id")
    op.alter_column("query_privilege", "instance_id", nullable=False)
    op.alter_column("query_privilege", "user_id", nullable=False)
