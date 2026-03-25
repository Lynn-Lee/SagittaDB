"""
SQL 回滚辅助路由（Pack E 重写）。
原 binlog.py 重新定位为"回滚辅助"，支持所有数据库类型。
MySQL 提供 my2sql 命令生成器，PgSQL 提供 WAL 查询，所有数据库提供逆向 SQL 生成。
"""
import logging

from fastapi import APIRouter, Depends
from fastapi import Query as QParam
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import current_user
from app.models.instance import Instance
from app.services.rollback import RollbackService

logger = logging.getLogger(__name__)
router = APIRouter()


class ReverseRequest(BaseModel):
    workflow_id: int | None = None
    sql: str
    db_type: str
    table_name: str = ""
    primary_keys: list[str] | None = None


class My2SqlRequest(BaseModel):
    instance_id: int
    start_time: str
    stop_time: str
    databases: str = ""
    tables: str = ""
    sql_types: str = "insert,update,delete"
    output_dir: str = "/tmp/rollback"


@router.get("/guide/", summary="各数据库回滚工具说明")
async def get_rollback_guide(
    db_type: str = QParam(..., description="数据库类型"),
    _user=Depends(current_user),
):
    """返回指定数据库的回滚工具使用说明和推荐方案。"""
    return RollbackService.get_rollback_guide(db_type)


@router.get("/guide/all/", summary="所有数据库回滚方案概览")
async def get_all_rollback_guides(_user=Depends(current_user)):
    """返回所有数据库的回滚方案对照表。"""
    from app.services.rollback import ROLLBACK_GUIDE
    return {
        "guides": {
            db: {
                "strategy": cfg["strategy"],
                "tool": cfg["tool"],
                "desc": cfg["desc"],
            }
            for db, cfg in ROLLBACK_GUIDE.items()
        }
    }


@router.post("/reverse-sql/", summary="基于 sqlglot 生成逆向 SQL（所有数据库）")
async def generate_reverse_sql(
    data: ReverseRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    解析 SQL 并生成逆向操作模板：
    - INSERT → DELETE 模板
    - DELETE → INSERT 模板（需要先查原数据）
    - UPDATE → UPDATE 模板（需要原始字段值）
    - DDL → 提示手动处理

    如果传入 workflow_id，自动从工单中读取 SQL 内容。
    """
    sql = data.sql
    db_type = data.db_type

    # 如果传入 workflow_id，从工单读取 SQL
    if data.workflow_id and not sql.strip():
        from sqlalchemy.orm import selectinload

        from app.models.workflow import SqlWorkflow
        result = await db.execute(
            select(SqlWorkflow)
            .options(selectinload(SqlWorkflow.content))
            .where(SqlWorkflow.id == data.workflow_id)
        )
        wf = result.scalar_one_or_none()
        if wf and wf.content:
            sql = wf.content.sql_content
            # 从工单关联的实例获取 db_type
            inst_result = await db.execute(select(Instance).where(Instance.id == wf.instance_id))
            inst = inst_result.scalar_one_or_none()
            if inst:
                db_type = inst.db_type

    if not sql.strip():
        return {"success": False, "msg": "SQL 内容不能为空"}

    return RollbackService.generate_reverse_sql(
        sql=sql,
        db_type=db_type,
        table_name=data.table_name,
        primary_keys=data.primary_keys,
    )


@router.post("/my2sql/command/", summary="生成 my2sql 回滚命令（MySQL/TiDB）")
async def generate_my2sql_command(
    data: My2SqlRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    根据实例信息和时间范围生成 my2sql 命令。
    用户在 MySQL 服务器上执行此命令获取回滚 SQL。
    """
    # 加载实例获取连接信息
    result = await db.execute(select(Instance).where(Instance.id == data.instance_id))
    inst = result.scalar_one_or_none()
    if not inst:
        from fastapi import HTTPException
        raise HTTPException(404, f"实例 ID={data.instance_id} 不存在")

    if inst.db_type not in ("mysql", "tidb"):
        return {
            "success": False,
            "msg": f"{inst.db_type} 不支持 my2sql，请查看 /rollback/guide/?db_type={inst.db_type} 了解对应回滚方案",
        }

    from app.core.security import decrypt_field
    return RollbackService.generate_my2sql_command(
        host=inst.host,
        port=inst.port,
        user=decrypt_field(inst.user),
        start_time=data.start_time,
        stop_time=data.stop_time,
        databases=data.databases,
        tables=data.tables,
        sql_types=data.sql_types,
        output_dir=data.output_dir,
    )


@router.get("/pg-wal/", summary="PostgreSQL WAL 查询语句生成")
async def get_pg_wal_query(
    slot_name: str = QParam("rollback_slot", description="逻辑复制槽名称"),
    _user=Depends(current_user),
):
    """生成 PostgreSQL 通过 WAL 逻辑复制槽查询变更记录的 SQL 语句。"""
    return RollbackService.get_pg_wal_query(slot_name=slot_name)
