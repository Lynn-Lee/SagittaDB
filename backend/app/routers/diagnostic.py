"""
会话/锁/事务诊断路由（Sprint 4）。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as QParam
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import current_user, require_perm
from app.engines.registry import get_engine
from app.models.instance import Instance

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_instance(db: AsyncSession, instance_id: int) -> Instance:
    result = await db.execute(select(Instance).where(Instance.id == instance_id, Instance.is_active))
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(404, f"实例 ID={instance_id} 不存在")
    return inst


@router.get("/processlist/", summary="查看会话列表", dependencies=[Depends(require_perm("process_view"))])
async def get_processlist(
    instance_id: int = QParam(..., description="实例ID"),
    command_type: str = "Query",
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    inst = await _get_instance(db, instance_id)
    engine = get_engine(inst)
    rs = await engine.processlist(command_type=command_type)
    if rs.error:
        raise HTTPException(400, f"获取会话列表失败：{rs.error}")
    return {
        "column_list": rs.column_list,
        "rows": [list(r) if isinstance(r, tuple) else r for r in rs.rows],
        "total": len(rs.rows),
    }


@router.post("/kill/", summary="Kill 会话", dependencies=[Depends(require_perm("process_kill"))])
async def kill_session(
    instance_id: int,
    thread_id: int,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    inst = await _get_instance(db, instance_id)
    engine = get_engine(inst)

    if hasattr(engine, 'kill_connection'):
        rs = await engine.kill_connection(thread_id)
        if rs.error:
            raise HTTPException(400, f"Kill 失败：{rs.error}")
        return {"status": 0, "msg": f"已 Kill 会话 {thread_id}"}
    else:
        raise HTTPException(400, f"{inst.db_type} 引擎暂不支持 Kill 操作")


@router.get("/variables/", summary="实例参数列表")
async def get_variables(
    instance_id: int = QParam(...),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    inst = await _get_instance(db, instance_id)
    engine = get_engine(inst)
    rs = await engine.get_variables()
    if rs.error:
        raise HTTPException(400, f"获取参数失败：{rs.error}")
    cols = rs.column_list or []
    return {
        "params": [dict(zip(cols, r, strict=False)) if isinstance(r, tuple) else r for r in rs.rows]
    }
