"""系统管理路由：用户、资源组、权限、系统配置、审计日志（Pack C1）。"""
import logging

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import current_user, require_perm
from app.schemas.user import (
    GrantPermissionRequest,
    ResourceGroupCreate,
    ResourceGroupUpdate,
    UserCreate,
    UserUpdate,
)
from app.services.audit_log import AuditLogService
from app.services.system_config import SystemConfigService
from app.services.user import ResourceGroupService, UserService

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════
# 用户管理
# ═══════════════════════════════════════════════════════════

@router.get("/users/", summary="用户列表")
async def list_users(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200),
    search: str | None = None, is_active: bool | None = None,
    db: AsyncSession = Depends(get_db), _user=Depends(require_perm("user_manage")),
):
    total, items = await UserService.list_users(db, page, page_size, search, is_active)
    perms_map = {u.id: await UserService.get_permissions(db, u.id) for u in items}
    return {
        "total": total, "page": page, "page_size": page_size,
        "items": [
            {
                "id": u.id, "username": u.username, "display_name": u.display_name,
                "email": u.email, "is_active": u.is_active, "is_superuser": u.is_superuser,
                "auth_type": u.auth_type, "totp_enabled": u.totp_enabled,
                "resource_groups": [rg.id for rg in u.resource_groups],
                "permissions": perms_map.get(u.id, []), "tenant_id": u.tenant_id,
            }
            for u in items
        ],
    }


@router.post("/users/", summary="创建用户")
async def create_user(
    data: UserCreate, db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("user_manage")),
):
    user = await UserService.create_user(db, data)
    return {"status": 0, "msg": "用户创建成功", "data": {"id": user.id, "username": user.username}}


@router.get("/users/{user_id}/", summary="用户详情")
async def get_user(
    user_id: int, db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("user_manage")),
):
    from fastapi import HTTPException
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    permissions = await UserService.get_permissions(db, user.id)
    return {
        "id": user.id, "username": user.username, "display_name": user.display_name,
        "email": user.email, "phone": user.phone, "is_active": user.is_active,
        "is_superuser": user.is_superuser, "auth_type": user.auth_type,
        "totp_enabled": user.totp_enabled,
        "resource_groups": [rg.id for rg in user.resource_groups],
        "permissions": permissions, "tenant_id": user.tenant_id,
    }


@router.put("/users/{user_id}/", summary="更新用户")
async def update_user(
    user_id: int, data: UserUpdate, db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("user_manage")),
):
    user = await UserService.update_user(db, user_id, data)
    return {"status": 0, "msg": "用户已更新", "data": {"id": user.id}}


@router.delete("/users/{user_id}/", summary="删除用户")
async def delete_user(
    user_id: int, db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("user_manage")),
):
    await UserService.delete_user(db, user_id)
    return {"status": 0, "msg": "用户已删除"}


@router.post("/users/{user_id}/permissions/grant/", summary="授予权限")
async def grant_permissions(
    user_id: int, data: GrantPermissionRequest, db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("user_manage")),
):
    await UserService.grant_permissions(db, user_id, data.permission_codes)
    return {"status": 0, "msg": f"已授予 {len(data.permission_codes)} 个权限"}


@router.post("/users/{user_id}/permissions/revoke/", summary="撤销权限")
async def revoke_permissions(
    user_id: int, data: GrantPermissionRequest, db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("user_manage")),
):
    await UserService.revoke_permissions(db, user_id, data.permission_codes)
    return {"status": 0, "msg": f"已撤销 {len(data.permission_codes)} 个权限"}


# ═══════════════════════════════════════════════════════════
# 资源组管理
# ═══════════════════════════════════════════════════════════

@router.get("/resource-groups/", summary="资源组列表")
async def list_resource_groups(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200),
    search: str | None = None,
    db: AsyncSession = Depends(get_db), _user=Depends(current_user),
):
    total, items = await ResourceGroupService.list_groups(db, page, page_size, search)
    result = []
    for rg in items:
        mc = await ResourceGroupService.get_member_count(db, rg.id)
        result.append({
            "id": rg.id, "group_name": rg.group_name, "group_name_cn": rg.group_name_cn,
            "ding_webhook": rg.ding_webhook, "feishu_webhook": rg.feishu_webhook,
            "is_active": rg.is_active, "tenant_id": rg.tenant_id, "member_count": mc,
        })
    return {"total": total, "page": page, "page_size": page_size, "items": result}


@router.post("/resource-groups/", summary="创建资源组")
async def create_resource_group(
    data: ResourceGroupCreate, db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("resource_group_manage")),
):
    rg = await ResourceGroupService.create(db, data)
    return {"status": 0, "msg": "资源组创建成功", "data": {"id": rg.id, "group_name": rg.group_name}}


@router.put("/resource-groups/{rg_id}/", summary="更新资源组")
async def update_resource_group(
    rg_id: int, data: ResourceGroupUpdate, db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("resource_group_manage")),
):
    rg = await ResourceGroupService.update(db, rg_id, data)
    return {"status": 0, "msg": "资源组已更新", "data": {"id": rg.id}}


@router.delete("/resource-groups/{rg_id}/", summary="删除资源组")
async def delete_resource_group(
    rg_id: int, db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("resource_group_manage")),
):
    await ResourceGroupService.delete(db, rg_id)
    return {"status": 0, "msg": "资源组已删除"}


@router.get("/resource-groups/{rg_id}/members/", summary="资源组成员列表")
async def list_rg_members(
    rg_id: int, db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    from sqlalchemy import select

    from app.models.user import Users, user_resource_group
    result = await db.execute(
        select(Users).join(
            user_resource_group,
            Users.id == user_resource_group.c.user_id
        ).where(user_resource_group.c.resource_group_id == rg_id)
    )
    members = result.scalars().all()
    return {"items": [{"id": u.id, "username": u.username, "display_name": u.display_name, "email": u.email} for u in members]}


class MemberUpdateRequest(BaseModel):
    user_ids: list[int]


@router.post("/resource-groups/{rg_id}/members/", summary="更新资源组成员")
async def update_rg_members(
    rg_id: int,
    data: MemberUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("resource_group_manage")),
):
    """全量更新：传入的 user_ids 即为最终成员列表。"""
    from sqlalchemy import delete, select

    from app.models.user import ResourceGroup, user_resource_group

    rg_result = await db.execute(select(ResourceGroup).where(ResourceGroup.id == rg_id))
    rg = rg_result.scalar_one_or_none()
    if not rg:
        from fastapi import HTTPException
        raise HTTPException(404, "资源组不存在")

    # 清除现有成员
    await db.execute(delete(user_resource_group).where(user_resource_group.c.resource_group_id == rg_id))

    # 插入新成员
    for uid in data.user_ids:
        await db.execute(user_resource_group.insert().values(user_id=uid, resource_group_id=rg_id))

    await db.commit()
    return {"status": 0, "msg": f"资源组成员已更新，共 {len(data.user_ids)} 人"}


# ═══════════════════════════════════════════════════════════
# 权限码
# ═══════════════════════════════════════════════════════════

@router.get("/permissions/", summary="权限码列表")
async def list_permissions(db: AsyncSession = Depends(get_db), _user=Depends(current_user)):
    from sqlalchemy import select

    from app.models.user import Permission
    result = await db.execute(select(Permission).order_by(Permission.codename))
    perms = result.scalars().all()
    return {"permissions": [{"codename": p.codename, "name": p.name} for p in perms]}


# ═══════════════════════════════════════════════════════════
# 系统配置（Pack C1 完整实现）
# ═══════════════════════════════════════════════════════════

class ConfigUpdateRequest(BaseModel):
    updates: dict[str, str]


class MailTestRequest(BaseModel):
    to_email: str


class LdapTestRequest(BaseModel):
    test_username: str = ""
    test_password: str = ""


@router.get("/config/", summary="获取系统配置（按分组）")
async def get_system_config(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("system_config_manage")),
):
    return await SystemConfigService.get_all(db)


@router.post("/config/", summary="批量更新系统配置")
async def update_system_config(
    data: ConfigUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_perm("system_config_manage")),
):
    count, change_summary = await SystemConfigService.update_batch(db, data.updates)
    # 审计日志记录具体变更项（敏感字段只记key，不记值）
    detail = f"更新 {count} 个配置项：" + "；".join(change_summary) if change_summary else f"更新 {count} 个配置项"
    await AuditLogService.write(
        db, user, action="update_config", module="system",
        detail=detail, request=request,
    )
    return {"status": 0, "msg": f"已保存 {count} 个配置项", "count": count}


@router.post("/config/test/mail/", summary="测试邮件配置")
async def test_mail_config(
    data: MailTestRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("system_config_manage")),
):
    result = await SystemConfigService.test_mail(db, data.to_email)
    return result


@router.post("/config/test/dingtalk/", summary="测试钉钉配置")
async def test_dingtalk_config(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("system_config_manage")),
):
    return await SystemConfigService.test_dingtalk(db)


@router.post("/config/test/wecom/", summary="测试企业微信配置")
async def test_wecom_config(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("system_config_manage")),
):
    return await SystemConfigService.test_wecom(db)


@router.post("/config/test/feishu/", summary="测试飞书配置")
async def test_feishu_config(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("system_config_manage")),
):
    return await SystemConfigService.test_feishu(db)


@router.post("/config/test/ldap/", summary="测试 LDAP 配置")
async def test_ldap_config(
    data: LdapTestRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("system_config_manage")),
):
    return await SystemConfigService.test_ldap(db, data.test_username, data.test_password)


# ═══════════════════════════════════════════════════════════
# 审计日志（Pack C1）
# ═══════════════════════════════════════════════════════════

@router.get("/audit-logs/", summary="操作审计日志列表")
async def list_audit_logs(
    username: str | None = None,
    module: str | None = None,
    action: str | None = None,
    result: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_perm("audit_user")),
):
    total, logs = await AuditLogService.list_logs(
        db, username=username, module=module, action=action,
        result=result, date_start=date_start, date_end=date_end,
        page=page, page_size=page_size,
    )
    return {
        "total": total, "page": page, "page_size": page_size,
        "items": [
            {
                "id": log.id, "username": log.username, "action": log.action,
                "module": log.module, "detail": log.detail, "ip_address": log.ip_address,
                "result": log.result, "remark": log.remark,
                "created_at": log.created_at.isoformat() if log.created_at else "",
            }
            for log in logs
        ],
        "modules": AuditLogService.get_modules(),
    }


# ═══════════════════════════════════════════════════════════
# 初始化
# ═══════════════════════════════════════════════════════════

@router.post("/init/", summary="初始化系统", include_in_schema=False)
async def init_system(db: AsyncSession = Depends(get_db)):
    await UserService.init_default_permissions(db)
    existing = await UserService.get_by_username(db, "admin")
    if not existing:
        from app.schemas.user import UserCreate
        await UserService.create_user(db, UserCreate(
            username="admin", password="Admin@2024!",
            display_name="超级管理员", is_superuser=True,
        ))
        return {"status": 0, "msg": "系统初始化完成，默认管理员：admin / Admin@2024！（请立即修改密码）"}
    return {"status": 0, "msg": "系统已初始化，权限表已更新"}
