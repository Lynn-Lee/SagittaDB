"""
pytest 测试配置与公共 fixtures。
"""
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base

# 测试数据库（使用独立的 test DB，避免污染开发数据）
# 只替换 URL 最后一段（数据库名），避免误替换用户名部分
_db_url_base, _, _ = settings.DATABASE_URL.rpartition("/")
TEST_DATABASE_URL = f"{_db_url_base}/archery_test"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """每个测试使用独立事务，测试后自动回滚。"""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session, session.begin():
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTPX 异步测试客户端，覆盖 get_db 依赖指向测试数据库。
    每个请求使用独立 session（自动回滚）。
    """
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def mock_user():
    """模拟已登录用户。"""
    return {
        "id": 1,
        "username": "testuser",
        "display_name": "Test User",
        "is_superuser": False,
        "permissions": ["sql.sql_submit", "sql.query_submit"],
        "tenant_id": 1,
    }


@pytest.fixture
def mock_superuser():
    """模拟超级管理员。"""
    return {
        "id": 1,
        "username": "admin",
        "display_name": "Admin",
        "is_superuser": True,
        "permissions": [],
        "tenant_id": 1,
    }


# ── 集成测试辅助工具 ─────────────────────────────────────────

@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """
    在测试 DB 中创建 admin 用户并返回 Authorization 头，供集成测试使用。
    """
    # 先尝试登录，若失败则通过 API /system/init 初始化
    resp = await client.post("/api/v1/auth/login/", json={
        "username": "admin", "password": "Admin@2024!",
    })
    if resp.status_code == 200:
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    # 用户不存在 → 直接调系统初始化接口
    await client.post("/api/v1/system/init/")
    resp = await client.post("/api/v1/auth/login/", json={
        "username": "admin", "password": "Admin@2024!",
    })
    assert resp.status_code == 200, f"初始化后仍无法登录: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
