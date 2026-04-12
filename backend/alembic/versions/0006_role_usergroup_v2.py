"""v2 授权体系 Phase 1：新增 role / user_group 表，sql_users 加 v2 字段

新增表：
- role（角色）
- user_group（用户组）
- role_permission（角色↔权限码 多对多）
- user_group_member（用户组↔成员 多对多）
- group_resource_group（用户组↔资源组 多对多）

sql_users 新增列：
- role_id FK→role.id
- manager_id FK→sql_users.id（自引用，直属上级）
- employee_id 工号
- department 部门
- title 职位

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-12
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 角色表 ──────────────────────────────────────────────────
    op.create_table(
        "role",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("name_cn", sa.String(100), nullable=False, server_default=""),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_role_tenant", "role", ["tenant_id"])

    # ── 用户组表 ────────────────────────────────────────────────
    op.create_table(
        "user_group",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("name_cn", sa.String(100), nullable=False, server_default=""),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("leader_id", sa.Integer(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["leader_id"], ["sql_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_id"], ["user_group.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_user_group_tenant", "user_group", ["tenant_id"])

    # ── role_permission（角色↔权限码 多对多）────────────────────
    op.create_table(
        "role_permission",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permission.id"], ondelete="CASCADE"),
    )

    # ── user_group_member（用户组↔成员 多对多）──────────────────
    op.create_table(
        "user_group_member",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["sql_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["user_group.id"], ondelete="CASCADE"),
    )

    # ── group_resource_group（用户组↔资源组 多对多）──────────────
    op.create_table(
        "group_resource_group",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("resource_group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["user_group.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_group_id"], ["resource_group.id"], ondelete="CASCADE"),
    )

    # ── sql_users 新增 v2 字段 ──────────────────────────────────
    op.add_column("sql_users", sa.Column("role_id", sa.Integer(), nullable=True))
    op.add_column("sql_users", sa.Column("manager_id", sa.Integer(), nullable=True))
    op.add_column(
        "sql_users",
        sa.Column("employee_id", sa.String(50), nullable=False, server_default=""),
    )
    op.add_column(
        "sql_users",
        sa.Column("department", sa.String(100), nullable=False, server_default=""),
    )
    op.add_column(
        "sql_users",
        sa.Column("title", sa.String(100), nullable=False, server_default=""),
    )

    op.create_foreign_key(
        "fk_users_role_id",
        "sql_users",
        "role",
        ["role_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_users_manager_id",
        "sql_users",
        "sql_users",
        ["manager_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # sql_users 新增列回滚
    op.drop_constraint("fk_users_manager_id", "sql_users", type_="foreignkey")
    op.drop_constraint("fk_users_role_id", "sql_users", type_="foreignkey")
    op.drop_column("sql_users", "title")
    op.drop_column("sql_users", "department")
    op.drop_column("sql_users", "employee_id")
    op.drop_column("sql_users", "manager_id")
    op.drop_column("sql_users", "role_id")

    # 新增表回滚
    op.drop_table("group_resource_group")
    op.drop_table("user_group_member")
    op.drop_table("role_permission")
    op.drop_index("ix_user_group_tenant", "user_group")
    op.drop_table("user_group")
    op.drop_index("ix_role_tenant", "role")
    op.drop_table("role")
