"""KRX 일별 OHLCV ETL 스크립트."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List

import pandas as pd
from pykrx import stock
from sqlalchemy.dialects.postgresql import insert

from utils.db import SessionLocal
from db.models import Price# models.Price 등

# ──────────────────────────────────────────────────────────────────────────────
# 로그 설정
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COL_MAP = {
    "날짜": "date",
    "시가": "open",
    "고가": "high",
    "저가": "low",
    "종가": "close",
    "거래량": "volume",
}

# 빠른 테스트용 기본 종목 (대형주)
DEFAULT_TEST_TICKERS = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035420",  # 네이버
    "005380",  # 현대차
    "051910",  # LG화학
]


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────────────────────────────────────
def _fetch_ohlcv(ticker: str, start: str, end: str) -> pd.DataFrame:
    """pykrx → DataFrame (ticker, date, open, high, low, close, volume)."""
    try:
        df = stock.get_market_ohlcv_by_date(start, end, ticker)
        if df.empty:
            logger.debug(f"No data for ticker: {ticker}")
            return df
        df = df.reset_index().rename(columns=COL_MAP)
        df["ticker"] = ticker
        return df[["ticker", *COL_MAP.values()]]
    except Exception as e:
        logger.warning(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()


def _get_sample_tickers(markets: List[str], max_tickers: int = 20) -> List[str]:
    """시장별로 샘플 종목만 가져오기 (테스트용)."""
    all_tickers = []
    
    for market in markets:
        if market == "TEST":
            # 테스트용 미리 정의된 종목들
            return DEFAULT_TEST_TICKERS
        elif market == "ALL":
            # 전체 시장에서 샘플만
            kospi_tickers = stock.get_market_ticker_list("KOSPI")[:10]
            kosdaq_tickers = stock.get_market_ticker_list("KOSDAQ")[:10]
            all_tickers.extend(kospi_tickers + kosdaq_tickers)
        else:
            # 특정 시장에서 샘플만
            market_tickers = stock.get_market_ticker_list(market)[:max_tickers]
            all_tickers.extend(market_tickers)
    
    return list(set(all_tickers))  # 중복 제거


# ──────────────────────────────────────────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────────────────────────────────────────
def run(
    start: str | None = None,
    end: str | None = None,
    markets: List[str] | None = None,
    quick_test: bool = True,  # 빠른 테스트 모드 추가
    max_tickers: int = 10,    # 최대 종목 수 제한
) -> None:
    """
    지정 구간의 일별 OHLCV를 수집한 뒤 Price 테이블에 upsert.

    - start/end: YYYYMMDD (default = 최근 30일 for quick_test, 최근 5년 for full)
    - markets: ["KOSPI", "KOSDAQ", "KONEX", "TEST", "ALL"] 등
    - quick_test: True면 최근 30일 + 제한된 종목수로 테스트
    - max_tickers: quick_test 모드에서 최대 종목 수
    """
    # 기본값 설정
    end = end or datetime.today().strftime("%Y%m%d")
    
    if quick_test:
        # 빠른 테스트: 최근 30일만
        start = start or (datetime.today() - timedelta(days=30)).strftime("%Y%m%d")
        markets = markets or ["TEST"]  # 테스트용 종목들
        logger.info("🚀 Quick test mode: 최근 30일, 제한된 종목수")
    else:
        # 전체 모드: 최근 5년
        start = start or (datetime.today() - timedelta(days=365 * 5)).strftime("%Y%m%d")
        markets = markets or ["ALL"]
        logger.info("📊 Full mode: 최근 5년, 전체 종목")

    logger.info(f"📅 Data range: {start} ~ {end}")
    logger.info(f"🏢 Markets: {markets}")

    # 종목 리스트 가져오기
    if quick_test or any(m in ["TEST", "ALL"] for m in markets):
        tickers = _get_sample_tickers(markets, max_tickers)
    else:
        tickers = []
        for m in markets:
            tickers += stock.get_market_ticker_list(market=m)

    logger.info(f"📈 Processing {len(tickers)} tickers: {tickers[:5]}...")

    session = SessionLocal()
    inserted_rows = 0
    processed_tickers = 0
    
    try:
        for i, tk in enumerate(tickers, 1):
            try:
                logger.info(f"⏳ [{i}/{len(tickers)}] Processing {tk}...")
                
                df = _fetch_ohlcv(tk, start, end)
                if df.empty:
                    logger.debug(f"No data for {tk}")
                    continue

                # 행 단위 upsert (ticker, date) ON CONFLICT DO UPDATE
                for _, row in df.iterrows():
                    stmt = (
                        insert(Price)  # type: ignore[attr-defined]
                        .values(**row.to_dict())
                        .on_conflict_do_update(
                            index_elements=["ticker", "date"],
                            set_=row.to_dict(),
                        )
                    )
                    session.execute(stmt)
                
                inserted_rows += len(df)
                processed_tickers += 1
                
                # 진행 상황 표시
                if i % 5 == 0 or i == len(tickers):
                    logger.info(f"✅ Progress: {i}/{len(tickers)} tickers, {inserted_rows} rows")
                    
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"❌ Skip {tk}: {exc}")

        session.commit()
        logger.info(f"🎉 KRX ETL 완료!")
        logger.info(f"📊 Processed: {processed_tickers}/{len(tickers)} tickers")
        logger.info(f"📝 Upserted: {inserted_rows} rows")

    finally:
        session.close()


def run_quick_test():
    """빠른 테스트 실행 (최근 30일, 5개 대형주만)."""
    logger.info("🔥 Quick Test Mode Starting...")
    run(
        quick_test=True,
        max_tickers=5,
        markets=["TEST"]
    )


def run_sample_test():
    """샘플 테스트 실행 (최근 90일, 각 시장에서 10개씩)."""
    logger.info("📊 Sample Test Mode Starting...")
    start = (datetime.today() - timedelta(days=90)).strftime("%Y%m%d")
    run(
        start=start,
        quick_test=True,
        max_tickers=10,
        markets=["KOSPI", "KOSDAQ"]
    )


def run_full():
    """전체 실행 (최근 5년, 모든 종목)."""
    logger.info("🌟 Full Mode Starting...")
    run(quick_test=False)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "quick":
            run_quick_test()
        elif mode == "sample":
            run_sample_test()
        elif mode == "full":
            run_full()
        else:
            print("Usage: python load_pykrx.py [quick|sample|full]")
            print("  quick:  최근 30일, 5개 대형주")
            print("  sample: 최근 90일, 각 시장 10개씩")
            print("  full:   최근 5년, 전체 종목")
    else:
        # 기본값: 빠른 테스트
        run_quick_test()