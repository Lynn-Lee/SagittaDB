"""
在线查询路由（Sprint 2）。
完整实现：执行查询、权限校验、数据脱敏、查询日志。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as QParam
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import current_user
from app.engines.registry import get_engine
from app.models.instance import Instance, InstanceDatabase
from app.schemas.query import QueryExecuteRequest
from app.services.masking import DataMaskingService
from app.services.masking_rule import MaskingRuleService
from app.services.query_priv import QueryPrivService

logger = logging.getLogger(__name__)
router = APIRouter()


async def _load_instance(db: AsyncSession, instance_id: int) -> Instance:
    result = await db.execute(
        select(Instance)
        .options(selectinload(Instance.resource_groups))
        .where(Instance.id == instance_id, Instance.is_active)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(404, f"实例 ID={instance_id} 不存在或已停用")
    return inst


@router.post("/", summary="执行在线查询")
async def execute_query(
    data: QueryExecuteRequest,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    执行在线查询，完整流程：
    1. 加载实例
    2. 查询权限校验（sqlglot 解析表引用，替代 goInception）
    3. 引擎执行查询
    4. 数据脱敏（sqlglot 解析列引用，支持所有方言）
    5. 写入查询日志
    """
    # ── 1. 加载实例 ────────────────────────────────────────────
    inst = await _load_instance(db, data.instance_id)
    engine = get_engine(inst)

    # ── 2. SQL 前置检查 ────────────────────────────────────────
    check = engine.query_check(data.db_name, data.sql)
    if check.get("msg") and check.get("syntax_error") is not False and check.get("syntax_error"):
        raise HTTPException(400, f"SQL 语法错误：{check['msg']}")

    # ── 3. 查询权限校验 ────────────────────────────────────────
    passed, reason = await QueryPrivService.check_query_priv(
        db=db,
        user=user,
        instance=inst,
        db_name=data.db_name,
        sql=data.sql,
    )
    if not passed:
        raise HTTPException(403, reason)

    # ── 3.5 数据库禁用校验（非超管）─────────────────────────────────
    if not user.get("is_superuser", False):
        inst_db_result = await db.execute(
            select(InstanceDatabase).where(
                InstanceDatabase.instance_id == data.instance_id,
                InstanceDatabase.db_name == data.db_name,
                InstanceDatabase.is_active.is_(True),
            )
        )
        if not inst_db_result.scalar_one_or_none():
            raise HTTPException(403, f"数据库 {data.db_name} 已禁用或未注册，不可查询")

    # ── 4. 注入 LIMIT ──────────────────────────────────────────
    safe_sql = engine.filter_sql(data.sql, data.limit_num)

    # ── 5. 执行查询 ────────────────────────────────────────────
    resultset = await engine.query(
        db_name=data.db_name,
        sql=safe_sql,
        limit_num=data.limit_num,
    )

    if resultset.error:
        raise HTTPException(400, f"查询执行失败：{resultset.error}")

    # ── 6. 数据脱敏（sqlglot，支持所有方言）────────────────────
    # 从数据库加载适用于此实例和数据库的脱敏规则
    active_rules = await MaskingRuleService.get_rules_for_instance(
        db, data.instance_id, data.db_name
    )
    masking_svc = DataMaskingService(rules=active_rules)
    masked_result = masking_svc.mask_result(resultset, data.sql, inst.db_type)
    is_masked = masked_result is not resultset

    # ── 7. 写查询日志（异步，不阻塞响应）─────────────────────
    try:
        await QueryPrivService.write_log(
            db=db,
            user_id=user["id"],
            instance_id=inst.id,
            db_name=data.db_name,
            sql=data.sql,
            effect_row=resultset.affected_rows,
            cost_time_ms=resultset.cost_time,
            priv_check=passed,
            hit_rule=False,
            masking=is_masked,
        )
    except Exception as e:
        logger.warning("write_query_log failed: %s", str(e))

    # ── 8. 返回结果 ────────────────────────────────────────────
    # 将 tuple 行转为 list（JSON 序列化友好）
    rows_as_list = []
    for row in masked_result.rows:
        if isinstance(row, (tuple, list)):
            rows_as_list.append(
                [
                    str(v) if v is not None and not isinstance(v, (int, float, bool, str)) else v
                    for v in row
                ]
            )
        elif isinstance(row, dict):
            rows_as_list.append(list(row.values()))
        else:
            rows_as_list.append([str(row)])

    return {
        "column_list": masked_result.column_list,
        "rows": rows_as_list,
        "affected_rows": masked_result.affected_rows,
        "cost_time_ms": masked_result.cost_time,
        "is_masked": is_masked,
        "error": "",
    }


@router.get("/logs/", summary="查询日志列表")
async def list_query_logs(
    instance_id: int | None = None,
    page: int = QParam(1, ge=1),
    page_size: int = QParam(20, ge=1, le=100),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    # 普通用户只能看自己的日志，超管可看所有
    uid = None if user.get("is_superuser") else user["id"]
    total, logs = await QueryPrivService.list_logs(
        db, user_id=uid, instance_id=instance_id, page=page, page_size=page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": log.id,
                "db_name": log.db_name,
                "sqllog": log.sqllog[:200],
                "effect_row": log.effect_row,
                "cost_time_ms": log.cost_time_ms,
                "priv_check": log.priv_check,
                "masking": log.masking,
                "is_favorite": log.is_favorite,
                "created_at": log.created_at.isoformat() if log.created_at else "",
            }
            for log in logs
        ],
    }


@router.post("/logs/{log_id}/favorite/", summary="收藏/取消收藏查询")
async def toggle_favorite(
    log_id: int,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.query import QueryLog

    result = await db.execute(
        select(QueryLog).where(QueryLog.id == log_id, QueryLog.user_id == user["id"])
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(404, "查询日志不存在")
    log.is_favorite = not log.is_favorite
    await db.commit()
    return {"status": 0, "is_favorite": log.is_favorite}
