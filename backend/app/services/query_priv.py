"""
查询权限校验与管理服务（Sprint 2）。
使用 sqlglot 提取表引用，替代 Archery 1.x 对 goInception 的依赖（修复 P0-3）。
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundException
from app.models.instance import Instance
from app.models.query import QueryLog, QueryPrivilege, QueryPrivilegeApply
from app.services.masking import extract_table_refs

logger = logging.getLogger(__name__)


class QueryPrivService:
    """查询权限校验与管理。"""

    # ── 权限校验 ──────────────────────────────────────────────

    @staticmethod
    async def check_query_priv(
        db: AsyncSession,
        user: dict,
        instance: Instance,
        db_name: str,
        sql: str,
    ) -> tuple[bool, str]:
        """
        查询权限三层校验：
          L1: 超管 / 拥有 query_all_instances 权限 → 直接放行
          L2: 资源组隔离（实例必须在用户资源组内）
          L3: 库/表级授权记录（含用户组授权、资源组范围授权）

        Returns:
            (passed, reason)
        """
        user_id: int = user["id"]
        is_superuser: bool = user.get("is_superuser", False)
        perms: list[str] = user.get("permissions", [])

        # L1: 超管或全量查询权限
        if is_superuser or "query_all_instances" in perms:
            return True, "admin"

        # L2: 资源组隔离（实例必须在用户可访问的资源组内）
        user_rg_ids: list[int] = user.get("resource_groups", [])
        instance_rg_ids = [rg.id for rg in instance.resource_groups]
        if not any(rid in instance_rg_ids for rid in user_rg_ids):
            return False, "实例不在你的资源组内"

        # 用户所属组ID列表
        user_group_ids: list[int] = user.get("user_groups", [])

        # L3: 用 sqlglot 提取表引用，校验库/表级权限
        table_refs = extract_table_refs(sql, db_name, instance.db_type)
        if not table_refs:
            has_db_priv = await QueryPrivService._has_db_priv(
                db, user_id, instance.id, db_name, user_group_ids, user_rg_ids
            )
            if has_db_priv:
                return True, "db_privilege"
            return False, f"没有数据库 {db_name} 的查询权限，请申请后重试"

        for ref in table_refs:
            schema = ref.get("schema", db_name) or db_name
            table = ref.get("name", "")
            if not table:
                continue
            has_priv = await QueryPrivService._has_table_priv(
                db, user_id, instance.id, schema, table, user_group_ids, user_rg_ids
            )
            if not has_priv:
                has_db = await QueryPrivService._has_db_priv(
                    db, user_id, instance.id, schema, user_group_ids, user_rg_ids
                )
                if not has_db:
                    return False, f"没有表 {schema}.{table} 的查询权限，请申请后重试"

        return True, "privilege"

    @staticmethod
    async def _has_db_priv(
        db: AsyncSession,
        user_id: int,
        instance_id: int,
        db_name: str,
        user_group_ids: list[int] | None = None,
        user_rg_ids: list[int] | None = None,
    ) -> bool:
        """v2: 检查库级权限，含用户直接授权、用户组授权、资源组范围授权。"""
        today = date.today()
        conditions = []

        # 条件1: 用户直接授权
        user_cond = and_(
            QueryPrivilege.user_id == user_id,
            QueryPrivilege.instance_id == instance_id,
            QueryPrivilege.db_name == db_name,
            QueryPrivilege.priv_type == 1,
            QueryPrivilege.valid_date >= today,
            QueryPrivilege.is_deleted == 0,
        )
        conditions.append(user_cond)

        # 条件2: 用户组授权
        if user_group_ids:
            conditions.append(
                and_(
                    QueryPrivilege.user_group_id.in_(user_group_ids),
                    QueryPrivilege.instance_id == instance_id,
                    QueryPrivilege.db_name == db_name,
                    QueryPrivilege.priv_type == 1,
                    QueryPrivilege.valid_date >= today,
                    QueryPrivilege.is_deleted == 0,
                )
            )

        # 条件3: 资源组范围授权（scope_type=resource_group）
        if user_rg_ids:
            conditions.append(
                and_(
                    QueryPrivilege.resource_group_id.in_(user_rg_ids),
                    QueryPrivilege.scope_type == "resource_group",
                    QueryPrivilege.db_name == db_name,
                    QueryPrivilege.valid_date >= today,
                    QueryPrivilege.is_deleted == 0,
                )
            )

        from sqlalchemy import or_

        result = await db.execute(select(QueryPrivilege).where(or_(*conditions)))
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def _has_table_priv(
        db: AsyncSession,
        user_id: int,
        instance_id: int,
        db_name: str,
        table_name: str,
        user_group_ids: list[int] | None = None,
        user_rg_ids: list[int] | None = None,
    ) -> bool:
        """v2: 检查表级权限，含用户直接授权、用户组授权、资源组范围授权。"""
        today = date.today()
        conditions = []

        user_cond = and_(
            QueryPrivilege.user_id == user_id,
            QueryPrivilege.instance_id == instance_id,
            QueryPrivilege.db_name == db_name,
            QueryPrivilege.table_name == table_name,
            QueryPrivilege.priv_type == 2,
            QueryPrivilege.valid_date >= today,
            QueryPrivilege.is_deleted == 0,
        )
        conditions.append(user_cond)

        if user_group_ids:
            conditions.append(
                and_(
                    QueryPrivilege.user_group_id.in_(user_group_ids),
                    QueryPrivilege.instance_id == instance_id,
                    QueryPrivilege.db_name == db_name,
                    QueryPrivilege.table_name == table_name,
                    QueryPrivilege.priv_type == 2,
                    QueryPrivilege.valid_date >= today,
                    QueryPrivilege.is_deleted == 0,
                )
            )

        if user_rg_ids:
            conditions.append(
                and_(
                    QueryPrivilege.resource_group_id.in_(user_rg_ids),
                    QueryPrivilege.scope_type == "resource_group",
                    QueryPrivilege.db_name == db_name,
                    (QueryPrivilege.table_name == table_name) | QueryPrivilege.table_name.is_(None),
                    QueryPrivilege.valid_date >= today,
                    QueryPrivilege.is_deleted == 0,
                )
            )

        from sqlalchemy import or_

        result = await db.execute(select(QueryPrivilege).where(or_(*conditions)))
        return result.scalar_one_or_none() is not None

    # ── 权限记录管理 ──────────────────────────────────────────

    @staticmethod
    async def list_my_privileges(
        db: AsyncSession, user_id: int, instance_id: int | None = None
    ) -> list[QueryPrivilege]:
        query = select(QueryPrivilege).where(
            and_(
                QueryPrivilege.user_id == user_id,
                QueryPrivilege.is_deleted == 0,
                QueryPrivilege.valid_date >= date.today(),
            )
        )
        if instance_id:
            query = query.where(QueryPrivilege.instance_id == instance_id)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def apply_privilege(
        db: AsyncSession,
        user_id: int,
        instance_id: int,
        group_id: int,
        db_name: str,
        table_name: str,
        valid_date: date,
        limit_num: int,
        priv_type: int,
        apply_reason: str,
        audit_auth_groups: str,
        title: str,
    ) -> QueryPrivilegeApply:
        apply = QueryPrivilegeApply(
            title=title,
            user_id=user_id,
            instance_id=instance_id,
            group_id=group_id,
            db_name=db_name,
            table_name=table_name or "",
            valid_date=valid_date,
            limit_num=limit_num,
            priv_type=priv_type,
            apply_reason=apply_reason,
            status=0,  # 待审核
            audit_auth_groups=audit_auth_groups,
        )
        db.add(apply)
        await db.commit()
        await db.refresh(apply)
        logger.info("query_priv_apply created: user=%s instance=%s", user_id, instance_id)
        return apply

    @staticmethod
    async def list_applies(
        db: AsyncSession,
        user_id: int | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[QueryPrivilegeApply]]:
        query = select(QueryPrivilegeApply)
        if user_id is not None:
            query = query.where(QueryPrivilegeApply.user_id == user_id)
        if status is not None:
            query = query.where(QueryPrivilegeApply.status == status)

        total_q = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_q.scalar_one()

        query = query.order_by(QueryPrivilegeApply.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return total, list(result.scalars().all())

    @staticmethod
    async def audit_apply(
        db: AsyncSession,
        apply_id: int,
        auditor: dict,
        action: str,  # "pass" | "reject"
        remark: str = "",
    ) -> QueryPrivilegeApply:
        result = await db.execute(
            select(QueryPrivilegeApply).where(QueryPrivilegeApply.id == apply_id)
        )
        apply = result.scalar_one_or_none()
        if not apply:
            raise NotFoundException(f"申请 ID={apply_id} 不存在")
        if apply.status != 0:
            raise AppException("该申请已审批，不能重复操作", code=400)

        if action == "pass":
            apply.status = 1
            # 创建权限记录
            priv = QueryPrivilege(
                user_id=apply.user_id,
                instance_id=apply.instance_id,
                db_name=apply.db_name,
                table_name=apply.table_name,
                valid_date=apply.valid_date,
                limit_num=apply.limit_num,
                priv_type=apply.priv_type,
                is_deleted=0,
            )
            db.add(priv)
        elif action == "reject":
            apply.status = 2
        else:
            raise AppException("action 必须是 pass 或 reject", code=400)

        await db.commit()
        await db.refresh(apply)
        return apply

    @staticmethod
    async def revoke_privilege(db: AsyncSession, priv_id: int, operator: dict) -> None:
        result = await db.execute(select(QueryPrivilege).where(QueryPrivilege.id == priv_id))
        priv = result.scalar_one_or_none()
        if not priv:
            raise NotFoundException(f"权限 ID={priv_id} 不存在")
        priv.is_deleted = 1
        await db.commit()

    # ── 查询日志 ──────────────────────────────────────────────

    @staticmethod
    async def write_log(
        db: AsyncSession,
        user_id: int,
        instance_id: int,
        db_name: str,
        sql: str,
        effect_row: int,
        cost_time_ms: int,
        priv_check: bool,
        hit_rule: bool,
        masking: bool,
    ) -> None:
        log = QueryLog(
            user_id=user_id,
            instance_id=instance_id,
            db_name=db_name,
            sqllog=sql[:10000],  # 截断超长 SQL
            effect_row=effect_row,
            cost_time_ms=cost_time_ms,
            priv_check=priv_check,
            hit_rule=hit_rule,
            masking=masking,
        )
        db.add(log)
        await db.commit()

    @staticmethod
    async def list_logs(
        db: AsyncSession,
        user_id: int | None = None,
        instance_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[QueryLog]]:
        query = select(QueryLog)
        if user_id:
            query = query.where(QueryLog.user_id == user_id)
        if instance_id:
            query = query.where(QueryLog.instance_id == instance_id)

        total_q = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_q.scalar_one()

        query = query.order_by(QueryLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return total, list(result.scalars().all())
