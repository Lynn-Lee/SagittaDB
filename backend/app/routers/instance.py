"""实例管理路由。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import current_user, require_perm
from app.schemas.instance import (
    InstanceCreate,
    InstanceUpdate,
    TunnelCreate,
)
from app.services.instance import InstanceService, TunnelService
from app.services.instance_database import InstanceDatabaseService

router = APIRouter()


# ─── 实例 CRUD ────────────────────────────────────────────────

@router.get("/", summary="实例列表")
async def list_instances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db_type: str | None = None,
    search: str | None = None,
    resource_group_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    total, items = await InstanceService.list_instances(
        db, page=page, page_size=page_size,
        db_type=db_type, search=search,
        resource_group_id=resource_group_id,
    )
    return {
        "total": total, "page": page, "page_size": page_size,
        "items": [InstanceService.to_response(i) for i in items],
    }


@router.post("/", summary="新建实例", dependencies=[Depends(require_perm("instance_manage"))])
async def create_instance(
    data: InstanceCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    inst = await InstanceService.create(db, data)
    return {"status": 0, "msg": "实例创建成功", "data": InstanceService.to_response(inst)}


@router.get("/{instance_id}/", summary="实例详情")
async def get_instance(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    inst = await InstanceService.get_by_id(db, instance_id)
    return InstanceService.to_response(inst)


@router.put("/{instance_id}/", summary="修改实例", dependencies=[Depends(require_perm("instance_manage"))])
async def update_instance(
    instance_id: int,
    data: InstanceUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    inst = await InstanceService.update(db, instance_id, data)
    return {"status": 0, "msg": "实例已更新", "data": InstanceService.to_response(inst)}


@router.delete("/{instance_id}/", summary="删除（停用）实例", dependencies=[Depends(require_perm("instance_manage"))])
async def delete_instance(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    await InstanceService.delete(db, instance_id)
    return {"status": 0, "msg": "实例已停用"}


@router.post("/{instance_id}/test/", summary="测试连接")
async def test_connection(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    result = await InstanceService.test_connection(db, instance_id)
    return result


@router.get("/{instance_id}/databases/", summary="获取数据库列表")
async def get_databases(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    databases = await InstanceService.get_databases(db, instance_id)
    return {"databases": databases}


@router.get("/{instance_id}/tables/", summary="获取表列表")
async def get_tables(
    instance_id: int,
    db_name: str = Query(..., description="数据库名"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    tables = await InstanceService.get_tables(db, instance_id, db_name)
    return {"tables": tables}


@router.get("/{instance_id}/columns/", summary="获取列信息")
async def get_columns(
    instance_id: int,
    db_name: str = Query(...),
    tb_name: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    columns = await InstanceService.get_columns(db, instance_id, db_name, tb_name)
    return {"columns": columns}


@router.get("/{instance_id}/params/", summary="实例参数列表")
async def get_params(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    params = await InstanceService.get_variables(db, instance_id)
    return {"params": params}


# ─── SSH 隧道 ─────────────────────────────────────────────────

# ── 实例数据库管理（Pack C2）────────────────────────────────

@router.get("/{instance_id}/db-list/", summary="已注册数据库列表")
async def list_registered_databases(
    instance_id: int,
    include_inactive: bool = False,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await InstanceDatabaseService.list_databases(db, instance_id, include_inactive)
    return {"items": items, "total": len(items)}


@router.post("/{instance_id}/db-list/", summary="手动添加数据库",
             dependencies=[Depends(require_perm("instance_manage"))])
async def add_database(
    instance_id: int,
    data: dict,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    db_name = data.get("db_name", "").strip()
    remark = data.get("remark", "")
    if not db_name:
        from fastapi import HTTPException
        raise HTTPException(400, "db_name 不能为空")
    idb = await InstanceDatabaseService.add_database(db, instance_id, db_name, remark)
    return {"status": 0, "msg": f"数据库 '{db_name}' 添加成功", "data": {"id": idb.id}}


@router.put("/{instance_id}/db-list/{idb_id}/", summary="更新数据库备注/状态",
            dependencies=[Depends(require_perm("instance_manage"))])
async def update_database(
    instance_id: int,
    idb_id: int,
    data: dict,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    idb = await InstanceDatabaseService.update_database(
        db, idb_id,
        remark=data.get("remark"),
        is_active=data.get("is_active"),
    )
    return {"status": 0, "msg": "已更新", "data": {"id": idb.id}}


@router.delete("/{instance_id}/db-list/{idb_id}/", summary="删除数据库注册",
               dependencies=[Depends(require_perm("instance_manage"))])
async def delete_database(
    instance_id: int,
    idb_id: int,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await InstanceDatabaseService.delete_database(db, idb_id)
    return {"status": 0, "msg": "已删除"}


@router.post("/{instance_id}/db-list/sync/", summary="从引擎自动同步数据库列表")
async def sync_databases(
    instance_id: int,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await InstanceDatabaseService.sync_from_engine(db, instance_id)
    return result


@router.get("/tunnels/", summary="SSH 隧道列表")
async def list_tunnels(
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    tunnels = await TunnelService.list_tunnels(db)
    return {"tunnels": [{"id": t.id, "tunnel_name": t.tunnel_name, "host": t.host, "port": t.port, "user": t.user} for t in tunnels]}


@router.post("/tunnels/", summary="新建 SSH 隧道", dependencies=[Depends(require_perm("instance_manage"))])
async def create_tunnel(
    data: TunnelCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    tunnel = await TunnelService.create(db, data)
    return {"status": 0, "msg": "SSH 隧道已创建", "data": {"id": tunnel.id, "tunnel_name": tunnel.tunnel_name}}


@router.delete("/tunnels/{tunnel_id}/", summary="删除 SSH 隧道", dependencies=[Depends(require_perm("instance_manage"))])
async def delete_tunnel(
    tunnel_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(current_user),
):
    await TunnelService.delete(db, tunnel_id)
    return {"status": 0, "msg": "SSH 隧道已删除"}
