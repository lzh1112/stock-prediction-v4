from __future__ import annotations

from collections.abc import AsyncGenerator

from app.core.config import settings

# SQLAlchemy async session — 将在阶段 1A 数据库模型就绪后激活
# from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
#
# engine = create_async_engine(settings.DATABASE_URL, echo=settings.APP_DEBUG)
# async_session = async_sessionmaker(engine, expire_on_commit=False)
#
#
# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     async with async_session() as session:
#         try:
#             yield session
#             await session.commit()
#         except Exception:
#             await session.rollback()
#             raise
