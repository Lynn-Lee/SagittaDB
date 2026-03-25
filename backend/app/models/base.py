"""
所有 ORM 模型的公共基类。
包含 tenant_id（SaaS 预留）、created_at、updated_at 三个公共字段。
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 声明基类。"""
    pass


class BaseModel(Base):
    """
    所有业务模型继承此类。
    
    tenant_id: SaaS 预留字段，企业版固定为 1。
               3.0 升级时在 TenantMiddleware 中从 JWT 提取并注入 DB 查询。
    """
    __abstract__ = True

    # SaaS 多租户预留（企业版 default=1，不实现路由逻辑）
    tenant_id: Mapped[int] = mapped_column(
        Integer, default=1, index=True, nullable=False, comment="租户ID（SaaS预留）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )
