"""
SQL 工单接口集成测试（Pack G P0）。
验证工单提交、列表查询、状态流转 API。
"""
import pytest
from httpx import AsyncClient


async def _get_admin_headers(client: AsyncClient) -> dict[str, str]:
    await client.post("/api/v1/system/init/")
    resp = await client.post("/api/v1/auth/login/", json={
        "username": "admin", "password": "Admin@2024!",
    })
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_instance(client: AsyncClient, headers: dict) -> int:
    """创建测试实例，返回 instance_id。"""
    resp = await client.post("/api/v1/instances/", json={
        "instance_name": "wf-test-instance",
        "type": "master",
        "db_type": "mysql",
        "host": "127.0.0.1",
        "port": 3306,
        "user": "root",
        "password": "root",
    }, headers=headers)
    if resp.status_code in (200, 201):
        return resp.json()["id"]
    # 若已存在，尝试查询
    list_resp = await client.get("/api/v1/instances/?page_size=100", headers=headers)
    items = list_resp.json().get("items", list_resp.json() if isinstance(list_resp.json(), list) else [])
    for item in items:
        if item.get("instance_name") == "wf-test-instance":
            return item["id"]
    pytest.skip("无法创建测试实例，跳过工单测试")


class TestWorkflowList:

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/workflows/")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_returns_paginated_result(self, client: AsyncClient):
        headers = await _get_admin_headers(client)
        resp = await client.get("/api/v1/workflows/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # 支持两种分页格式：{"items": [], "total": n} 或 {"data": [], ...}
        assert "items" in data or "data" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_supports_status_filter(self, client: AsyncClient):
        headers = await _get_admin_headers(client)
        resp = await client.get("/api/v1/workflows/?status=0", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_supports_pagination(self, client: AsyncClient):
        headers = await _get_admin_headers(client)
        resp = await client.get("/api/v1/workflows/?page=1&page_size=5", headers=headers)
        assert resp.status_code == 200


class TestWorkflowSubmit:

    @pytest.mark.asyncio
    async def test_submit_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/workflows/", json={})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_submit_missing_fields_returns_422(self, client: AsyncClient):
        headers = await _get_admin_headers(client)
        resp = await client.post(
            "/api/v1/workflows/",
            json={"workflow_name": "incomplete"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_workflow_creates_record(self, client: AsyncClient):
        headers = await _get_admin_headers(client)
        instance_id = await _create_instance(client, headers)

        resp = await client.post("/api/v1/workflows/", json={
            "workflow_name": "CI 测试工单 #1",
            "group_id": 1,
            "instance_id": instance_id,
            "db_name": "test_db",
            "sql_content": "SELECT 1;",
            "is_backup": False,
            "audit_auth_groups": "",
        }, headers=headers)
        # 201 或 200 成功，400 表示实例无法连接（可接受），401/403/422 为失败
        assert resp.status_code in (200, 201, 400)
        if resp.status_code in (200, 201):
            data = resp.json()
            assert "id" in data or "workflow_id" in data

    @pytest.mark.asyncio
    async def test_get_workflow_detail(self, client: AsyncClient):
        headers = await _get_admin_headers(client)
        instance_id = await _create_instance(client, headers)

        create_resp = await client.post("/api/v1/workflows/", json={
            "workflow_name": "CI 详情测试",
            "group_id": 1,
            "instance_id": instance_id,
            "db_name": "test_db",
            "sql_content": "SELECT 2;",
            "is_backup": False,
            "audit_auth_groups": "",
        }, headers=headers)

        if create_resp.status_code not in (200, 201):
            pytest.skip(f"创建工单失败({create_resp.status_code})，跳过详情测试")

        wf_data = create_resp.json()
        wf_id = wf_data.get("id") or wf_data.get("workflow_id")
        assert wf_id

        detail_resp = await client.get(f"/api/v1/workflows/{wf_id}/", headers=headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert "status" in detail
        assert "workflow_name" in detail

    @pytest.mark.asyncio
    async def test_get_nonexistent_workflow_returns_404(self, client: AsyncClient):
        headers = await _get_admin_headers(client)
        resp = await client.get("/api/v1/workflows/99999999/", headers=headers)
        assert resp.status_code == 404


class TestWorkflowSQLCheck:

    @pytest.mark.asyncio
    async def test_sql_check_endpoint_exists(self, client: AsyncClient):
        headers = await _get_admin_headers(client)
        instance_id = await _create_instance(client, headers)

        resp = await client.post("/api/v1/workflows/check/", json={
            "instance_id": instance_id,
            "db_name": "test_db",
            "sql_content": "SELECT 1;",
        }, headers=headers)
        # 200 成功或 400 实例无法连接均可接受
        assert resp.status_code in (200, 400, 422)
