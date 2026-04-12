"""
角色与用户组业务逻辑服务。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, NotFoundException
from app.models.role import (
    Role,
    UserGroup,
    group_resource_group,
    role_permission,
    user_group_member,
)
from app.models.user import Permission, ResourceGroup, Users

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

BUILTIN_ROLES: list[dict] = [
    {
        "name": "superadmin",
        "name_cn": "超级管理员",
        "description": "拥有系统全部权限，is_superuser=True 时绕过一切检查",
        "permissions": [
            "menu_dashboard",
            "menu_sqlworkflow",
            "menu_query",
            "menu_ops",
            "sql_submit",
            "sql_review",
            "sql_execute",
            "sql_execute_for_resource_group",
            "query_submit",
            "query_applypriv",
            "query_review",
            "query_mgtpriv",
            "query_all_instances",
            "query_resource_group_instance",
            "process_view",
            "process_kill",
            "menu_monitor",
            "monitor_all_instances",
            "monitor_config_manage",
            "monitor_apply",
            "monitor_review",
            "monitor_alert_manage",
            "archive_apply",
            "archive_review",
            "audit_user",
            "menu_system",
            "menu_audit",
            "system_config_manage",
            "instance_manage",
            "resource_group_manage",
            "user_manage",
        ],
    },
    {
        "name": "dba",
        "name_cn": "全局DBA",
        "description": "全局 DBA，拥有 query_all_instances + monitor_all_instances",
        "permissions": [
            "menu_dashboard",
            "menu_sqlworkflow",
            "menu_query",
            "menu_ops",
            "sql_submit",
            "sql_review",
            "sql_execute",
            "sql_execute_for_resource_group",
            "query_submit",
            "query_applypriv",
            "query_review",
            "query_mgtpriv",
            "query_all_instances",
            "process_view",
            "process_kill",
            "menu_monitor",
            "monitor_all_instances",
            "monitor_config_manage",
            "monitor_apply",
            "monitor_review",
            "monitor_alert_manage",
            "archive_apply",
            "archive_review",
            "audit_user",
            "menu_audit",
            "instance_manage",
            "resource_group_manage",
        ],
    },
    {
        "name": "dba_group",
        "name_cn": "资源组DBA",
        "description": "资源组 DBA，运维权限但实例范围限于资源组（无 _all_instances 权限）",
        "permissions": [
            "menu_dashboard",
            "menu_sqlworkflow",
            "menu_query",
            "menu_ops",
            "sql_submit",
            "sql_review",
            "sql_execute",
            "sql_execute_for_resource_group",
            "query_submit",
            "query_applypriv",
            "query_review",
            "query_mgtpriv",
            "query_resource_group_instance",
            "process_view",
            "process_kill",
            "menu_monitor",
            "monitor_config_manage",
            "monitor_apply",
            "monitor_review",
            "archive_apply",
            "archive_review",
            "audit_user",
            "menu_audit",
            "instance_manage",
            "resource_group_manage",
        ],
    },
    {
        "name": "developer",
        "name_cn": "开发工程师",
        "description": "开发工程师，可提交工单和查询申请",
        "permissions": [
            "menu_dashboard",
            "menu_sqlworkflow",
            "menu_query",
            "sql_submit",
            "query_submit",
            "query_applypriv",
        ],
    },
]


class RoleService:
    @staticmethod
    async def get_by_id(db: AsyncSession, role_id: int) -> Role | None:
        result = await db.execute(
            select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Role | None:
        result = await db.execute(
            select(Role).options(selectinload(Role.permissions)).where(Role.name == name)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_roles(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 50,
        is_active: bool | None = None,
    ) -> tuple[int, list[Role]]:
        query = select(Role).options(selectinload(Role.permissions))
        if is_active is not None:
            query = query.where(Role.is_active.is_(is_active))
        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Role.id)
        result = await db.execute(query)
        return total, list(result.scalars().all())

    @staticmethod
    async def create_role(
        db: AsyncSession,
        name: str,
        name_cn: str = "",
        description: str = "",
        permission_codes: list[str] | None = None,
    ) -> Role:
        existing = await RoleService.get_by_name(db, name)
        if existing:
            raise ConflictException(f"角色 '{name}' 已存在")
        role = Role(name=name, name_cn=name_cn, description=description)
        db.add(role)
        await db.flush()

        if permission_codes:
            await RoleService._set_permissions(db, role, permission_codes)

        await db.commit()
        await db.refresh(role)
        logger.info("role_created: %s", name)
        return role

    @staticmethod
    async def update_role(
        db: AsyncSession,
        role_id: int,
        name_cn: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
        permission_codes: list[str] | None = None,
    ) -> Role:
        role = await RoleService.get_by_id(db, role_id)
        if not role:
            raise NotFoundException(f"角色 ID={role_id} 不存在")
        if name_cn is not None:
            role.name_cn = name_cn
        if description is not None:
            role.description = description
        if is_active is not None:
            role.is_active = is_active
        if permission_codes is not None:
            await RoleService._set_permissions(db, role, permission_codes)
        await db.commit()
        return await RoleService.get_by_id(db, role.id)

    @staticmethod
    async def delete_role(db: AsyncSession, role_id: int) -> None:
        role = await RoleService.get_by_id(db, role_id)
        if not role:
            raise NotFoundException(f"角色 ID={role_id} 不存在")
        if role.is_system:
            raise ConflictException(f"内置角色 '{role.name}' 不可删除")
        from sqlalchemy import update

        await db.execute(update(Users).where(Users.role_id == role_id).values(role_id=None))
        await db.delete(role)
        await db.commit()

    @staticmethod
    async def _set_permissions(db: AsyncSession, role: Role, codes: list[str]) -> None:
        await db.execute(delete(role_permission).where(role_permission.c.role_id == role.id))
        result = await db.execute(select(Permission).where(Permission.codename.in_(codes)))
        perms = list(result.scalars().all())
        existing_codes = {p.codename for p in perms}
        for code in codes:
            if code not in existing_codes:
                perm = Permission(codename=code, name=code)
                db.add(perm)
                perms.append(perm)
        await db.flush()
        for perm in perms:
            stmt = (
                pg_insert(role_permission)
                .values(role_id=role.id, permission_id=perm.id)
                .on_conflict_do_nothing()
            )
            await db.execute(stmt)

    @staticmethod
    async def init_builtin_roles(db: AsyncSession) -> None:
        """初始化 4 个内置角色及其权限码关联。先确保权限码存在。"""
        from app.services.user import UserService

        await UserService.init_default_permissions(db)
        for role_def in BUILTIN_ROLES:
            existing = await RoleService.get_by_name(db, role_def["name"])
            if not existing:
                role = Role(
                    name=role_def["name"],
                    name_cn=role_def["name_cn"],
                    description=role_def["description"],
                    is_system=True,
                )
                db.add(role)
                await db.flush()
                await RoleService._set_permissions(db, role, role_def["permissions"])
                await db.commit()
            else:
                await RoleService._set_permissions(db, existing, role_def["permissions"])
                await db.commit()


class UserGroupService:
    @staticmethod
    async def get_by_id(db: AsyncSession, group_id: int) -> UserGroup | None:
        result = await db.execute(select(UserGroup).where(UserGroup.id == group_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_groups(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 50,
        is_active: bool | None = None,
        parent_id: int | None = None,
    ) -> tuple[int, list[UserGroup]]:
        query = select(UserGroup)
        if is_active is not None:
            query = query.where(UserGroup.is_active.is_(is_active))
        if parent_id is not None:
            query = query.where(UserGroup.parent_id == parent_id)
        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(UserGroup.id)
        result = await db.execute(query)
        return total, list(result.scalars().all())

    @staticmethod
    async def create_group(
        db: AsyncSession,
        name: str,
        name_cn: str = "",
        description: str = "",
        leader_id: int | None = None,
        parent_id: int | None = None,
        resource_group_ids: list[int] | None = None,
        member_ids: list[int] | None = None,
    ) -> UserGroup:
        existing = await db.execute(select(UserGroup).where(UserGroup.name == name))
        if existing.scalar_one_or_none():
            raise ConflictException(f"用户组 '{name}' 已存在")
        group = UserGroup(
            name=name,
            name_cn=name_cn,
            description=description,
            leader_id=leader_id,
            parent_id=parent_id,
        )
        db.add(group)
        await db.flush()

        if resource_group_ids:
            rgs = await db.execute(
                select(ResourceGroup).where(ResourceGroup.id.in_(resource_group_ids))
            )
            for rg in rgs.scalars().all():
                await db.execute(
                    group_resource_group.insert().values(group_id=group.id, resource_group_id=rg.id)
                )

        if member_ids:
            for uid in member_ids:
                await db.execute(user_group_member.insert().values(user_id=uid, group_id=group.id))

        await db.commit()
        await db.refresh(group)
        logger.info("user_group_created: %s", name)
        return group

    @staticmethod
    async def update_group(
        db: AsyncSession,
        group_id: int,
        name_cn: str | None = None,
        description: str | None = None,
        leader_id: int | None = None,
        parent_id: int | None = None,
        is_active: bool | None = None,
        resource_group_ids: list[int] | None = None,
        member_ids: list[int] | None = None,
    ) -> UserGroup:
        group = await UserGroupService.get_by_id(db, group_id)
        if not group:
            raise NotFoundException(f"用户组 ID={group_id} 不存在")
        if name_cn is not None:
            group.name_cn = name_cn
        if description is not None:
            group.description = description
        if leader_id is not None:
            group.leader_id = leader_id
        if parent_id is not None:
            group.parent_id = parent_id
        if is_active is not None:
            group.is_active = is_active

        if resource_group_ids is not None:
            await db.execute(
                delete(group_resource_group).where(group_resource_group.c.group_id == group_id)
            )
            for rg_id in resource_group_ids:
                await db.execute(
                    group_resource_group.insert().values(group_id=group_id, resource_group_id=rg_id)
                )

        if member_ids is not None:
            await db.execute(
                delete(user_group_member).where(user_group_member.c.group_id == group_id)
            )
            for uid in member_ids:
                await db.execute(user_group_member.insert().values(user_id=uid, group_id=group_id))

        await db.commit()
        await db.refresh(group)
        return group

    @staticmethod
    async def delete_group(db: AsyncSession, group_id: int) -> None:
        group = await UserGroupService.get_by_id(db, group_id)
        if not group:
            raise NotFoundException(f"用户组 ID={group_id} 不存在")
        await db.delete(group)
        await db.commit()

    @staticmethod
    async def get_members(db: AsyncSession, group_id: int) -> list[Users]:
        result = await db.execute(
            select(Users)
            .join(user_group_member, Users.id == user_group_member.c.user_id)
            .where(user_group_member.c.group_id == group_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_resource_groups(db: AsyncSession, group_id: int) -> list[ResourceGroup]:
        result = await db.execute(
            select(ResourceGroup)
            .join(
                group_resource_group, ResourceGroup.id == group_resource_group.c.resource_group_id
            )
            .where(group_resource_group.c.group_id == group_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_user_groups_for_resource_group(
        db: AsyncSession, resource_group_id: int
    ) -> list[UserGroup]:  # noqa: F821
        result = await db.execute(
            select(UserGroup)
            .join(group_resource_group, UserGroup.id == group_resource_group.c.group_id)
            .where(group_resource_group.c.resource_group_id == resource_group_id)
        )
        return list(result.scalars().all())
