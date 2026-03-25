"""
数据归档路由（Pack E 重写）。
支持所有平台接入的数据库类型，不支持的返回明确提示。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import current_user, require_perm
from app.services.archive import ARCHIVE_SUPPORT, ArchiveService

logger = logging.getLogger(__name__)
router = APIRouter()


class ArchiveRequest(BaseModel):
    source_instance_id: int
    source_db: str
    source_table: str
    condition: str = Field(..., description="WHERE 条件（MongoDB 需为 JSON 格式）")
    archive_mode: str = Field(default="purge", description="purge=直接删除 dest=归档到目标")
    dest_instance_id: int | None = None
    dest_db: str | None = None
    dest_table: str | None = None
    batch_size: int = Field(default=1000, ge=1, le=10000)
    sleep_ms: int = Field(default=100, ge=0, le=10000)
    dry_run: bool = Field(default=True, description="True=只估算不执行，默认开启防止误操作")
    apply_reason: str = ""


@router.get("/support/", summary="查询数据库归档支持情况")
async def get_archive_support(_user=Depends(current_user)):
    """返回所有数据库类型的归档支持情况，前端用于展示提示信息。"""
    result = {}
    for db_type, cfg in ARCHIVE_SUPPORT.items():
        result[db_type] = {
            "purge": cfg.get("purge", False),
            "dest": cfg.get("dest", False),
            "reason": cfg.get("reason", ""),
        }
    return {"support": result}


@router.post("/estimate/", summary="估算归档影响行数（不执行）")
async def estimate_archive(
    data: ArchiveRequest,
    user=Depends(require_perm("archive_apply")),
    db: AsyncSession = Depends(get_db),
):
    return await ArchiveService.estimate_rows(
        db, data.source_instance_id, data.source_db,
        data.source_table, data.condition,
    )


@router.post("/run/", summary="执行数据归档")
async def run_archive(
    data: ArchiveRequest,
    user=Depends(require_perm("archive_apply")),
    db: AsyncSession = Depends(get_db),
):
    """
    执行数据归档。

    **重要：默认 dry_run=True，只估算不执行。**
    确认行数后将 dry_run 改为 false 再提交。

    归档模式说明：
    - purge：直接分批删除源数据（支持大多数数据库）
    - dest：先插入到目标实例，再删除源数据（跨实例归档）
    """
    if data.archive_mode == "dest" and not data.dest_instance_id:
        raise HTTPException(400, "归档模式为 dest 时必须填写目标实例 dest_instance_id")

    if data.archive_mode not in ("purge", "dest"):
        raise HTTPException(400, f"不支持的归档模式：{data.archive_mode}")

    if data.archive_mode == "purge":
        return await ArchiveService.run_purge(
            db=db,
            instance_id=data.source_instance_id,
            db_name=data.source_db,
            table_name=data.source_table,
            condition=data.condition,
            batch_size=data.batch_size,
            sleep_ms=data.sleep_ms,
            dry_run=data.dry_run,
        )
    else:  # dest
        return await ArchiveService.run_to_dest(
            db=db,
            src_instance_id=data.source_instance_id,
            src_db=data.source_db,
            src_table=data.source_table,
            condition=data.condition,
            dest_instance_id=data.dest_instance_id,
            dest_db=data.dest_db or data.source_db,
            dest_table=data.dest_table or data.source_table,
            batch_size=data.batch_size,
            sleep_ms=data.sleep_ms,
            dry_run=data.dry_run,
        )
