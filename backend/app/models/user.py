"""
用户、权限组、资源组相关模型。
"""
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModel

# ─── 关联表（多对多）─────────────────────────────────────────
instance_resource_group = Table(
    "instance_resource_group",
    Base.metadata,
    Column("instance_id", Integer, ForeignKey("sql_instance.id", ondelete="CASCADE")),
    Column("resource_group_id", Integer, ForeignKey("resource_group.id", ondelete="CASCADE")),
)

user_resource_group = Table(
    "user_resource_group",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("sql_users.id", ondelete="CASCADE")),
    Column("resource_group_id", Integer, ForeignKey("resource_group.id", ondelete="CASCADE")),
)


class Users(BaseModel):
    """用户表。"""
    __tablename__ = "sql_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, comment="用户名")
    display_name: Mapped[str] = mapped_column(String(50), default="", comment="显示名称")
    password: Mapped[str] = mapped_column(String(128), nullable=False, comment="密码哈希")
    email: Mapped[str] = mapped_column(String(100), default="", comment="邮箱")
    phone: Mapped[str] = mapped_column(String(20), default="", comment="手机号")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否超级管理员")

    # 认证来源（local / ldap / oidc / dingtalk）
    auth_type: Mapped[str] = mapped_column(String(20), default="local", comment="认证来源")
    # 外部系统 ID（LDAP dn、OIDC sub 等）
    external_id: Mapped[str] = mapped_column(String(200), default="", comment="外部认证ID")

    # 2FA
    totp_secret: Mapped[str | None] = mapped_column(String(500), comment="TOTP 密钥（加密）")
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否启用 2FA")

    remark: Mapped[str] = mapped_column(String(500), default="", comment="备注")

    resource_groups: Mapped[list["ResourceGroup"]] = relationship(
        "ResourceGroup", secondary=user_resource_group, back_populates="users"
    )

    __table_args__ = (
        Index("ix_users_tenant", "tenant_id"),
        Index("ix_users_auth_type", "auth_type"),
    )


class ResourceGroup(BaseModel):
    """
    资源组：隔离不同团队对实例的访问权限。
    是企业多团队场景的核心设计（继承自 Archery）。
    """
    __tablename__ = "resource_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="资源组名称")
    group_name_cn: Mapped[str] = mapped_column(String(100), default="", comment="资源组中文名")
    ding_webhook: Mapped[str] = mapped_column(String(500), default="", comment="钉钉 Webhook")
    feishu_webhook: Mapped[str] = mapped_column(String(500), default="", comment="飞书 Webhook")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    instances: Mapped[list["Instance"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Instance", secondary=instance_resource_group, back_populates="resource_groups"
    )
    users: Mapped[list[Users]] = relationship(
        Users, secondary=user_resource_group, back_populates="resource_groups"
    )

    __table_args__ = (Index("ix_rg_tenant", "tenant_id"),)


class Permission(BaseModel):
    """
    自定义权限表（继承 Archery 的 55 个权限定义）。
    用户权限通过 user_permission 关联表授予。
    """
    __tablename__ = "permission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codename: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="权限码")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="权限说明")


user_permission = Table(
    "user_permission",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("sql_users.id", ondelete="CASCADE")),
    Column("permission_id", Integer, ForeignKey("permission.id", ondelete="CASCADE")),
)
