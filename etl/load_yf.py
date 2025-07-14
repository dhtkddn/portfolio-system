"""yfinance 백필(보조) OHLCV ETL 스크립트."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List

import tenacity
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert

from utils.db import SessionLocal
from db.models import PriceYf  # 예: models.Price

# ──────────────────────────────────────────────────────────────────────────────
# 설정 & 로거
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
SEM = asyncio.Semaphore(5)  # 동시 요청 제한 (더 보수적으로)

# 기본 테스트용 매핑
DEFAULT_MAPPING = {
    "005930": "005930.KS",  # 삼성전자
    "000660": "000660.KS",  # SK하이닉스
    "035420": "035420.KS",  # 네이버
    "005380": "005380.KS",  # 현대차
    "051910": "051910.KS",  # LG화학
}


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼: yfinance 다운로드
# ──────────────────────────────────────────────────────────────────────────────
@tenacity.retry(
    wait=tenacity.wait_random_exponential(min=1, max=10),  # 더 짧은 대기 시간
    stop=tenacity.stop_after_attempt(3),  # 재시도 횟수 줄임
    reraise=True,
)
def _download_yf_sync(ticker: str, start: str, end: str):
    """동기 yfinance 다운로드 (retry wrapper)."""
    try:
        logger.info(f"📈 Downloading {ticker} from {start} to {end}")
        return yf.download(ticker, start=start, end=end, progress=False, threads=False)
    except Exception as e:
        logger.warning(f"⚠️ Error downloading {ticker}: {e}")
        raise


async def _fetch_yf(ticker: str, start: str, end: str):
    """비동기로 yfinance 다운로드."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _download_yf_sync, ticker, start, end)


# ──────────────────────────────────────────────────────────────────────────────
# 동기 버전 (더 안정적)
# ──────────────────────────────────────────────────────────────────────────────
def _fetch_yf_sync(ticker: str, start: str, end: str):
    """동기 버전 yfinance 다운로드."""
    try:
        logger.info(f"📈 Fetching {ticker}...")
        df = _download_yf_sync(ticker, start, end)
        
        if df.empty:
            logger.warning(f"⚠️ No data for {ticker}")
            return None
            
        df = (
            df.reset_index()
            .rename(
                columns={
                    "Date": "date",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )
            [["date", "open", "high", "low", "close", "volume"]]
        )
        
        logger.info(f"✅ Got {len(df)} rows for {ticker}")
        return df
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch {ticker}: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────────────────────────────────────────
async def _worker(yf_ticker: str, kr_ticker: str, start: str, end: str):
    """단일 ticker 비동기 작업."""
    async with SEM:
        try:
            logger.debug("yfinance fetch %s", yf_ticker)
            df = await _fetch_yf(yf_ticker, start, end)
            
            if df is None or df.empty:
                return kr_ticker, None
                
            df = (
                df.reset_index()
                .rename(
                    columns={
                        "Date": "date",
                        "Open": "open",
                        "High": "high",
                        "Low": "low",
                        "Close": "close",
                        "Volume": "volume",
                    }
                )
                [["date", "open", "high", "low", "close", "volume"]]
            )
            df["ticker"] = kr_ticker  # 내부 DB용 ticker(KRX 코드)로 치환
            return kr_ticker, df
            
        except Exception as e:
            logger.error(f"❌ Worker error for {yf_ticker}: {e}")
            return kr_ticker, None


def run_sync(
    start: str | None = None,
    end: str | None = None,
    mapping_file: str = "ticker_map.json",
    quick_test: bool = True,
) -> None:
    """
    동기 버전 yfinance 데이터 수집 (더 안정적).
    
    Args:
        start/end: YYYY-MM-DD format (default: 최근 30일 for quick_test, 1년 for full)
        mapping_file: KRX코드 → yfinance코드 JSON 파일
        quick_test: True면 최근 30일만 수집
    """
    # 기본값 설정
    end = end or datetime.today().strftime("%Y-%m-%d")
    
    if quick_test:
        start = start or (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        logger.info("🚀 Quick test mode: 최근 30일")
    else:
        start = start or (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")
        logger.info("📊 Full mode: 최근 1년")

    logger.info(f"📅 Date range: {start} ~ {end}")

    # 매핑 파일 로드
    try:
        if os.path.exists(mapping_file):
            with open(mapping_file, "r", encoding="utf-8") as f:
                mapping = json.load(f)
        else:
            logger.warning(f"⚠️ {mapping_file} not found, using default mapping")
            mapping = DEFAULT_MAPPING
    except Exception as e:
        logger.error(f"❌ Error loading mapping file: {e}")
        logger.info("🔄 Using default mapping")
        mapping = DEFAULT_MAPPING

    logger.info(f"📈 Processing {len(mapping)} tickers: {list(mapping.keys())}")

    session = SessionLocal()
    upsert_rows = 0
    successful_tickers = 0
    
    try:
        for i, (kr_ticker, yf_ticker) in enumerate(mapping.items(), 1):
            logger.info(f"⏳ [{i}/{len(mapping)}] Processing {kr_ticker} → {yf_ticker}")
            
            df = _fetch_yf_sync(yf_ticker, start, end)
            
            if df is None or df.empty:
                logger.warning(f"⚠️ Skipping {kr_ticker} (no data)")
                continue

            # 데이터베이스에 저장
            df["ticker"] = kr_ticker
            for _, row in df.iterrows():
                stmt = (
                    insert(PriceYf)  # yfinance 전용 테이블 사용
                    .values(**row.to_dict())
                    .on_conflict_do_update(
                        index_elements=["ticker", "date"],
                        set_=row.to_dict(),
                    )
                )
                session.execute(stmt)
            
            upsert_rows += len(df)
            successful_tickers += 1
            
            logger.info(f"✅ {kr_ticker}: {len(df)} rows saved")

        session.commit()
        logger.info(f"🎉 yfinance ETL 완료!")
        logger.info(f"📊 Successful: {successful_tickers}/{len(mapping)} tickers")
        logger.info(f"📝 Upserted: {upsert_rows} rows")

    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        session.rollback()
    finally:
        session.close()


async def run_async(
    start: str | None = None,
    end: str | None = None,
    mapping_file: str = "ticker_map.json",
):
    """
    비동기 버전 yfinance 데이터 수집 (원본).
    
    - start/end: YYYY-MM-DD format (default 지난 1년)
    - mapping_file: 'KRX코드 → yfinance코드' JSON
    """
    end = end or datetime.today().strftime("%Y-%m-%d")
    start = start or (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")

    # 매핑 파일 로드
    try:
        if os.path.exists(mapping_file):
            with open(mapping_file, "r", encoding="utf-8") as f:
                mapping = json.load(f)
        else:
            logger.warning(f"⚠️ {mapping_file} not found, using default mapping")
            mapping = DEFAULT_MAPPING
    except Exception as e:
        logger.error(f"❌ Error loading mapping file: {e}")
        mapping = DEFAULT_MAPPING

    tasks = [
        _worker(yf_ticker, kr_ticker, start, end)
        for kr_ticker, yf_ticker in mapping.items()
    ]

    results = dict(await asyncio.gather(*tasks))

    session = SessionLocal()
    upsert_rows = 0
    try:
        for kr_ticker, df in results.items():
            if df is None or df.empty:
                continue

            for _, row in df.iterrows():
                stmt = (
                    insert(models.PriceYf)  # type: ignore[attr-defined]
                    .values(**row.to_dict())
                    .on_conflict_do_update(
                        index_elements=["ticker", "date"],
                        set_=row.to_dict(),
                    )
                )
                session.execute(stmt)
            upsert_rows += len(df)

        session.commit()
        logger.info("yfinance ETL 완료 – upsert rows: %s", upsert_rows)

    finally:
        session.close()


def run_quick_test():
    """빠른 테스트 실행 (최근 30일, 동기 방식)."""
    logger.info("🔥 yfinance Quick Test Starting...")
    run_sync(quick_test=True)


def run_full():
    """전체 실행 (최근 1년, 동기 방식)."""
    logger.info("🌟 yfinance Full Mode Starting...")
    run_sync(quick_test=False)


# 하위 호환성을 위한 기본 함수
async def run(
    start: str | None = None,
    end: str | None = None,
    mapping_file: str = "ticker_map.json",
):
    """기본 비동기 실행 함수 (하위 호환성)."""
    await run_async(start, end, mapping_file)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "quick":
            run_quick_test()
        elif mode == "full":
            run_full()
        elif mode == "async":
            asyncio.run(run())
        else:
            print("Usage: python load_yf.py [quick|full|async]")
            print("  quick: 최근 30일, 동기 방식")
            print("  full:  최근 1년, 동기 방식") 
            print("  async: 최근 1년, 비동기 방식")
    else:
        # 기본값: 빠른 테스트 (동기 방식)
        run_quick_test()