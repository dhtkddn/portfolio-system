"""품질 검사 + yfinance 백필 병합 스크립트."""
from __future__ import annotations

import logging

from sqlalchemy import text

from utils.db import SessionLocal

logger = logging.getLogger(__name__)

THRESHOLD = 0.98  # 결측 허용치 (open 컬럼 기준 98 %)

MERGE_SQL = """
INSERT INTO prices_merged (date, ticker, open, high, low, close, volume)
SELECT
    COALESCE(p.date, y.date)                               AS date,
    COALESCE(p.ticker, y.ticker)                           AS ticker,
    COALESCE(p.open , y.open )                             AS open,
    COALESCE(p.high , y.high )                             AS high,
    COALESCE(p.low  , y.low  )                             AS low,
    COALESCE(p.close, y.close)                             AS close,
    COALESCE(p.volume, y.volume)                           AS volume
FROM prices          p
FULL OUTER JOIN prices_yf y
  ON p.date = y.date AND p.ticker = y.ticker;
"""


def run() -> None:
    """1) 품질지표 계산 → 2) 필요 시 병합."""
    sess = SessionLocal()
    try:
        nulls = sess.execute(text("SELECT COUNT(*) FROM prices WHERE open IS NULL")).scalar_one()
        total = sess.execute(text("SELECT COUNT(*) FROM prices")).scalar_one()
        ratio = 1.0 if total == 0 else 1 - nulls / total

        logger.info("Price table coverage %.2f%%", ratio * 100)

        if ratio < THRESHOLD:
            logger.warning("Coverage below threshold %.2f%% → merge with yfinance", ratio * 100)
            sess.execute(text("TRUNCATE TABLE prices_merged"))
            sess.execute(text(MERGE_SQL))
            sess.commit()
            logger.info("Merged into prices_merged")

    finally:
        sess.close()


if __name__ == "__main__":
    run()