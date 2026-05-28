#!/usr/bin/env python3
"""为50只成分股补充行业分类信息"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import Stock

# 50只沪深300样本股的行业分类 (申万一级)
INDUSTRIES = {
    "000001.SZ": "银行", "000002.SZ": "房地产", "000063.SZ": "通信",
    "000100.SZ": "电子", "000333.SZ": "家用电器", "000338.SZ": "机械设备",
    "000425.SZ": "机械设备", "000568.SZ": "食品饮料", "000625.SZ": "汽车",
    "000651.SZ": "家用电器", "000725.SZ": "电子", "000776.SZ": "非银金融",
    "000858.SZ": "食品饮料", "002142.SZ": "银行", "002230.SZ": "计算机",
    "002352.SZ": "交通运输", "002415.SZ": "计算机", "002459.SZ": "电力设备",
    "002594.SZ": "汽车", "002714.SZ": "农林牧渔", "300059.SZ": "非银金融",
    "300274.SZ": "电力设备", "300308.SZ": "通信", "300498.SZ": "农林牧渔",
    "300750.SZ": "电力设备", "600000.SH": "银行", "600009.SH": "交通运输",
    "600016.SH": "银行", "600028.SH": "石油石化", "600030.SH": "非银金融",
    "600036.SH": "银行", "600048.SH": "房地产", "600050.SH": "通信",
    "600085.SH": "医药生物", "600104.SH": "汽车", "600276.SH": "医药生物",
    "600309.SH": "基础化工", "600406.SH": "电力设备", "600436.SH": "医药生物",
    "600438.SH": "电力设备", "600519.SH": "食品饮料", "600585.SH": "建筑材料",
    "600809.SH": "食品饮料", "600887.SH": "食品饮料", "600900.SH": "公用事业",
    "601012.SH": "电力设备", "601088.SH": "煤炭", "601166.SH": "银行",
    "601318.SH": "非银金融", "601398.SH": "银行",
}


def main():
    engine = create_engine(settings.DATABASE_URL_SYNC)
    with Session(engine) as session:
        for code, industry in INDUSTRIES.items():
            stock = session.execute(select(Stock).where(Stock.code == code)).scalar_one_or_none()
            if stock:
                stock.industry = industry
                print(f"  {code} {stock.name} → {industry}")
        session.commit()
    engine.dispose()
    print(f"\nUpdated {len(INDUSTRIES)} stocks")


if __name__ == "__main__":
    main()
