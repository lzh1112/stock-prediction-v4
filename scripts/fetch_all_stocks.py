"""
抓取全部 A 股股价数据 — 独立运行，不受 HTTP 超时限制
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.models import Base
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.services.data_fetcher import ensure_stocks, fetch_and_store_prices

    async with async_session() as session:
        all_stocks = await ensure_stocks(session)
        print(f"全部 A 股: {len(all_stocks)} 只")

        processed = 0
        new_data = 0
        for stock in all_stocks:
            try:
                n = await fetch_and_store_prices(session, stock)
                processed += 1
                if n > 0:
                    new_data += 1
                if processed % 200 == 0:
                    print(f"进度: {processed}/{len(all_stocks)} — {stock.code} (新增 {n} 条)")
            except Exception as e:
                print(f"跳过 {stock.code}: {e}")

        print(f"完成: {processed} 只已处理, {new_data} 只有效数据")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
