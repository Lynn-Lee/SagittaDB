"""
查询权限与查询日志模型。

v2 变更：
- QueryPrivilege 新增 user_group_id（用户组授权）、scope_type（授权粒度）、resource_group_id
- QueryPrivilegeApply 新增 user_group_id、scope_type、resource_group_id
- scope_type 枚举：resource_group / instance / database / table
"""

from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class QueryPrivilege(BaseModel):
    """查询权限记录（库级或表级）。

    v2 支持授权给用户或用户组，粒度扩展到四级：
    - resource_group: 资源组下所有实例
    - instance: 单实例
    - database: 单库
    - table: 单表
    """

    __tablename__ = "query_privilege"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sql_users.id", ondelete="CASCADE"),
        nullable=True,
        comment="被授权用户ID（用户授权时非空）",
    )
    user_group_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("user_group.id", ondelete="CASCADE"),
        nullable=True,
        comment="被授权用户组ID（用户组授权时非空）",
    )
    instance_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sql_instance.id", ondelete="CASCADE"),
        nullable=True,
        comment="实例ID（scope_type=instance/database/table 时非空）",
    )
    resource_group_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("resource_group.id", ondelete="CASCADE"),
        nullable=True,
        comment="资源组ID（scope_type=resource_group 时非空）",
    )
    # scope_type 取值：resource_group / instance / database / table
    scope_type: Mapped[str] = mapped_column(
        String(20),
        default="instance",
        comment="授权粒度: resource_group|instance|database|table",
    )
    db_name: Mapped[str] = mapped_column(String(64), default="", comment="数据库名")
    table_name: Mapped[str] = mapped_column(String(64), default="", comment="表名（空=库级权限）")
    valid_date: Mapped[date] = mapped_column(Date, nullable=False, comment="权限有效期")
    limit_num: Mapped[int] = mapped_column(Integer, default=100, comment="单次查询行数限制")
    # 1=DATABASE 级 2=TABLE 级（兼容旧数据，新数据优先看 scope_type）
    priv_type: Mapped[int] = mapped_column(Integer, default=1, comment="权限粒度")
    is_deleted: Mapped[int] = mapped_column(Integer, default=0, comment="软删除标志")

    __table_args__ = (
        Index(
            "ix_priv_user_inst_date",
            "user_id",
            "instance_id",
            "valid_date",
            "is_deleted",
        ),
        Index("ix_priv_tenant", "tenant_id"),
        Index("ix_priv_user_group", "user_group_id"),
        Index("ix_priv_scope_type", "scope_type"),
        Index("ix_priv_resource_group", "resource_group_id"),
    )


class QueryPrivilegeApply(BaseModel):
    """查询权限申请表（走审批流）。

    v2 新增 user_group_id / scope_type / resource_group_id。
    """

    __tablename__ = "query_privilege_apply"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(50), nullable=False, comment="申请标题")
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sql_users.id", ondelete="CASCADE"), nullable=False
    )
    user_group_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("user_group.id", ondelete="SET NULL"),
        nullable=True,
        comment="授权给用户组（为空则授权给用户自己）",
    )
    instance_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sql_instance.id", ondelete="CASCADE"),
        nullable=True,
        comment="实例ID（scope_type=instance/database/table 时非空）",
    )
    resource_group_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("resource_group.id", ondelete="SET NULL"),
        nullable=True,
        comment="资源组ID（scope_type=resource_group 时非空）",
    )
    # 保留 group_id 向后兼容（值等于 resource_group_id）
    group_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="资源组ID（兼容旧字段）")
    # scope_type 取值：resource_group / instance / database / table
    scope_type: Mapped[str] = mapped_column(
        String(20),
        default="instance",
        comment="申请粒度: resource_group|instance|database|table",
    )
    db_name: Mapped[str] = mapped_column(String(64), default="", comment="数据库名")
    table_name: Mapped[str] = mapped_column(String(64), default="", comment="表名")
    valid_date: Mapped[date] = mapped_column(Date, nullable=False, comment="申请有效期")
    limit_num: Mapped[int] = mapped_column(Integer, default=100, comment="行数限制")
    priv_type: Mapped[int] = mapped_column(Integer, default=1)
    apply_reason: Mapped[str] = mapped_column(String(500), default="", comment="申请理由")
    # 复用 AuditStatus: 0待审 1通过 2驳回 3取消
    status: Mapped[int] = mapped_column(Integer, default=0, comment="审批状态")
    audit_auth_groups: Mapped[str] = mapped_column(String(255), default="", comment="审批链")

    __table_args__ = (
        Index("ix_qpa_user", "user_id"),
        Index("ix_qpa_status", "status"),
        Index("ix_qpa_user_group", "user_group_id"),
        Index("ix_qpa_scope_type", "scope_type"),
    )


class QueryLog(BaseModel):
    """
    查询日志（记录每次在线查询）。
    修复 1.x TODO：user_id / instance_id 改为外键。
    """

    __tablename__ = "query_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sql_users.id", ondelete="SET NULL"), nullable=True
    )
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sql_instance.id", ondelete="SET NULL"), nullable=True
    )
    db_name: Mapped[str] = mapped_column(String(64), default="", comment="数据库名")
    sqllog: Mapped[str] = mapped_column(Text, nullable=False, comment="执行的 SQL")
    effect_row: Mapped[int] = mapped_column(BigInteger, default=0, comment="影响行数")
    cost_time_ms: Mapped[int] = mapped_column(Integer, default=0, comment="执行耗时(ms)")
    # 权限校验是否通过
    priv_check: Mapped[bool] = mapped_column(Boolean, default=False, comment="权限校验通过")
    # 是否命中脱敏规则
    hit_rule: Mapped[bool] = mapped_column(Boolean, default=False, comment="命中脱敏规则")
    # 是否实际执行了脱敏
    masking: Mapped[bool] = mapped_column(Boolean, default=False, comment="已脱敏")
    # 是否收藏
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, comment="已收藏")

    __table_args__ = (
        Index("ix_qlog_user_date", "user_id", "created_at"),
        Index("ix_qlog_instance", "instance_id"),
        Index("ix_qlog_tenant", "tenant_id"),
    )
