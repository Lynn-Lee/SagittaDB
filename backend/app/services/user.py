"""
用户与资源组业务逻辑服务。
"""

from __future__ import annotations

import logging

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import hash_password, verify_password
from app.models.role import role_permission
from app.models.user import Permission, ResourceGroup, Users, user_permission, user_resource_group
from app.schemas.user import (
    ResourceGroupCreate,
    ResourceGroupUpdate,
    UserCreate,
    UserUpdate,
)

logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> Users | None:
        result = await db.execute(
            select(Users)
            .options(
                selectinload(Users.resource_groups),
                selectinload(Users.user_groups),
                selectinload(Users.role),
            )
            .where(Users.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> Users | None:
        result = await db.execute(
            select(Users)
            .options(
                selectinload(Users.resource_groups),
                selectinload(Users.role),
            )
            .where(Users.username == username)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_phone(db: AsyncSession, phone: str) -> Users | None:
        result = await db.execute(
            select(Users)
            .options(selectinload(Users.resource_groups))
            .where(Users.phone == phone, Users.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_users(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[int, list[Users]]:
        query = select(Users).options(
            selectinload(Users.resource_groups),
            selectinload(Users.user_groups),
            selectinload(Users.role),
        )
        if search:
            query = query.where(
                Users.username.ilike(f"%{search}%")
                | Users.display_name.ilike(f"%{search}%")
                | Users.email.ilike(f"%{search}%")
            )
        if is_active is not None:
            query = query.where(Users.is_active.is_(is_active))

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return total, list(result.scalars().all())

    @staticmethod
    async def create_user(db: AsyncSession, data: UserCreate) -> Users:
        existing = await UserService.get_by_username(db, data.username)
        if existing:
            raise ConflictException(f"用户名 '{data.username}' 已存在")

        user = Users(
            username=data.username,
            password=hash_password(data.password),
            display_name=data.display_name or data.username,
            email=data.email,
            phone=data.phone,
            is_superuser=data.is_superuser,
            auth_type="local",
        )
        db.add(user)
        await db.flush()

        if data.resource_group_ids:
            rgs = await ResourceGroupService.get_by_ids(db, data.resource_group_ids)
            user.resource_groups = rgs

        await db.commit()
        user = await UserService.get_by_id(db, user.id)
        logger.info("user_created: %s", data.username)
        return user

    @staticmethod
    async def update_user(db: AsyncSession, user_id: int, data: UserUpdate) -> Users:
        user = await UserService.get_by_id(db, user_id)
        if not user:
            raise NotFoundException(f"用户 ID={user_id} 不存在")

        if data.display_name is not None:
            user.display_name = data.display_name
        if data.email is not None:
            user.email = data.email
        if data.phone is not None:
            user.phone = data.phone
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.is_superuser is not None:
            user.is_superuser = data.is_superuser
        # v2 字段：支持显式清空（0 表示清空 role_id/manager_id）
        if data.role_id is not None:
            user.role_id = data.role_id if data.role_id else None
        if data.manager_id is not None:
            user.manager_id = data.manager_id if data.manager_id else None
        if data.employee_id is not None:
            user.employee_id = data.employee_id
        if data.department is not None:
            user.department = data.department
        if data.title is not None:
            user.title = data.title
        if data.resource_group_ids is not None:
            rgs = await ResourceGroupService.get_by_ids(db, data.resource_group_ids)
            user.resource_groups = rgs
        if data.user_group_ids is not None:
            from app.models.role import UserGroup

            ugs_result = await db.execute(
                select(UserGroup).where(UserGroup.id.in_(data.user_group_ids))
            )
            user.user_groups = list(ugs_result.scalars().all())

        await db.commit()
        user = await UserService.get_by_id(db, user.id)
        return user

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int) -> None:
        user = await UserService.get_by_id(db, user_id)
        if not user:
            raise NotFoundException(f"用户 ID={user_id} 不存在")
        await db.delete(user)
        await db.commit()

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> None:
        user = await UserService.get_by_id(db, user_id)
        if not user:
            raise NotFoundException("用户不存在")
        if not verify_password(old_password, user.password):
            from app.core.exceptions import AppException

            raise AppException("原密码错误", code=400)
        user.password = hash_password(new_password)
        await db.commit()

    @staticmethod
    async def get_permissions(db: AsyncSession, user_id: int) -> list[str]:
        result = await db.execute(
            select(Permission.codename)
            .join(user_permission, Permission.id == user_permission.c.permission_id)
            .where(user_permission.c.user_id == user_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_merged_permissions(
        db: AsyncSession, user_id: int, db_user: Users | None = None
    ) -> list[str]:
        """v2: 合并角色权限 + 用户直接权限。"""

        direct = set(await UserService.get_permissions(db, user_id))
        role_perms: set[str] = set()
        if db_user is None:
            db_user = await UserService.get_by_id(db, user_id)
        if db_user and db_user.role_id:
            result = await db.execute(
                select(Permission.codename)
                .join(role_permission, Permission.id == role_permission.c.permission_id)
                .where(role_permission.c.role_id == db_user.role_id)
            )
            role_perms = set(result.scalars().all())
        return sorted(role_perms | direct)

    @staticmethod
    async def grant_permissions(db: AsyncSession, user_id: int, perm_codes: list[str]) -> None:
        user = await UserService.get_by_id(db, user_id)
        if not user:
            raise NotFoundException(f"用户 ID={user_id} 不存在")

        result = await db.execute(select(Permission).where(Permission.codename.in_(perm_codes)))
        perms = list(result.scalars().all())
        existing_codes = {p.codename for p in perms}

        for code in perm_codes:
            if code not in existing_codes:
                perm = Permission(codename=code, name=code)
                db.add(perm)
                perms.append(perm)
        await db.flush()

        for perm in perms:
            stmt = (
                pg_insert(user_permission)
                .values(user_id=user_id, permission_id=perm.id)
                .on_conflict_do_nothing()
            )
            await db.execute(stmt)
        await db.commit()

    @staticmethod
    async def revoke_permissions(db: AsyncSession, user_id: int, perm_codes: list[str]) -> None:
        result = await db.execute(select(Permission).where(Permission.codename.in_(perm_codes)))
        perm_ids = [p.id for p in result.scalars().all()]
        if perm_ids:
            await db.execute(
                delete(user_permission).where(
                    user_permission.c.user_id == user_id,
                    user_permission.c.permission_id.in_(perm_ids),
                )
            )
            await db.commit()

    @staticmethod
    async def init_default_permissions(db: AsyncSession) -> None:
        """初始化标准权限定义。"""
        default_perms = [
            ("menu_dashboard", "Dashboard 菜单"),
            ("menu_sqlworkflow", "SQL 工单菜单"),
            ("sql_submit", "提交 SQL 工单"),
            ("sql_review", "审核 SQL 工单"),
            ("sql_execute", "执行工单（自己）"),
            ("sql_execute_for_resource_group", "执行工单（资源组）"),
            ("query_submit", "提交查询"),
            ("query_applypriv", "申请查询权限"),
            ("query_review", "审核查询权限申请"),
            ("query_mgtpriv", "管理查询权限"),
            ("query_all_instances", "查询所有实例"),
            ("query_resource_group_instance", "查询资源组内实例"),
            ("process_view", "查看会话"),
            ("process_kill", "Kill 会话"),
            ("menu_monitor", "可观测中心菜单"),
            ("monitor_all_instances", "查看所有实例监控"),
            ("monitor_config_manage", "管理采集配置"),
            ("monitor_apply", "申请监控权限"),
            ("monitor_review", "审批监控权限"),
            ("monitor_alert_manage", "管理告警规则"),
            ("archive_apply", "申请数据归档"),
            ("archive_review", "审批数据归档"),
            ("audit_user", "查看审计日志"),
            ("system_config_manage", "管理系统配置"),
            ("instance_manage", "管理实例"),
            ("resource_group_manage", "管理资源组"),
            ("user_manage", "管理用户"),
        ]
        for codename, name in default_perms:
            existing = await db.execute(select(Permission).where(Permission.codename == codename))
            if not existing.scalar_one_or_none():
                db.add(Permission(codename=codename, name=name))
        await db.commit()


class ResourceGroupService:
    @staticmethod
    async def get_by_id(db: AsyncSession, rg_id: int) -> ResourceGroup | None:
        result = await db.execute(select(ResourceGroup).where(ResourceGroup.id == rg_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_ids(db: AsyncSession, rg_ids: list[int]) -> list[ResourceGroup]:
        if not rg_ids:
            return []
        result = await db.execute(select(ResourceGroup).where(ResourceGroup.id.in_(rg_ids)))
        return list(result.scalars().all())

    @staticmethod
    async def list_groups(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[int, list[ResourceGroup]]:
        query = select(ResourceGroup)
        if search:
            query = query.where(
                ResourceGroup.group_name.ilike(f"%{search}%")
                | ResourceGroup.group_name_cn.ilike(f"%{search}%")
            )
        total_q = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_q.scalar_one()
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return total, list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, data: ResourceGroupCreate) -> ResourceGroup:
        existing = await db.execute(
            select(ResourceGroup).where(ResourceGroup.group_name == data.group_name)
        )
        if existing.scalar_one_or_none():
            raise ConflictException(f"资源组 '{data.group_name}' 已存在")
        rg = ResourceGroup(**data.model_dump())
        db.add(rg)
        await db.commit()
        await db.refresh(rg)
        return rg

    @staticmethod
    async def update(db: AsyncSession, rg_id: int, data: ResourceGroupUpdate) -> ResourceGroup:
        rg = await ResourceGroupService.get_by_id(db, rg_id)
        if not rg:
            raise NotFoundException(f"资源组 ID={rg_id} 不存在")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(rg, field, value)
        await db.commit()
        await db.refresh(rg)
        return rg

    @staticmethod
    async def delete(db: AsyncSession, rg_id: int) -> None:
        rg = await ResourceGroupService.get_by_id(db, rg_id)
        if not rg:
            raise NotFoundException(f"资源组 ID={rg_id} 不存在")
        await db.delete(rg)
        await db.commit()

    @staticmethod
    async def get_member_count(db: AsyncSession, rg_id: int) -> int:
        """v2: 返回直接成员数（不含用户组成员）。前端成员管理穿梭框仅显示直接成员。"""
        result = await db.execute(
            select(func.count())
            .select_from(user_resource_group)
            .where(user_resource_group.c.resource_group_id == rg_id)
        )
        return result.scalar_one()
