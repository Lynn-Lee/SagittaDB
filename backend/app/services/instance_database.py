"""
实例数据库注册服务（Pack C2）。
管理每个实例下已注册的数据库列表，支持手动维护和从引擎自动同步。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, ConflictException, NotFoundException
from app.engines.registry import get_engine
from app.models.instance import Instance, InstanceDatabase

logger = logging.getLogger(__name__)

# Oracle 用 Schema，Redis 用编号，其他用 Database
DB_NAME_LABEL = {
    "oracle":       "Schema",
    "redis":        "数据库编号",
    "elasticsearch":"索引前缀",
}


class InstanceDatabaseService:

    @staticmethod
    def get_db_label(db_type: str) -> str:
        """根据数据库类型返回数据库名的 label。"""
        return DB_NAME_LABEL.get(db_type, "数据库")

    @staticmethod
    async def list_databases(
        db: AsyncSession,
        instance_id: int,
        include_inactive: bool = False,
    ) -> list[dict]:
        """获取实例下已注册的数据库列表。"""
        stmt = select(InstanceDatabase).where(
            InstanceDatabase.instance_id == instance_id
        )
        if not include_inactive:
            stmt = stmt.where(InstanceDatabase.is_active == True)
        stmt = stmt.order_by(InstanceDatabase.db_name)
        result = await db.execute(stmt)
        rows = result.scalars().all()

        # 获取实例 db_type 用于返回 label
        inst_result = await db.execute(select(Instance).where(Instance.id == instance_id))
        inst = inst_result.scalar_one_or_none()
        label = InstanceDatabaseService.get_db_label(inst.db_type if inst else "")

        return [
            {
                "id": r.id,
                "db_name": r.db_name,
                "remark": r.remark,
                "is_active": r.is_active,
                "sync_at": r.sync_at.isoformat() if r.sync_at else None,
                "db_name_label": label,
            }
            for r in rows
        ]

    @staticmethod
    async def add_database(
        db: AsyncSession,
        instance_id: int,
        db_name: str,
        remark: str = "",
    ) -> InstanceDatabase:
        """手动添加一个数据库。"""
        inst = await db.execute(select(Instance).where(Instance.id == instance_id))
        if not inst.scalar_one_or_none():
            raise NotFoundException(f"实例 ID={instance_id} 不存在")

        # 检查是否已存在
        existing = await db.execute(
            select(InstanceDatabase).where(
                and_(
                    InstanceDatabase.instance_id == instance_id,
                    InstanceDatabase.db_name == db_name,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictException(f"数据库 '{db_name}' 已存在于此实例")

        idb = InstanceDatabase(
            instance_id=instance_id,
            db_name=db_name.strip(),
            remark=remark,
            is_active=True,
        )
        db.add(idb)
        await db.commit()
        await db.refresh(idb)
        logger.info("instance_db_added: instance=%s db=%s", instance_id, db_name)
        return idb

    @staticmethod
    async def update_database(
        db: AsyncSession,
        idb_id: int,
        remark: str | None = None,
        is_active: bool | None = None,
    ) -> InstanceDatabase:
        result = await db.execute(select(InstanceDatabase).where(InstanceDatabase.id == idb_id))
        idb = result.scalar_one_or_none()
        if not idb:
            raise NotFoundException(f"记录 ID={idb_id} 不存在")
        if remark is not None:
            idb.remark = remark
        if is_active is not None:
            idb.is_active = is_active
        await db.commit()
        await db.refresh(idb)
        return idb

    @staticmethod
    async def delete_database(db: AsyncSession, idb_id: int) -> None:
        result = await db.execute(select(InstanceDatabase).where(InstanceDatabase.id == idb_id))
        idb = result.scalar_one_or_none()
        if not idb:
            raise NotFoundException(f"记录 ID={idb_id} 不存在")
        await db.delete(idb)
        await db.commit()

    @staticmethod
    async def sync_from_engine(
        db: AsyncSession,
        instance_id: int,
    ) -> dict:
        """
        连接引擎拉取数据库列表，自动同步到 instance_database 表。
        只新增不存在的，不删除已有的（防止误删除）。
        返回同步结果统计。
        """
        inst_result = await db.execute(
            select(Instance).where(Instance.id == instance_id, Instance.is_active == True)
        )
        inst = inst_result.scalar_one_or_none()
        if not inst:
            raise NotFoundException(f"实例 ID={instance_id} 不存在或已停用")

        engine = get_engine(inst)
        now = datetime.now(timezone.utc)

        # 根据数据库类型调用不同的查询方式
        try:
            if inst.db_type == "redis":
                # Redis 固定返回 0-15
                db_list = [str(i) for i in range(16)]
            else:
                rs = await engine.get_all_databases()
                if rs.error:
                    return {
                        "success": False,
                        "message": f"连接失败：{rs.error}",
                        "added": 0, "skipped": 0,
                    }
                db_list = [
                    row[0] if isinstance(row, (tuple, list)) else str(row)
                    for row in rs.rows
                ]
        except Exception as e:
            return {
                "success": False,
                "message": f"查询失败：{str(e)}",
                "added": 0, "skipped": 0,
            }

        # 查已有记录
        existing_result = await db.execute(
            select(InstanceDatabase.db_name).where(
                InstanceDatabase.instance_id == instance_id
            )
        )
        existing_names = {r[0] for r in existing_result}

        added = 0
        skipped = 0
        for db_name in db_list:
            if not db_name or db_name in ("information_schema", "performance_schema",
                                           "mysql", "sys", "pg_catalog", "pg_toast"):
                skipped += 1
                continue
            if db_name in existing_names:
                # 更新同步时间
                await db.execute(
                    select(InstanceDatabase).where(
                        and_(
                            InstanceDatabase.instance_id == instance_id,
                            InstanceDatabase.db_name == db_name,
                        )
                    )
                )
                skipped += 1
            else:
                db.add(InstanceDatabase(
                    instance_id=instance_id,
                    db_name=db_name,
                    remark="",
                    is_active=True,
                    sync_at=now,
                ))
                added += 1

        await db.commit()
        logger.info(
            "instance_db_synced: instance=%s added=%d skipped=%d",
            instance_id, added, skipped
        )
        return {
            "success": True,
            "message": f"同步完成：新增 {added} 个，跳过 {skipped} 个",
            "added": added,
            "skipped": skipped,
            "total": len(db_list),
        }
