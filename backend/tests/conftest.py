"""
pytest 测试配置与公共 fixtures。
"""
import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.main import app
from app.models.base import Base

# 测试数据库（使用独立的 test DB，避免污染开发数据）
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/archery", "/archery_test")


@pytest.fixture(scope="session")
def event_loop():
    """使用 session 级别的事件循环，避免每个测试重新创建。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


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
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTPX 异步测试客户端。"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


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
