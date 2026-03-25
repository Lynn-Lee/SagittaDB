"""可观测中心 + Dashboard 统计服务（Sprint 5）。"""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, ConflictException, NotFoundException
from app.models.instance import Instance
from app.models.monitor import MonitorCollectConfig, MonitorPrivilege, MonitorPrivilegeApply
from app.models.query import QueryLog
from app.models.workflow import SqlWorkflow
from app.schemas.monitor import MonitorConfigCreate, MonitorConfigUpdate

logger = logging.getLogger(__name__)


class MonitorService:

    @staticmethod
    async def list_configs(db: AsyncSession, page: int = 1, page_size: int = 20) -> tuple[int, list[dict]]:
        total_q = await db.execute(select(func.count()).select_from(MonitorCollectConfig))
        total = total_q.scalar_one()
        result = await db.execute(
            select(MonitorCollectConfig, Instance.instance_name)
            .join(Instance, MonitorCollectConfig.instance_id == Instance.id)
            .offset((page - 1) * page_size).limit(page_size)
        )
        items = []
        for cfg, inst_name in result:
            items.append({
                "id": cfg.id, "instance_id": cfg.instance_id, "instance_name": inst_name,
                "is_enabled": cfg.is_enabled, "collect_interval": cfg.collect_interval,
                "exporter_url": cfg.exporter_url, "exporter_type": cfg.exporter_type,
                "alert_rules_override": cfg.alert_rules_override or {}, "created_by": cfg.created_by,
            })
        return total, items

    @staticmethod
    async def create_config(db: AsyncSession, data: MonitorConfigCreate, operator: dict) -> MonitorCollectConfig:
        inst = await db.execute(select(Instance).where(Instance.id == data.instance_id))
        if not inst.scalar_one_or_none():
            raise NotFoundException(f"实例 ID={data.instance_id} 不存在")
        existing = await db.execute(select(MonitorCollectConfig).where(MonitorCollectConfig.instance_id == data.instance_id))
        if existing.scalar_one_or_none():
            raise ConflictException(f"实例 ID={data.instance_id} 已有采集配置")
        cfg = MonitorCollectConfig(
            instance_id=data.instance_id, exporter_url=data.exporter_url,
            exporter_type=data.exporter_type, collect_interval=data.collect_interval,
            alert_rules_override=data.alert_rules_override, created_by=operator.get("username", ""),
        )
        db.add(cfg)
        await db.commit()
        await db.refresh(cfg)
        return cfg

    @staticmethod
    async def update_config(db: AsyncSession, config_id: int, data: MonitorConfigUpdate) -> MonitorCollectConfig:
        result = await db.execute(select(MonitorCollectConfig).where(MonitorCollectConfig.id == config_id))
        cfg = result.scalar_one_or_none()
        if not cfg:
            raise NotFoundException(f"采集配置 ID={config_id} 不存在")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(cfg, field, value)
        await db.commit()
        await db.refresh(cfg)
        return cfg

    @staticmethod
    async def delete_config(db: AsyncSession, config_id: int) -> None:
        result = await db.execute(select(MonitorCollectConfig).where(MonitorCollectConfig.id == config_id))
        cfg = result.scalar_one_or_none()
        if not cfg:
            raise NotFoundException(f"采集配置 ID={config_id} 不存在")
        await db.delete(cfg)
        await db.commit()

    @staticmethod
    async def get_sd_targets(db: AsyncSession) -> list[dict]:
        """Prometheus HTTP SD 格式 targets。"""
        result = await db.execute(
            select(MonitorCollectConfig, Instance)
            .join(Instance, MonitorCollectConfig.instance_id == Instance.id)
            .where(MonitorCollectConfig.is_enabled)
        )
        targets = []
        for cfg, inst in result:
            url = cfg.exporter_url
            host_part = url.split("//")[-1].split("/")[0]
            path_part = "/" + "/".join(url.split("//")[-1].split("/")[1:]) if "/" in url.split("//")[-1] else "/metrics"
            targets.append({
                "targets": [host_part],
                "labels": {
                    "__metrics_path__": path_part,
                    "__scrape_interval__": f"{cfg.collect_interval}s",
                    "job": cfg.exporter_type,
                    "instance_id": str(inst.id),
                    "instance_name": inst.instance_name,
                    "db_type": inst.db_type,
                },
            })
        return targets

    @staticmethod
    async def apply_privilege(db: AsyncSession, data, user: dict) -> MonitorPrivilegeApply:
        apply = MonitorPrivilegeApply(
            title=data.title, user_id=user["id"], instance_id=data.instance_id,
            group_id=data.group_id, valid_date=data.valid_date,
            apply_reason=data.apply_reason,
            audit_auth_groups=data.audit_auth_groups or str(data.group_id), status=0,
        )
        db.add(apply)
        await db.commit()
        await db.refresh(apply)
        return apply

    @staticmethod
    async def audit_privilege(db: AsyncSession, apply_id: int, action: str, operator: dict, remark: str = "") -> MonitorPrivilegeApply:
        result = await db.execute(select(MonitorPrivilegeApply).where(MonitorPrivilegeApply.id == apply_id))
        apply = result.scalar_one_or_none()
        if not apply:
            raise NotFoundException(f"申请 ID={apply_id} 不存在")
        if apply.status != 0:
            raise AppException("该申请已审批", code=400)
        if action == "pass":
            apply.status = 1
            db.add(MonitorPrivilege(apply_id=apply.id, user_id=apply.user_id, instance_id=apply.instance_id, valid_date=apply.valid_date, is_deleted=0))
        else:
            apply.status = 2
        await db.commit()
        await db.refresh(apply)
        return apply

    @staticmethod
    async def check_privilege(db: AsyncSession, user: dict, instance_id: int) -> bool:
        if user.get("is_superuser") or "monitor_all_instances" in user.get("permissions", []):
            return True
        result = await db.execute(
            select(MonitorPrivilege).where(and_(
                MonitorPrivilege.user_id == user["id"],
                MonitorPrivilege.instance_id == instance_id,
                MonitorPrivilege.valid_date >= date.today(),
                MonitorPrivilege.is_deleted == 0,
            ))
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def list_applies(db: AsyncSession, user: dict, status: int | None = None, page: int = 1, page_size: int = 20) -> tuple[int, list]:
        query = select(MonitorPrivilegeApply)
        if not user.get("is_superuser") and "monitor_review" not in user.get("permissions", []):
            query = query.where(MonitorPrivilegeApply.user_id == user["id"])
        if status is not None:
            query = query.where(MonitorPrivilegeApply.status == status)
        total_q = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_q.scalar_one()
        result = await db.execute(query.order_by(MonitorPrivilegeApply.created_at.desc()).offset((page-1)*page_size).limit(page_size))
        return total, list(result.scalars().all())


class DashboardService:

    @staticmethod
    async def get_stats(db: AsyncSession, days: int = 30) -> dict:
        """
        Dashboard 统计。
        days: 统计周期（天），默认 30 天，前端可自定义传入。
        返回：指定周期内各状态工单数量 + 全局统计。
        """
        now = datetime.now(UTC)
        period_start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        async def count(stmt):
            return (await db.execute(stmt)).scalar_one()

        # 指定周期内各状态工单数量
        async def wf_count_by_status(status: int) -> int:
            return await count(
                select(func.count()).select_from(SqlWorkflow).where(
                    and_(SqlWorkflow.created_at >= period_start, SqlWorkflow.status == status)
                )
            )

        # 周期内总提交数
        wf_total = await count(
            select(func.count()).select_from(SqlWorkflow)
            .where(SqlWorkflow.created_at >= period_start)
        )

        return {
            "period_days": days,
            "workflow_total": wf_total,
            # 各状态明细
            "workflow_by_status": {
                "pending_review":   await wf_count_by_status(0),   # 待审核
                "review_rejected":  await wf_count_by_status(1),   # 审批驳回
                "review_pass":      await wf_count_by_status(2),   # 审核通过
                "timing":           await wf_count_by_status(3),   # 定时执行
                "queuing":          await wf_count_by_status(4),   # 队列中
                "executing":        await wf_count_by_status(5),   # 执行中
                "finish":           await wf_count_by_status(6),   # 执行成功
                "exception":        await wf_count_by_status(7),   # 执行异常
                "canceled":         await wf_count_by_status(8),   # 已取消
            },
            # 全局统计（不受周期限制）
            "instance_total": await count(
                select(func.count()).select_from(Instance).where(Instance.is_active)
            ),
            "query_today_total": await count(
                select(func.count()).select_from(QueryLog).where(QueryLog.created_at >= today_start)
            ),
            "monitor_instance_total": await count(
                select(func.count()).select_from(MonitorCollectConfig)
                .where(MonitorCollectConfig.is_enabled)
            ),
        }

    @staticmethod
    async def get_workflow_trend(db: AsyncSession, days: int = 7) -> list[dict]:
        """
        工单趋势。days 由前端传入，支持用户自定义周期。
        返回每天各状态工单数量。
        """
        result = []
        now = datetime.now(UTC)
        for i in range(days - 1, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            async def day_count_status(status_val: int, ds=day_start, de=day_end) -> int:
                stmt = select(func.count()).select_from(SqlWorkflow).where(
                    and_(SqlWorkflow.created_at >= ds, SqlWorkflow.created_at < de,
                         SqlWorkflow.status == status_val)
                )
                return (await db.execute(stmt)).scalar_one()

            async def day_count_all(ds=day_start, de=day_end) -> int:
                stmt = select(func.count()).select_from(SqlWorkflow).where(
                    and_(SqlWorkflow.created_at >= ds, SqlWorkflow.created_at < de)
                )
                return (await db.execute(stmt)).scalar_one()

            result.append({
                "date": day_start.strftime("%m-%d"),
                "submit":   await day_count_all(),
                "finish":   await day_count_status(6),
                "reject":   await day_count_status(1),
                "canceled": await day_count_status(8),
                "exception":await day_count_status(7),
            })
        return result

    @staticmethod
    async def get_instance_dist(db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(Instance.db_type, func.count().label("count"))
            .where(Instance.is_active)
            .group_by(Instance.db_type)
            .order_by(func.count().desc())
        )
        return [{"db_type": row.db_type, "count": row.count} for row in result]
