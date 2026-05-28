from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
async def _setup_test_db():
    """每个测试使用独立的临时 SQLite 数据库"""
    tmp = tempfile.mkdtemp()
    db_path = Path(tmp) / "test.db"

    from app.api import deps
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.models import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)

    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    deps.engine = engine
    deps.async_session = async_sessionmaker(engine, expire_on_commit=False)

    yield

    await engine.dispose()
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
