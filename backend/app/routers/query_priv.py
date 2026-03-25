"""
查询权限管理路由（Sprint 2）。
"""
import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query as QParam
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import current_user, require_perm
from app.schemas.query import AuditPrivRequest, PrivApplyRequest
from app.services.query_priv import QueryPrivService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/privileges/", summary="我的查询权限列表")
async def list_my_privileges(
    instance_id: int | None = None,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    privs = await QueryPrivService.list_my_privileges(
        db, user_id=user["id"], instance_id=instance_id
    )
    return {
        "items": [
            {
                "id": p.id,
                "instance_id": p.instance_id,
                "db_name": p.db_name,
                "table_name": p.table_name,
                "valid_date": p.valid_date.isoformat(),
                "limit_num": p.limit_num,
                "priv_type": p.priv_type,
                "created_at": p.created_at.isoformat() if p.created_at else "",
            }
            for p in privs
        ]
    }


@router.post("/privileges/apply/", summary="申请查询权限")
async def apply_privilege(
    data: PrivApplyRequest,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    apply = await QueryPrivService.apply_privilege(
        db=db,
        user_id=user["id"],
        instance_id=data.instance_id,
        group_id=data.group_id,
        db_name=data.db_name,
        table_name=data.table_name,
        valid_date=data.valid_date,
        limit_num=data.limit_num,
        priv_type=data.priv_type,
        apply_reason=data.apply_reason,
        audit_auth_groups=data.audit_auth_groups,
        title=data.title,
    )
    return {"status": 0, "msg": "申请已提交", "data": {"apply_id": apply.id}}


@router.get("/privileges/applies/", summary="权限申请列表")
async def list_applies(
    status: int | None = None,
    page: int = QParam(1, ge=1),
    page_size: int = QParam(20, ge=1, le=100),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    # 普通用户只看自己的，审核员看所有待审核的
    if user.get("is_superuser") or "query_review" in user.get("permissions", []):
        uid = None
    else:
        uid = user["id"]

    total, applies = await QueryPrivService.list_applies(
        db, user_id=uid, status=status, page=page, page_size=page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": a.id,
                "title": a.title,
                "instance_id": a.instance_id,
                "db_name": a.db_name,
                "table_name": a.table_name,
                "valid_date": a.valid_date.isoformat(),
                "limit_num": a.limit_num,
                "priv_type": a.priv_type,
                "apply_reason": a.apply_reason,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else "",
            }
            for a in applies
        ],
    }


@router.post(
    "/privileges/audit/",
    summary="审批查询权限申请",
    dependencies=[Depends(require_perm("query_review"))],
)
async def audit_apply(
    apply_id: int,
    data: AuditPrivRequest,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    apply = await QueryPrivService.audit_apply(
        db=db,
        apply_id=apply_id,
        auditor=user,
        action=data.action,
        remark=data.remark,
    )
    msg = "已通过" if data.action == "pass" else "已驳回"
    return {"status": 0, "msg": msg, "data": {"apply_id": apply.id, "status": apply.status}}


@router.delete(
    "/privileges/{priv_id}/",
    summary="撤销查询权限",
    dependencies=[Depends(require_perm("query_mgtpriv"))],
)
async def revoke_privilege(
    priv_id: int,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await QueryPrivService.revoke_privilege(db, priv_id=priv_id, operator=user)
    return {"status": 0, "msg": "权限已撤销"}
