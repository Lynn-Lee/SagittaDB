"""
查询权限校验与管理服务。
v2-lite: 资源访问范围由 UserGroup -> ResourceGroup -> Instance 决定，
数据级授权仅保留 user 主体的 database / table 两级粒度。
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException, NotFoundException
from app.models.instance import Instance
from app.models.query import QueryLog, QueryPrivilege, QueryPrivilegeApply
from app.services.masking import extract_table_refs

logger = logging.getLogger(__name__)


class QueryPrivService:
    """查询权限校验与管理。"""

    @staticmethod
    def user_has_instance_access(user: dict, instance: Instance) -> bool:
        if user.get("is_superuser") or "query_all_instances" in user.get("permissions", []):
            return True
        user_rg_ids = set(user.get("resource_groups", []))
        instance_rg_ids = {rg.id for rg in instance.resource_groups}
        return bool(user_rg_ids & instance_rg_ids)

    @staticmethod
    def _normalize_scope_type(scope_type: str | None, table_name: str = "") -> tuple[str, int]:
        if scope_type == "table" or table_name.strip():
            return "table", 2
        return "database", 1

    @staticmethod
    async def _has_db_priv(
        db: AsyncSession,
        user_id: int,
        instance_id: int,
        db_name: str,
    ) -> bool:
        result = await db.execute(
            select(QueryPrivilege).where(
                and_(
                    QueryPrivilege.user_id == user_id,
                    QueryPrivilege.user_group_id.is_(None),
                    QueryPrivilege.instance_id == instance_id,
                    QueryPrivilege.scope_type == "database",
                    QueryPrivilege.db_name == db_name,
                    QueryPrivilege.valid_date >= date.today(),
                    QueryPrivilege.is_deleted == 0,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def _has_table_priv(
        db: AsyncSession,
        user_id: int,
        instance_id: int,
        db_name: str,
        table_name: str,
    ) -> bool:
        result = await db.execute(
            select(QueryPrivilege).where(
                and_(
                    QueryPrivilege.user_id == user_id,
                    QueryPrivilege.user_group_id.is_(None),
                    QueryPrivilege.instance_id == instance_id,
                    QueryPrivilege.scope_type == "table",
                    QueryPrivilege.db_name == db_name,
                    QueryPrivilege.table_name == table_name,
                    QueryPrivilege.valid_date >= date.today(),
                    QueryPrivilege.is_deleted == 0,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def _resolve_apply_group_id(
        db: AsyncSession,
        user: dict,
        instance_id: int,
        group_id: int | None,
    ) -> int:
        result = await db.execute(
            select(Instance)
            .options(selectinload(Instance.resource_groups))
            .where(Instance.id == instance_id, Instance.is_active.is_(True))
        )
        instance = result.scalar_one_or_none()
        if not instance:
            raise NotFoundException(f"实例 ID={instance_id} 不存在或已停用")
        if not QueryPrivService.user_has_instance_access(user, instance):
            raise AppException("实例不在你的资源组内，不能申请查询权限", code=403)

        allowed_group_ids = {rg.id for rg in instance.resource_groups} & set(user.get("resource_groups", []))
        if group_id is not None:
            if group_id not in allowed_group_ids:
                raise AppException("所选资源组与目标实例不匹配", code=400)
            return group_id
        if allowed_group_ids:
            return sorted(allowed_group_ids)[0]
        raise AppException("目标实例未关联到你的资源组，无法创建申请", code=400)

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
          L1: 超管 / query_all_instances
          L2: 资源组范围
          L3: 数据级授权（database/table）
        """
        if user.get("is_superuser") or "query_all_instances" in user.get("permissions", []):
            return True, "admin"

        if not QueryPrivService.user_has_instance_access(user, instance):
            return False, "实例不在你的资源组内"

        table_refs = extract_table_refs(sql, db_name, instance.db_type)
        if not table_refs:
            has_db_priv = await QueryPrivService._has_db_priv(db, user["id"], instance.id, db_name)
            if has_db_priv:
                return True, "db_privilege"
            return False, f"没有数据库 {db_name} 的查询权限，请申请后重试"

        for ref in table_refs:
            schema = ref.get("schema", db_name) or db_name
            table = ref.get("name", "")
            if not table:
                continue

            if await QueryPrivService._has_table_priv(db, user["id"], instance.id, schema, table):
                continue
            if await QueryPrivService._has_db_priv(db, user["id"], instance.id, schema):
                continue
            return False, f"没有表 {schema}.{table} 的查询权限，请申请后重试"

        return True, "privilege"

    @staticmethod
    async def explain_query_access(
        db: AsyncSession,
        user: dict,
        instance: Instance,
        db_name: str,
        sql: str,
    ) -> dict:
        allowed, reason = await QueryPrivService.check_query_priv(db, user, instance, db_name, sql)
        layer = (
            "identity"
            if reason == "admin"
            else "resource_scope"
            if reason == "实例不在你的资源组内"
            else "data_scope"
        )
        return {"allowed": allowed, "reason": reason, "layer": layer}

    @staticmethod
    async def list_my_privileges(
        db: AsyncSession, user_id: int, instance_id: int | None = None
    ) -> list[QueryPrivilege]:
        query = select(QueryPrivilege).where(
            and_(
                QueryPrivilege.user_id == user_id,
                QueryPrivilege.user_group_id.is_(None),
                QueryPrivilege.is_deleted == 0,
                QueryPrivilege.valid_date >= date.today(),
            )
        )
        if instance_id:
            query = query.where(QueryPrivilege.instance_id == instance_id)
        query = query.order_by(QueryPrivilege.instance_id, QueryPrivilege.db_name, QueryPrivilege.table_name)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def apply_privilege(
        db: AsyncSession,
        user_id: int,
        instance_id: int,
        group_id: int | None,
        db_name: str,
        table_name: str,
        valid_date: date,
        limit_num: int,
        priv_type: int,
        apply_reason: str,
        audit_auth_groups: str,
        title: str,
        scope_type: str = "database",
        user: dict | None = None,
    ) -> QueryPrivilegeApply:
        if user is None:
            raise AppException("缺少申请用户上下文", code=400)
        normalized_scope_type, normalized_priv_type = QueryPrivService._normalize_scope_type(
            scope_type, table_name
        )
        resolved_group_id = await QueryPrivService._resolve_apply_group_id(
            db, user=user, instance_id=instance_id, group_id=group_id
        )

        apply = QueryPrivilegeApply(
            title=title,
            user_id=user_id,
            instance_id=instance_id,
            user_group_id=None,
            resource_group_id=resolved_group_id,
            group_id=resolved_group_id,
            scope_type=normalized_scope_type,
            db_name=db_name,
            table_name=table_name or "",
            valid_date=valid_date,
            limit_num=limit_num,
            priv_type=normalized_priv_type if priv_type not in (1, 2) else normalized_priv_type,
            apply_reason=apply_reason,
            status=0,
            audit_auth_groups=audit_auth_groups,
        )
        db.add(apply)
        await db.commit()
        await db.refresh(apply)
        logger.info(
            "query_priv_apply created: user=%s instance=%s scope=%s",
            user_id,
            instance_id,
            normalized_scope_type,
        )
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
        action: str,
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
            normalized_scope_type, normalized_priv_type = QueryPrivService._normalize_scope_type(
                apply.scope_type, apply.table_name
            )
            priv = QueryPrivilege(
                user_id=apply.user_id,
                user_group_id=None,
                instance_id=apply.instance_id,
                resource_group_id=None,
                scope_type=normalized_scope_type,
                db_name=apply.db_name,
                table_name=apply.table_name,
                valid_date=apply.valid_date,
                limit_num=apply.limit_num,
                priv_type=normalized_priv_type,
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
            sqllog=sql[:10000],
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
