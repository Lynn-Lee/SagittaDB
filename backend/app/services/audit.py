"""
审批流核心服务（Sprint 3）。
从 Archery 1.x AuditV2 移植，重构为 async SQLAlchemy。

工单类型支持：SQL(2) / Query(1) / Archive(3) / Monitor(4)
审批链格式：逗号分隔的资源组ID，如 "1,2,3"
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundException
from app.models.workflow import (
    AuditStatus,
    SqlWorkflow,
    WorkflowAudit,
    WorkflowLog,
    WorkflowStatus,
    WorkflowType,
)

logger = logging.getLogger(__name__)

# 操作类型常量
OP_SUBMIT  = "submit"    # 提交
OP_PASS    = "pass"      # 审批通过
OP_REJECT  = "reject"    # 驳回
OP_CANCEL  = "cancel"    # 取消
OP_EXECUTE = "execute"   # 执行
OP_TIMING  = "timing"    # 定时执行
OP_ABORT   = "abort"     # 中止


class AuditService:
    """
    审批流服务。
    移植自 Archery 1.x workflow_audit.py AuditV2，
    支持多级审批链、自动审批判断、操作日志记录。
    """

    def __init__(
        self,
        workflow: SqlWorkflow,
        workflow_type: WorkflowType = WorkflowType.SQL,
    ):
        self.workflow = workflow
        self.workflow_type = workflow_type

    # ── 创建审批记录 ──────────────────────────────────────────

    async def create_audit(self, db: AsyncSession, operator: dict) -> WorkflowAudit:
        """
        工单提交时创建审批记录。
        审批链从工单的 audit_auth_groups 读取（格式："1,2,3"）。
        """
        auth_groups = self.workflow.audit_auth_groups or ""
        groups = [g.strip() for g in auth_groups.split(",") if g.strip()]

        # 构建审批链详情
        groups_info = [
            {"order": i + 1, "group_id": g, "status": AuditStatus.PENDING}
            for i, g in enumerate(groups)
        ]

        audit = WorkflowAudit(
            workflow_id=self.workflow.id,
            workflow_type=int(self.workflow_type),
            workflow_title=self.workflow.workflow_name,
            current_audit_auth_group=groups[0] if groups else "",
            current_status=AuditStatus.PENDING,
            audit_auth_groups=auth_groups,
            audit_auth_groups_info=json.dumps(groups_info, ensure_ascii=False),
            create_user=operator.get("username", ""),
            create_user_id=operator.get("id", 0),
        )
        db.add(audit)
        await db.flush()

        # 记录提交日志
        await self._write_log(
            db, audit.id, operator, OP_SUBMIT,
            remark=f"提交工单：{self.workflow.workflow_name}"
        )
        await db.commit()

        logger.info("audit_created: workflow=%s", self.workflow.id)
        return audit

    # ── 审批操作 ──────────────────────────────────────────────

    @staticmethod
    async def operate(
        db: AsyncSession,
        workflow_id: int,
        action: str,
        operator: dict,
        remark: str = "",
    ) -> dict:
        """
        审批操作：pass / reject / cancel。
        返回操作结果和工单新状态。
        """
        # 加载工单
        wf_result = await db.execute(
            select(SqlWorkflow).where(SqlWorkflow.id == workflow_id)
        )
        workflow = wf_result.scalar_one_or_none()
        if not workflow:
            raise NotFoundException(f"工单 ID={workflow_id} 不存在")

        # 加载审批记录
        audit_result = await db.execute(
            select(WorkflowAudit).where(WorkflowAudit.workflow_id == workflow_id)
        )
        audit = audit_result.scalar_one_or_none()
        if not audit:
            raise AppException("审批记录不存在", code=400)

        operator.get("id")
        operator.get("username", "")

        if action == OP_PASS:
            return await AuditService._do_pass(db, workflow, audit, operator, remark)
        elif action == OP_REJECT:
            return await AuditService._do_reject(db, workflow, audit, operator, remark)
        elif action == OP_CANCEL:
            return await AuditService._do_cancel(db, workflow, audit, operator, remark)
        else:
            raise AppException(f"不支持的操作：{action}", code=400)

    @staticmethod
    async def _do_pass(
        db: AsyncSession,
        workflow: SqlWorkflow,
        audit: WorkflowAudit,
        operator: dict,
        remark: str,
    ) -> dict:
        if workflow.status not in (
            WorkflowStatus.PENDING_REVIEW, WorkflowStatus.REVIEW_PASS
        ):
            raise AppException("当前状态不允许审批通过", code=400)

        # 解析审批链，判断是否还有下一级
        groups_info = json.loads(audit.audit_auth_groups_info or "[]")
        current_order = next(
            (g["order"] for g in groups_info if g["status"] == AuditStatus.PENDING),
            None,
        )

        if current_order is None:
            raise AppException("审批链已完成，无法重复审批", code=400)

        # 更新当前节点状态
        for g in groups_info:
            if g["order"] == current_order:
                g["status"] = AuditStatus.PASSED
                g["operator"] = operator.get("username")
                g["operated_at"] = datetime.now(UTC).isoformat()
                break

        # 判断是否还有下一节点
        next_pending = next(
            (g for g in groups_info if g["status"] == AuditStatus.PENDING),
            None,
        )

        audit.audit_auth_groups_info = json.dumps(groups_info, ensure_ascii=False)

        if next_pending:
            # 还有下一级审批
            audit.current_audit_auth_group = str(next_pending["group_id"])
            audit.current_status = AuditStatus.PENDING
            workflow.status = WorkflowStatus.PENDING_REVIEW
            msg = f"第 {current_order} 级审批通过，等待下一级审批"
        else:
            # 全部审批通过
            audit.current_status = AuditStatus.PASSED
            workflow.status = WorkflowStatus.REVIEW_PASS
            msg = "审批全部通过，工单已就绪"

        await AuditService._write_log(db, audit.id, operator, OP_PASS, remark=remark or msg)
        await db.commit()
        return {"msg": msg, "status": workflow.status}

    @staticmethod
    async def _do_reject(
        db: AsyncSession,
        workflow: SqlWorkflow,
        audit: WorkflowAudit,
        operator: dict,
        remark: str,
    ) -> dict:
        if workflow.status not in (
            WorkflowStatus.PENDING_REVIEW, WorkflowStatus.REVIEW_PASS
        ):
            raise AppException("当前状态不允许驳回", code=400)

        audit.current_status = AuditStatus.REJECTED
        # 状态值 1 = 审批驳回（人工），描述为"审批驳回"
        # 注意：区别于系统自动拒绝（未来可用状态值 9）
        workflow.status = WorkflowStatus.AUTO_REVIEW_FAIL

        await AuditService._write_log(
            db, audit.id, operator, OP_REJECT,
            remark=remark or "审批人驳回"
        )
        await db.commit()
        return {"msg": "工单已驳回", "status": workflow.status}

    @staticmethod
    async def _do_cancel(
        db: AsyncSession,
        workflow: SqlWorkflow,
        audit: WorkflowAudit,
        operator: dict,
        remark: str,
    ) -> dict:
        cancelable = (
            WorkflowStatus.PENDING_REVIEW,
            WorkflowStatus.AUTO_REVIEW_FAIL,
            WorkflowStatus.REVIEW_PASS,
            WorkflowStatus.TIMING_TASK,
        )
        if workflow.status not in cancelable:
            raise AppException("当前状态不允许取消", code=400)

        audit.current_status = AuditStatus.CANCELED
        # 状态值 8 = 已取消（人工操作），描述为"已取消"
        workflow.status = WorkflowStatus.ABORT

        await AuditService._write_log(
            db, audit.id, operator, OP_CANCEL,
            remark=remark or "提交人/审批人取消工单"
        )
        await db.commit()
        return {"msg": "工单已取消", "status": workflow.status}

    # ── 获取审批日志 ──────────────────────────────────────────

    @staticmethod
    async def get_audit_logs(db: AsyncSession, workflow_id: int) -> list[dict]:
        result = await db.execute(
            select(WorkflowAudit).where(WorkflowAudit.workflow_id == workflow_id)
        )
        audit = result.scalar_one_or_none()
        if not audit:
            return []

        logs_result = await db.execute(
            select(WorkflowLog)
            .where(WorkflowLog.audit_id == audit.id)
            .order_by(WorkflowLog.created_at)
        )
        logs = logs_result.scalars().all()
        return [
            {
                "operator": log.operator,
                "operation_type": log.operation_type,
                "remark": log.remark,
                "created_at": log.created_at.isoformat() if log.created_at else "",
            }
            for log in logs
        ]

    @staticmethod
    async def get_audit_info(db: AsyncSession, workflow_id: int) -> dict | None:
        result = await db.execute(
            select(WorkflowAudit).where(WorkflowAudit.workflow_id == workflow_id)
        )
        audit = result.scalar_one_or_none()
        if not audit:
            return None
        return {
            "current_audit_auth_group": audit.current_audit_auth_group,
            "current_status": audit.current_status,
            "audit_auth_groups_info": json.loads(audit.audit_auth_groups_info or "[]"),
        }

    # ── 内部工具 ──────────────────────────────────────────────

    @staticmethod
    async def _write_log(
        db: AsyncSession,
        audit_id: int,
        operator: dict,
        operation_type: str,
        remark: str = "",
    ) -> None:
        log = WorkflowLog(
            audit_id=audit_id,
            operator=operator.get("username", "system"),
            operator_id=operator.get("id", 0),
            operation_type=operation_type,
            remark=remark,
        )
        db.add(log)
